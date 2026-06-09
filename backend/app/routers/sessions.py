"""Session lifecycle endpoints (spec 017, T010).

POST create / GET state / GET list / DELETE — all delegate to `SessionService`.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, status

from ..deps import get_session_service
from ..models import CreateSessionRequest, SessionState, SessionSummary
from ..service import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionState, status_code=status.HTTP_201_CREATED)
def create_session(
    body: CreateSessionRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Create a new session at L4 from a named demo dataset."""
    return svc.create(body.source)


@router.get("", response_model=List[SessionSummary])
def list_sessions(svc: SessionService = Depends(get_session_service)) -> List[SessionSummary]:
    """Index of persisted sessions (id + title)."""
    return svc.list_sessions()


@router.get("/{session_id}", response_model=SessionState)
def get_session(
    session_id: str,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Current state of a session (rehydrated from the durable store)."""
    return svc.get(session_id)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    svc: SessionService = Depends(get_session_service),
) -> None:
    svc.delete(session_id)
