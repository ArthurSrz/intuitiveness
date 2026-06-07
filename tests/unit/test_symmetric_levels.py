"""T020 — all 5 levels symmetric: uniform lineage shape + correct summary() (FR-001..FR-003, SC-001/SC-002)."""

import networkx as nx
import pandas as pd

from intuitiveness.complexity import (
    ComplexityLevel,
    Level0Dataset,
    Level1Dataset,
    Level2Dataset,
    Level3Dataset,
    Level4Dataset,
)
from intuitiveness.redesign.lineage import DataLineage


def _all_levels():
    g = nx.DiGraph()
    g.add_edge("a", "b")
    return [
        Level4Dataset({"f1.csv": pd.DataFrame({"x": [1]}), "f2.csv": pd.DataFrame({"y": [2]})}),
        Level3Dataset(g),
        Level2Dataset(pd.DataFrame({"score": [1, 2, 3], "cat": ["a", "b", "a"]})),
        Level1Dataset(pd.Series([1, 2, 3], name="score")),
        Level0Dataset(42, description="avg"),
    ]


def test_every_level_has_lineage_of_uniform_type():
    for ds in _all_levels():
        assert isinstance(ds.lineage, DataLineage)  # FR-002 uniform shape
        assert hasattr(ds.lineage, "get_history")


def test_summary_always_includes_level_keys():
    for ds in _all_levels():
        s = ds.summary()
        assert s["level"] == ds.complexity_level.value
        assert s["level_name"] == ds.complexity_level.name


def test_summary_is_level_appropriate():
    l4, l3, l2, l1, l0 = _all_levels()
    assert l4.summary()["type"] == "unlinkable" and l4.summary()["source_count"] == 2
    assert l3.summary()["type"] == "graph" and l3.summary()["node_count"] == 2 and l3.summary()["edge_count"] == 1
    assert l2.summary()["type"] == "dataframe" and l2.summary()["row_count"] == 3 and l2.summary()["columns"] == ["score", "cat"]
    assert l1.summary()["type"] == "vector" and l1.summary()["length"] == 3
    assert l0.summary()["type"] == "datum" and l0.summary()["value"] == 42


def test_l3_dataframe_payload_summary():
    l3 = Level3Dataset(pd.DataFrame({"a": [1, 2]}))
    s = l3.summary()
    assert s["type"] == "graph"
    assert s["row_count"] == 2


def test_lineage_is_independent_per_instance():
    a = Level0Dataset(1)
    b = Level0Dataset(2)
    a.lineage.metadata["k"] = "v"
    assert "k" not in b.lineage.metadata
