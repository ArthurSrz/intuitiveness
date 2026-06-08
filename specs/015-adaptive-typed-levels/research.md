# Phase 0 Research: Adaptive Typed Levels & Unified Redesign Engine

All design decisions were resolved during the grill-me interview; this document records the technical rationale and the codebase facts each rests on. No open NEEDS CLARIFICATION remain.

---

## R1 — Lineage isolation via deepcopy is cheap

**Decision**: On every transition the Redesigner does `child_lineage = deepcopy(parent.lineage)` then appends one `SourceReference`. `DataLineage.add_operation` stays mutating; isolation comes from the copy at the chokepoint.

**Rationale**: `DataLineage` stores `operations: List[SourceReference]` plus a small `metadata` dict. `SourceReference` holds scalars (levels, timestamp, row counts, a params dict, optional hash strings) — **never** DataFrames/graphs. So `deepcopy` copies records, not payloads; cost is O(history length × small record), negligible vs. the transform itself. Verified: `redesign/lineage.py` `add_operation` appends a `SourceReference`; no payload is ever stored in lineage.

**Alternatives considered**: (a) backward link + walk — rejected in Q2 (generator wants self-contained chains); (b) immutable/functional `DataLineage` — rejected (breaks existing mutating API used elsewhere); (c) copy-only-on-branch — rejected (re-introduces "external bookkeeper must remember" fragility).

---

## R2 — One provenance record: extend `SourceReference`, delete `AscentOperation`

**Decision**: `SourceReference` becomes the single per-step record for both directions. Add optional `id: str` (UUID), `source_data_hash`/`result_data_hash`. Ascent specifics (`enrichment_function`, `dimensions_added`) ride in the existing `parameters` dict. Delete `AscentOperation`; move its `validate_integrity` row-count rule into the Redesigner ascent dispatch.

**Rationale**: `AscentOperation` (in `ascent/operations.py`) duplicates level/timestamp/row-count fields already in `SourceReference` and adds only hashing + UUID + an adjacency check + a row-count invariant. Hashing/UUID become optional fields; adjacency + row-count are *enforcement*, which belongs in the engine (Q7), not on a data record.

**Codebase impact (breaking)**: `tests/...` and UI import `from intuitiveness.ascent.operations import AscentOperation`. These call-sites must migrate to building a `SourceReference` (or reading lineage). Tracked in tasks; covered by the E2E regression net.

**Alternatives considered**: keep both records (Q6-B, rejected: perpetuates multiplicity); base + per-direction subclasses (Q6-C, rejected: heavier union/serialization).

---

## R3 — Typed dispatch replaces `**kwargs` + injected `Callable`

**Decision**: Public `Redesigner.reduce_complexity(dataset, target_level, params)` / `increase_complexity(dataset, target_level, params)` route to typed per-transition methods backed by typed param dataclasses: `L4toL3Params(model)`, `L3toL2Params(domains)`, `L2toL1Params(column, filter_query)`, `L1toL0Params(aggregation)`, and ascent mirrors `L0toL1Params`, `L1toL2Params`, `L2toL3Params`. No injected `builder_func`/`query_func`.

**Rationale**: The legacy `_reduce_4_to_3(dataset, builder_func: Callable, ...)` forced callers to inject transformation logic — the very reason `InteractiveRedesigner` reimplemented transitions inline. With transforms now owned by `descent/`/`ascent/` (R4), the engine calls them directly; parameters become a small typed object per transition. Eliminates the untyped `**kwargs` recursion that silently reused the same kwargs for multi-step jumps.

**Alternatives considered**: typed methods only with no unified surface (Q5-A, rejected: loses the paper's "dispatches transitions" surface); generic dispatch + param object but no typed methods (Q5-B, rejected: weaker internal typing). Chosen hybrid (Q5-C) keeps both.

---

## R4 — `descent/`/`ascent/` become payload-pure; engine wraps + stamps

**Decision**: Transformation modules take and return **payloads** (dict→graph, df→df, series→series). The 7 `LevelNDataset(...)` constructions in `ascent/graph_builder.py` (3) and `ascent/unfold.py` (4) move into the Redesigner, which is the sole constructor.

**Rationale**: Verified the modules are already ~80% payload-pure (`semantic_join.py`, `dimensions.py`, `enrichment.py`, `operations.py` construct zero datasets). Only `graph_builder.py` and `unfold.py` instantiate level classes. Relocating those 7 sites makes the chokepoint real and keeps transform logic first-class and unit-testable on raw payloads.

**Alternatives considered**: promote `InteractiveRedesigner` as engine (Q4-B, rejected: entrenches a 979-line god-class); replicate lineage rule in all three engines (Q4-C, rejected: guaranteed drift).

---

## R5 — Polymorphic `summary()` replaces the tree's type-switch

**Decision**: Add `summary() -> dict` to base `Dataset`; each level implements it. `NavigationTree._generate_output_snapshot`'s 40-line `if level == …` block is deleted; tree/UI call `dataset.summary()`.

**Rationale**: The snapshot logic already switches on `complexity_level` to compute level-specific shape (source count / row+cols / length / node+edge count / scalar). That is polymorphism inverted; pushing it onto the typed classes removes external type-branching (SC-002) and is the natural companion to "self-describing artifacts."

**Alternatives considered**: keep display logic external (rejected in Q8 Part 2: keeps a type-switch, weakens the typed-structure thesis).

---

## R6 — One always-on branching tree; delete flat history

**Decision**: Remove the `use_tree` flag (defaults False today) and the `NavigationHistory` class. `NavigationSession` always uses `NavigationTree`. Linear path = `tree.get_current_branch_path()`. Remove every `if self._use_tree / elif self._history` fork.

**Rationale**: The flat history is a non-branching special case of the tree; the paper makes branching/time-travel first-class. The dual dispatch appears in ≥4 methods (descend/ascend/get_history/exit) — collapsing it removes duplicated code paths and a whole class. `get_current_branch_path` already exists.

**Alternatives considered**: keep both (Q8-B, rejected: two code paths, default-off branching); flat-only (Q8-C, rejected: contradicts paper).

---

## R7 — Full payloads at every node + generator-facing queries

**Decision**: `NavigationTreeNode` retains the complete `Dataset` (payload + lineage + edge decision). Add `branches()`, `nodes_at_level(level)`, `siblings(node)`, `divergence_point(a, b)`. Memory bounded only by explicit user `prune(branch)`/`archive(branch)`.

**Rationale**: The L4→L3 step uses non-deterministic LLM entity discovery (§5.3.2) — lazy replay would produce a *different* graph than the one navigated, so payloads must be retained, not re-derived. The generator (a separate service) consumes branches as "multiple coherent views of the same data," needing level/sibling/divergence queries. `get_all_branches` partially exists and is generalized.

**Alternatives considered**: leaves-only + lazy replay (Q9-B, rejected: non-determinism); navigation-only now, defer queries (Q9-C, rejected: retrofitting a UI-only tree is the rework we're already doing).

---

## R8 — Full-fidelity, versioned, self-contained export (separate from localStorage index)

**Decision**: New `persistence/session_export.py` produces a JSON record: a top-level `schema_version`, session `metadata`, and a **flat `nodes` map keyed by node id**, each node carrying `level` (int), `parent_id`, `children_ids`, `edge_decision`, `lineage` (list of serialized `SourceReference`), and `payload` (encoded via existing serializers with a `payload_kind` tag). A new `persistence/durable_backend.py` (file/blob) stores these. The existing localStorage `StorageBackend` is demoted to a **session index**: `{id, title, backend_location}` only.

**Rationale**: Synthetic generation is a separate service → the record is an interchange contract, not a save file. Flat id-keyed map with `parent_id` references stores shared ancestors once (FR-026/SC-009). `payload_kind` + documented encodings (`dataframe` = zlib+base64 of CSV/parquet bytes; `graph` = node-link JSON; `value` = JSON scalar; `sources` = map of dataframe encodings for L4) make the record decodable **without importing `intuitiveness`** (FR-025/SC-008) — a consumer only needs the documented decode rules. localStorage's ~5 MB ceiling is respected because it holds only the index (FR-027/SC-010).

**Codebase facts**: `serializers.py` already provides `serialize_dataframe` (zlib+base64), `serialize_graph` (node-link), `serialize_value`. `storage_backend.py` `StorageBackend` is a localStorage abstraction (`get/set` string, `get_available_space`). `tree.to_dict()` currently **excludes** `dataset_snapshot` — this is the gap to close.

**Alternatives considered**: structure-only export (status quo, rejected: generator gets no data); payloads in localStorage (rejected: 5 MB ceiling); pickling whole Dataset objects (rejected: not language-neutral, couples consumer to package internals).

---

## R9 — Backward compatibility posture

**Decision**: Treat this as a **breaking internal refactor**. The compatibility guarantee is the *external user journey* (SC-011: all E2E descent/ascent journeys for the 3 reference datasets still pass), **not** internal API signatures. Deliberate removals: `AscentOperation`, `NavigationHistory`, `redesign_legacy.Redesigner` (replaced by `redesign.engine.Redesigner`), the `use_tree` flag, and `Redesigner.reduce_complexity(**kwargs)` shape. Previously exported structure-only sessions are **not** migrated (Out of Scope).

**Rationale**: Shims for every changed signature would preserve the duplication we are removing. The E2E suite (incl. Playwright UI) is the safety net; `redesign/__init__.py` re-exports `Redesigner` so the common import path `from intuitiveness.redesign import Redesigner` keeps working with the new engine.

**Migration of known call-sites** (from grep): `interactive.py` (delegates to engine), `navigation/session.py` (uses engine + tree), tests importing `AscentOperation`/`Level*` directly, UI ascent forms importing `ascent.*`. Sequenced in the dependency-ordered migration (plan §Summary / tasks).

---

## R10 — Testing strategy

**Decision**: Three tiers. (1) **Unit** (`tests/unit/`, new): symmetric lineage on each level, `summary()` per level, deepcopy isolation, typed-param validation, each invariant in exactly one place, export/import round-trip per payload type, shared-ancestor de-dup, divergence_point. (2) **Integration** (`tests/integration/`): engine ↔ session ↔ tree; guided-workflow transition == programmatic transition (SC indistinguishability). (3) **E2E** (`tests/e2e/`, reuse + extend): the 3 reference datasets full descent/ascent (regression, SC-011) plus a new branch→time-travel→export→reload-without-package scenario.

**Rationale**: pytest is configured (`testpaths=["tests"]`, markers `slow`/`integration`). The "exactly one component/place" criteria (SC-003/SC-004) are checked by targeted unit tests + code-inspection assertions (grep for `LevelNDataset(` outside the engine must yield only the engine).

**Alternatives considered**: rely on E2E only (rejected: can't pin the structural "exactly one" guarantees); TDD pure (encouraged per-component but the refactor is migration-shaped, so characterization tests on current behavior come first).
