# Implementation Plan: Adaptive Typed Levels & Unified Redesign Engine

**Branch**: `015-adaptive-typed-levels` | **Date**: 2026-06-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/015-adaptive-typed-levels/spec.md`

## Summary

Realign the `intuitiveness` package with the paper's §5.3 architecture. Make all five level classes **symmetric and self-describing** (each carries its full derivation history + a polymorphic `summary()`), collapse the **three parallel transition engines** into a single typed **Redesigner chokepoint** that is the sole constructor of level artifacts and the sole lineage-stamper, keep `descent/`/`ascent/` as **payload-pure transformation cores** the engine calls, unify provenance into **one record type**, split invariant enforcement by the **stateless (Redesigner) / stateful (NavigationSession)** principle, make the **branching tree always-on** as the single history structure with a generator-facing query API, and add a **full-fidelity, versioned, self-contained persistence contract** (distinct from the lightweight localStorage index) for a future synthetic-generation service to consume.

## Technical Context

**Language/Version**: Python 3.11.9
**Primary Dependencies**: pandas 2.3.3 (DataFrames/Series), networkx 3.6.1 (graphs), dataclasses + typing (entities/typed params), copy.deepcopy (lineage isolation). No new runtime dependencies.
**Storage**: JSON for the session export record (cross-service contract); existing payload serializers (`serialize_dataframe` = zlib+base64, `serialize_graph` = node-link JSON, `serialize_value`); a durable file/blob backend for full payloads; the existing localStorage-style `StorageBackend` demoted to a lightweight session index.
**Testing**: pytest (+ behave) — `testpaths=["tests"]`, markers `slow`/`integration`; existing E2E suite under `tests/e2e/` (incl. Playwright UI) is the behavioral safety net (SC-011).
**Target Platform**: Python library + Streamlit app (Streamlit Cloud deploy). Consumer of the export contract may be any process/language.
**Project Type**: Single project (library `intuitiveness/` + bundled Streamlit app). No new top-level structure.
**Performance Goals**: Lineage deepcopy adds negligible per-transition cost (records only, no payloads copied). Lineage retrieval <1s for 100K-row sessions (inherited `DataLineage` target). Export/load linear in node count.
**Constraints**: localStorage session **index** must stay within ≈5 MB regardless of session size (FR-027/SC-010); export must be loadable **without importing `intuitiveness`** internal classes (FR-025/SC-008); the non-deterministic L4→L3 step forbids lazy re-derivation (full payloads retained, FR-020).
**Scale/Scope**: 5 level classes, 1 engine, ~7 typed transition methods + param dataclasses, 1 tree, 1 export schema. Touches `complexity.py`, `redesign*/`, `descent/`, `ascent/`, `interactive.py`, `navigation/`, `persistence/`. Reference datasets: 3 (school scores, ADEME fundings, energy prices).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Abstraction Levels & Navigation Rules** | ✅ Strengthens | FR-014 (adjacency / no L4 destination) + FR-015 (entry-only at L4, no re-entry) encode Principle I rules 1–3 in exactly one place each. Horizontal same-level movement (rule 2) is **preserved**, not removed — the always-on tree hosts sibling nodes; no regression. |
| **II. Descent-Ascent Cycle** | ✅ Strengthens | Single Redesigner exposes `reduce_complexity` (descent) and `increase_complexity` (ascent) symmetrically; descent/ascent semantics stay first-class (FR-010). |
| **III. Complexity Quantification** | ✅ Compatible | Provenance step retains `row_count_before/after` (FR-004); ascent row-count preservation enforced (FR-014). Reduction-bound *measurement* is untouched (out of scope), not violated. |
| **IV. Human-Data Interaction Granularity (end-to-end interpretability)** | ✅ **Operationalizes** | FR-001/FR-002 make *every* level carry full lineage back to atomic/raw origin — this is the concrete mechanism for "trace from any derived insight back to atomic data points." Today only L0 can; this closes the gap. |
| **V. Design for Diverse Data Publics (non-technical users)** | ✅ No impact | Internal architecture realignment; no user-facing terminology changes. The export contract targets a downstream **service**, not end users. UI continues to use domain language. |
| **Quality Gate: transitions preserve data integrity** | ✅ | FR-014 (row-count preservation) + FR-004 (optional integrity fingerprints). |
| **Quality Gate: final dataset independently testable** | ✅ | Per-level `summary()` + symmetric lineage make any level independently inspectable/testable. |
| **Coding practice: spec-driven (speckit)** | ✅ | This plan is produced via the speckit flow. |

**Result: PASS — no violations.** No entries in Complexity Tracking. This refactor advances Principles I and IV beyond their current partial implementation.

*Constitution re-check after Phase 1 design: still PASS (see end of plan).*

## Project Structure

### Documentation (this feature)

```text
specs/015-adaptive-typed-levels/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── dataset_api.md            # base Dataset: lineage + summary() contract
│   ├── redesigner_api.md         # typed transition methods + param dataclasses
│   ├── navigation_api.md         # NavigationSession + NavigationTree query API
│   └── session_export.schema.json # versioned cross-service wire schema
└── tasks.md             # /speckit.tasks output (NOT created here)
```

### Source Code (repository root)

The package already exists; this refactor **modifies in place** and adds two focused modules. No new top-level layout.

```text
intuitiveness/
├── complexity.py                 # MODIFY: base Dataset gains lineage + summary(); 5 levels symmetric
├── redesign/
│   ├── __init__.py               # MODIFY: export the promoted Redesigner + typed params
│   ├── lineage.py                # MODIFY: extend SourceReference (id, hashes); DataLineage unchanged API
│   ├── params.py                 # ADD: typed transition param dataclasses (L4toL3Params … ascent mirrors)
│   └── engine.py                 # ADD: promoted Redesigner (sole chokepoint, typed dispatch, deepcopy+stamp)
├── redesign_legacy.py            # REMOVE at end (after callers migrated)
├── descent/
│   └── semantic_join.py          # KEEP payload-pure (already is)
├── ascent/
│   ├── dimensions.py             # KEEP (payload-pure)
│   ├── enrichment.py             # KEEP (payload-pure)
│   ├── semantic_join? / unfold.py# MODIFY: strip 4 LevelNDataset constructions → return payloads
│   ├── graph_builder.py          # MODIFY: strip 3 LevelNDataset constructions → return payloads
│   └── operations.py             # MODIFY: delete AscentOperation (fields absorbed into SourceReference)
├── interactive.py                # MODIFY: InteractiveRedesigner delegates transitions to Redesigner
├── navigation/
│   ├── session.py                # MODIFY: tree-only; path-invariants only; remove use_tree dual dispatch
│   ├── tree.py                   # MODIFY: full-payload nodes; query API; full-fidelity to_dict/from_dict
│   └── history.py                # REMOVE: flat NavigationHistory (subsumed by tree)
└── persistence/
    ├── serializers.py            # REUSE
    ├── storage_backend.py        # KEEP as localStorage index backend
    ├── durable_backend.py        # ADD: file/blob backend for full-payload records
    └── session_export.py         # ADD: versioned full-fidelity export/import (flat id-keyed map)

tests/
├── unit/                         # ADD focused unit tests per component (new dir)
├── integration/                  # extend: engine+session integration
└── e2e/                          # REUSE as regression net (SC-011); extend with branch/export E2E
```

**Structure Decision**: Single-project, in-place modification of the existing `intuitiveness/` package. Two new modules (`redesign/engine.py`, `redesign/params.py`) and two new persistence files (`durable_backend.py`, `session_export.py`) are additive; everything else modifies existing files. The `intuitiveness.*` import surface is preserved except for the deliberately-removed `AscentOperation`, `NavigationHistory`, and `redesign_legacy` (tracked breaking removals — see research.md §Backward Compatibility).

## Complexity Tracking

> No Constitution violations. Section intentionally empty.
