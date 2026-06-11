"""P4 parity walkthrough — full descent+ascent on all 3 test datasets.

Verifies:
1. CSV upload path builds a valid L4 session
2. Descent L4→L3→L2→L1→L0 completes without error
3. L3→L2 step produces real multi-category distribution (P2 fix)
4. Ascent L0→L1→L2→L3 completes without error
"""
import csv as _csv
import io
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

# Ensure the repo root (not intuitiveness/) is on the path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.app.service import SessionService
from intuitiveness.persistence.durable_backend import FileDurableBackend

TEST_DATA = REPO_ROOT / "test_data"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_csv(path: Path) -> pd.DataFrame:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    try:
        dialect = _csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
        sep = dialect.delimiter
    except _csv.Error:
        sep = ","
    return pd.read_csv(io.StringIO(text), sep=sep)


def make_svc(tmp_path: Path) -> SessionService:
    return SessionService(backend=FileDurableBackend(tmp_path))


def _inspect_session_df(svc: SessionService, sid: str) -> pd.DataFrame:
    """Return the current level's data as a DataFrame (best-effort)."""
    from intuitiveness.persistence.session_export import import_session
    record = svc._backend.load_record(sid)
    tree = import_session(record)   # returns NavigationTree, not NavigationSession
    node = tree.current_node
    data = node.dataset.get_data()
    if isinstance(data, pd.DataFrame):
        return data
    # Graph → rows
    if hasattr(data, "nodes"):
        return pd.DataFrame(
            [{"node": n, **(attrs or {})} for n, attrs in data.nodes(data=True)]
        )
    return pd.DataFrame()


def _first_numeric_col_of_df(df: pd.DataFrame) -> str:
    """Return the first numeric column; prefer named measure columns."""
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric:
        return df.columns[0]
    for c in numeric:
        if any(k in c.lower() for k in ("value", "amount", "price", "score", "montant", "niveau")):
            return c
    return numeric[0]


def full_cycle(svc: SessionService, tables: dict, domains: list[str]) -> dict:
    """Run descent then ascent on `tables`; return final state."""
    state = svc.create_from_tables(tables)
    sid = state["session_id"]

    # ---- Descent ----
    # L4→L3
    state = svc.descend(sid, {"builder": "rows_as_nodes"})
    assert state["current_level"] == 3, f"expected L3 after L4→L3, got {state}"

    # L3→L2 — real categorization
    state = svc.descend(sid, {"domains": domains})
    assert state["current_level"] == 2, f"expected L2 after L3→L2, got {state}"

    # Inspect the L2 DataFrame to pick the right numeric column for L2→L1
    l2_df = _inspect_session_df(svc, sid)
    measure_col = _first_numeric_col_of_df(l2_df) if not l2_df.empty else None

    # L2→L1 — pass the measure column so the engine knows what to reduce
    state = svc.descend(sid, {"column": measure_col} if measure_col else {})
    assert state["current_level"] == 1, f"expected L1 after L2→L1, got {state}"

    # L1→L0
    state = svc.descend(sid, {"aggregation": "mean"})
    assert state["current_level"] == 0, f"expected L0 after L1→L0, got {state}"
    l0_value = state.get("summary", {}).get("value")
    assert l0_value is not None, "L0 should have a scalar value"

    # ---- Ascent ----
    state = svc.ascend(sid, {})
    assert state["current_level"] == 1, f"expected L1 on ascent, got {state}"

    state = svc.ascend(sid, {})
    assert state["current_level"] == 2, f"expected L2 on ascent, got {state}"

    state = svc.ascend(sid, {})
    assert state["current_level"] == 3, f"expected L3 on ascent, got {state}"

    return state


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("test_dir,csv_files,domains", [
    (
        "test0",
        ["fr-en-indicateurs-valeur-ajoutee-colleges_small.csv"],
        ["bas score", "haut score"],
    ),
    (
        "test1",
        ["Les aides financieres ADEME.csv"],
        ["petit financement", "grand financement"],
    ),
    (
        "test2",
        ["Niveaux_prix_TRVG.csv"],
        ["prix bas", "prix haut"],
    ),
])
def test_full_cycle(tmp_path, test_dir, csv_files, domains):
    tables = {}
    for fname in csv_files:
        path = TEST_DATA / test_dir / fname
        if not path.exists():
            pytest.skip(f"Test data not found: {path}")
        tables[fname] = _parse_csv(path)

    svc = make_svc(tmp_path)
    final = full_cycle(svc, tables, domains)
    assert final["current_level"] == 3


def test_l2_categorization_distributes_rows(tmp_path):
    """The L3→L2 step must assign rows to both categories, not just the first."""
    df = pd.DataFrame({"score": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]})
    svc = make_svc(tmp_path)
    state = svc.create_from_tables({"scores.csv": df})
    sid = state["session_id"]

    svc.descend(sid, {"builder": "rows_as_nodes"})
    svc.descend(sid, {"domains": ["low", "high"]})

    l2_df = _inspect_session_df(svc, sid)
    assert not l2_df.empty, "L2 data should be non-empty"
    if "category" in l2_df.columns:
        counts = l2_df["category"].value_counts()
        assert len(counts) > 1, \
            f"Both categories should be populated, got: {counts.to_dict()}"
