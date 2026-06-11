"""Session lifecycle endpoints (spec 017, T010).

POST create / POST upload / GET state / GET list / DELETE — all delegate to `SessionService`.
"""

from __future__ import annotations

import csv
import io
from typing import List

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from ..deps import get_session_service
from ..models import CreateSessionRequest, SessionState, SessionSummary
from ..service import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _parse_csv(upload: UploadFile) -> pd.DataFrame:
    """Read a CSV UploadFile into a DataFrame — tries utf-8 then latin-1."""
    raw = upload.file.read()
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise HTTPException(status_code=422, detail=f"Cannot decode '{upload.filename}' — try saving it as UTF-8.")
    # Sniff delimiter (comma, semicolon, tab, pipe)
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
        sep = dialect.delimiter
    except csv.Error:
        sep = ","
    return pd.read_csv(io.StringIO(text), sep=sep)


@router.post("", response_model=SessionState, status_code=status.HTTP_201_CREATED)
def create_session(
    body: CreateSessionRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Create a new session at L4 from a named demo dataset."""
    return svc.create(body.source)


@router.post("/upload", response_model=SessionState, status_code=status.HTTP_201_CREATED)
def upload_csv(
    files: List[UploadFile],
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Create a session from one or more uploaded CSV files.

    Each file becomes one source table in the L4 dataset.  Encoding (utf-8 /
    latin-1) and delimiter (, ; \\t |) are detected automatically.
    """
    if not files:
        raise HTTPException(status_code=422, detail="At least one CSV file is required.")
    tables: dict = {}
    for upload in files:
        name = upload.filename or f"table_{len(tables) + 1}"
        if name in tables:
            name = f"{name}_{len(tables)}"
        tables[name] = _parse_csv(upload)
    return svc.create_from_tables(tables)


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
