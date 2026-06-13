"""Engine transition endpoints (spec 017, T011).

`POST /sessions/{id}/descend` and `/ascend`. The body's documented fields plus
any extras are forwarded verbatim to the engine via `SessionService`. Engine
errors become 409 (illegal transition) / 422 (bad value) through the app-level
exception handlers in `main.py`.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from ..deps import get_session_service
from ..models import AscendRequest, DescendRequest, SessionState
from ..service import SessionService

logger = logging.getLogger("intuitiveness.api.transitions")

router = APIRouter(prefix="/sessions", tags=["transitions"])


@router.post("/{session_id}/descend", response_model=SessionState)
def descend(
    session_id: str,
    body: DescendRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Reduce complexity one level (L4→L3→…→L0)."""
    params = body.model_dump(exclude_none=True)
    logger.warning("DESCEND session=%s params=%s", session_id[:8], {k: str(v)[:80] for k, v in params.items()})
    result = svc.descend(session_id, params)
    logger.warning("DESCEND result: level=%s", result.get("current_level"))
    return result


@router.post("/{session_id}/ascend", response_model=SessionState)
def ascend(
    session_id: str,
    body: AscendRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Increase complexity one level (L0→L1→L2→L3; never L4)."""
    params = body.model_dump(exclude_none=True)
    logger.warning("ASCEND session=%s params=%s", session_id[:8], {k: str(v)[:80] for k, v in params.items()})
    result = svc.ascend(session_id, params)
    logger.warning("ASCEND result: level=%s", result.get("current_level"))
    return result
