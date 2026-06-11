"""US1 acceptance over HTTP (spec 017, T013) — SC-001 + SC-002.

Drives a full L4→L0 descent + L0→L3 ascent through the REST API, asserts the
canonical L0 datum (55.0) and a schema-valid export, and proves statelessness:
every request is served by a fresh service over the shared store, so a mid-session
"restart" (a brand-new service instance) rehydrates from the durable record.
"""

from __future__ import annotations

from intuitiveness.persistence.session_export import import_session

from app.service import SessionService


def _descend(client, sid, body):
    r = client.post(f"/sessions/{sid}/descend", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _ascend(client, sid, body=None):
    r = client.post(f"/sessions/{sid}/ascend", json=body or {})
    assert r.status_code == 200, r.text
    return r.json()


def test_full_descent_ascent_cycle(client, store):
    # --- create at L4 ---------------------------------------------------- #
    r = client.post("/sessions", json={"source": "demo:school_scores"})
    assert r.status_code == 201, r.text
    state = r.json()
    sid = state["session_id"]
    assert state["current_level"] == 4

    # --- descend L4→L0 --------------------------------------------------- #
    assert _descend(client, sid, {"builder": "rows_as_nodes"})["current_level"] == 3
    assert _descend(client, sid, {"domains": ["high score", "low score"]})["current_level"] == 2
    assert _descend(client, sid, {"column": "value"})["current_level"] == 1
    l0 = _descend(client, sid, {"aggregation": "mean"})
    assert l0["current_level"] == 0
    # SC-001: the canonical datum.
    assert float(l0["summary"]["value"]) == 55.0

    # --- ascend L0→L3 (registry defaults + persisted parent vector) ------ #
    assert _ascend(client, sid)["current_level"] == 1
    assert _ascend(client, sid)["current_level"] == 2
    assert _ascend(client, sid)["current_level"] == 3

    # --- export is schema-valid + round-trips (SC-006) ------------------- #
    r = client.get(f"/sessions/{sid}/export")
    assert r.status_code == 200, r.text
    record = r.json()
    # spec-015 record shape: versioned, with a flat node map (see export_session).
    assert record["schema_version"].startswith("1.")
    assert "nodes" in record and record["nodes"], "export must carry the node map"
    # import_session must accept what the API exported (cross-service contract).
    tree = import_session(record)
    assert tree.current_id is not None


def test_statelessness_rehydrates(client, store):
    """SC-002: no in-memory session affinity — a fresh service sees the same state."""
    r = client.post("/sessions", json={"source": "demo:school_scores"})
    sid = r.json()["session_id"]
    _descend(client, sid, {"builder": "rows_as_nodes"})

    # Simulate a backend restart: a brand-new service over the same store.
    fresh = SessionService(backend=store)
    assert fresh.get(sid)["current_level"] == 3


def test_illegal_transition_is_409(client):
    """Ascending from L4 is illegal → engine NavigationError → 409."""
    r = client.post("/sessions", json={"source": "demo:school_scores"})
    sid = r.json()["session_id"]
    r = client.post(f"/sessions/{sid}/ascend", json={})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "illegal_transition"


def test_unknown_demo_is_422(client):
    r = client.post("/sessions", json={"source": "demo:does_not_exist"})
    assert r.status_code == 422, r.text


def test_unknown_session_is_404(client):
    r = client.get("/sessions/nope-nope-nope")
    assert r.status_code == 404, r.text
