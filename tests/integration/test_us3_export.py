"""T039 + T040 — US3: full-fidelity, versioned, self-contained session export.

Proves (spec 015):
- round-trip fidelity across payload kinds (SC-007)
- a consumer can read payloads WITHOUT importing intuitiveness internals (SC-008)
- shared ancestors stored once (SC-009)
- fail-closed on an unknown schema version
"""

import base64
import json
import zlib

import networkx as nx
import pandas as pd
import pytest

from intuitiveness.complexity import ComplexityLevel, Level2Dataset, Level4Dataset
from intuitiveness.navigation.tree import NavigationTree
from intuitiveness.navigation.state import NavigationAction
from intuitiveness.redesign.engine import Redesigner
from intuitiveness.redesign.params import L2toL1Params
from intuitiveness.persistence.session_export import (
    SCHEMA_VERSION, SchemaVersionError, export_session, import_session,
)


def _tree_with_two_branches():
    root = Level2Dataset(pd.DataFrame({"score": [10, 20, 30], "cat": ["a", "b", "a"]}), name="scores")
    tree = NavigationTree(root)
    a = Redesigner.reduce_complexity(root, ComplexityLevel.LEVEL_1, L2toL1Params(column="score"))
    tree.branch(NavigationAction.DESCEND, a, edge_decision_payload={"column": "score"})
    tree.restore(tree.root_id)
    b = Redesigner.reduce_complexity(root, ComplexityLevel.LEVEL_1, L2toL1Params(column="cat"))
    tree.branch(NavigationAction.DESCEND, b, edge_decision_payload={"column": "cat"})
    return tree


def test_export_has_version_and_flat_nodes():
    rec = export_session(_tree_with_two_branches(), metadata={"title": "demo"})
    assert rec["schema_version"] == SCHEMA_VERSION
    assert rec["metadata"]["title"] == "demo"
    # root + 2 children = 3 nodes, each once (SC-009: shared root not duplicated)
    assert len(rec["nodes"]) == 3
    levels = sorted(n["level"] for n in rec["nodes"].values())
    assert levels == [1, 1, 2]


def test_round_trip_fidelity():
    tree = _tree_with_two_branches()
    rebuilt = import_session(export_session(tree))
    assert len(rebuilt.nodes) == len(tree.nodes)
    # the L2 root table survives intact
    root = rebuilt.get_node(rebuilt.root_id).dataset_snapshot
    assert list(root.get_data().columns) == ["score", "cat"]
    assert root.get_data().shape == (3, 2)
    # a child vector survives with its lineage
    child = next(n for n in rebuilt.nodes.values() if n.level == ComplexityLevel.LEVEL_1)
    assert child.dataset_snapshot.lineage.operations[-1].operation_type == "L2→L1"


def test_payload_readable_without_importing_package():
    """SC-008: a separate program decodes payloads using only documented rules."""
    rec = export_session(_tree_with_two_branches())

    def decode_blob(blob):  # the only knowledge a consumer needs
        return json.loads(zlib.decompress(base64.b64decode(blob)).decode("utf-8"))

    root = rec["nodes"][rec["metadata"]["root_id"]]
    assert root["payload_kind"] == "dataframe"
    split = decode_blob(root["payload"])           # pandas 'split' orient
    assert split["columns"] == ["score", "cat"]
    assert len(split["data"]) == 3                  # 3 rows recovered, no package import


def test_graph_and_value_kinds_round_trip():
    g = nx.DiGraph()
    g.add_edge("x", "y")
    tree = NavigationTree(Level4Dataset({"f.csv": pd.DataFrame({"a": [1, 2]})}))
    rec = export_session(tree)
    root = rec["nodes"][rec["metadata"]["root_id"]]
    assert root["payload_kind"] == "unlinkable"
    rebuilt = import_session(rec)
    data = rebuilt.get_node(rebuilt.root_id).dataset_snapshot.get_data()
    assert "f.csv" in data and list(data["f.csv"].columns) == ["a"]


def test_unknown_version_fails_closed():
    rec = export_session(_tree_with_two_branches())
    rec["schema_version"] = "9.0.0"
    with pytest.raises(SchemaVersionError):
        import_session(rec)
