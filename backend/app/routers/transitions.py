"""Engine transition endpoints (spec 017, T011).

`POST /sessions/{id}/descend` and `/ascend`. The body's documented fields plus
any extras are forwarded verbatim to the engine via `SessionService`. Engine
errors become 409 (illegal transition) / 422 (bad value) through the app-level
exception handlers in `main.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_session_service
from ..models import AscendRequest, DescendRequest, SessionState
from ..service import SessionService

router = APIRouter(prefix="/sessions", tags=["transitions"])


@router.post("/{session_id}/descend", response_model=SessionState)
def descend(
    session_id: str,
    body: DescendRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Reduce complexity one level (L4→L3→…→L0)."""
    # model_dump(exclude_none) keeps the payload tight; extras are preserved
    # because the model allows them.
    return svc.descend(session_id, body.model_dump(exclude_none=True))


@router.post("/{session_id}/ascend", response_model=SessionState)
def ascend(
    session_id: str,
    body: AscendRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Increase complexity one level (L0→L1→L2→L3; never L4)."""
    return svc.ascend(session_id, body.model_dump(exclude_none=True))
