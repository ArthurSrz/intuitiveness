"""Search and import-from-URL endpoints (spec 017, P4).

GET  /search                   — federated open-data search (data.gouv.fr)
GET  /search/worldbank         — World Bank indicator search
POST /sessions/import-url      — download a CSV by URL and create a session
POST /sessions/import-worldbank — fetch WB indicator data and create a session

Both search endpoints try the MCP server first (better natural-language
search), falling back to the direct REST API when the MCP is unavailable.
"""

from __future__ import annotations

import io
import logging
from typing import List, Optional

import pandas as pd
import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from intuitiveness.navigation.exceptions import NavigationError

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
    source: str = "rest"


def _hosted_csv_resources(resources: list) -> list:
    """CSV resources hosted on trusted French open-data domains.

    Search and import MUST share this predicate: anything search counts as a
    CSV here is something import-url will actually download.  data.gouv.fr is
    a federation hub — most files live on ministry portals (*.gouv.fr), which
    are reliable.  Untrusted third-party hosts are still excluded.
    """
    return [
        r
        for r in resources
        if ((r.get("format") or "").lower() == "csv" or str(r.get("url", "")).endswith(".csv"))
        and ".gouv.fr" in str(r.get("url", ""))
    ]


# --------------------------------------------------------------------------- #
# data.gouv.fr MCP singleton (lazy)
# --------------------------------------------------------------------------- #

_datagouv_mcp = None


def _get_datagouv_mcp():
    global _datagouv_mcp
    if _datagouv_mcp is None:
        from intuitiveness.services.datagouv_mcp import DataGouvMCPService
        _datagouv_mcp = DataGouvMCPService()
    return _datagouv_mcp


def _search_via_mcp(q: str, page: int, size: int) -> Optional[SearchResponse]:
    """Try searching via the data.gouv.fr MCP server. Returns None on failure."""
    try:
        mcp = _get_datagouv_mcp()
        if not mcp.is_available():
            return None

        result = mcp.search_datasets(q, page=page, page_size=size)
        datasets = []
        for ds in result.datasets:
            datasets.append(DatasetResult(
                id=ds.id,
                title=(ds.title or "")[:120],
                description=(ds.description or "")[:200],
                organization=ds.organization_name or "",
                has_csv=True,
                resource_count=ds.resource_count or 0,
            ))
        return SearchResponse(
            datasets=datasets,
            total=result.total,
            has_more=result.has_more,
            source="mcp",
        )
    except Exception as exc:
        logger.warning("data.gouv MCP search failed, falling back to REST: %s", exc)
        return None


def _search_via_rest(q: str, page: int, size: int) -> SearchResponse:
    """Search data.gouv.fr via the REST API (fallback)."""
    try:
        resp = requests.get(
            "https://www.data.gouv.fr/api/1/datasets/",
            params={"q": q, "page": page, "page_size": size * 3},
            timeout=10,
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("data.gouv REST search failed: %s", exc)
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
    return SearchResponse(
        datasets=datasets,
        total=total,
        has_more=data.get("next_page") is not None,
        source="rest",
    )


# --------------------------------------------------------------------------- #
# Search endpoint
# --------------------------------------------------------------------------- #

@router.get("/search", response_model=SearchResponse)
def search_datasets(
    q: str = Query(..., description="Search query — keywords or natural language."),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=8, ge=1, le=20),
) -> SearchResponse:
    """Search data.gouv.fr — MCP first, REST fallback."""
    result = _search_via_mcp(q, page, size)
    if result is not None and result.datasets:
        return result
    return _search_via_rest(q, page, size)


# --------------------------------------------------------------------------- #
# Import-from-URL endpoint
# --------------------------------------------------------------------------- #

_MAX_IMPORT_ROWS = 100


class ImportUrlRequest(BaseModel):
    url: str
    filename: Optional[str] = None
    max_rows: Optional[int] = _MAX_IMPORT_ROWS


_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Intuitiveness/1.0; +https://intuitiveness.app)",
    "Accept": "text/csv,text/plain,*/*",
}


def _resolve_csv_candidates(url: str) -> list[tuple[str, str]]:
    """Return list of (download_url, filename) candidates to try in order."""
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
                detail=f"No .gouv.fr-hosted CSV found for dataset '{dataset_id}'. Try another dataset.",
            )
        return [(res["url"], (res.get("title") or dataset_id) + ".csv") for res in hosted]
    return [(url, url.split("/")[-1].split("?")[0] or "dataset.csv")]


def _download_csv(candidates: list[tuple[str, str]], max_rows: int | None = None) -> tuple[str, str]:
    """Try each candidate URL; return (csv_text, filename).

    When *max_rows* is set, streams the response and stops after
    header + max_rows lines so we never buffer the full file.
    """
    last_exc: Exception = RuntimeError("No candidates")
    for csv_url, filename in candidates:
        try:
            if max_rows and max_rows > 0:
                resp = requests.get(csv_url, timeout=30, headers=_BROWSER_HEADERS, stream=True)
                resp.raise_for_status()
                lines: list[str] = []
                for raw_line in resp.iter_lines():
                    for enc in ("utf-8-sig", "utf-8", "latin-1"):
                        try:
                            line = raw_line.decode(enc)
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        line = raw_line.decode("latin-1")
                    lines.append(line)
                    if len(lines) > max_rows:
                        break
                resp.close()
                return "\n".join(lines), filename
            else:
                resp = requests.get(csv_url, timeout=30, headers=_BROWSER_HEADERS)
                resp.raise_for_status()
                raw = resp.content
                for enc in ("utf-8-sig", "utf-8", "latin-1"):
                    try:
                        return raw.decode(enc), filename
                    except UnicodeDecodeError:
                        continue
                return raw.decode("latin-1"), filename
        except Exception as exc:
            logger.warning("Failed to download %s: %s", csv_url, exc)
            last_exc = exc
    raise HTTPException(status_code=502, detail=f"Could not download any CSV resource: {last_exc}")


def _fetch_csv_as_df(url: str, filename: str | None, max_rows: int | None) -> tuple[pd.DataFrame, str]:
    """Download a CSV from a URL, parse it, return (df, filename)."""
    candidates = _resolve_csv_candidates(url)
    text, auto_filename = _download_csv(candidates, max_rows=max_rows)
    name = filename or auto_filename
    if not name.lower().endswith(".csv"):
        name += ".csv"

    import csv as _csv
    try:
        dialect = _csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
        sep = dialect.delimiter
    except _csv.Error:
        sep = ","

    df = pd.read_csv(io.StringIO(text), sep=sep)
    if len(df) > 100:
        logger.info("Truncating %s from %d to 100 rows (schema + intent, not volume)", name, len(df))
        df = df.head(100)
    return df, name


@router.post("/sessions/import-url", response_model=SessionState, status_code=201)
def import_from_url(
    body: ImportUrlRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Download a CSV from a public URL and create a new session."""
    max_rows = body.max_rows if body.max_rows and body.max_rows > 0 else None
    df, filename = _fetch_csv_as_df(body.url, body.filename, max_rows)
    return svc.create_from_tables({filename: df})


@router.post("/sessions/{session_id}/add-source-url", response_model=SessionState)
def add_source_url(
    session_id: str,
    body: ImportUrlRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Download a CSV and add it to an existing session as a new source."""
    max_rows = body.max_rows if body.max_rows and body.max_rows > 0 else None
    df, filename = _fetch_csv_as_df(body.url, body.filename, max_rows)
    try:
        return svc.add_source(session_id, {filename: df})
    except NavigationError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


# --------------------------------------------------------------------------- #
# World Bank Data360 search + import
# --------------------------------------------------------------------------- #

_DATA360_BASE = "https://data360api.worldbank.org/data360"


class WBIndicator(BaseModel):
    id: str
    name: str
    database_id: str
    score: float = 0.0


class WBSearchResponse(BaseModel):
    indicators: List[WBIndicator]
    total: int
    source: str = "rest"


# World Bank MCP singleton (lazy)
_wb_mcp = None


def _get_wb_mcp():
    global _wb_mcp
    if _wb_mcp is None:
        from intuitiveness.services.worldbank_mcp import WorldBankMCPService
        _wb_mcp = WorldBankMCPService()
    return _wb_mcp


def _wb_search_via_mcp(q: str, size: int) -> Optional[WBSearchResponse]:
    """Try searching via the Data360 MCP server. Returns None on failure."""
    try:
        mcp = _get_wb_mcp()
        if not mcp.is_available():
            return None

        results = mcp.search_indicators(q, max_results=size)
        if not results:
            return None

        indicators = [
            WBIndicator(id=r.id, name=r.name, database_id=r.database_id, score=r.score)
            for r in results
        ]
        return WBSearchResponse(
            indicators=indicators,
            total=len(indicators),
            source="mcp",
        )
    except Exception as exc:
        logger.warning("Data360 MCP search failed, falling back to REST: %s", exc)
        return None


def _wb_search_via_rest(q: str, size: int) -> WBSearchResponse:
    """Search World Bank indicators via the REST API (fallback)."""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = requests.post(
                f"{_DATA360_BASE}/searchv2",
                json={
                    "search": q,
                    "searchFields": "series_description/name",
                    "select": "series_description/idno, series_description/name, series_description/database_id",
                    "top": size,
                    "count": True,
                },
                timeout=20,
            )
            resp.raise_for_status()
            payload = resp.json()
            break
        except Exception as exc:
            last_exc = exc
            logger.warning("Data360 REST search attempt %d failed: %s", attempt + 1, exc)
    else:
        raise HTTPException(status_code=502, detail=f"World Bank search unavailable after 3 attempts: {last_exc}") from last_exc

    indicators = [
        WBIndicator(
            id=hit["series_description"]["idno"],
            name=hit["series_description"]["name"],
            database_id=hit["series_description"]["database_id"],
            score=hit.get("@search.score", 0),
        )
        for hit in payload.get("value", [])
    ]
    total = payload.get("@odata.count", len(indicators))
    return WBSearchResponse(indicators=indicators, total=total, source="rest")


@router.get("/search/worldbank", response_model=WBSearchResponse)
def search_worldbank(
    q: str = Query(..., description="Indicator name or keyword"),
    size: int = Query(default=8, ge=1, le=20),
) -> WBSearchResponse:
    """Search World Bank indicators — MCP first, REST fallback."""
    result = _wb_search_via_mcp(q, size)
    if result is not None:
        return result
    return _wb_search_via_rest(q, size)


class ImportWBRequest(BaseModel):
    indicator_id: str
    database_id: str
    indicator_name: str


_DIMENSION_COLS = {
    "REF_AREA": "country",
    "TIME_PERIOD": "year",
    "OBS_VALUE": "value",
    "SEX": "sex",
    "AGE": "age",
    "URBANISATION": "urbanisation",
    "UNIT_MEASURE": "unit",
}


def _fetch_wb_indicator(body: ImportWBRequest) -> tuple[pd.DataFrame, str]:
    """Fetch a World Bank indicator and return (df, filename)."""
    try:
        rows: list = []
        skip = 0
        page_size = 1000
        while True:
            resp = requests.get(
                f"{_DATA360_BASE}/data",
                params={
                    "DATABASE_ID": body.database_id,
                    "INDICATOR": body.indicator_id,
                    "top": page_size,
                    "skip": skip,
                },
                timeout=30,
            )
            resp.raise_for_status()
            batch = resp.json().get("value", [])
            if not batch:
                break
            rows.extend(batch)
            if len(batch) < page_size:
                break
            skip += page_size
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"World Bank API error: {exc}") from exc

    if not rows:
        raise HTTPException(status_code=404, detail=f"No data for indicator '{body.indicator_id}'.")

    records = []
    for r in rows:
        if r.get("OBS_VALUE") is None:
            continue
        record = {}
        for api_key, col_name in _DIMENSION_COLS.items():
            val = r.get(api_key)
            if val is not None:
                record[col_name] = val
        records.append(record)

    if not records:
        raise HTTPException(status_code=404, detail=f"All values are null for '{body.indicator_id}'.")

    df = pd.DataFrame(records)
    if "value" in df.columns:
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

    for col in ["sex", "age", "urbanisation"]:
        if col in df.columns and df[col].nunique() <= 1:
            df.drop(columns=col, inplace=True)

    safe_name = body.indicator_name[:40].replace("/", "-").replace(" ", "_") + ".csv"
    return df, safe_name


@router.post("/sessions/import-worldbank", response_model=SessionState, status_code=201)
def import_worldbank(
    body: ImportWBRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Fetch World Bank indicator data and create a new session."""
    df, filename = _fetch_wb_indicator(body)
    return svc.create_from_tables({filename: df})


@router.post("/sessions/{session_id}/add-source-worldbank", response_model=SessionState)
def add_source_worldbank(
    session_id: str,
    body: ImportWBRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Fetch World Bank indicator data and add it to an existing session."""
    df, filename = _fetch_wb_indicator(body)
    try:
        return svc.add_source(session_id, {filename: df})
    except NavigationError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
