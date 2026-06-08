"""T034 + T037 + T038 — durable full-fidelity persistence.

- DurableBackend writes/reads versioned records to files (T034).
- NavigationTreeNode.to_dict(include_payload=True)/from_dict round-trips a node
  with its data payload + lineage (T037).
- NavigationSession.save()/load() round-trips a whole session through the
  durable backend, package-free (T038), preserving branches and current data.
"""

import networkx as nx
import pandas as pd
import pytest

from intuitiveness.complexity import ComplexityLevel, Level2Dataset, Level4Dataset
from intuitiveness.navigation.session import NavigationSession
from intuitiveness.navigation.tree import NavigationTree, NavigationTreeNode
from intuitiveness.navigation.state import NavigationAction
from intuitiveness.persistence.durable_backend import (
    DurableBackend, FileDurableBackend, get_durable_backend,
)
from intuitiveness.redesign.engine import Redesigner
from intuitiveness.redesign.params import L2toL1Params


# --- T034: DurableBackend ----------------------------------------------------- #

def test_durable_backend_round_trips_a_record(tmp_path):
    backend = DurableBackend(root=tmp_path)
    record = {"schema_version": "1.0.0", "metadata": {"root_id": "r"}, "nodes": {}}

    location = backend.save_record("sess-1", record)
    assert backend.exists("sess-1")
    assert backend.load_record("sess-1") == record
    assert backend.load_record(location) == record           # by full path too
    assert "sess-1" in backend.list_session_ids()

    assert backend.delete("sess-1") is True
    assert backend.exists("sess-1") is False


def test_durable_backend_missing_raises(tmp_path):
    backend = DurableBackend(root=tmp_path)
    with pytest.raises(FileNotFoundError):
        backend.load_record("nope")


def test_factory_falls_back_to_files_without_database_url(monkeypatch):
    # No DATABASE_URL / POSTGRES_URL configured → file backend (offline-safe).
    for var in ("SESSION_DATABASE_URL", "DATABASE_URL", "POSTGRES_URL"):
        monkeypatch.delenv(var, raising=False)
    backend = get_durable_backend()
    assert isinstance(backend, FileDurableBackend)


def test_file_backend_session_index(tmp_path):
    backend = FileDurableBackend(root=tmp_path)
    backend.save_record("s1", {"metadata": {"title": "Schools run"}, "nodes": {}})
    backend.save_record("s2", {"metadata": {}, "nodes": {}})
    index = dict(backend.list_sessions())
    assert index["s1"] == "Schools run"
    assert index["s2"] == "s2"  # title falls back to id


# --- T037: node full-fidelity round-trip -------------------------------------- #

def test_node_to_dict_lightweight_excludes_payload():
    root = Level2Dataset(pd.DataFrame({"score": [1, 2, 3]}), name="s")
    tree = NavigationTree(root)
    light = tree.current_node.to_dict()
    assert "payload" not in light and "payload_kind" not in light


def test_node_full_fidelity_round_trip():
    root = Level2Dataset(pd.DataFrame({"score": [1, 2, 3]}), name="s")
    tree = NavigationTree(root)
    child = Redesigner.reduce_complexity(root, ComplexityLevel.LEVEL_1, L2toL1Params(column="score"))
    cid = tree.branch(NavigationAction.DESCEND, child, edge_decision_payload={"column": "score"})

    full = tree.get_node(cid).to_dict(include_payload=True)
    assert full["payload_kind"] == "vector"

    restored = NavigationTreeNode.from_dict(full)
    assert restored.level == ComplexityLevel.LEVEL_1
    assert list(restored.dataset_snapshot.get_data()) == [1, 2, 3]
    # lineage survives the round-trip
    assert restored.dataset_snapshot.lineage.operations[-1].parameters["column"] == "score"


# --- T038: whole-session save/load through the durable backend ---------------- #

def _build_graph(sources: dict) -> nx.Graph:
    df = sources["schools"]
    g = nx.DiGraph()
    for _, row in df.iterrows():
        g.add_node(row["school"], node_type="school", score=row["score"])
        g.add_node(row["category"], node_type="category")
        g.add_edge(row["school"], row["category"])
    return g


def _query_table(graph: nx.Graph) -> pd.DataFrame:
    rows = [{"school": n, "score": a.get("score")}
            for n, a in graph.nodes(data=True) if a.get("node_type") == "school"]
    return pd.DataFrame(rows)


def _l4():
    schools = pd.DataFrame({
        "school": ["A", "B", "C", "D"],
        "score": [80, 90, 70, 100],
        "category": ["down town", "country side", "down town", "country side"],
    })
    return Level4Dataset({"schools": schools})


def test_session_save_load_round_trip(tmp_path):
    session = NavigationSession(_l4())
    session.descend(builder_func=_build_graph)   # L4→L3
    session.descend(query_func=_query_table)     # L3→L2
    session.descend(column="score")              # L2→L1
    original_node_count = len(session.navigation_tree)
    original_session_id = session.session_id

    location = session.save(str(tmp_path / "session.json"))

    restored = NavigationSession.load(location)
    assert restored.session_id == original_session_id
    assert len(restored.navigation_tree) == original_node_count
    assert restored.current_level == ComplexityLevel.LEVEL_1
    assert list(restored.current_dataset.get_data()) == [80, 90, 70, 100]


def test_session_load_unknown_location_raises():
    from intuitiveness.navigation.exceptions import SessionNotFoundError
    with pytest.raises(SessionNotFoundError):
        NavigationSession.load("/tmp/definitely-not-a-real-session-xyz")
