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

    return pd.read_csv(io.StringIO(text), sep=sep), name


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
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        logger.warning("Data360 REST search failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"World Bank search unavailable: {exc}") from exc

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


# --------------------------------------------------------------------------- #
# LLM Entity Matching
# --------------------------------------------------------------------------- #

class RelationshipDeclaration(BaseModel):
    source_a: str
    column_a: str
    source_b: str
    column_b: str


class EntityMatchRequest(BaseModel):
    relationships: List[RelationshipDeclaration]


class EntityMatchResponse(BaseModel):
    catalog: List[dict] = []
    join_plan: dict = {}
    explanation: str = ""
    error: Optional[str] = None


class EntityAnalyzeResponse(BaseModel):
    catalog: List[dict] = []
    join_plan: dict = {}
    column_transforms: dict = {}
    explanation: str = ""
    error: Optional[str] = None


@router.post("/sessions/{session_id}/entity-analyze", response_model=EntityAnalyzeResponse)
def entity_analyze(
    session_id: str,
    body: EntityMatchRequest,
    svc: SessionService = Depends(get_session_service),
) -> EntityAnalyzeResponse:
    """Three-tier entity discovery without descending. Returns catalog for user validation."""
    from intuitiveness.services.entity_discovery import discover_entities

    state = svc.get(session_id)
    if state["current_level"] != 4:
        raise HTTPException(status_code=409, detail="Entity matching is only available at L4.")

    session = svc._load(session_id)
    data = session.current_dataset.get_data()
    if not isinstance(data, dict) or len(data) < 2:
        raise HTTPException(status_code=422, detail="Need at least 2 sources for entity matching.")

    result = discover_entities(data, use_llm=True)

    return EntityAnalyzeResponse(
        catalog=result.catalog,
        join_plan={},
        column_transforms={},
        explanation=result.explanation,
        error=None,
    )


class DomainAnalyzeResponse(BaseModel):
    proposed_column: str = ""
    proposed_domains: List[str] = []
    explanation: str = ""
    confidence: str = ""
    code: str = ""
    sample_distribution: dict = {}
    columns: List[str] = []
    error: Optional[str] = None


class AnalyzeRequest(BaseModel):
    intent: str = ""


@router.post("/sessions/{session_id}/domain-analyze", response_model=DomainAnalyzeResponse)
def domain_analyze(
    session_id: str,
    body: AnalyzeRequest = AnalyzeRequest(),
    svc: SessionService = Depends(get_session_service),
) -> DomainAnalyzeResponse:
    """LLM analyzes data and writes categorization code."""
    from intuitiveness.services.domain_suggester import suggest_domains

    state = svc.get(session_id)
    if state["current_level"] != 3:
        raise HTTPException(status_code=409, detail="Domain analysis is only available at L3.")

    session = svc._load(session_id)
    data = session.current_dataset.get_data()
    result = suggest_domains(data, intent=body.intent)
    logger.warning("DOMAIN-ANALYZE result: domains=%s, dist=%s, code=%s", result.get("proposed_domains"), result.get("sample_distribution"), (result.get("code") or "")[:150])

    return DomainAnalyzeResponse(**result)


class DomainConfirmRequest(BaseModel):
    code: str
    domains: List[str] = []


@router.post("/sessions/{session_id}/domain-confirm", response_model=SessionState)
def domain_confirm(
    session_id: str,
    body: DomainConfirmRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Execute Claude's categorization code and descend to L2."""
    from intuitiveness.services.domain_suggester import execute_categorization

    state = svc.get(session_id)
    if state["current_level"] != 3:
        raise HTTPException(status_code=409, detail="Can only confirm domain mapping at L3.")

    session = svc._load(session_id)
    data = session.current_dataset.get_data()
    categorized = execute_categorization(data, body.code)

    session.descend(query_func=lambda _data: categorized)
    svc._save(session)
    return svc.state_of(session)


class ColumnAnalyzeResponse(BaseModel):
    proposed_column: str = ""
    proposed_filter: str = ""
    explanation: str = ""
    confidence: str = ""
    code: str = ""
    columns: List[str] = []
    preview_stats: dict = {}
    error: Optional[str] = None


@router.post("/sessions/{session_id}/column-analyze", response_model=ColumnAnalyzeResponse)
def column_analyze(
    session_id: str,
    body: AnalyzeRequest = AnalyzeRequest(),
    svc: SessionService = Depends(get_session_service),
) -> ColumnAnalyzeResponse:
    """AI analyzes L2 table and suggests which column to extract as L1 vector."""
    from intuitiveness.services.column_suggester import suggest_column

    state = svc.get(session_id)
    if state["current_level"] != 2:
        raise HTTPException(status_code=409, detail="Column analysis is only available at L2.")

    session = svc._load(session_id)
    data = session.current_dataset.get_data()
    result = suggest_column(data, intent=body.intent)
    logger.warning("COLUMN-ANALYZE result: col=%s, stats=%s, code=%s", result.get("proposed_column"), result.get("preview_stats"), (result.get("code") or "")[:150])

    return ColumnAnalyzeResponse(**result)


class ColumnConfirmRequest(BaseModel):
    code: str
    column: str = ""


@router.post("/sessions/{session_id}/column-confirm", response_model=SessionState)
def column_confirm(
    session_id: str,
    body: ColumnConfirmRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Execute AI's extraction code and descend to L1."""
    from intuitiveness.services.column_suggester import execute_column_extraction

    state = svc.get(session_id)
    if state["current_level"] != 2:
        raise HTTPException(status_code=409, detail="Can only confirm column extraction at L2.")

    session = svc._load(session_id)
    data = session.current_dataset.get_data()
    series = execute_column_extraction(data, body.code)
    col_name = body.column or (series.name if series.name else "value")
    series.name = col_name

    session.descend(column=col_name, prebuilt_series=series)
    svc._save(session)
    return svc.state_of(session)


class AggregationAnalyzeResponse(BaseModel):
    proposed_aggregation: str = ""
    explanation: str = ""
    confidence: str = ""
    code: str = ""
    preview_value: Optional[float] = None
    vector_profile: dict = {}
    error: Optional[str] = None


@router.post("/sessions/{session_id}/aggregation-analyze", response_model=AggregationAnalyzeResponse)
def aggregation_analyze(
    session_id: str,
    body: AnalyzeRequest = AnalyzeRequest(),
    svc: SessionService = Depends(get_session_service),
) -> AggregationAnalyzeResponse:
    """AI analyzes L1 vector and suggests how to compress to L0 datum."""
    from intuitiveness.services.aggregation_suggester import suggest_aggregation

    state = svc.get(session_id)
    if state["current_level"] != 1:
        raise HTTPException(status_code=409, detail="Aggregation analysis is only available at L1.")

    session = svc._load(session_id)
    data = session.current_dataset.get_data()
    result = suggest_aggregation(data, intent=body.intent)
    logger.warning("AGGREGATION-ANALYZE result: agg=%s, preview=%s, code=%s", result.get("proposed_aggregation"), result.get("preview_value"), (result.get("code") or "")[:150])

    return AggregationAnalyzeResponse(**result)


class AggregationConfirmRequest(BaseModel):
    code: str
    aggregation: str = "mean"


@router.post("/sessions/{session_id}/aggregation-confirm", response_model=SessionState)
def aggregation_confirm(
    session_id: str,
    body: AggregationConfirmRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Execute AI's aggregation code and descend to L0."""
    from intuitiveness.services.aggregation_suggester import execute_aggregation

    state = svc.get(session_id)
    if state["current_level"] != 1:
        raise HTTPException(status_code=409, detail="Can only confirm aggregation at L1.")

    session = svc._load(session_id)
    data = session.current_dataset.get_data()
    datum = execute_aggregation(data, body.code)

    session.descend(aggregation=body.aggregation, prebuilt_value=datum)
    svc._save(session)
    return svc.state_of(session)


class IntentSuggestResponse(BaseModel):
    intents: List[dict] = []
    error: Optional[str] = None


@router.post("/sessions/{session_id}/intent-suggest", response_model=IntentSuggestResponse)
def intent_suggest(
    session_id: str,
    svc: SessionService = Depends(get_session_service),
) -> IntentSuggestResponse:
    """AI suggests analytical intents based on the descent path."""
    from intuitiveness.services.intent_suggester import suggest_intents

    state = svc.get(session_id)
    session = svc._load(session_id)

    summary = state.get("summary", {})

    # Walk the tree to gather context from all levels
    data_context = {}
    try:
        session = svc._load(session_id)
        tree = session.navigation_tree.export_to_json()
        for node in tree.get("nodes", []):
            nid = node.get("id")
            lvl = node.get("level")
            if lvl == 4:
                try:
                    nd = svc.node(session_id, nid)
                    shapes = nd.get("summary", {}).get("shapes", {})
                    data_context["sources"] = list(shapes.keys()) if shapes else []
                except Exception:
                    pass
            elif lvl == 3:
                try:
                    nd = svc.node(session_id, nid)
                    cols = nd.get("summary", {}).get("columns", [])
                    if cols:
                        data_context["l3_columns"] = cols[:15]
                except Exception:
                    pass
    except Exception:
        pass

    descent_summary = {
        "current_level": state["current_level"],
        "datum_value": summary.get("value"),
        "datum_description": summary.get("description"),
        "aggregation_method": summary.get("aggregation_method"),
        "parent_column": summary.get("parent_name"),
        "entity_count": summary.get("parent_length"),
        "columns_seen": state.get("options", {}).get("columns", []),
        "data_sources": data_context.get("sources", []),
        "data_columns": data_context.get("l3_columns", []),
    }

    result = suggest_intents(descent_summary)
    logger.warning("INTENT-SUGGEST result: %s", [i.get("short") for i in result.get("intents", [])])
    return IntentSuggestResponse(**result)


class DatumDescribeResponse(BaseModel):
    title: str = ""
    description: str = ""
    error: Optional[str] = None


@router.post("/sessions/{session_id}/datum-describe", response_model=DatumDescribeResponse)
def datum_describe(
    session_id: str,
    svc: SessionService = Depends(get_session_service),
) -> DatumDescribeResponse:
    """AI describes the L0 datum in plain language."""
    from intuitiveness.services.datum_describer import describe_datum

    state = svc.get(session_id)
    summary = state.get("summary", {})

    context = {
        "value": summary.get("value"),
        "aggregation": summary.get("aggregation_method", summary.get("description", "")),
        "column_name": summary.get("parent_name", ""),
        "dataset_description": summary.get("description", ""),
        "entity_count": summary.get("parent_length", ""),
    }

    # Try to get lineage info for richer context
    try:
        session = svc._load(session_id)
        lineage = getattr(session.current_dataset, "lineage", None)
        if lineage and hasattr(lineage, "sources"):
            ops = [s.operation for s in lineage.sources if hasattr(s, "operation")]
            context["descent_operations"] = ops
    except Exception:
        pass

    logger.warning("DATUM-DESCRIBE context: value=%s, agg=%s, col=%s", context.get("value"), context.get("aggregation"), context.get("column_name"))
    result = describe_datum(context)
    logger.warning("DATUM-DESCRIBE result: title=%s, desc=%s", result.get("title"), (result.get("description") or "")[:100])
    return DatumDescribeResponse(**result)


class EnrichmentAnalyzeResponse(BaseModel):
    method: str = ""
    explanation: str = ""
    confidence: str = ""
    preview_length: int = 0
    preview_description: str = ""
    error: Optional[str] = None


@router.post("/sessions/{session_id}/enrichment-analyze", response_model=EnrichmentAnalyzeResponse)
def enrichment_analyze(
    session_id: str,
    body: AnalyzeRequest = AnalyzeRequest(),
    svc: SessionService = Depends(get_session_service),
) -> EnrichmentAnalyzeResponse:
    """AI suggests how to enrich the L0 datum back to L1 vector."""
    from intuitiveness.services.enrichment_suggester import suggest_enrichment

    state = svc.get(session_id)
    if state["current_level"] != 0:
        raise HTTPException(status_code=409, detail="Enrichment analysis is only available at L0.")

    summary = state.get("summary", {})
    parent_info = {
        "aggregation_method": summary.get("aggregation_method", ""),
        "parent_name": summary.get("parent_name", ""),
        "parent_length": summary.get("parent_length", 0),
    }

    result = suggest_enrichment(summary.get("value"), parent_info, intent=body.intent)
    logger.warning("ENRICHMENT-ANALYZE result: method=%s, explanation=%s", result.get("method"), (result.get("explanation") or "")[:100])
    return EnrichmentAnalyzeResponse(**result)


class DimensionAnalyzeResponse(BaseModel):
    explanation: str = ""
    confidence: str = ""
    code: str = ""
    proposed_columns: List[str] = []
    sample_distribution: dict = {}
    error: Optional[str] = None


@router.post("/sessions/{session_id}/dimension-analyze", response_model=DimensionAnalyzeResponse)
def dimension_analyze(
    session_id: str,
    body: AnalyzeRequest = AnalyzeRequest(),
    svc: SessionService = Depends(get_session_service),
) -> DimensionAnalyzeResponse:
    """AI writes code to add dimensions for L1→L2 ascent."""
    from intuitiveness.services.dimension_suggester import suggest_dimensions

    state = svc.get(session_id)
    if state["current_level"] != 1:
        raise HTTPException(status_code=409, detail="Dimension analysis is only available at L1.")

    session = svc._load(session_id)
    series = session.current_dataset.get_data()
    vector_info = {
        "name": getattr(series, "name", "value"),
        "length": len(series) if hasattr(series, "__len__") else 0,
        "min": round(float(series.min()), 2) if hasattr(series, "min") and series.notna().any() else None,
        "max": round(float(series.max()), 2) if hasattr(series, "max") and series.notna().any() else None,
        "mean": round(float(series.mean()), 2) if hasattr(series, "mean") and series.notna().any() else None,
        "sample_index": [str(i) for i in series.index[:10]],
        "sample_values": [str(v) for v in series.dropna()[:10]],
    }

    result = suggest_dimensions(vector_info, intent=body.intent)

    # Run code on real data for distribution preview
    code = result.get("code", "")
    if code:
        try:
            from intuitiveness.services.dimension_suggester import execute_dimension_code
            preview_df = execute_dimension_code(series.head(200), code)
            for col in preview_df.columns:
                if col != "value":
                    dist = preview_df[col].value_counts().to_dict()
                    result["sample_distribution"] = {str(k): int(v) for k, v in dist.items()}
                    break
        except Exception as exc:
            logger.warning("DIMENSION preview failed: %s", exc)

    logger.warning("DIMENSION-ANALYZE result: cols=%s, code=%s", result.get("proposed_columns"), (result.get("code") or "")[:150])
    return DimensionAnalyzeResponse(**result)


class DimensionConfirmRequest(BaseModel):
    code: str


@router.post("/sessions/{session_id}/dimension-confirm", response_model=SessionState)
def dimension_confirm(
    session_id: str,
    body: DimensionConfirmRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Execute AI's dimension code and ascend to L2."""
    from intuitiveness.services.dimension_suggester import execute_dimension_code

    state = svc.get(session_id)
    if state["current_level"] != 1:
        raise HTTPException(status_code=409, detail="Can only confirm dimensions at L1.")

    session = svc._load(session_id)
    series = session.current_dataset.get_data()
    built_df = execute_dimension_code(series, body.code)

    logger.warning("DIMENSION-CONFIRM: %d cols, %d rows", len(built_df.columns), len(built_df))
    session.ascend(prebuilt_dataframe=built_df)
    svc._save(session)
    return svc.state_of(session)


class LinkageAnalyzeResponse(BaseModel):
    proposed_dimensions: List[str] = []
    proposed_relationships: List[str] = []
    explanation: str = ""
    confidence: str = ""
    graph_description: str = ""
    available_dimensions: List[str] = []
    error: Optional[str] = None


@router.post("/sessions/{session_id}/linkage-analyze", response_model=LinkageAnalyzeResponse)
def linkage_analyze(
    session_id: str,
    body: AnalyzeRequest = AnalyzeRequest(),
    svc: SessionService = Depends(get_session_service),
) -> LinkageAnalyzeResponse:
    """AI suggests linkages for L2→L3 ascent."""
    from intuitiveness.services.linkage_suggester import suggest_linkage
    from intuitiveness.ascent.dimensions import DimensionRegistry

    state = svc.get(session_id)
    if state["current_level"] != 2:
        raise HTTPException(status_code=409, detail="Linkage analysis is only available at L2.")

    session = svc._load(session_id)
    df = session.current_dataset.get_data()
    table_info = {
        "columns": list(df.columns) if hasattr(df, "columns") else [],
        "row_count": len(df) if hasattr(df, "__len__") else 0,
        "categories": list(df["category"].unique()) if "category" in getattr(df, "columns", []) else [],
    }

    registry = DimensionRegistry.get_instance()
    available = [d.name for d in registry.get_all()] if hasattr(registry, "get_all") else []

    ascend_moves = state.get("available_moves", {}).get("ascend", [])
    if ascend_moves and isinstance(ascend_moves[0], dict):
        dims_from_moves = [d["name"] for d in ascend_moves[0].get("dimensions", []) if isinstance(d, dict)]
        if dims_from_moves:
            available = dims_from_moves

    result = suggest_linkage(table_info, available, intent=body.intent)
    logger.warning("LINKAGE-ANALYZE result: dims=%s, rels=%s", result.get("proposed_dimensions"), result.get("proposed_relationships"))
    return LinkageAnalyzeResponse(**result)


class EntityConfirmRequest(BaseModel):
    catalog: List[dict]
    join_plan: dict = {}
    column_transforms: dict = {}


@router.post("/sessions/{session_id}/entity-preview")
def entity_preview(
    session_id: str,
    body: EntityConfirmRequest,
    svc: SessionService = Depends(get_session_service),
) -> dict:
    """Dry-run the join and return row count + sample rows without persisting anything."""
    from intuitiveness.services.entity_matcher import execute_join

    session = svc._load(session_id)
    data = session.current_dataset.get_data()
    if not isinstance(data, dict):
        raise HTTPException(status_code=409, detail="No multi-source payload at current level.")

    import pandas as pd
    payload: dict = {}
    for name, val in data.items():
        if isinstance(val, pd.DataFrame):
            payload[name] = val
        elif isinstance(val, str):
            import zlib, base64
            raw = zlib.decompress(base64.b64decode(val))
            import json as _json
            records = _json.loads(raw)
            payload[name] = pd.DataFrame(records)

    join_plan = body.join_plan or {}
    if not join_plan.get("join_key"):
        for entry in body.catalog:
            if len(entry.get("mappings", [])) >= 2:
                join_plan["join_key"] = entry.get("concept", "")
                join_plan["join_type"] = "inner"
                break

    # Sample for speed — run join on first 200 rows of each source
    sampled = {k: v.head(200) for k, v in payload.items()}
    try:
        merged, _ = execute_join(sampled, join_plan, body.catalog, body.column_transforms)
    except Exception as exc:
        return {"row_count": 0, "unmatched_count": 0, "sample_rows": [], "sample_columns": [], "warnings": [str(exc)]}

    first_size = len(next(iter(sampled.values())))
    unmatched = max(0, first_size - len(merged))
    warnings = []
    if len(merged) == 0:
        warnings.append("0 rows matched — try excluding a join concept (e.g. Year/Session if the datasets cover different years)")

    sample_cols = list(merged.columns)
    sample_rows = []
    for _, row in merged.head(3).iterrows():
        r = {}
        for c in sample_cols:
            v = row[c]
            r[c] = None if (isinstance(v, float) and v != v) else (v if isinstance(v, (str, int, float, bool, type(None))) else str(v))
        sample_rows.append(r)

    return {"row_count": len(merged), "unmatched_count": unmatched, "sample_rows": sample_rows, "sample_columns": sample_cols, "warnings": warnings}


@router.post("/sessions/{session_id}/entity-confirm", response_model=SessionState)
def entity_confirm(
    session_id: str,
    body: EntityConfirmRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Confirm the entity matching and descend to L3 with the merged data table."""
    import networkx as nx
    from intuitiveness.services.entity_matcher import execute_join

    state = svc.get(session_id)
    if state["current_level"] != 4:
        raise HTTPException(status_code=409, detail="Can only confirm entity matching at L4.")

    catalog = body.catalog
    transforms = body.column_transforms

    def builder_func(payload):
        if not isinstance(payload, dict):
            import networkx as nx
            return nx.DiGraph()

        # Build a proper join plan from the catalog
        join_plan = body.join_plan or {}
        if not join_plan.get("join_key"):
            for entry in catalog:
                if len(entry.get("mappings", [])) >= 2:
                    join_plan["join_key"] = entry.get("concept", "")
                    join_plan["join_type"] = "inner"
                    break

        # Use execute_join to produce a MERGED DataFrame with renamed columns
        merged, col_source_map = execute_join(payload, join_plan, catalog, transforms)
        logger.warning("ENTITY-CONFIRM merged: %d rows × %d cols — %s", len(merged), len(merged.columns), list(merged.columns))

        # Build a graph from the merged data
        import networkx as nx
        import json as _json
        g = nx.DiGraph()
        g.graph["_catalog"] = _json.dumps(catalog, default=str)
        g.graph["_sources"] = _json.dumps({
            name: {"rows": len(df), "columns": list(df.columns)}
            for name, df in payload.items()
        }, default=str)
        g.graph["_col_sources"] = _json.dumps(col_source_map, default=str)

        for idx, row in merged.iterrows():
            node_id = f"merged:{idx}"
            attrs = {}
            for c in merged.columns:
                v = row[c]
                if isinstance(v, float) and v != v:
                    attrs[c] = None
                else:
                    attrs[c] = v
            g.add_node(node_id, **attrs)

        return g

    return svc.descend(session_id, params={"builder_func": builder_func})


@router.post("/sessions/{session_id}/entity-match", response_model=SessionState)
def entity_match(
    session_id: str,
    body: EntityMatchRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Use an LLM to match entities across sources, execute the join,
    and descend to L3 with the result as a knowledge graph."""
    import networkx as nx
    from intuitiveness.services.entity_matcher import match_entities, execute_join

    state = svc.get(session_id)
    if state["current_level"] != 4:
        raise HTTPException(status_code=409, detail="Entity matching is only available at L4.")

    session = svc._load(session_id)
    data = session.current_dataset.get_data()
    if not isinstance(data, dict) or len(data) < 2:
        raise HTTPException(status_code=422, detail="Need at least 2 sources for entity matching.")

    relationships = [r.model_dump() for r in body.relationships] if body.relationships else []
    result = match_entities(data, relationships)

    if result.get("error"):
        raise HTTPException(status_code=502, detail=result["error"])

    catalog = result.get("catalog", [])
    explanation = result.get("explanation", "")
    transforms = result.get("column_transforms", {})

    def builder_func(payload):
        g = nx.DiGraph()
        # Concept nodes
        for entry in catalog:
            concept = entry["concept"]
            g.add_node(concept, node_type="concept", description=entry.get("description", ""))
            for m in entry.get("mappings", []):
                col_id = f"{m['source']}:{m['column']}"
                g.add_node(col_id, node_type="column", source=m["source"],
                           column=m["column"], notes=m.get("notes", ""))
                transform = transforms.get(col_id, "none")
                g.add_edge(concept, col_id, relationship="maps_to", transform=transform)
        # Source nodes linking to their columns
        if isinstance(payload, dict):
            for source_name, df in payload.items():
                g.add_node(source_name, node_type="source",
                           rows=len(df), columns=len(df.columns))
                for col in df.columns:
                    col_id = f"{source_name}:{col}"
                    if col_id not in g:
                        g.add_node(col_id, node_type="column", source=source_name,
                                   column=col, notes="")
                    g.add_edge(source_name, col_id, relationship="has_column")
        return g

    return svc.descend(session_id, params={"builder_func": builder_func})
