"""Server-side transform builders for descent edges that need a callable.

JSON can't carry Python callables, so the API selects a NAMED builder and the
service hands the resulting callable to `NavigationSession.descend()` exactly as
the Streamlit UI handed its own callables (the path proven by
tests/integration/test_session_cutover.py). The engine then wraps the produced
payload and stamps lineage — behavior is identical, just driven by JSON.

Builders are pure: dict-of-DataFrames (L4) or a payload in → a raw payload out
(nx.Graph / DataFrame). No LevelNDataset construction (the engine owns that).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import networkx as nx
import pandas as pd


def _single_frame(data: Any) -> pd.DataFrame:
    """L4 data is a {filename: DataFrame} dict; take or concat all frames."""
    if isinstance(data, dict):
        frames = [v for v in data.values() if isinstance(v, pd.DataFrame)]
        if not frames:
            raise ValueError("No DataFrames found in payload.")
        if len(frames) == 1:
            return frames[0]
        return pd.concat(frames, ignore_index=True)
    if isinstance(data, pd.DataFrame):
        return data
    raise ValueError(f"Unsupported L4 payload type: {type(data).__name__}")


def rows_as_nodes(*, id_column: Optional[str] = None) -> Callable[[Any], nx.Graph]:
    """L4→L3: each row becomes a graph node keyed by id_column, other columns as
    attributes. The engine's L3→L2 step turns this back into a table whose
    columns include those attributes — so a numeric attribute survives to L1."""
    def build(data: Any) -> nx.Graph:
        df = _single_frame(data)
        id_col = id_column or df.columns[0]
        g = nx.DiGraph()
        for _, row in df.iterrows():
            attrs = {c: row[c] for c in df.columns if c != id_col}
            g.add_node(row[id_col], **attrs)
        return g
    return build


def bipartite(*, entity_column: str, attribute_column: str,
              value_column: Optional[str] = None) -> Callable[[Any], nx.Graph]:
    """L4→L3: link each entity value to its attribute value (e.g. school→category),
    optionally carrying a numeric value on the entity node."""
    def build(data: Any) -> nx.Graph:
        df = _single_frame(data)
        g = nx.DiGraph()
        for _, row in df.iterrows():
            entity, attribute = row[entity_column], row[attribute_column]
            node_attrs = {value_column: row[value_column]} if value_column else {}
            g.add_node(entity, node_type="entity", **node_attrs)
            g.add_node(attribute, node_type="attribute")
            g.add_edge(entity, attribute, relationship="has_attribute")
        return g
    return build


def join_sources(*, left_key: str, right_key: Optional[str] = None,
                 how: str = "inner") -> Callable[[Any], nx.Graph]:
    """L4→L3 entity matching: join two (or more) L4 source tables on a shared key,
    then build a graph where each merged row is a node. This is the 'entity matching'
    builder — it links entities that appear across multiple source files.

    Config keys: left_key (shared join column), right_key (if different across sources,
    defaults to left_key), how ('inner'|'left'|'outer').
    """
    def build(data: Any) -> nx.Graph:
        if not isinstance(data, dict) or len(data) < 1:
            raise ValueError("join_sources requires at least one source DataFrame.")
        frames = list(data.values())
        if len(frames) == 1:
            merged = frames[0]
        else:
            rk = right_key or left_key
            merged = frames[0]
            for other in frames[1:]:
                left_col = left_key if left_key in merged.columns else merged.columns[0]
                right_col = rk if rk in other.columns else other.columns[0]
                merged = merged.merge(other, left_on=left_col, right_on=right_col, how=how,
                                      suffixes=("", "_r"))
        g = nx.DiGraph()
        id_col = left_key if left_key in merged.columns else merged.columns[0]
        for _, row in merged.iterrows():
            attrs = {c: row[c] for c in merged.columns if c != id_col}
            g.add_node(row[id_col], **attrs)
        return g
    return build


# Registry: name -> factory(**config) -> callable(payload) -> payload
DESCENT_BUILDERS: Dict[str, Callable[..., Callable[[Any], Any]]] = {
    "rows_as_nodes": rows_as_nodes,
    "bipartite": bipartite,
    "join_sources": join_sources,
}


def resolve_builder(name: str, config: Dict[str, Any]) -> Callable[[Any], Any]:
    if name not in DESCENT_BUILDERS:
        raise KeyError(
            f"Unknown builder '{name}'. Available: {list(DESCENT_BUILDERS)}"
        )
    return DESCENT_BUILDERS[name](**config)
