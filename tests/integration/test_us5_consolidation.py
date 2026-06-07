"""T044 — US5 consolidation: the single unified engine is the sole transition path.

The legacy redesign_legacy.Redesigner has been removed; these tests assert the
engine produces the correct outcomes and stamps lineage (the behavior the old
equivalence comparison validated during migration is now confirmed live + here).
"""

import pandas as pd

from intuitiveness.complexity import ComplexityLevel, Level1Dataset, Level2Dataset
from intuitiveness.redesign.engine import Redesigner
from intuitiveness.redesign.params import L1toL0Params, L2toL1Params


def test_l2_to_l1_extracts_column():
    df = pd.DataFrame({"score": [10, 20, 30], "cat": ["a", "b", "a"]})
    out = Redesigner.reduce_complexity(Level2Dataset(df), ComplexityLevel.LEVEL_1, L2toL1Params(column="score"))
    assert list(out.get_data()) == [10, 20, 30]
    assert out.complexity_level == ComplexityLevel.LEVEL_1


def test_l1_to_l0_aggregates():
    series = pd.Series([10, 20, 30], name="score")
    out = Redesigner.reduce_complexity(Level1Dataset(series, name="score"),
                                       ComplexityLevel.LEVEL_0, L1toL0Params(aggregation="sum"))
    assert out.get_data() == 60


def test_engine_stamps_full_lineage():
    series = pd.Series([1, 2, 3], name="v")
    out = Redesigner.reduce_complexity(Level1Dataset(series, name="v"),
                                       ComplexityLevel.LEVEL_0, L1toL0Params(aggregation="sum"))
    assert len(out.lineage.operations) == 1
    assert out.lineage.operations[-1].operation_type == "L1→L0"
