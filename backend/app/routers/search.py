"""Search and import-from-URL endpoints (spec 017, P4).

GET  /search                   — federated open-data search (data.gouv.fr)
GET  /search/worldbank         — World Bank indicator search
POST /sessions/import-url      — download a CSV by URL and create a session
POST /sessions/import-worldbank — fetch WB indicator data and create a session
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


def _hosted_csv_resources(resources: list) -> list:
    """CSV resources hosted on data.gouv.fr — the only ones import accepts.

    Search and import MUST share this predicate: anything search counts as a
    CSV here is something import-url will actually download. External hosts
    are excluded everywhere (unreliable; frequently reject programmatic
    downloads), so datasets without a hosted CSV never appear in results.
    """
    return [
        r
        for r in resources
        if ((r.get("format") or "").lower() == "csv" or str(r.get("url", "")).endswith(".csv"))
        and "data.gouv.fr" in str(r.get("url", ""))
    ]


# --------------------------------------------------------------------------- #
# Search endpoint
# --------------------------------------------------------------------------- #

@router.get("/search", response_model=SearchResponse)
def search_datasets(
    q: str = Query(..., description="Search query — keywords or natural language."),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=8, ge=1, le=20),
) -> SearchResponse:
    """Search data.gouv.fr for datasets that have CSV resources."""
    try:
        resp = requests.get(
            "https://www.data.gouv.fr/api/1/datasets/",
            params={"q": q, "format": "csv", "page": page, "page_size": size},
            timeout=10,
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("data.gouv search failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Search unavailable: {exc}") from exc

    datasets = []
    for ds in data.get("data", []):
        csv_resources = _hosted_csv_resources(ds.get("resources", []))
        if not csv_resources:
            continue
        org = ds.get("organization") or {}
        datasets.append(DatasetResult(
            id=ds["id"],
            title=ds.get("title", "")[:120],
            description=(ds.get("description") or "")[:200],
            organization=org.get("name", "") if isinstance(org, dict) else "",
            has_csv=True,
            resource_count=len(csv_resources),
        ))
    total = data.get("total", len(datasets))
    return SearchResponse(datasets=datasets, total=total, has_more=data.get("next_page") is not None)


# --------------------------------------------------------------------------- #
# Import-from-URL endpoint (mounted on the sessions router)
# --------------------------------------------------------------------------- #

class ImportUrlRequest(BaseModel):
    url: str
    filename: Optional[str] = None


_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Intuitiveness/1.0; +https://intuitiveness.app)",
    "Accept": "text/csv,text/plain,*/*",
}


def _resolve_csv_candidates(url: str) -> list[tuple[str, str]]:
    """Return list of (download_url, filename) candidates to try in order.

    For data.gouv.fr dataset pages: returns ALL csv resources so we can fall
    back to the next one if a host rejects the connection.
    For direct URLs: returns a single-item list.
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
        except requests.exceptions.RequestException as exc:
            raise HTTPException(status_code=502, detail=f"Could not resolve CSV for dataset '{dataset_id}': {exc}") from exc
        hosted = _hosted_csv_resources(data.get("resources", []))
        if not hosted:
            raise HTTPException(
                status_code=404,
                detail=f"No data.gouv.fr-hosted CSV found for dataset '{dataset_id}'. Try another dataset.",
            )
        return [(res["url"], (res.get("title") or dataset_id) + ".csv") for res in hosted]
    return [(url, url.split("/")[-1].split("?")[0] or "dataset.csv")]


def _download_csv(candidates: list[tuple[str, str]]) -> tuple[bytes, str]:
    """Try each candidate URL with a browser User-Agent; return (raw_bytes, filename)."""
    last_exc: Exception = RuntimeError("No candidates")
    for csv_url, filename in candidates:
        try:
            resp = requests.get(csv_url, timeout=30, headers=_BROWSER_HEADERS)
            resp.raise_for_status()
            return resp.content, filename
        except Exception as exc:
            logger.warning("Failed to download %s: %s", csv_url, exc)
            last_exc = exc
    raise HTTPException(status_code=502, detail=f"Could not download any CSV resource: {last_exc}")


@router.post("/sessions/import-url", response_model=SessionState, status_code=201)
def import_from_url(
    body: ImportUrlRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Download a CSV from a public URL (or a data.gouv.fr dataset page) and create a session."""
    candidates = _resolve_csv_candidates(body.url)
    raw, auto_filename = _download_csv(candidates)
    filename = body.filename or auto_filename
    if not filename.lower().endswith(".csv"):
        filename += ".csv"

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


# --------------------------------------------------------------------------- #
# World Bank search + import
# --------------------------------------------------------------------------- #

class WBIndicator(BaseModel):
    id: str
    name: str
    source: str
    topics: List[str]


class WBSearchResponse(BaseModel):
    indicators: List[WBIndicator]
    total: int


@router.get("/search/worldbank", response_model=WBSearchResponse)
def search_worldbank(
    q: str = Query(..., description="Indicator name or keyword"),
    size: int = Query(default=8, ge=1, le=20),
) -> WBSearchResponse:
    """Search World Bank indicators by keyword."""
    try:
        resp = requests.get(
            "https://api.worldbank.org/v2/indicator",
            params={"q": q, "format": "json", "per_page": size},
            timeout=10,
        )
        resp.raise_for_status()
        payload = resp.json()
        meta, items = payload[0], payload[1] if len(payload) > 1 else []
        indicators = [
            WBIndicator(
                id=item["id"],
                name=item["name"],
                source=item.get("source", {}).get("value", "World Bank"),
                topics=[t.get("value", "") for t in item.get("topics", []) if t.get("value")],
            )
            for item in (items or [])
        ]
        return WBSearchResponse(indicators=indicators, total=meta.get("total", len(indicators)))
    except Exception as exc:
        logger.warning("WB search failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"World Bank search unavailable: {exc}") from exc


class ImportWBRequest(BaseModel):
    indicator_id: str
    indicator_name: str
    mrv: int = 10  # most recent values (years)


@router.post("/sessions/import-worldbank", response_model=SessionState, status_code=201)
def import_worldbank(
    body: ImportWBRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Fetch World Bank indicator data for all countries and create a session."""
    try:
        resp = requests.get(
            f"https://api.worldbank.org/v2/country/all/indicator/{body.indicator_id}",
            params={"format": "json", "per_page": 500, "mrv": body.mrv},
            timeout=20,
        )
        resp.raise_for_status()
        payload = resp.json()
        rows = payload[1] if len(payload) > 1 and payload[1] else []
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"World Bank API error: {exc}") from exc

    if not rows:
        raise HTTPException(status_code=404, detail=f"No data found for indicator '{body.indicator_id}'.")

    records = [
        {
            "country": r["country"]["value"],
            "country_code": r["countryiso3code"],
            "year": r["date"],
            "value": r["value"],
        }
        for r in rows
        if r.get("value") is not None
    ]
    if not records:
        raise HTTPException(status_code=404, detail=f"All values are null for '{body.indicator_id}'.")

    df = pd.DataFrame(records)
    safe_name = body.indicator_name[:40].replace("/", "-").replace(" ", "_") + ".csv"
    return svc.create_from_tables({safe_name: df})
