"""Search and import-from-URL endpoints (spec 017, P4).

GET  /search          — federated open-data search (data.gouv.fr)
POST /sessions/import-url — download a CSV by URL and create a session
"""

from __future__ import annotations

import io
import logging
from typing import List, Optional

import pandas as pd
import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..deps import get_session_service
from ..models import SessionState
from ..routers.sessions import _parse_csv as _parse_csv_bytes
from ..service import SessionService

logger = logging.getLogger("intuitiveness.api.search")

router = APIRouter(tags=["search"])


# --------------------------------------------------------------------------- #
# Response shapes
# --------------------------------------------------------------------------- #

class DatasetResult(BaseModel):
    id: str
    title: str
    description: str
    organization: str
    has_csv: bool
    resource_count: int


class SearchResponse(BaseModel):
    datasets: List[DatasetResult]
    total: int
    has_more: bool


# --------------------------------------------------------------------------- #
# Search endpoint
# --------------------------------------------------------------------------- #

@router.get("/search", response_model=SearchResponse)
def search_datasets(
    q: str = Query(..., description="Search query — keywords or natural language."),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=8, ge=1, le=20),
) -> SearchResponse:
    """Search data.gouv.fr for public datasets matching a query."""
    try:
        from intuitiveness.services.datagouv_client import DataGouvSearchService
        svc = DataGouvSearchService()
        result = svc.search(q, page=page, page_size=size)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Search failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Search unavailable: {exc}") from exc

    datasets = [
        DatasetResult(
            id=ds.id,
            title=ds.title,
            description=ds.description[:200],
            organization=ds.organization_name,
            has_csv=ds.has_csv,
            resource_count=ds.resource_count,
        )
        for ds in result.datasets
    ]
    return SearchResponse(datasets=datasets, total=result.total, has_more=result.has_more)


# --------------------------------------------------------------------------- #
# Import-from-URL endpoint (mounted on the sessions router)
# --------------------------------------------------------------------------- #

class ImportUrlRequest(BaseModel):
    url: str
    filename: Optional[str] = None


def _resolve_csv_url(url: str) -> tuple[str, str]:
    """Return (download_url, filename).

    Handles two URL shapes:
    - data.gouv.fr dataset page: resolve via the public API → first CSV resource
    - direct CSV URL: return as-is
    """
    import re
    m = re.match(r"https?://www\.data\.gouv\.fr/[^/]+/datasets/([^/?#]+)/?", url)
    if m:
        dataset_id = m.group(1)
        try:
            api_resp = requests.get(
                f"https://www.data.gouv.fr/api/1/datasets/{dataset_id}/",
                timeout=10,
                headers={"Accept": "application/json"},
            )
            api_resp.raise_for_status()
            data = api_resp.json()
            for res in data.get("resources", []):
                if res.get("format", "").upper() == "CSV" or str(res.get("url", "")).endswith(".csv"):
                    return res["url"], res.get("title", dataset_id) + ".csv"
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"Could not resolve CSV for dataset '{dataset_id}': {exc}") from exc
        raise HTTPException(status_code=404, detail=f"No CSV resource found for dataset '{dataset_id}'.")
    return url, url.split("/")[-1].split("?")[0] or "dataset.csv"


@router.post("/sessions/import-url", response_model=SessionState, status_code=201)
def import_from_url(
    body: ImportUrlRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Download a CSV from a public URL (or a data.gouv.fr dataset page) and create a session."""
    csv_url, auto_filename = _resolve_csv_url(body.url)
    filename = body.filename or auto_filename
    if not filename.lower().endswith(".csv"):
        filename += ".csv"

    try:
        resp = requests.get(csv_url, timeout=30)
        resp.raise_for_status()
        raw = resp.content
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Could not download '{csv_url}': {exc}") from exc

    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise HTTPException(status_code=422, detail=f"Cannot decode CSV from '{csv_url}' — try UTF-8.")

    import csv as _csv
    try:
        dialect = _csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
        sep = dialect.delimiter
    except _csv.Error:
        sep = ","

    df = pd.read_csv(io.StringIO(text), sep=sep)
    return svc.create_from_tables({filename: df})
