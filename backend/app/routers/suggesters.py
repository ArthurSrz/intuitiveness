"""LLM-powered analyze/confirm endpoints for each level transition.

Each pair follows the same pattern:
  1. POST /{session_id}/{name}-analyze  — LLM suggests code/params
  2. POST /{session_id}/{name}-confirm  — execute the code, descend or ascend

Descent: domain (L3→L2), column (L2→L1), aggregation (L1→L0)
Ascent:  enrichment (L0→L1), dimension (L1→L2), linkage (L2→L3)
Other:   intent-suggest (at L0), datum-describe (at L0)
"""

from __future__ import annotations

import logging
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from intuitiveness.services.transition_models import (
    AggregationSuggestion,
    ColumnSuggestion,
    DatumDescription,
    DimensionSuggestion,
    DomainSuggestion,
    EnrichmentSuggestion,
    IntentSuggestion,
    LinkageSuggestion,
)

from ..deps import get_session_service
from ..models import SessionState
from ..service import SessionService

logger = logging.getLogger("intuitiveness.api.suggesters")

router = APIRouter(prefix="/sessions", tags=["suggesters"])


# --------------------------------------------------------------------------- #
# Shared request model
# --------------------------------------------------------------------------- #

class AnalyzeRequest(BaseModel):
    intent: str = ""


# --------------------------------------------------------------------------- #
# Domain: L3 → L2 (descent)
# --------------------------------------------------------------------------- #

class DomainAnalyzeResponse(DomainSuggestion):
    confidence: str = ""
    sample_distribution: dict = {}
    columns: List[str] = []
    error: Optional[str] = None


class DomainConfirmRequest(BaseModel):
    code: str
    domains: List[str] = []


@router.post("/{session_id}/domain-analyze", response_model=DomainAnalyzeResponse)
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


@router.post("/{session_id}/domain-confirm", response_model=SessionState)
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
    try:
        categorized = execute_categorization(data, body.code)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Code execution failed: {str(e)}")

    session.descend(query_func=lambda _data: categorized)
    svc._save(session)
    return svc.state_of(session)


# --------------------------------------------------------------------------- #
# Column: L2 → L1 (descent)
# --------------------------------------------------------------------------- #

class ColumnAnalyzeResponse(ColumnSuggestion):
    confidence: str = ""
    columns: List[str] = []
    preview_stats: dict = {}
    error: Optional[str] = None


class ColumnConfirmRequest(BaseModel):
    code: str
    column: str = ""


@router.post("/{session_id}/column-analyze", response_model=ColumnAnalyzeResponse)
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


@router.post("/{session_id}/column-confirm", response_model=SessionState)
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
    try:
        series = execute_column_extraction(data, body.code)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Code execution failed: {str(e)}")
    col_name = body.column or (series.name if series.name else "value")
    series.name = col_name

    session.descend(column=col_name, prebuilt_series=series)
    svc._save(session)
    return svc.state_of(session)


# --------------------------------------------------------------------------- #
# Aggregation: L1 → L0 (descent)
# --------------------------------------------------------------------------- #

class AggregationAnalyzeResponse(AggregationSuggestion):
    confidence: str = ""
    vector_profile: dict = {}
    error: Optional[str] = None


class AggregationConfirmRequest(BaseModel):
    code: str
    aggregation: str = "mean"


@router.post("/{session_id}/aggregation-analyze", response_model=AggregationAnalyzeResponse)
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


@router.post("/{session_id}/aggregation-confirm", response_model=SessionState)
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


# --------------------------------------------------------------------------- #
# Intent + Datum: at L0
# --------------------------------------------------------------------------- #

class IntentSuggestResponse(IntentSuggestion):
    error: Optional[str] = None


def _build_descent_story(session, svc, session_id: str) -> dict:
    """Walk the navigation tree and build a rich context for intent suggestion.

    Collects what happened at each level during descent so the LLM can
    suggest questions grounded in the actual data, not generic templates.
    """
    tree = session.navigation_tree
    current_id = tree.current_id
    story = {"steps": []}

    # Walk from current node up to root, collecting each level's context
    node_id = current_id
    while node_id:
        node = tree.nodes.get(node_id)
        if not node:
            break
        step = {
            "level": node.level.value,
            "action": node.action,
            "decision": node.decision_description,
        }
        ds = node.dataset_snapshot
        if ds:
            s = ds.summary() if hasattr(ds, "summary") else {}
            level = node.level.value
            if level == 4:
                data = ds.get_data()
                if isinstance(data, dict):
                    step["sources"] = {
                        name: {"rows": len(df), "columns": list(df.columns)[:10]}
                        for name, df in data.items()
                        if hasattr(df, "columns")
                    }
            elif level == 3:
                data = ds.get_data()
                if hasattr(data, "columns"):
                    step["columns"] = list(data.columns)[:15]
                elif hasattr(data, "number_of_nodes"):
                    step["node_count"] = data.number_of_nodes()
                    step["edge_count"] = data.number_of_edges()
            elif level == 2:
                data = ds.get_data()
                if hasattr(data, "columns"):
                    step["columns"] = list(data.columns)[:10]
                    if "category" in data.columns:
                        step["categories"] = list(data["category"].dropna().unique()[:8])
                    step["row_count"] = len(data)
            elif level == 1:
                data = ds.get_data()
                if hasattr(data, "describe"):
                    desc = data.describe()
                    step["stats"] = {
                        "count": int(desc.get("count", 0)),
                        "mean": round(float(desc["mean"]), 2) if "mean" in desc.index else None,
                        "min": round(float(desc["min"]), 2) if "min" in desc.index else None,
                        "max": round(float(desc["max"]), 2) if "max" in desc.index else None,
                    }
                    step["name"] = getattr(data, "name", "value")
            elif level == 0:
                step["value"] = s.get("value")
                step["description"] = s.get("description")
                step["aggregation"] = s.get("aggregation_method")

        story["steps"].append(step)
        node_id = node.parent_id

    story["steps"].reverse()  # root → leaf order
    return story


@router.post("/{session_id}/intent-suggest", response_model=IntentSuggestResponse)
def intent_suggest(
    session_id: str,
    svc: SessionService = Depends(get_session_service),
) -> IntentSuggestResponse:
    """AI suggests analytical intents based on the descent path."""
    from intuitiveness.services.intent_suggester import suggest_intents

    session = svc._load(session_id)

    try:
        descent_story = _build_descent_story(session, svc, session_id)
    except Exception as exc:
        logger.warning("Failed to build descent story: %s", exc)
        descent_story = {"steps": []}

    result = suggest_intents(descent_story)
    logger.warning("INTENT-SUGGEST result: %s", [i.get("short") for i in result.get("intents", [])])
    return IntentSuggestResponse(**result)


class DatumDescribeResponse(DatumDescription):
    error: Optional[str] = None


@router.post("/{session_id}/datum-describe", response_model=DatumDescribeResponse)
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


# --------------------------------------------------------------------------- #
# Enrichment: L0 → L1 (ascent)
# --------------------------------------------------------------------------- #

class EnrichmentAnalyzeResponse(EnrichmentSuggestion):
    confidence: str = ""
    preview_stats: dict = {}
    error: Optional[str] = None


class EnrichmentConfirmRequest(BaseModel):
    code: str


@router.post("/{session_id}/enrichment-analyze", response_model=EnrichmentAnalyzeResponse)
def enrichment_analyze(
    session_id: str,
    body: AnalyzeRequest = AnalyzeRequest(),
    svc: SessionService = Depends(get_session_service),
) -> EnrichmentAnalyzeResponse:
    """AI writes code to rebuild the L0 datum back to L1 vector."""
    from intuitiveness.services.enrichment_suggester import suggest_enrichment, execute_enrichment_code

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
    logger.warning("ENRICHMENT-ANALYZE result: code=%s, explanation=%s", (result.get("code") or "")[:100], (result.get("explanation") or "")[:100])

    code = result.get("code", "")
    preview_stats = {}
    if code:
        try:
            session = svc._load(session_id)
            dataset = session.current_dataset
            scalar = dataset.get_data()
            parent_series = dataset.get_parent_data()
            if parent_series is not None:
                preview_parent = parent_series.head(200)
                preview_series = execute_enrichment_code(scalar, preview_parent, code)
                preview_stats = {
                    "count": int(len(preview_series)),
                    "mean": round(float(preview_series.mean()), 4) if preview_series.dtype.kind in "iufb" else None,
                    "min": round(float(preview_series.min()), 4) if preview_series.dtype.kind in "iufb" else None,
                    "max": round(float(preview_series.max()), 4) if preview_series.dtype.kind in "iufb" else None,
                }
        except Exception as exc:
            logger.warning("ENRICHMENT-ANALYZE preview failed: %s", exc, exc_info=True)

    return EnrichmentAnalyzeResponse(
        code=code,
        explanation=result.get("explanation", ""),
        confidence=result.get("confidence", ""),
        preview_description=result.get("preview_description", ""),
        preview_stats=preview_stats,
        error=result.get("error"),
    )


@router.post("/{session_id}/enrichment-confirm", response_model=SessionState)
def enrichment_confirm(
    session_id: str,
    body: EnrichmentConfirmRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Execute AI's enrichment code and ascend to L1."""
    from intuitiveness.services.enrichment_suggester import execute_enrichment_code

    state = svc.get(session_id)
    if state["current_level"] != 0:
        raise HTTPException(status_code=409, detail="Can only confirm enrichment at L0.")

    session = svc._load(session_id)
    dataset = session.current_dataset
    scalar = dataset.get_data()
    parent_series = dataset.get_parent_data()

    if parent_series is None:
        raise HTTPException(status_code=422, detail="No parent data available for enrichment.")

    try:
        result_series = execute_enrichment_code(scalar, parent_series, body.code)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Code execution failed: {str(e)}")

    logger.warning("ENRICHMENT-CONFIRM: %d values produced", len(result_series))
    session.ascend(prebuilt_series=result_series)
    svc._save(session)
    return svc.state_of(session)


# --------------------------------------------------------------------------- #
# Dimension: L1 → L2 (ascent)
# --------------------------------------------------------------------------- #

class DimensionAnalyzeResponse(DimensionSuggestion):
    confidence: str = ""
    sample_distribution: dict = {}
    error: Optional[str] = None


class DimensionConfirmRequest(BaseModel):
    code: str


@router.post("/{session_id}/dimension-analyze", response_model=DimensionAnalyzeResponse)
def dimension_analyze(
    session_id: str,
    body: AnalyzeRequest = AnalyzeRequest(),
    svc: SessionService = Depends(get_session_service),
) -> DimensionAnalyzeResponse:
    """AI writes code to add dimensions for L1→L2 ascent."""
    from intuitiveness.services.dimension_suggester import suggest_dimensions

    state = svc.get(session_id)
    logger.warning("DIMENSION-ANALYZE: session=%s current_level=%s intent=%r", session_id, state["current_level"], body.intent)
    if state["current_level"] != 1:
        logger.warning("DIMENSION-ANALYZE: REJECTED — level is %s not 1", state["current_level"])
        raise HTTPException(status_code=409, detail="Dimension analysis is only available at L1.")

    session = svc._load(session_id)
    raw_data = session.current_dataset.get_data()
    logger.warning("DIMENSION-ANALYZE: raw_data type=%s", type(raw_data).__name__)

    series = raw_data
    logger.warning("DIMENSION-ANALYZE: series dtype=%s len=%s name=%r notna_count=%s",
                   getattr(series, "dtype", "?"),
                   len(series) if hasattr(series, "__len__") else "?",
                   getattr(series, "name", "?"),
                   series.notna().sum() if hasattr(series, "notna") else "?")

    vector_info = {
        "name": getattr(series, "name", "value"),
        "length": len(series) if hasattr(series, "__len__") else 0,
        "min": round(float(series.min()), 2) if hasattr(series, "min") and series.notna().any() else None,
        "max": round(float(series.max()), 2) if hasattr(series, "max") and series.notna().any() else None,
        "mean": round(float(series.mean()), 2) if hasattr(series, "mean") and series.notna().any() else None,
        "sample_index": [str(i) for i in series.index[:10]],
        "sample_values": [str(v) for v in series.dropna()[:10]],
        "index_is_numeric": pd.api.types.is_integer_dtype(series.index) or pd.api.types.is_float_dtype(series.index),
        "dtypes": {"value": str(series.dtype)},
    }
    logger.warning("DIMENSION-ANALYZE: vector_info=%s", vector_info)

    result = suggest_dimensions(vector_info, intent=body.intent)
    logger.warning("DIMENSION-ANALYZE: suggest_dimensions returned keys=%s error=%r", list(result.keys()), result.get("error"))

    code = result.get("code", "")
    logger.warning("DIMENSION-ANALYZE: code present=%s len=%d", bool(code), len(code))
    if code:
        try:
            from intuitiveness.services.dimension_suggester import execute_dimension_code
            logger.warning("DIMENSION-ANALYZE: running preview on %d rows", min(200, len(series)))
            preview_df = execute_dimension_code(series.head(200), code)
            logger.warning("DIMENSION-ANALYZE: preview_df cols=%s shape=%s", list(preview_df.columns), preview_df.shape)
            for col in preview_df.columns:
                if col != "value":
                    dist = preview_df[col].value_counts().to_dict()
                    result["sample_distribution"] = {str(k): int(v) for k, v in dist.items()}
                    logger.warning("DIMENSION-ANALYZE: distribution for col=%r: %s", col, result["sample_distribution"])
                    break
        except Exception as exc:
            logger.warning("DIMENSION-ANALYZE preview FAILED: %s", exc, exc_info=True)

    logger.warning("DIMENSION-ANALYZE result: cols=%s, code=%s", result.get("proposed_columns"), (result.get("code") or "")[:150])
    return DimensionAnalyzeResponse(**result)


@router.post("/{session_id}/dimension-confirm", response_model=SessionState)
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
    try:
        built_df = execute_dimension_code(series, body.code)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Code execution failed: {str(e)}")

    logger.warning("DIMENSION-CONFIRM: %d cols, %d rows", len(built_df.columns), len(built_df))
    session.ascend(prebuilt_dataframe=built_df)
    svc._save(session)
    return svc.state_of(session)


# --------------------------------------------------------------------------- #
# Linkage: L2 → L3 (ascent)
# --------------------------------------------------------------------------- #

class LinkageAnalyzeResponse(LinkageSuggestion):
    confidence: str = ""
    sample_distribution: dict = {}
    error: Optional[str] = None


class LinkageConfirmRequest(BaseModel):
    code: str


@router.post("/{session_id}/linkage-analyze", response_model=LinkageAnalyzeResponse)
def linkage_analyze(
    session_id: str,
    body: AnalyzeRequest = AnalyzeRequest(),
    svc: SessionService = Depends(get_session_service),
) -> LinkageAnalyzeResponse:
    """AI writes code to add linkage columns for L2->L3 ascent."""
    from intuitiveness.services.linkage_suggester import suggest_linkage, execute_linkage_code
    from intuitiveness.ascent.dimensions import DimensionRegistry

    state = svc.get(session_id)
    if state["current_level"] != 2:
        raise HTTPException(status_code=409, detail="Linkage analysis is only available at L2.")

    session = svc._load(session_id)
    df = session.current_dataset.get_data()
    table_info = {
        "columns": list(df.columns) if hasattr(df, "columns") else [],
        "dtypes": {col: str(df[col].dtype) for col in df.columns} if hasattr(df, "columns") else {},
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
    logger.warning("LINKAGE-ANALYZE result: cols=%s, code=%s", result.get("proposed_columns"), (result.get("code") or "")[:150])

    code = result.get("code", "")
    sample_distribution: dict = {}
    if code:
        try:
            preview_df = execute_linkage_code(df.head(200), code)
            original_cols = set(df.columns)
            for col in preview_df.columns:
                if col not in original_cols:
                    dist = preview_df[col].value_counts().to_dict()
                    sample_distribution[col] = {str(k): int(v) for k, v in dist.items()}
        except Exception as exc:
            logger.warning("LINKAGE-ANALYZE preview failed: %s", exc, exc_info=True)

    return LinkageAnalyzeResponse(
        code=code,
        proposed_columns=result.get("proposed_columns", []),
        explanation=result.get("explanation", ""),
        confidence=result.get("confidence", ""),
        graph_description=result.get("graph_description", ""),
        sample_distribution=sample_distribution,
        error=result.get("error"),
    )


@router.post("/{session_id}/linkage-confirm", response_model=SessionState)
def linkage_confirm(
    session_id: str,
    body: LinkageConfirmRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Execute AI's linkage code and ascend to L3."""
    from intuitiveness.services.linkage_suggester import execute_linkage_code

    state = svc.get(session_id)
    if state["current_level"] != 2:
        raise HTTPException(status_code=409, detail="Can only confirm linkage at L2.")

    session = svc._load(session_id)
    df = session.current_dataset.get_data()
    try:
        linked_df = execute_linkage_code(df, body.code)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Code execution failed: {str(e)}")

    logger.warning("LINKAGE-CONFIRM: %d cols, %d rows", len(linked_df.columns), len(linked_df))
    session.ascend(prebuilt_dataframe=linked_df)
    svc._save(session)
    return svc.state_of(session)
