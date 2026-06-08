# Phase 1 Data Model: Adaptive Typed Levels & Unified Redesign Engine

Entities, fields, relationships, validation rules, and state transitions derived from the spec's Functional Requirements and Key Entities.

---

## 1. `Dataset` (abstract base) + 5 symmetric level classes

The base gains two responsibilities so all five levels are symmetric (FR-001, FR-002, FR-003).

**Base fields/behaviors**:
| Member | Type | Notes |
|--------|------|-------|
| `complexity_level` | `ComplexityLevel` (property) | unchanged |
| `get_data()` | `Any` | unchanged (payload accessor) |
| `lineage` | `DataLineage` | **NEW** — full denormalized history from raw origin to self (FR-001). Defaults to empty `DataLineage` for a freshly-ingested L4. |
| `summary()` | `dict` | **NEW** — polymorphic self-description (FR-003, R5). |

**Per-level payload + `summary()` shape** (payload types unchanged from today):
| Class | Payload | `summary()` returns (keys) |
|-------|---------|----------------------------|
| `Level4Dataset` | `Dict[str, Any]` (named raw sources) | `{level, level_name, type:"unlinkable", source_count}` |
| `Level3Dataset` | `Union[nx.Graph, pd.DataFrame]` | graph → `{…, type:"graph", node_count, edge_count}`; df → `{…, type:"graph", row_count}` |
| `Level2Dataset` | `pd.DataFrame` (+`name`) | `{…, type:"dataframe", row_count, columns}` |
| `Level1Dataset` | `pd.Series` (+`name`) | `{…, type:"vector", length}` |
| `Level0Dataset` | scalar (+`description`) | `{…, type:"datum", value}` |

**Validation rules**:
- `lineage` MUST be present on every instance (never `None`); empty chain is valid only for an un-transitioned L4 entry.
- `summary()` MUST NOT raise for any well-formed payload; MUST return `level`+`level_name` for all.
- Legacy `Level0Dataset.parent_data`/`aggregation_method` are **removed** — that information now lives as the last `SourceReference` in `lineage` (migration note: callers reading `parent_data` read `lineage.operations[-1]` instead).

**State transitions**: A `Dataset` is immutable after construction (frozen-at-birth, R1). A new level is produced only by the Redesigner, never mutated in place.

---

## 2. `SourceReference` (single canonical provenance step)

Extends today's record (FR-004, FR-005, FR-006, R2). One type for both directions.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `operation_type` | `str` | yes | e.g. `"L4→L3"`, `"L1→L0"`, `"L0→L1"` |
| `input_level` | `ComplexityLevel` | yes | |
| `output_level` | `ComplexityLevel` | yes | |
| `timestamp` | `datetime` | yes | |
| `parameters` | `Dict[str, Any]` | yes (may be empty) | carries direction-specific detail: `enrichment_function`, `dimensions_added`, `column`, `filter_query`, `aggregation`, `domains`, … |
| `duration_ms` | `float` | no (default 0) | |
| `row_count_before` | `Optional[int]` | no | |
| `row_count_after` | `Optional[int]` | no | |
| `id` | `Optional[str]` (UUID) | **NEW**, optional | per-step identity |
| `source_data_hash` | `Optional[str]` | **NEW**, optional | tamper-detection fingerprint of input payload |
| `result_data_hash` | `Optional[str]` | **NEW**, optional | fingerprint of output payload |

**Validation rules**:
- `to_dict()`/`from_dict()` MUST round-trip every field (levels as ints, timestamp ISO-8601).
- Optional hashes absent ⇒ record still valid (Assumption: integrity fingerprints optional).
- The record is **descriptive only** — it carries NO validation methods (the deleted `AscentOperation.validate_integrity` rule moves to the engine).

---

## 3. `DataLineage` (ordered chain)

API unchanged (mutating `add_operation`); isolation via deepcopy at the engine (R1).

| Field | Type | Notes |
|-------|------|-------|
| `operations` | `List[SourceReference]` | ordered raw-origin → here |
| `metadata` | `Dict[str, Any]` | session_id, user, etc. |

**Behaviors**: `add_operation(...)`, `get_history()`, `export()/load()`, plus serialization used by the session export (R8). Holds **no payloads**.

---

## 4. `Redesigner` (single engine / sole chokepoint)

Promoted to `redesign/engine.py` (FR-007, FR-008, FR-009, FR-014, R3, R4).

**Public surface**:
- `reduce_complexity(dataset, target_level, params) -> Dataset` (descent)
- `increase_complexity(dataset, target_level, params) -> Dataset` (ascent)

**Internal typed methods** (one per adjacent transition), each: validate transition-legality → call payload-pure transform in `descent/`/`ascent/` → construct the target `LevelNDataset` → `deepcopy(parent.lineage)` + append `SourceReference` → return.

**Typed params** (`redesign/params.py`):
| Param dataclass | Fields |
|-----------------|--------|
| `L4toL3Params` | `model` (data-model spec for graph build) |
| `L3toL2Params` | `domains: List[str]` |
| `L2toL1Params` | `column: str`, `filter_query: Optional[str]` |
| `L1toL0Params` | `aggregation: str` |
| `L0toL1Params` | `enrichment_function: str`, … |
| `L1toL2Params` | `dimensions: List[str]` |
| `L2toL3Params` | `dimensions/links: …` |

**Invariants enforced here (stateless, FR-014, FR-016)**:
- adjacency: `abs(input.value - target.value) == 1` else `ValueError`.
- no L4 destination on ascent: structurally — there is **no** `_increase_3_to_4` method.
- ascent row-count preservation: `row_count_after == row_count_before` else reject.

**Validation rules**: the engine is the ONLY code that calls `LevelNDataset(...)` (SC-003). Stateless — holds no session state.

---

## 5. `NavigationSession` (stateful path-legality owner)

(FR-015, FR-016, R6.)

| Field | Type | Notes |
|-------|------|-------|
| `_tree` | `NavigationTree` | always present (no `use_tree` flag) |
| `_current_node_id` | `str` | active node |
| `session_id` / `state` | | unchanged |

**Behaviors**: `descend(params)`, `ascend(params)` (both delegate the transition to `Redesigner`, then record a tree node), `time_travel(node_id)`, `branch_from(node_id, params)`, `get_history()` (= current branch path), `save()/load()` (→ session export, R8), `prune(branch)/archive(branch)`.

**Invariants enforced here (stateful, FR-015)**:
- entry MUST be L4 (constructor rejects non-L4).
- no re-entry to L4 once departed.

**Removed**: `_history`/`NavigationHistory`, `use_tree`, all `if use_tree / elif history` forks.

---

## 6. `NavigationTree` + `NavigationTreeNode` (single history structure)

(FR-017–FR-022, R7.)

**`NavigationTreeNode`**:
| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | identity |
| `level` | `ComplexityLevel` | |
| `dataset` | `Dataset` | **full payload retained** (was `dataset_snapshot`, was excluded from `to_dict`) |
| `parent_id` | `Optional[str]` | |
| `children_ids` | `List[str]` | |
| `edge_decision` | `Dict[str, Any]` | the typed params/choice that produced this node from parent |
| `timestamp` | `datetime` | |

**`NavigationTree` query API** (FR-021):
- `branches() -> List[List[Node]]`
- `nodes_at_level(level) -> List[Node]`
- `siblings(node) -> List[Node]`
- `divergence_point(a, b) -> Node`
- existing: `get_current_branch_path()`, `restore(node_id)`, `branch(...)`.

**Validation rules**:
- time-travel `restore(id)` returns the node's `dataset` exactly as created (FR-019).
- `branch(...)` creates a sibling without mutating existing nodes (FR-013).
- `prune/archive` are explicit; never automatic (FR-022).

---

## 7. `SessionExportRecord` (versioned cross-service contract)

Produced by `persistence/session_export.py` (FR-023–FR-028, R8). Wire schema in `contracts/session_export.schema.json`.

| Field | Type | Notes |
|-------|------|-------|
| `schema_version` | `str` | fail-closed on unknown future version |
| `metadata` | `object` | `session_id`, `title`, `created_at`, `root_id`, `current_id` |
| `nodes` | `object` (map keyed by node `id`) | **flat** — shared ancestors stored once (FR-026) |
| `nodes[id].level` | `int` | 0–4 |
| `nodes[id].parent_id` | `string\|null` | |
| `nodes[id].children_ids` | `string[]` | |
| `nodes[id].edge_decision` | `object` | params/choice on incoming edge |
| `nodes[id].lineage` | `array` | serialized `SourceReference` list |
| `nodes[id].payload_kind` | `enum` | `unlinkable\|graph\|dataframe\|vector\|value` |
| `nodes[id].payload` | `string\|object` | encoded per `payload_kind` (documented, package-free decode) |

**Validation rules**:
- Loadable without importing `intuitiveness` internal classes (FR-025): decode rules are documented in the schema file.
- Round-trips all payload kinds (FR-024).
- On load, re-link `parent_id`/`children_ids` to shared nodes (FR-028).

---

## 8. `SessionIndexEntry` (lightweight localStorage pointer)

(FR-027, R8.) Stored via the existing `StorageBackend`.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | session id |
| `title` | `str` | human label |
| `backend_location` | `str` | pointer into durable backend |

**Validation rule**: holds NO payloads; total index size MUST stay within the localStorage budget (≈5 MB) regardless of session data size (SC-010).

---

## Relationship summary

```text
NavigationSession 1──1 NavigationTree 1──* NavigationTreeNode *──1 Dataset
Dataset 1──1 DataLineage 1──* SourceReference
Redesigner (stateless) ──constructs──> Dataset ; ──stamps──> DataLineage
Redesigner ──calls──> descent/ascent transforms (payload-pure)
NavigationSession ──save()──> SessionExportRecord ──stored in──> DurableBackend
StorageBackend (localStorage) holds SessionIndexEntry ──points to──> DurableBackend
```
