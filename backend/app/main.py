"""FastAPI application entrypoint (spec 017, T009).

Thin HTTP adapter over the headless `intuitiveness` engine. Responsibilities:
  - CORS (origins from ALLOWED_ORIGINS),
  - a Postgres connection warm-up on startup (lifespan) — best-effort,
  - exception handlers mapping the engine's errors to HTTP status codes,
  - mounting the resource routers.

No business logic lives here; every endpoint delegates to `SessionService`.
Run: `uvicorn app.main:app` (from the `backend/` directory).
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from intuitiveness.navigation.exceptions import NavigationError, SessionNotFoundError
from intuitiveness.persistence.durable_backend import get_database_url, get_durable_backend

from .routers import artifacts, health, sessions, transitions, tree

logger = logging.getLogger("intuitiveness.api")


def _allowed_origins() -> list[str]:
    """Frontend origins permitted by CORS. '*' allows all (dev default)."""
    raw = os.getenv("ALLOWED_ORIGINS", "*")
    return [o.strip() for o in raw.split(",") if o.strip()] or ["*"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm the durable backend once at startup so the first request isn't slow
    # and so a misconfigured DB surfaces in the logs immediately. Best-effort:
    # the file backend (no DB) is a valid fallback, so we never crash here.
    url = get_database_url()
    if url:
        try:
            get_durable_backend()  # constructs + ensures the table exists
            logger.info("Durable store: PostgreSQL (configured).")
        except Exception as e:  # noqa: BLE001
            logger.warning("Postgres unavailable at startup (%s); using file backend.", e)
    else:
        logger.info("Durable store: local files (no DATABASE_URL set).")
    yield


app = FastAPI(
    title="Intuitiveness API",
    version="0.1.0",
    summary="REST surface over the descent/ascent abstraction-level engine.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Exception handlers — engine errors → HTTP status (contract: rest-api.md)
# --------------------------------------------------------------------------- #
@app.exception_handler(SessionNotFoundError)
async def _not_found(_: Request, exc: SessionNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc), "code": "session_not_found"})


@app.exception_handler(NavigationError)
async def _navigation_error(_: Request, exc: NavigationError):
    # Illegal transition / branching / prune-root etc. → 409 Conflict.
    return JSONResponse(status_code=409, content={"detail": str(exc), "code": "illegal_transition"})


@app.exception_handler(KeyError)
async def _key_error(_: Request, exc: KeyError):
    # Unknown demo source / builder name → 422 (the client sent a bad value).
    return JSONResponse(status_code=422, content={"detail": str(exc), "code": "invalid_parameter"})


# --------------------------------------------------------------------------- #
# Routers
# --------------------------------------------------------------------------- #
app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(transitions.router)
app.include_router(tree.router)
app.include_router(artifacts.router)


@app.get("/", tags=["meta"])
def root():
    return {"name": "Intuitiveness API", "docs": "/docs", "openapi": "/openapi.json"}
