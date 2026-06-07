"""T021 — US1 Independent Test: descend via the engine, assert full lineage chain + summaries.

Spec 015 US1 / FR-001 / SC-001 / SC-002.
"""

import pandas as pd

from intuitiveness.complexity import ComplexityLevel, Level2Dataset
from intuitiveness.redesign.engine import Redesigner
from intuitiveness.redesign.params import L2toL1Params, L1toL0Params


def test_descent_produces_full_lineage_and_summaries():
    l2 = Level2Dataset(
        pd.DataFrame({"score": [80, 90, 100], "school": ["A", "B", "C"]}),
        name="school_scores",
    )

    l1 = Redesigner.reduce_complexity(l2, ComplexityLevel.LEVEL_1, L2toL1Params(column="score"))
    l0 = Redesigner.reduce_complexity(l1, ComplexityLevel.LEVEL_0, L1toL0Params(aggregation="mean"))

    # Full chain from origin is present on the deepest artifact (FR-001/SC-001)
    chain = [op.operation_type for op in l0.lineage.operations]
    assert chain == ["L2→L1", "L1→L0"]

    # Each step recorded its decision parameters
    assert l0.lineage.operations[0].parameters["column"] == "score"
    assert l0.lineage.operations[1].parameters["aggregation"] == "mean"

    # Self-summaries are level-appropriate (SC-002)
    assert l1.summary() == {"level": 1, "level_name": "LEVEL_1", "type": "vector", "length": 3}
    assert l0.summary()["type"] == "datum"
    assert l0.summary()["value"] == 90  # mean of 80,90,100


def test_intermediate_artifact_also_carries_its_own_history():
    l2 = Level2Dataset(pd.DataFrame({"v": [1, 2, 3, 4]}), name="t")
    l1 = Redesigner.reduce_complexity(l2, ComplexityLevel.LEVEL_1, L2toL1Params(column="v"))
    # L1 (an intermediate level) is self-describing with its own one-step history
    assert [op.operation_type for op in l1.lineage.operations] == ["L2→L1"]
    assert l1.summary()["length"] == 4
