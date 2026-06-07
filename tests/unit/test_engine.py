"""T007 + T015 — Redesigner engine: typed dispatch, deepcopy isolation, invariants, stamping.

Maps to contracts/redesigner_api.md (RD-1..RD-8) and spec FR-008/FR-012/FR-014.
"""

import copy

import pandas as pd
import pytest

from intuitiveness.complexity import (
    ComplexityLevel,
    Level1Dataset,
    Level2Dataset,
)
from intuitiveness.redesign.engine import Redesigner, TransitionError
from intuitiveness.redesign.params import (
    L1toL0Params,
    L1toL2Params,
    L2toL1Params,
    L2toL3Params,
)


def _l2():
    return Level2Dataset(pd.DataFrame({"score": [10, 20, 30], "cat": ["a", "b", "a"]}), name="scores")


# --- typed dispatch / params validation (RD via FR-009) --------------------- #

def test_wrong_params_type_for_edge_raises():
    with pytest.raises(TransitionError):
        Redesigner.reduce_complexity(_l2(), ComplexityLevel.LEVEL_1, L1toL0Params(aggregation="sum"))


def test_l2_to_l1_extracts_column():
    l1 = Redesigner.reduce_complexity(_l2(), ComplexityLevel.LEVEL_1, L2toL1Params(column="score"))
    assert isinstance(l1, Level1Dataset)
    assert list(l1.get_data()) == [10, 20, 30]


# --- RD-1: returns new object, does not mutate input ------------------------ #

def test_does_not_mutate_input():
    l2 = _l2()
    before_cols = list(l2.get_data().columns)
    Redesigner.reduce_complexity(l2, ComplexityLevel.LEVEL_1, L2toL1Params(column="score"))
    assert list(l2.get_data().columns) == before_cols


# --- RD-2 / RD-3: lineage stamped + deepcopy isolation ---------------------- #

def test_lineage_grows_by_one_step():
    l2 = _l2()
    assert len(l2.lineage.operations) == 0
    l1 = Redesigner.reduce_complexity(l2, ComplexityLevel.LEVEL_1, L2toL1Params(column="score"))
    assert len(l1.lineage.operations) == 1
    step = l1.lineage.operations[-1]
    assert step.operation_type == "L2→L1"
    assert step.parameters["column"] == "score"
    # optional integrity fingerprints populated
    assert step.source_data_hash and step.result_data_hash


def test_child_lineage_isolated_from_parent():
    l2 = _l2()
    l1 = Redesigner.reduce_complexity(l2, ComplexityLevel.LEVEL_1, L2toL1Params(column="score"))
    # mutating parent lineage afterwards must not touch child (deepcopy at chokepoint)
    l2.lineage.add_operation(
        operation_type="noise",
        input_level=ComplexityLevel.LEVEL_2,
        output_level=ComplexityLevel.LEVEL_1,
    )
    assert len(l1.lineage.operations) == 1


def test_full_chain_accumulates_across_descent():
    l2 = _l2()
    l1 = Redesigner.reduce_complexity(l2, ComplexityLevel.LEVEL_1, L2toL1Params(column="score"))
    l0 = Redesigner.reduce_complexity(l1, ComplexityLevel.LEVEL_0, L1toL0Params(aggregation="sum"))
    ops = [o.operation_type for o in l0.lineage.operations]
    assert ops == ["L2→L1", "L1→L0"]
    assert l0.get_data() == 60


# --- RD-4: adjacency rejection --------------------------------------------- #

def test_non_adjacent_descent_rejected():
    with pytest.raises(TransitionError):
        Redesigner.reduce_complexity(_l2(), ComplexityLevel.LEVEL_0, L2toL1Params(column="score"))


def test_ascent_to_l4_structurally_rejected():
    l2 = _l2()
    with pytest.raises(TransitionError):
        Redesigner.increase_complexity(l2, ComplexityLevel.LEVEL_4, L2toL3Params())


# --- RD-6: ascent row-count preservation ----------------------------------- #

def test_ascent_l1_to_l2_preserves_row_count():
    l1 = Level1Dataset(pd.Series([1, 2, 3], name="v"))
    l2 = Redesigner.increase_complexity(l1, ComplexityLevel.LEVEL_2, L1toL2Params(dimensions=["region"]))
    assert l2.get_data().shape[0] == 3  # rows preserved, dimension added as column
    assert "region" in l2.get_data().columns


def test_ascent_l1_to_l2_lineage_recorded():
    l1 = Level1Dataset(pd.Series([1, 2, 3], name="v"))
    l2 = Redesigner.increase_complexity(l1, ComplexityLevel.LEVEL_2, L1toL2Params(dimensions=["region"]))
    assert l2.lineage.operations[-1].operation_type == "L1→L2"
    assert l2.lineage.operations[-1].row_count_before == l2.lineage.operations[-1].row_count_after
