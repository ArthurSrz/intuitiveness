"""Test fixtures — drive the API over a temp file backend (never Postgres).

The key fixture overrides `get_session_service` to inject a `SessionService`
bound to a temp `FileDurableBackend`. Because each request builds a fresh
service over the SAME on-disk store, the suite exercises the stateless
load→transition→save path exactly as production does (SC-002).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from intuitiveness.persistence.durable_backend import FileDurableBackend

from app.deps import get_session_service
from app.main import app
from app.service import SessionService


@pytest.fixture()
def store(tmp_path):
    """A temp durable store shared across all requests in one test."""
    return FileDurableBackend(root=tmp_path)


@pytest.fixture()
def client(store):
    # Fresh service per call, same backend → mimics horizontal scaling / restarts.
    app.dependency_overrides[get_session_service] = lambda: SessionService(backend=store)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
