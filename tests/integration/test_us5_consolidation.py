"""T044 — US5 equivalence: the new engine is a faithful drop-in for legacy Redesigner.

Proves the spec-015 engine produces the SAME data outcomes as the legacy
``redesign_legacy.Redesigner`` on the deterministic edges (L2→L1, L1→L0),
de-risking the eventual cutover + deletion of legacy (T041/T042).

The graph edges (L4→L3, L3→L2) are intentionally NOT compared here: the legacy
contract injects callables from the UI forms, which the new engine deliberately
replaces — that cutover is gated on the full Playwright E2E suite (SC-011).
"""

import pandas as pd

from intuitiveness.complexity import ComplexityLevel, Level1Dataset, Level2Dataset
from intuitiveness.redesign.engine import Redesigner as Engine
from intuitiveness.redesign.params import L1toL0Params, L2toL1Params
from intuitiveness.redesign_legacy import Redesigner as Legacy


def test_l2_to_l1_equivalent_to_legacy():
    df = pd.DataFrame({"score": [10, 20, 30], "cat": ["a", "b", "a"]})

    legacy_out = Legacy.reduce_complexity(Level2Dataset(df.copy()), ComplexityLevel.LEVEL_1, column="score")
    engine_out = Engine.reduce_complexity(Level2Dataset(df.copy()), ComplexityLevel.LEVEL_1, L2toL1Params(column="score"))

    assert list(engine_out.get_data()) == list(legacy_out.get_data())
    assert engine_out.complexity_level == legacy_out.complexity_level == ComplexityLevel.LEVEL_1


def test_l1_to_l0_equivalent_to_legacy():
    series = pd.Series([10, 20, 30], name="score")

    legacy_out = Legacy.reduce_complexity(Level1Dataset(series.copy(), name="score"),
                                          ComplexityLevel.LEVEL_0, aggregation="sum")
    engine_out = Engine.reduce_complexity(Level1Dataset(series.copy(), name="score"),
                                          ComplexityLevel.LEVEL_0, L1toL0Params(aggregation="sum"))

    assert engine_out.get_data() == legacy_out.get_data() == 60


def test_engine_adds_provenance_legacy_lacks():
    """The engine is not just equivalent — it additionally stamps full lineage."""
    series = pd.Series([1, 2, 3], name="v")
    engine_out = Engine.reduce_complexity(Level1Dataset(series, name="v"),
                                          ComplexityLevel.LEVEL_0, L1toL0Params(aggregation="sum"))
    assert engine_out.lineage.operations[-1].operation_type == "L1→L0"
    # legacy L0 carries only parent_data/aggregation_method, no lineage chain
    legacy_out = Legacy.reduce_complexity(Level1Dataset(series, name="v"),
                                          ComplexityLevel.LEVEL_0, aggregation="sum")
    assert len(engine_out.lineage.operations) == 1
    assert len(legacy_out.lineage.operations) == 0  # lazily-empty for legacy-built datasets
