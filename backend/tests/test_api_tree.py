"""US2 acceptance over HTTP (spec 017, T015) — branch / time-travel / prune.

From a partially-descended session: branch a different decision off an earlier
node (→ two branches), time-travel between them, prune the off-path branch, and
confirm pruning the current branch / root is rejected (409).
"""

from __future__ import annotations


def _node_ids(tree):
    return [n["id"] for n in tree["nodes"]]


def _bootstrap_to_l2(client):
    """Create a session and descend L4→L3→L2 so there's a branch point."""
    sid = client.post("/sessions", json={"source": "demo:school_scores"}).json()["session_id"]
    client.post(f"/sessions/{sid}/descend", json={"builder": "rows_as_nodes"})       # L3
    client.post(f"/sessions/{sid}/descend", json={"domains": ["high", "low"]})        # L2
    return sid


def test_branch_time_travel_prune(client):
    sid = _bootstrap_to_l2(client)

    tree = client.get(f"/sessions/{sid}/tree").json()
    root_id = tree["root_id"]
    l3_id = next(n["id"] for n in tree["nodes"] if n["level"] == 3)
    before = len(tree["nodes"])

    # Branch a *different* descent off the L3 node → a sibling L2 branch.
    r = client.post(f"/sessions/{sid}/branch-from", json={
        "node_id": l3_id,
        "action": "descend",
        "params": {"domains": ["country side", "down town"]},
    })
    assert r.status_code == 200, r.text

    tree = client.get(f"/sessions/{sid}/tree").json()
    assert len(tree["nodes"]) == before + 1, "branch should add exactly one node"
    # The L3 node now has two children (two L2 branches).
    l3 = next(n for n in tree["nodes"] if n["id"] == l3_id)
    assert len(l3["children_ids"]) == 2

    new_branch_current = tree["current_id"]

    # Time-travel back to the original L2 leaf (the first child of L3).
    original_l2 = l3["children_ids"][0]
    r = client.post(f"/sessions/{sid}/time-travel", json={"node_id": original_l2})
    assert r.status_code == 200, r.text
    assert client.get(f"/sessions/{sid}").json()["current_node_id"] == original_l2

    # Prune the OTHER (off-current) branch → removed.
    r = client.post(f"/sessions/{sid}/prune", json={"node_id": new_branch_current})
    assert r.status_code == 200, r.text
    assert r.json()["count"] >= 1
    assert new_branch_current not in _node_ids(client.get(f"/sessions/{sid}/tree").json())


def test_prune_root_rejected(client):
    sid = _bootstrap_to_l2(client)
    root_id = client.get(f"/sessions/{sid}/tree").json()["root_id"]
    r = client.post(f"/sessions/{sid}/prune", json={"node_id": root_id})
    assert r.status_code == 409, r.text


def test_prune_current_branch_rejected(client):
    sid = _bootstrap_to_l2(client)
    current = client.get(f"/sessions/{sid}").json()["current_node_id"]
    r = client.post(f"/sessions/{sid}/prune", json={"node_id": current})
    assert r.status_code == 409, r.text
