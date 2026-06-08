"""Durable backend for full-fidelity session records (spec 015 T034/T038).

The browser ``StorageBackend`` (localStorage) caps out around 4–5 MB and lives
only in one browser. Full-fidelity session exports (every branch, every point's
data + lineage) routinely exceed that. This module persists the versioned record
produced by :func:`intuitiveness.persistence.session_export.export_session` to a
durable store so it survives reloads, is shareable, and can be read back by a
separate program using only the documented schema.

Two interchangeable backends, same interface:

- :class:`PostgresDurableBackend` — a PostgreSQL table (e.g. Railway). The record
  is one ``JSONB`` column keyed by ``session_id``; the surrounding columns
  (``title``, ``current_id``, ``updated_at``) double as the **session index**
  (T038), so the index and the payload live in one place.
- :class:`FileDurableBackend` — ``~/.intuitiveness/sessions/<id>.json`` files.
  The default/local fallback when no database is configured.

:func:`get_durable_backend` picks Postgres when a connection is configured (and
the driver is importable), otherwise falls back to files — mirroring how the
graph DB and embeddings read their config from ``st.secrets`` then env.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_ROOT = Path(os.path.expanduser("~")) / ".intuitiveness" / "sessions"


# --------------------------------------------------------------------------- #
# Config resolution (st.secrets first, then environment)
# --------------------------------------------------------------------------- #

def _secret(*names: str) -> Optional[str]:
    """Resolve a config value from st.secrets first, then environment."""
    try:
        import streamlit as st
        for n in names:
            try:
                if n in st.secrets:
                    return st.secrets[n]
            except Exception:
                pass
    except Exception:
        pass
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return None


def get_database_url() -> Optional[str]:
    """The PostgreSQL connection URL, if configured.

    Railway exposes ``DATABASE_URL`` by default; we also accept a couple of
    common aliases. ``None`` means "no database configured" → use files.
    """
    return _secret("SESSION_DATABASE_URL", "DATABASE_URL", "POSTGRES_URL")


# --------------------------------------------------------------------------- #
# File backend (local default)
# --------------------------------------------------------------------------- #

class FileDurableBackend:
    """Persist/retrieve full session records as JSON files."""

    def __init__(self, root: Optional[os.PathLike] = None):
        self.root = Path(root) if root is not None else DEFAULT_ROOT

    def _path_for(self, session_id: str) -> Path:
        # Guard against path traversal from an untrusted id.
        safe = session_id.replace("/", "_").replace("\\", "_").replace("..", "_")
        return self.root / f"{safe}.json"

    def save_record(self, session_id: str, record: Dict[str, Any]) -> str:
        """Write a full-fidelity export record. Returns the durable location."""
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path_for(session_id)
        tmp = path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False)
        os.replace(tmp, path)  # atomic
        return str(path)

    def load_record(self, session_id_or_location: str) -> Dict[str, Any]:
        """Read a record back, by session id or by full location path."""
        path = Path(session_id_or_location)
        if not path.suffix:  # looks like a session id, not a path
            path = self._path_for(session_id_or_location)
        if not path.exists():
            raise FileNotFoundError(f"No durable session record at {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def exists(self, session_id: str) -> bool:
        return self._path_for(session_id).exists()

    def delete(self, session_id: str) -> bool:
        path = self._path_for(session_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_session_ids(self) -> List[str]:
        if not self.root.exists():
            return []
        return sorted(p.stem for p in self.root.glob("*.json"))

    def list_sessions(self) -> List[Tuple[str, str]]:
        """Session index: (session_id, title). Title falls back to the id."""
        index = []
        for sid in self.list_session_ids():
            title = sid
            try:
                rec = self.load_record(sid)
                title = rec.get("metadata", {}).get("title", sid)
            except Exception:
                pass
            index.append((sid, title))
        return index


# Backwards-compatible alias: the original class name was DurableBackend.
DurableBackend = FileDurableBackend


# --------------------------------------------------------------------------- #
# PostgreSQL backend (durable store + session index in one table)
# --------------------------------------------------------------------------- #

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS session_records (
    session_id     TEXT PRIMARY KEY,
    title          TEXT,
    schema_version TEXT,
    current_id     TEXT,
    record         JSONB NOT NULL,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

_UPSERT = """
INSERT INTO session_records (session_id, title, schema_version, current_id, record, updated_at)
VALUES (%s, %s, %s, %s, %s, now())
ON CONFLICT (session_id) DO UPDATE SET
    title = EXCLUDED.title,
    schema_version = EXCLUDED.schema_version,
    current_id = EXCLUDED.current_id,
    record = EXCLUDED.record,
    updated_at = now();
"""


def _import_psycopg():
    """Return a (connect, Json) pair from psycopg3 or psycopg2, or None."""
    try:
        import psycopg  # psycopg3
        from psycopg.types.json import Json
        return psycopg.connect, Json
    except Exception:
        pass
    try:
        import psycopg2  # psycopg2
        from psycopg2.extras import Json
        return psycopg2.connect, Json
    except Exception:
        return None


class PostgresDurableBackend:
    """Store full session records in a PostgreSQL table (e.g. on Railway).

    The table doubles as the session index (T038): one row per session, the
    full record in a ``JSONB`` column, with ``title``/``current_id``/``updated_at``
    available for listing without decoding the payload.
    """

    def __init__(self, database_url: str):
        driver = _import_psycopg()
        if driver is None:
            raise RuntimeError(
                "PostgreSQL driver not installed. Add 'psycopg2-binary' (or "
                "'psycopg') to requirements to use the Postgres session store."
            )
        self._connect, self._Json = driver
        self._database_url = database_url
        self._ensure_table()

    def _conn(self):
        return self._connect(self._database_url)

    def _ensure_table(self) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(_CREATE_TABLE)
            conn.commit()

    def save_record(self, session_id: str, record: Dict[str, Any]) -> str:
        meta = record.get("metadata", {})
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(_UPSERT, (
                    session_id,
                    meta.get("title", session_id),
                    record.get("schema_version"),
                    meta.get("current_id"),
                    self._Json(record),
                ))
            conn.commit()
        return f"postgres://session_records/{session_id}"

    def load_record(self, session_id: str) -> Dict[str, Any]:
        # Accept the postgres:// locator form too.
        sid = session_id.rsplit("/", 1)[-1]
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT record FROM session_records WHERE session_id = %s", (sid,))
                row = cur.fetchone()
        if row is None:
            raise FileNotFoundError(f"No durable session record for {sid!r}")
        record = row[0]
        # psycopg2 may hand back JSONB as text depending on config.
        return record if isinstance(record, dict) else json.loads(record)

    def exists(self, session_id: str) -> bool:
        sid = session_id.rsplit("/", 1)[-1]
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM session_records WHERE session_id = %s", (sid,))
                return cur.fetchone() is not None

    def delete(self, session_id: str) -> bool:
        sid = session_id.rsplit("/", 1)[-1]
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM session_records WHERE session_id = %s", (sid,))
                deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    def list_session_ids(self) -> List[str]:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT session_id FROM session_records ORDER BY updated_at DESC")
                return [r[0] for r in cur.fetchall()]

    def list_sessions(self) -> List[Tuple[str, str]]:
        """Session index: (session_id, title), newest first — no payload decode."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT session_id, COALESCE(title, session_id) "
                    "FROM session_records ORDER BY updated_at DESC"
                )
                return [(r[0], r[1]) for r in cur.fetchall()]


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #

def get_durable_backend():
    """Return the configured durable backend.

    PostgreSQL when a connection URL is configured AND the driver is importable;
    otherwise the local file backend. This means the app and the offline tests
    work with zero configuration, and switching to the Railway database is a
    secrets-only change (no code change) — verified live like the graph DB.
    """
    url = get_database_url()
    if url:
        try:
            return PostgresDurableBackend(url)
        except Exception as e:  # driver missing or DB unreachable → fall back
            logger.warning(
                "Postgres session store unavailable (%s); falling back to file backend.", e
            )
    return FileDurableBackend()
