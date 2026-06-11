"""FastAPI dependency wiring (spec 017 R3).

`get_session_service` returns a FRESH `SessionService` per request. Because the
service holds no state between calls (it loads from the durable store, runs one
transition, saves back), a new instance per request is correct and cheap — this
is what makes the "restart mid-session loses nothing" guarantee hold (SC-002).

Tests override this dependency to inject a temp `FileDurableBackend` so they
never touch Postgres.
"""

from __future__ import annotations

from .service import SessionService


def get_session_service() -> SessionService:
    # No DB connection is opened here; the backend is resolved lazily by
    # `get_durable_backend()` (Postgres when DATABASE_URL is set, else files).
    return SessionService()
