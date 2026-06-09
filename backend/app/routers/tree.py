"""Navigation-tree endpoints (spec 017, T014) — the spec-015 branching model.

GET tree / POST time-travel / branch-from / prune / archive. Prune of the root
or a node on the current branch is rejected by the engine with a NavigationError
→ 409 (handled in main.py).
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..deps import get_session_service
from ..models import BranchFromRequest, MutationCount, NodeIdRequest, SessionState
from ..service import SessionService

router = APIRouter(prefix="/sessions", tags=["tree"])


@router.get("/{session_id}/tree")
def get_tree(
    session_id: str,
    svc: SessionService = Depends(get_session_service),
) -> Dict[str, Any]:
    """Flat node list + root_id + current_id; the frontend builds the tree."""
    return svc.tree(session_id)


@router.post("/{session_id}/time-travel", response_model=SessionState)
def time_travel(
    session_id: str,
    body: NodeIdRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Move the current pointer to an existing node (no new transition)."""
    return svc.time_travel(session_id, body.node_id)


@router.post("/{session_id}/branch-from", response_model=SessionState)
def branch_from(
    session_id: str,
    body: BranchFromRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Restore an earlier node and run a (possibly different) transition off it,
    creating a sibling branch without disturbing the original path."""
    return svc.branch_from(session_id, body.node_id, body.action, body.params)


@router.post("/{session_id}/prune", response_model=MutationCount)
def prune(
    session_id: str,
    body: NodeIdRequest,
    svc: SessionService = Depends(get_session_service),
) -> MutationCount:
    """Permanently remove a node + its subtree (409 if root / on current branch)."""
    return MutationCount(count=svc.prune(session_id, body.node_id))


@router.post("/{session_id}/archive", response_model=MutationCount)
def archive(
    session_id: str,
    body: NodeIdRequest,
    svc: SessionService = Depends(get_session_service),
) -> MutationCount:
    """Soft-hide a node + its subtree (reversible)."""
    return MutationCount(count=svc.archive(session_id, body.node_id))
