"""Per-level artifacts + export/import (spec 017, T012).

- `GET  /sessions/{id}/nodes/{node_id}` → full-fidelity node (level + payload + lineage).
- `GET  /sessions/{id}/export`          → the spec-015 versioned record (attachment).
- `POST /sessions/import`               → rehydrate a record into a new session.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..deps import get_session_service
from ..models import ImportRequest, SessionState
from ..service import SessionService

router = APIRouter(prefix="/sessions", tags=["artifacts"])


@router.get("/{session_id}/nodes/{node_id}")
def get_node(
    session_id: str,
    node_id: str,
    svc: SessionService = Depends(get_session_service),
) -> Dict[str, Any]:
    """Full node record for rendering a level view (payload encoded per spec 015)."""
    return svc.node(session_id, node_id)


@router.get("/{session_id}/export")
def export_session_record(
    session_id: str,
    svc: SessionService = Depends(get_session_service),
) -> JSONResponse:
    """Download the full-fidelity, schema-versioned session record (spec-015 contract)."""
    record = svc.export(session_id)
    return JSONResponse(
        content=record,
        headers={
            "Content-Disposition": f'attachment; filename="session_{session_id}.json"'
        },
    )


# Note: import is NOT under /{session_id} — it MINTS a session from a record.
@router.post("/import", response_model=SessionState)
def import_session_record(
    body: ImportRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Create a new session by importing a previously exported record."""
    return svc.import_record(body.model_dump(exclude_none=True))
