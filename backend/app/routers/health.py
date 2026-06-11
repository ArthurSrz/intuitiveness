"""Health / readiness endpoint (spec 017, T022).

`GET /healthz` mirrors the three verify scripts (postgres / memgraph / embeddings)
but is non-blocking and never raises: each dependency is OPTIONAL (spec 016
graceful degradation), so the endpoint reports per-dependency `{configured, ok}`
and an overall `status: "ok"` as long as the process is up. The frontend renders
this as a status badge.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..models import DepStatus, HealthResponse

router = APIRouter(tags=["meta"])


def _check_postgres() -> DepStatus:
    from intuitiveness.persistence.durable_backend import (
        PostgresDurableBackend,
        get_database_url,
    )

    url = get_database_url()
    if not url:
        return DepStatus(configured=False, ok=False, detail="No DATABASE_URL; using file backend.")
    try:
        backend = PostgresDurableBackend(url)
        # exists() runs a trivial query against the table → proves connectivity.
        backend.exists("__healthz_probe__")
        return DepStatus(configured=True, ok=True)
    except Exception as e:  # noqa: BLE001
        return DepStatus(configured=True, ok=False, detail=str(e)[:200])


def _check_embeddings() -> DepStatus:
    try:
        from intuitiveness.models import _embedding_config

        cfg = _embedding_config()
        if not cfg.get("api_key"):
            return DepStatus(configured=False, ok=False, detail="No EMBEDDING_API_KEY set.")
        # Don't spend a network round-trip on healthz; configured ⇒ ready.
        return DepStatus(configured=True, ok=True, detail=f"model={cfg.get('model')}")
    except Exception as e:  # noqa: BLE001
        return DepStatus(configured=False, ok=False, detail=str(e)[:200])


def _check_memgraph() -> DepStatus:
    try:
        from intuitiveness.neo4j_client import Neo4jClient, get_graph_db_credentials
    except Exception as e:  # noqa: BLE001 — graph extra not installed
        return DepStatus(configured=False, ok=False, detail=f"graph client unavailable: {str(e)[:120]}")
    try:
        creds = get_graph_db_credentials()
        if not creds or not creds.get("uri"):
            return DepStatus(configured=False, ok=False, detail="No MEMGRAPH_URI / NEO4J_URI set.")
        client = Neo4jClient(**creds)
        connected = bool(client.connect()) and client.is_connected
        try:
            client.close()
        except Exception:  # noqa: BLE001
            pass
        return DepStatus(configured=True, ok=connected,
                         detail=None if connected else "Could not connect.")
    except Exception as e:  # noqa: BLE001
        return DepStatus(configured=True, ok=False, detail=str(e)[:200])


@router.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(
        status="ok",
        deps={
            "postgres": _check_postgres(),
            "memgraph": _check_memgraph(),
            "embeddings": _check_embeddings(),
        },
    )
