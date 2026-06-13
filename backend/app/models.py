"""Pydantic request/response models for the REST API (spec 017, T008).

These mirror the `SessionService` projection and the per-edge engine params
(`intuitiveness/redesign/params.py`). Request models use `extra="allow"` so the
engine keeps ownership of the exact param contract (FR-003) — the API documents
the common fields without re-validating what the core already validates. The
edge-specific fields below exist mainly so they appear in the OpenAPI schema the
frontend's TypeScript client is generated from (SC-003).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------- #
# Sessions
# --------------------------------------------------------------------------- #
class CreateSessionRequest(BaseModel):
    """Create a session from a named demo dataset (or, later, an upload)."""
    source: str = Field(
        default="demo:school_scores",
        description="Dataset source, e.g. 'demo:school_scores' | 'demo:ademe' | 'demo:energy'.",
        examples=["demo:school_scores"],
    )


class SessionState(BaseModel):
    """The projection every mutating/read call returns (see `state_of`)."""
    session_id: str
    current_level: int = Field(description="0–4; the level the session now sits at.")
    current_node_id: str
    summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Shape/counts of the current artifact; includes `value` at L0.",
    )
    available_moves: Dict[str, List[Any]] = Field(
        default_factory=dict,
        description="{'descend': [...], 'ascend': [...]} valid next transitions.",
    )
    options: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Introspection for per-edge controls: builders, aggregations, the "
            "current node's columns, and source names. Ascent option lists "
            "(enrichment_functions, dimensions) ride on available_moves."
        ),
    )


class SessionSummary(BaseModel):
    session_id: str
    title: str


# --------------------------------------------------------------------------- #
# Transitions (engine) — fields documented, extras allowed
# --------------------------------------------------------------------------- #
class DescendRequest(BaseModel):
    """`reduce_complexity(target = current-1)`. Fields are per-edge; only the
    relevant ones apply at each level (extras pass through to the engine)."""
    model_config = ConfigDict(extra="allow")

    # L4→L3: pick a named server-side graph builder + its config.
    builder: Optional[str] = Field(default=None, description="L4→L3 graph builder name, e.g. 'rows_as_nodes' | 'bipartite'.")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Builder kwargs (e.g. {'id_column': 'id'}).")
    # L3→L2: domain categorization (optionally semantic via embeddings).
    domains: Optional[List[str]] = Field(default=None, description="L3→L2 category labels, e.g. ['high score','low score'].")
    use_semantic: Optional[bool] = Field(default=None, description="L3→L2 use embedding similarity for matching.")
    threshold: Optional[float] = Field(default=None, description="L3→L2 semantic similarity threshold (0–1).")
    category_column: Optional[str] = Field(default=None, description="L3→L2 column to categorize by (overrides auto-detection).")
    # L2→L1: pick the column to reduce to a vector.
    column: Optional[str] = Field(default=None, description="L2→L1 column to keep.")
    filter_query: Optional[str] = Field(default=None, description="L2→L1 optional pandas query filter.")
    # L1→L0: aggregation.
    aggregation: Optional[str] = Field(default=None, description="L1→L0 aggregation: 'mean' | 'sum' | 'count' | ...")


class AscendRequest(BaseModel):
    """`increase_complexity(target = current+1)`. Never reaches L4.

    Field names match the engine's ascent adapter kwargs (`_ascent_params`);
    all are optional because each edge falls back to registry defaults (and L0→L1
    reconstructs from the persisted parent vector — the spec-015 T007 fix).
    """
    model_config = ConfigDict(extra="allow")

    enrichment_func: Optional[str] = Field(default=None, description="L0→L1 enrichment name; omit to use parent-data 'source_expansion' / defaults.")
    dimensions: Optional[List[str]] = Field(default=None, description="L1→L2 and L2→L3 dimension names; omit for registry defaults.")
    relationships: Optional[List[str]] = Field(default=None, description="L2→L3 relationship names.")
    source_column: Optional[str] = Field(default=None, description="L2→L3 column to derive from (defaults to 'value').")


# --------------------------------------------------------------------------- #
# Navigation tree (branch / time-travel / prune / archive)
# --------------------------------------------------------------------------- #
class NodeIdRequest(BaseModel):
    node_id: str = Field(description="Target tree node id.")


class BranchFromRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    node_id: str
    action: str = Field(description="'descend' | 'ascend' — the transition to run off the node.")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Per-edge params (same shape as descend/ascend).")


class MutationCount(BaseModel):
    """Return shape for prune/archive — how many nodes were affected."""
    count: int


# --------------------------------------------------------------------------- #
# Export / import (spec-015 contract)
# --------------------------------------------------------------------------- #
class ImportRequest(BaseModel):
    """A full-fidelity `session_export` record to rehydrate into a new session."""
    model_config = ConfigDict(extra="allow")
    schema_version: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tree: Optional[Dict[str, Any]] = None


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
class DepStatus(BaseModel):
    configured: bool
    ok: bool
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = Field(description="'ok' if the app is up (deps may degrade gracefully).")
    deps: Dict[str, DepStatus]
