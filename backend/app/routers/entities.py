"""Entity discovery, preview, confirmation, and matching at L4→L3.

POST /sessions/{id}/entity-analyze   — LLM discovers entities across sources
POST /sessions/{id}/entity-preview   — dry-run join, return sample rows
POST /sessions/{id}/entity-confirm   — execute join, build graph, descend to L3
POST /sessions/{id}/entity-match     — one-shot: match + build catalog graph
"""

from __future__ import annotations

import logging
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..deps import get_session_service
from ..models import SessionState
from ..service import SessionService

logger = logging.getLogger("intuitiveness.api.entities")

router = APIRouter(prefix="/sessions", tags=["entities"])


# --------------------------------------------------------------------------- #
# Request / response models
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


class EntityConfirmRequest(BaseModel):
    catalog: List[dict]
    join_plan: dict = {}
    column_transforms: dict = {}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _require_l4_multi_source(state: dict, session) -> dict:
    """Validate we're at L4 with multiple sources. Returns the payload dict."""
    if state["current_level"] != 4:
        raise HTTPException(status_code=409, detail="Entity matching is only available at L4.")
    data = session.current_dataset.get_data()
    if not isinstance(data, dict) or len(data) < 2:
        raise HTTPException(status_code=422, detail="Need at least 2 sources for entity matching.")
    return data


def _resolve_payload(data: dict) -> dict:
    """Decode compressed DataFrames in the session payload."""
    payload: dict = {}
    for name, val in data.items():
        if isinstance(val, pd.DataFrame):
            payload[name] = val
        elif isinstance(val, str):
            import zlib, base64, json as _json
            raw = zlib.decompress(base64.b64decode(val))
            records = _json.loads(raw)
            payload[name] = pd.DataFrame(records)
    return payload


def _resolve_join_plan(join_plan: dict, catalog: list) -> dict:
    """Fill in missing join_key from the catalog if not explicitly provided."""
    if not join_plan.get("join_key"):
        for entry in catalog:
            if len(entry.get("mappings", [])) >= 2:
                join_plan["join_key"] = entry.get("concept", "")
                join_plan["join_type"] = "inner"
                break
    return join_plan


def build_entity_graph(payload, catalog, join_plan, transforms):
    """Join multi-source payload into a merged DataFrame, then build a NetworkX
    DiGraph with metadata."""
    import networkx as nx
    import json as _json
    from intuitiveness.services.entity_matcher import execute_join

    merged_df, col_source_map = execute_join(payload, join_plan, catalog, transforms)

    before_dedup = len(merged_df)
    merged_df = merged_df.drop_duplicates()
    if len(merged_df) < before_dedup:
        logger.warning("build_entity_graph: dedup removed %d rows (%d → %d)", before_dedup - len(merged_df), before_dedup, len(merged_df))

    MAX_ROWS = 500_000
    if len(merged_df) > MAX_ROWS:
        logger.warning("Merged result %d rows exceeds cap %d, truncating", len(merged_df), MAX_ROWS)
        merged_df = merged_df.head(MAX_ROWS)

    g = nx.DiGraph()
    g.graph["_catalog"] = _json.dumps(catalog, default=str)
    g.graph["_sources"] = _json.dumps({
        name: {"rows": len(df), "columns": list(df.columns)}
        for name, df in payload.items()
    }, default=str)
    g.graph["_col_sources"] = _json.dumps(col_source_map, default=str)

    def _sanitize(v):
        if isinstance(v, float) and v != v:
            return None
        return v

    records = merged_df.to_dict("records")
    g.add_nodes_from(
        (f"merged:{i}", {c: _sanitize(v) for c, v in attrs.items()})
        for i, attrs in enumerate(records)
    )

    return g


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@router.post("/{session_id}/entity-analyze", response_model=EntityAnalyzeResponse)
def entity_analyze(
    session_id: str,
    body: EntityMatchRequest,
    svc: SessionService = Depends(get_session_service),
) -> EntityAnalyzeResponse:
    """Three-tier entity discovery without descending. Returns catalog for user validation."""
    from intuitiveness.services.entity_discovery import discover_entities

    state = svc.get(session_id)
    session = svc._load(session_id)
    data = _require_l4_multi_source(state, session)

    result = discover_entities(data, use_llm=True)

    return EntityAnalyzeResponse(
        catalog=result.catalog,
        join_plan={},
        column_transforms={},
        explanation=result.explanation,
        error=None,
    )


@router.post("/{session_id}/entity-preview")
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

    payload = _resolve_payload(data)
    join_plan = _resolve_join_plan(body.join_plan or {}, body.catalog)

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


@router.post("/{session_id}/entity-confirm", response_model=SessionState)
def entity_confirm(
    session_id: str,
    body: EntityConfirmRequest,
    svc: SessionService = Depends(get_session_service),
) -> SessionState:
    """Confirm the entity matching and descend to L3 with the merged data table."""
    state = svc.get(session_id)
    if state["current_level"] != 4:
        raise HTTPException(status_code=409, detail="Can only confirm entity matching at L4.")

    catalog = body.catalog
    transforms = body.column_transforms
    join_plan = _resolve_join_plan(body.join_plan or {}, catalog)

    def builder_func(payload):
        return build_entity_graph(payload, catalog, join_plan, transforms)

    from app.storage import get_database_storage
    db = get_database_storage()

    def builder_func_with_storage(payload):
        graph = builder_func(payload)
        if db is not None:
            try:
                if isinstance(payload, dict):
                    for name, df in payload.items():
                        db.store_dataframe(session_id, "L4-root", level=4, df=df, table_name=name)
                db.store_graph(session_id, "L3-entity-confirm", graph)
                logger.info("DB storage: persisted L4 sources + L3 graph for session %s", session_id)
            except Exception as exc:
                logger.warning("DB storage write failed (non-fatal): %s", exc)
        return graph

    parent_node_id = None
    try:
        pre_session = svc._load(session_id)
        parent_node_id = pre_session.navigation_tree.current_id
    except Exception:
        pass

    result = svc.descend(session_id, params={"builder_func": builder_func_with_storage})

    if db is not None:
        try:
            post_session = svc._load(session_id)
            result_node_id = post_session.navigation_tree.current_id
            db.store_tree_node(
                session_id, result_node_id, parent_node_id,
                level=3, action="descend", params={},
            )
            logger.info("Tree node persisted: %s -> %s", parent_node_id, result_node_id)
        except Exception as e:
            logger.warning("Tree node persistence failed: %s", e)

    return result


@router.post("/{session_id}/entity-match", response_model=SessionState)
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
    session = svc._load(session_id)
    data = _require_l4_multi_source(state, session)

    relationships = [r.model_dump() for r in body.relationships] if body.relationships else []
    result = match_entities(data, relationships)

    if result.get("error"):
        raise HTTPException(status_code=502, detail=result["error"])

    catalog = result.get("catalog", [])
    explanation = result.get("explanation", "")
    transforms = result.get("column_transforms", {})

    def builder_func(payload):
        g = nx.DiGraph()
        for entry in catalog:
            concept = entry["concept"]
            g.add_node(concept, node_type="concept", description=entry.get("description", ""))
            for m in entry.get("mappings", []):
                col_id = f"{m['source']}:{m['column']}"
                g.add_node(col_id, node_type="column", source=m["source"],
                           column=m["column"], notes=m.get("notes", ""))
                transform = transforms.get(col_id, "none")
                g.add_edge(concept, col_id, relationship="maps_to", transform=transform)
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
