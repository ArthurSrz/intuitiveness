"""TDD spec for the add-source endpoint (plan 017-L4-multisource-ux).

Verifies that POST /sessions/{id}/add-source merges new CSV tables into an
existing L4 session without changing the session_id.
"""

from __future__ import annotations

import io
import pandas as pd
import pytest


# ---- helpers ----------------------------------------------------------------

def _upload(client, *csvs):
    """Create a session from one or more (name, content) CSV pairs via /upload."""
    files = [
        ("files", (name, io.BytesIO(content.encode()), "text/csv"))
        for name, content in csvs
    ]
    r = client.post("/sessions/upload", files=files)
    assert r.status_code == 201, r.text
    return r.json()


def _add_source(client, session_id, *csvs):
    """POST /sessions/{id}/add-source with one or more CSV files."""
    files = [
        ("files", (name, io.BytesIO(content.encode()), "text/csv"))
        for name, content in csvs
    ]
    r = client.post(f"/sessions/{session_id}/add-source", files=files)
    return r


# ---- tests ------------------------------------------------------------------

def test_add_source_increments_source_count(client, store):
    """Adding a CSV to an L4 session raises source_count by 1."""
    state = _upload(client, ("scores.csv", "school,score\nA,80\nB,70\n"))
    sid = state["session_id"]
    assert state["summary"].get("source_count", 1) == 1

    state2 = _add_source(client, sid, ("funding.csv", "org,amount\nX,5000\nY,3000\n")).json()
    assert state2["session_id"] == sid, "session_id must not change"
    assert state2["current_level"] == 4, "session must stay at L4"
    assert state2["summary"]["source_count"] == 2


def test_add_multiple_sources_at_once(client, store):
    """Multiple files can be added in a single add-source call."""
    state = _upload(client, ("a.csv", "x,y\n1,2\n"))
    sid = state["session_id"]

    r = _add_source(
        client,
        sid,
        ("b.csv", "p,q\n3,4\n"),
        ("c.csv", "m,n\n5,6\n"),
    )
    assert r.status_code == 200, r.text
    state2 = r.json()
    assert state2["summary"]["source_count"] == 3


def test_add_source_rejected_below_l4(client, store):
    """add-source is only valid at L4; once descent starts it must return 409."""
    state = _upload(client, ("scores.csv", "school,score\nA,80\nB,70\n"))
    sid = state["session_id"]

    # start descent
    r = client.post(f"/sessions/{sid}/descend", json={})
    assert r.status_code == 200, r.text

    r2 = _add_source(client, sid, ("extra.csv", "k,v\n1,2\n"))
    assert r2.status_code == 409, f"Expected 409 but got {r2.status_code}: {r2.text}"
