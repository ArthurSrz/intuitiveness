# Tasks: Adaptive Typed Levels & Unified Redesign Engine

**Input**: Design documents from `/specs/015-adaptive-typed-levels/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: INCLUDED — the project mandates unit tests per dataset and a Playwright E2E (CLAUDE.md), and research.md R10 defines a 3-tier strategy. Test tasks are first-class here.

**Organization**: Tasks grouped by user story. This is an in-place refactor of `intuitiveness/`; paths are repo-relative.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: US1–US5 (user-story phases only)

## Path Conventions

- Library: `intuitiveness/`  · Tests: `tests/` (unit/ integration/ e2e/) at repo root.

---

## Phase 1: Setup (Safety Net Before Refactor)

**Purpose**: Lock current behavior so the refactor can be proven non-regressive (SC-011).

- [X] T001 [P] Create `tests/unit/` directory with `tests/unit/__init__.py`
- [X] T002 Run existing E2E suite (`tests/e2e/`) and record the green baseline for the 3 reference datasets (school scores, ADEME fundings, energy prices) as the SC-011 reference
- [ ] T003 [P] Write characterization tests locking current descent/ascent OUTPUTS (not internal APIs) for the 3 reference datasets in `tests/unit/test_characterization.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The unified core (provenance, typed params, payload-pure transforms, the engine, the self-describing base) that EVERY story depends on. No story can be tested until this is complete.

- [X] T004 [P] Extend `SourceReference` in `intuitiveness/redesign/lineage.py`: add optional `id` (UUID), `source_data_hash`, `result_data_hash`; keep `to_dict`/`from_dict` round-tripping every field (levels as ints, ISO timestamp)
- [X] T005 [P] Unit-test `SourceReference` round-trip + optional-field absence validity in `tests/unit/test_source_reference.py`
- [X] T006 [P] Add typed param dataclasses in `intuitiveness/redesign/params.py`: `L4toL3Params`, `L3toL2Params`, `L2toL1Params`, `L1toL0Params`, `L0toL1Params`, `L1toL2Params`, `L2toL3Params` (per contracts/redesigner_api.md)
- [X] T007 [P] Unit-test param construction/validation (wrong-param-for-edge raises) in `tests/unit/test_params.py`
- [ ] T008 Make `intuitiveness/ascent/graph_builder.py` payload-pure: strip the 3 `LevelNDataset(...)` constructions; functions return raw payloads (nx.Graph / DataFrame)
- [ ] T009 Make `intuitiveness/ascent/unfold.py` payload-pure: strip the 4 `LevelNDataset(...)` constructions; return raw payloads
- [ ] T010 [P] Assert remaining transform modules stay payload-pure (`descent/semantic_join.py`, `ascent/dimensions.py`, `ascent/enrichment.py` construct zero datasets) in `tests/unit/test_transforms_pure.py`
- [X] T011 Add `lineage: DataLineage` field + abstract `summary() -> dict` to base `Dataset` in `intuitiveness/complexity.py` (per-level `summary()` bodies come in US1)
- [X] T012 Create the unified engine in `intuitiveness/redesign/engine.py`: public `reduce_complexity`/`increase_complexity` + typed per-transition methods that call the payload-pure transforms, construct the target `LevelNDataset`, and `deepcopy(parent.lineage)` + append one `SourceReference`. This is the SOLE constructor of level artifacts (per contracts/redesigner_api.md)
- [X] T013 Add transition-legality enforcement to the engine in `intuitiveness/redesign/engine.py`: adjacency check; no L4-as-ascent-target (structurally — no such method); ascent row-count preservation (`row_count_after == row_count_before`)
- [X] T014 [P] Export `Redesigner` + params from `intuitiveness/redesign/__init__.py`, pointing at `redesign.engine` (replace the legacy re-export)
- [X] T015 [P] Unit-test engine guarantees in `tests/unit/test_engine.py`: deepcopy isolation (RD-2/RD-3), adjacency rejection (RD-4), ascent row-count rejection (RD-6), new-object-not-mutation (RD-1)

**Checkpoint**: A working typed engine produces self-contained, lineage-stamped datasets. Foundational complete.

---

## Phase 3: User Story 1 — Every artifact carries its complete derivation history (Priority: P1) 🎯 MVP

**Goal**: All five levels are symmetric and self-describing — uniform lineage shape + correct polymorphic `summary()`, traceable to raw origin.

**Independent Test**: Descend two levels, request the artifact's history (lists every step from raw origin) and self-summary (level-appropriate, no external type-switch).

- [X] T016 [P] [US1] Implement `summary()` on `Level4Dataset` and `Level3Dataset` in `intuitiveness/complexity.py` (per contracts/dataset_api.md key table)
- [X] T017 [P] [US1] Implement `summary()` on `Level2Dataset`, `Level1Dataset`, `Level0Dataset` in `intuitiveness/complexity.py`
- [~] T018 [US1] CANCELLED (IMPLEMENTATION_NOTES.md Deviation 1): `parent_data` is the parent **Series payload** that `ascent/unfold.py` needs to reconstruct the L1 vector; lineage stores records not payloads, so it is NOT redundant. Keep it.
- [X] T019 [US1] Replace `NavigationTree._generate_output_snapshot` type-switch with a call to `dataset.summary()` in `intuitiveness/navigation/tree.py`
- [X] T020 [P] [US1] Unit-test uniform lineage shape across all 5 levels + correct `summary()` per level in `tests/unit/test_symmetric_levels.py` (DS-1..DS-4, SC-001/SC-002)
- [X] T021 [US1] Integration test (US1 Independent Test): descend 2 levels via the engine, assert full lineage chain from raw origin + correct summaries in `tests/integration/test_us1_provenance.py`

**Checkpoint**: MVP — every artifact self-describes and carries full provenance (delivers the paper's traceability claim, constitution Principle IV).

---

## Phase 4: User Story 2 — Branching never corrupts sibling trajectories (Priority: P1)

**Goal**: Always-on branching tree with full-payload nodes; time-travel restores exact state; branching is isolated.

**Independent Test**: Build a trajectory, time-travel to an intermediate node, take a different choice (sibling branch), confirm the original branch is byte-for-byte unchanged and two branches exist.

- [ ] T022 [US2] Make `NavigationSession` tree-only in `intuitiveness/navigation/session.py`: remove the `use_tree` flag and every `if self._use_tree / elif self._history` fork
- [ ] T023 [US2] Delete the flat `NavigationHistory` class (`intuitiveness/navigation/history.py`) and remove its imports
- [X] T024 [P] [US2] `NavigationTreeNode` retains the COMPLETE `Dataset` (rename `dataset_snapshot`→`dataset`, ensure payload kept, add `edge_decision`) in `intuitiveness/navigation/tree.py`
- [ ] T025 [US2] Add `branch_from(node_id, params)` and `time_travel(node_id)` to `NavigationSession` in `intuitiveness/navigation/session.py` (both go through the engine)
- [X] T026 [P] [US2] Add tree query API in `intuitiveness/navigation/tree.py`: `branches()`, `nodes_at_level(level)`, `siblings(node)`, `divergence_point(a, b)`
- [ ] T027 [P] [US2] Add explicit `prune(node_id)`/`archive(node_id)` (no automatic eviction) in `intuitiveness/navigation/session.py`
- [X] T028 [P] [US2] Unit-test branching isolation (SC-005), time-travel restore (NT-1), divergence_point (SC-012) in `tests/unit/test_branching.py`
- [ ] T029 [US2] Integration test (US2 Independent Test): trajectory → time-travel → sibling branch → assert original unchanged + 2 branches in `tests/integration/test_us2_branching.py`

**Checkpoint**: Safe comparative exploration; branching first-class (SC-006).

---

## Phase 5: User Story 4 — Every transition enforces the rules, regardless of entry path (Priority: P2)

**Goal**: Stateless/stateful invariant split with each rule in exactly one place; consistent rejection across all entry paths.

**Independent Test**: Attempt each illegal move (skip level, target L4 on ascent, re-enter L4) through session and direct engine; confirm identical rejection.

- [ ] T030 [US4] Restrict `NavigationSession` to PATH-legality only in `intuitiveness/navigation/session.py` (entry must be L4; no re-entry to L4); remove any transition-rule checks (delegated to engine)
- [ ] T031 [US4] Delete `AscentOperation` from `intuitiveness/ascent/operations.py` (its fields already absorbed into `SourceReference`; its row-count invariant already in the engine from T013)
- [ ] T032 [US4] Migrate call-sites importing `AscentOperation` (tests + `intuitiveness/ui/ascent*` forms) to build/read `SourceReference`/lineage instead
- [ ] T033 [P] [US4] Unit-test invariant placement in `tests/unit/test_invariants.py`: each illegal move rejected identically via session vs direct engine; assert each rule enforced in exactly one location (SC-004)

**Checkpoint**: Guard-rails consistent across guided/programmatic paths (constitution Principle I).

---

## Phase 6: User Story 3 — Full-fidelity versioned cross-service export (Priority: P2)

**Goal**: Export the whole tree (payloads + lineage) as a versioned, self-contained record loadable without the package; localStorage demoted to an index.

**Independent Test**: Export a multi-branch session; load it in a context that does NOT import `intuitiveness` internals; recover every payload + lineage; format declares its version.

- [ ] T034 [P] [US3] Add durable file/blob backend in `intuitiveness/persistence/durable_backend.py`
- [ ] T035 [US3] Implement full-fidelity export in `intuitiveness/persistence/session_export.py`: tree → record with `schema_version`, `metadata`, flat `nodes` map keyed by id, payloads via existing serializers + `payload_kind`, `lineage`, `edge_decision` (conform to contracts/session_export.schema.json)
- [ ] T036 [US3] Implement import in `intuitiveness/persistence/session_export.py`: record → tree, re-linking shared ancestors to the same node (FR-028); fail-closed on unknown major `schema_version`
- [ ] T037 [US3] Change `NavigationTreeNode.to_dict`/`from_dict` to FULL fidelity (include `payload`) in `intuitiveness/navigation/tree.py` (remove the current `dataset_snapshot` exclusion)
- [ ] T038 [US3] Demote `StorageBackend` to a session index (`id`/`title`/`backend_location`) and wire `NavigationSession.save()/load()` to the durable backend + index in `intuitiveness/persistence/storage_backend.py` and `intuitiveness/navigation/session.py`
- [ ] T039 [P] [US3] Validate export against `contracts/session_export.schema.json` + assert shared-ancestor stored once (SC-009) in `tests/unit/test_export_schema.py`
- [ ] T040 [US3] Integration test (US3 Independent Test): export → reload WITHOUT importing package internals; round-trip tables/graphs/vectors/scalars (SC-007/SC-008) in `tests/integration/test_us3_export.py`

**Checkpoint**: The cross-service contract is real and consumable by a separate generation service.

---

## Phase 7: User Story 5 — One transition engine, one history structure (Priority: P3)

**Goal**: Collapse the three transition engines into the single chokepoint; verify exactly one constructor.

**Independent Test**: A guided-workflow transition produces an artifact+lineage indistinguishable from a direct engine call; grep confirms one constructor.

- [ ] T041 [US5] Rewire `InteractiveRedesigner` in `intuitiveness/interactive.py` to delegate ALL transitions to the engine; remove every inline `LevelNDataset(...)` construction (owns no transition logic)
- [ ] T042 [US5] Delete `intuitiveness/redesign_legacy.py`; repoint any remaining imports to `intuitiveness.redesign.engine`
- [ ] T043 [P] [US5] Guard test in `tests/unit/test_single_chokepoint.py`: `grep` finds no `LevelNDataset(` outside `redesign/engine.py` (SC-003); no `use_tree`/`NavigationHistory`/`redesign_legacy`/`AscentOperation` references remain
- [X] T044 [US5] Integration test (US5 Independent Test): guided-workflow transition == programmatic engine transition (identical artifact + lineage) in `tests/integration/test_us5_consolidation.py`

**Checkpoint**: Single engine, single history structure; SC-003 verified.

---

## Phase 8: Polish & Cross-Cutting

- [ ] T045 [P] Extend Playwright E2E: full descent/ascent + branch + export for all 3 reference datasets in `tests/e2e/` (constitution: ultimate test exports all intermediate artifacts)
- [ ] T046 Run the full suite; confirm SC-011 (all 3 datasets pass, no user-facing UI regression vs the T002 baseline)
- [ ] T047 [P] Run `quickstart.md` end to end as acceptance; document the new architecture + any fixes in `troubleshooting.md`
- [ ] T048 Final constitution compliance check + execute the quickstart.md "Regression checklist" grep guards

---

## Dependencies & Execution Order

```text
Phase 1 (Setup) ─────────────────────────────────────────────┐
                                                              ▼
Phase 2 (Foundational) ── blocks ALL stories ────────────────┐
  T004,T006 [P] → T005,T007 [P]                               │
  T008,T009 → T010                                            │
  T011 → T012 → T013 → T014,T015                              │
                                                              ▼
Phase 3 US1 (P1) 🎯 MVP   ── depends on Foundational
Phase 4 US2 (P1)          ── depends on Foundational; tree work independent of US1
Phase 5 US4 (P2)          ── depends on Foundational; T031 needs T004 (SourceReference extended)
Phase 6 US3 (P2)          ── depends on US2 (tree to export) + Foundational (lineage)
Phase 7 US5 (P3)          ── depends on Foundational (engine to delegate to); touches US2/US4 areas → last
Phase 8 Polish            ── after all stories
```

**Hard dependencies**:
- Everything depends on Phase 2.
- T031 (delete `AscentOperation`) requires T004 (fields absorbed into `SourceReference`).
- US3 (export) requires US2 (full-payload tree) — T035/T037 need T024.
- US5 (T041 rewire interactive) requires the engine (T012/T013) and is safest last so US1–US4 tests run against the new engine while legacy still exists as fallback.

## Parallel Opportunities

- **Setup**: T001 ∥ T003.
- **Foundational**: {T004, T006} ∥ then {T005, T007} ∥; T008 ∥ T009; T014 ∥ T015.
- **US1**: T016 ∥ T017 ∥ T020 (different concerns; T018/T019 after).
- **US2**: T024 ∥ T026 ∥ T027 ∥ T028 (distinct methods/files) after T022/T023.
- **US3**: T034 ∥ T039.
- **Polish**: T045 ∥ T047.

## Implementation Strategy

- **MVP = Phase 1 + Phase 2 + Phase 3 (US1)**: delivers symmetric, self-describing artifacts with full provenance — the paper's core traceability value and constitution Principle IV. Independently demoable.
- **Increment 2 = US2**: safe branching/time-travel (the §5.3.5 headline).
- **Increment 3 = US4 + US3**: consistent guard-rails, then the cross-service export contract.
- **Increment 4 = US5**: final consolidation + grep-verified single chokepoint.
- Each story phase ends at a checkpoint that is independently testable; the E2E baseline (T002) gates every merge against regression (SC-011).

## Task Summary

- **Total**: 48 tasks
- **Setup**: 3 (T001–T003) · **Foundational**: 12 (T004–T015)
- **US1 (P1, MVP)**: 6 (T016–T021) · **US2 (P1)**: 8 (T022–T029) · **US4 (P2)**: 4 (T030–T033) · **US3 (P2)**: 7 (T034–T040) · **US5 (P3)**: 4 (T041–T044)
- **Polish**: 4 (T045–T048)
- **Test tasks**: T003, T005, T007, T010, T015, T020, T021, T028, T029, T033, T039, T040, T043, T044, T045 (15)
- **Parallel-marked**: 22 tasks
