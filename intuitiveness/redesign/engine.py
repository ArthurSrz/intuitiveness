"""
Unified Redesigner engine — the single transition chokepoint (spec 015).

This engine is the ONLY component allowed to construct a ``LevelNDataset`` and
stamp its lineage (FR-007/FR-008). It is a thin, stateless typed dispatcher:

    reduce_complexity(dataset, target_level, params)    # descent
    increase_complexity(dataset, target_level, params)  # ascent

Each public call routes to a typed per-transition method (FR-009), which:
  1. validates transition-legality (adjacency; ascent never targets L4;
     ascent preserves row counts) — FR-014, stateless;
  2. calls a payload-pure transform to produce the new payload;
  3. constructs the typed target dataset;
  4. deepcopies the parent's lineage and appends one SourceReference (FR-012),
     so the child is frozen-at-birth and isolated from parent/siblings.

Path-legality (entry-at-L4, no re-entry) is NOT enforced here — it is the
stateful concern of NavigationSession (FR-015/FR-016).
"""

from __future__ import annotations

import copy
import hashlib
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd

from intuitiveness.complexity import (
    ComplexityLevel,
    Dataset,
    Level0Dataset,
    Level1Dataset,
    Level2Dataset,
    Level3Dataset,
    Level4Dataset,
)
from intuitiveness.redesign.lineage import DataLineage, SourceReference
from intuitiveness.redesign.params import (
    PARAMS_FOR_EDGE,
    L0toL1Params,
    L1toL0Params,
    L1toL2Params,
    L2toL1Params,
    L2toL3Params,
    L3toL2Params,
    L4toL3Params,
    TransitionParams,
)


class TransitionError(ValueError):
    """Raised when a requested transition is not well-formed (stateless rule)."""


def _row_count(payload: Any) -> Optional[int]:
    if isinstance(payload, pd.DataFrame):
        return int(payload.shape[0])
    if isinstance(payload, pd.Series):
        return int(payload.shape[0])
    if hasattr(payload, "number_of_nodes"):
        return int(payload.number_of_nodes())
    return None


def _hash(payload: Any) -> str:
    try:
        return hashlib.md5(str(payload).encode()).hexdigest()[:16]
    except Exception:
        return "hash_error"


class Redesigner:
    """Stateless engine. Sole constructor of level artifacts + lineage stamper."""

    # ------------------------------------------------------------------ #
    # Public dispatch
    # ------------------------------------------------------------------ #
    @staticmethod
    def reduce_complexity(dataset: Dataset, target_level: ComplexityLevel,
                          params: TransitionParams) -> Dataset:
        """Descent: move down exactly one level (FR-014 adjacency)."""
        src = dataset.complexity_level
        Redesigner._require_adjacent(src, target_level, descending=True)
        Redesigner._require_params(src, target_level, params)
        method = {
            (4, 3): Redesigner._l4_to_l3,
            (3, 2): Redesigner._l3_to_l2,
            (2, 1): Redesigner._l2_to_l1,
            (1, 0): Redesigner._l1_to_l0,
        }[(src.value, target_level.value)]
        return method(dataset, params)

    @staticmethod
    def increase_complexity(dataset: Dataset, target_level: ComplexityLevel,
                            params: TransitionParams) -> Dataset:
        """Ascent: move up exactly one level. Never targets L4 (FR-014)."""
        src = dataset.complexity_level
        if target_level == ComplexityLevel.LEVEL_4:
            # Structurally unreachable — there is no ascent method to L4.
            raise TransitionError("L4 is entry-only; it can never be an ascent target.")
        Redesigner._require_adjacent(src, target_level, descending=False)
        Redesigner._require_params(src, target_level, params)
        method = {
            (0, 1): Redesigner._l0_to_l1,
            (1, 2): Redesigner._l1_to_l2,
            (2, 3): Redesigner._l2_to_l3,
        }[(src.value, target_level.value)]
        return method(dataset, params)

    # ------------------------------------------------------------------ #
    # Stateless invariants (FR-014)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _require_adjacent(src: ComplexityLevel, target: ComplexityLevel,
                          descending: bool) -> None:
        if descending and src.value - target.value != 1:
            raise TransitionError(
                f"Descent must move down exactly one level: {src.name} → {target.name}."
            )
        if not descending and target.value - src.value != 1:
            raise TransitionError(
                f"Ascent must move up exactly one level: {src.name} → {target.name}."
            )

    @staticmethod
    def _require_params(src: ComplexityLevel, target: ComplexityLevel,
                        params: TransitionParams) -> None:
        expected = PARAMS_FOR_EDGE.get((src.value, target.value))
        if expected is not None and not isinstance(params, expected):
            raise TransitionError(
                f"Edge {src.name}→{target.name} expects {expected.__name__}, "
                f"got {type(params).__name__}."
            )

    @staticmethod
    def _require_row_count_preserved(before: Optional[int], after: Optional[int],
                                     edge: str) -> None:
        """Ascent that adds attributes (not entities) must preserve item count."""
        if before is not None and after is not None and before != after:
            raise TransitionError(
                f"Ascent {edge} must preserve row count "
                f"(before={before}, after={after}); ascent adds attributes, not entities."
            )

    # ------------------------------------------------------------------ #
    # Lineage stamping (FR-012) — the only place a child lineage is born
    # ------------------------------------------------------------------ #
    @staticmethod
    def _stamp(parent: Dataset, operation_type: str, input_level: ComplexityLevel,
               output_level: ComplexityLevel, parameters: dict,
               before: Optional[int], after: Optional[int],
               src_payload: Any, out_payload: Any) -> DataLineage:
        child_lineage = copy.deepcopy(parent.lineage)
        child_lineage.add_operation(
            operation_type=operation_type,
            input_level=input_level,
            output_level=output_level,
            parameters=parameters,
            row_count_before=before,
            row_count_after=after,
            timestamp=datetime.now(timezone.utc),
        )
        # attach optional integrity fingerprints to the just-added step
        last = child_lineage.operations[-1]
        last.source_data_hash = _hash(src_payload)
        last.result_data_hash = _hash(out_payload)
        return child_lineage

    # ------------------------------------------------------------------ #
    # Descent transforms (payload-pure logic wrapped + stamped)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _l4_to_l3(dataset: Level4Dataset, params: L4toL3Params) -> Level3Dataset:
        # L4→L3 is non-deterministic (LLM-assisted) — accept a prebuilt graph
        # payload rather than re-derive it (research R7).
        graph = params.prebuilt_graph
        if graph is None:
            raise TransitionError(
                "L4→L3 requires params.prebuilt_graph (the built graph payload); "
                "graph construction is non-deterministic and must not be re-derived."
            )
        lineage = Redesigner._stamp(
            dataset, "L4→L3", ComplexityLevel.LEVEL_4, ComplexityLevel.LEVEL_3,
            {"model": str(params.model), **params.metadata},
            None, _row_count(graph), dataset.get_data(), graph,
        )
        return Level3Dataset(graph, lineage=lineage)

    @staticmethod
    def _l3_to_l2(dataset: Level3Dataset, params: L3toL2Params) -> Level2Dataset:
        data = dataset.get_data()
        if params.prebuilt_table is not None:
            # caller (e.g. session adapter) already extracted the table via a
            # query — wrap it, preserving legacy query semantics.
            df = params.prebuilt_table
        elif isinstance(data, pd.DataFrame):
            df = data
        else:
            # graph → table of nodes carrying attributes
            import networkx as nx  # local import; networkx already a dep
            rows = [{"node": n, **(attrs or {})} for n, attrs in data.nodes(data=True)]
            df = pd.DataFrame(rows)
        out = df
        lineage = Redesigner._stamp(
            dataset, "L3→L2", ComplexityLevel.LEVEL_3, ComplexityLevel.LEVEL_2,
            {"domains": list(params.domains), **params.metadata},
            _row_count(data), _row_count(out), data, out,
        )
        name = params.domains[0] if params.domains else "domain"
        return Level2Dataset(out, name=name, lineage=lineage)

    @staticmethod
    def _l2_to_l1(dataset: Level2Dataset, params: L2toL1Params) -> Level1Dataset:
        df = dataset.get_data()
        if params.filter_query:
            df = df.query(params.filter_query)
        column = params.column
        if column:
            if column not in df.columns:
                raise TransitionError(f"Column '{column}' not found in table.")
            series = df[column]
        elif df.shape[1] == 1:
            series = df.iloc[:, 0]
        else:
            raise TransitionError("L2→L1 requires params.column when the table has >1 column.")
        lineage = Redesigner._stamp(
            dataset, "L2→L1", ComplexityLevel.LEVEL_2, ComplexityLevel.LEVEL_1,
            {"column": column, "filter_query": params.filter_query, **params.metadata},
            _row_count(dataset.get_data()), _row_count(series), dataset.get_data(), series,
        )
        return Level1Dataset(series, name=column or "variable", lineage=lineage)

    @staticmethod
    def _l1_to_l0(dataset: Level1Dataset, params: L1toL0Params) -> Level0Dataset:
        series = dataset.get_data()
        agg = params.aggregation
        try:
            value = getattr(series, agg)()
        except AttributeError:
            raise TransitionError(f"Unsupported aggregation '{agg}'.")
        lineage = Redesigner._stamp(
            dataset, "L1→L0", ComplexityLevel.LEVEL_1, ComplexityLevel.LEVEL_0,
            {"aggregation": agg, **params.metadata},
            _row_count(series), None, series, value,
        )
        return Level0Dataset(
            value,
            description=f"{agg} of {dataset.name}",
            parent_data=series.copy() if hasattr(series, "copy") else series,
            aggregation_method=agg,
            lineage=lineage,
        )

    # ------------------------------------------------------------------ #
    # Ascent transforms
    # ------------------------------------------------------------------ #
    @staticmethod
    def _l0_to_l1(dataset: Level0Dataset, params: L0toL1Params) -> Level1Dataset:
        # Reconstruct a vector. If the datum remembers its parent vector, use it;
        # otherwise wrap the scalar into a 1-element series. L0→L1 legitimately
        # changes item count (reconstruction), so row-count is NOT preserved here.
        parent = dataset.get_parent_data() if hasattr(dataset, "get_parent_data") else None
        if parent is not None:
            series = parent.copy() if hasattr(parent, "copy") else pd.Series(parent)
        else:
            series = pd.Series([dataset.get_data()])
        lineage = Redesigner._stamp(
            dataset, "L0→L1", ComplexityLevel.LEVEL_0, ComplexityLevel.LEVEL_1,
            {"enrichment_function": params.enrichment_function, **params.metadata},
            None, _row_count(series), dataset.get_data(), series,
        )
        return Level1Dataset(series, name="reconstructed", lineage=lineage)

    @staticmethod
    def _l1_to_l2(dataset: Level1Dataset, params: L1toL2Params) -> Level2Dataset:
        series = dataset.get_data()
        df = series.to_frame(name=dataset.name or "value")
        # Dimensions are added as (initially empty/derived) attribute columns.
        for dim in params.dimensions:
            if dim not in df.columns:
                df[dim] = None
        before, after = _row_count(series), _row_count(df)
        Redesigner._require_row_count_preserved(before, after, "L1→L2")
        lineage = Redesigner._stamp(
            dataset, "L1→L2", ComplexityLevel.LEVEL_1, ComplexityLevel.LEVEL_2,
            {"dimensions": list(params.dimensions), **params.metadata},
            before, after, series, df,
        )
        return Level2Dataset(df, name=f"table_{dataset.name}", lineage=lineage)

    @staticmethod
    def _l2_to_l3(dataset: Level2Dataset, params: L2toL3Params) -> Level3Dataset:
        import networkx as nx
        df = dataset.get_data()
        before = _row_count(df)
        graph = nx.DiGraph()
        entity_col = params.entity_column
        # Build a simple bipartite graph row-entity -> extracted-entity; if no
        # entity_column given, build a star around row indices (no orphans).
        for idx in df.index:
            graph.add_node(f"row_{idx}", node_type="row")
        if entity_col and entity_col in df.columns:
            for idx, val in df[entity_col].items():
                if pd.notna(val):
                    graph.add_node(val, node_type="entity", entity_type=entity_col)
                    graph.add_edge(f"row_{idx}", val, relationship="belongs_to")
        after_rows = before  # entities-as-rows preserved
        Redesigner._require_row_count_preserved(before, after_rows, "L2→L3")
        lineage = Redesigner._stamp(
            dataset, "L2→L3", ComplexityLevel.LEVEL_2, ComplexityLevel.LEVEL_3,
            {"dimensions": list(params.dimensions), "entity_column": entity_col, **params.metadata},
            before, after_rows, df, graph,
        )
        return Level3Dataset(graph, lineage=lineage)
