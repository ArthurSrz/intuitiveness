"""
Typed transition parameters for the unified Redesigner engine.

Spec 015 (FR-009): transitions are invoked through explicit, well-typed
per-transition parameter objects — never opaque ``**kwargs`` nor injected
``Callable`` builders. Each dataclass corresponds to exactly one adjacent
level transition.

Descent (reduce_complexity):  L4→L3, L3→L2, L2→L1, L1→L0
Ascent  (increase_complexity): L0→L1, L1→L2, L2→L3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class TransitionParams:
    """Marker base class for all transition parameter objects."""


# --------------------------------------------------------------------------- #
# Descent params
# --------------------------------------------------------------------------- #

@dataclass
class L4toL3Params(TransitionParams):
    """L4→L3: build a graph / linked structure from raw sources.

    ``model`` describes how to connect the raw sources (entities, keys,
    relationships). When the graph has already been built by an upstream
    transform (e.g. LLM-assisted entity discovery, which is non-deterministic
    and therefore must not be re-derived), pass it via ``prebuilt_graph``.
    """
    model: Optional[Any] = None
    prebuilt_graph: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class L3toL2Params(TransitionParams):
    """L3→L2: isolate a domain-specific table from the graph/linked data.

    ``prebuilt_table`` lets a caller (e.g. NavigationSession adapting a UI
    ``query_func``) supply the already-extracted table, so the engine wraps it
    rather than re-deriving — preserving legacy query semantics during cutover.
    """
    domains: List[str] = field(default_factory=list)
    prebuilt_table: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class L2toL1Params(TransitionParams):
    """L2→L1: extract a single column (optionally filtered) as a vector."""
    column: Optional[str] = None
    filter_query: Optional[str] = None
    prebuilt_series: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class L1toL0Params(TransitionParams):
    """L1→L0: aggregate a vector to a single atomic datum."""
    aggregation: str = "sum"
    prebuilt_value: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Ascent params (mirror)
# --------------------------------------------------------------------------- #

@dataclass
class L0toL1Params(TransitionParams):
    """L0→L1: reconstruct a vector from the atomic datum via an enrichment."""
    enrichment_function: Optional[str] = None
    prebuilt_series: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class L1toL2Params(TransitionParams):
    """L1→L2: add classification dimensions to a vector, producing a table."""
    dimensions: List[str] = field(default_factory=list)
    prebuilt_dataframe: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class L2toL3Params(TransitionParams):
    """L2→L3: add analytic dimensions / links, producing a graph/linked set."""
    dimensions: List[str] = field(default_factory=list)
    relationships: List[Any] = field(default_factory=list)
    source_column: Optional[str] = None
    entity_column: Optional[str] = None
    value_column: Optional[str] = None
    prebuilt_dataframe: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# Lookup: (input_level_value, output_level_value) -> expected params class.
# Used by the engine to validate that the caller passed the right params type.
PARAMS_FOR_EDGE = {
    (4, 3): L4toL3Params,
    (3, 2): L3toL2Params,
    (2, 1): L2toL1Params,
    (1, 0): L1toL0Params,
    (0, 1): L0toL1Params,
    (1, 2): L1toL2Params,
    (2, 3): L2toL3Params,
}
