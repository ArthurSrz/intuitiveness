# Implementation Notes & Spec Deviations — 015-adaptive-typed-levels

Discovered during `/speckit.implement`. These are findings that change the plan;
recorded here (and reflected in tasks.md) so the cutover is done correctly.

## Status snapshot

- **20/48 tasks complete**, all additive & non-breaking.
- **89 tests green**: 25 unit + 5 integration + 39 quality + 20 pure-Python E2E (`test_full_pipeline.py`, `test_domain_specific_pipeline.py`).
- New engine ships **beside** legacy; deployed app untouched.

---

## Deviation 1 — T018 is INCORRECT: `Level0Dataset.parent_data` must stay

**Spec/plan said**: remove `parent_data`/`aggregation_method`; "that info now lives as the last `SourceReference` in `lineage`."

**Reality (verified)**: `ascent/unfold.py:130` reads `datum.parent_data` (the actual parent **Series**) to reconstruct the L1 vector during ascent. The new engine's `_l0_to_l1` does the same. Per the R1 design, `DataLineage` stores operation **records, not payloads** — so the parent Series is **not** recoverable from lineage. `parent_data` is *reconstruction payload*, not redundant provenance.

**Resolution**: **Keep `parent_data`.** It is load-bearing for L0→L1 ascent. T018 is cancelled. Lineage (provenance records) and `parent_data` (the cached parent payload for reconstruction) are complementary, not duplicative.

**Spec impact**: data-model §1 note "Remove L0 special-casing … last SourceReference carries it" is withdrawn for the Series payload. The *aggregation_method* string is duplicated in the last `SourceReference.parameters["aggregation"]`, so that scalar could later be derived from lineage — but the Series cannot.

---

## Deviation 2 — Cutover (T041/T042) requires UI-forms + E2E-harness changes together

**Spec/plan said**: rewire `interactive.py`/`session.py` to the engine, then delete `redesign_legacy`.

**Reality (verified)**: the legacy callable-injection contract leaks **into the regression net and the UI**:
- `tests/e2e/test_full_pipeline.py:313` calls `Redesigner.reduce_complexity(l4, LEVEL_3, builder_func=...)` and `:339` `query_func=...`.
- `navigation/session.py` forwards `**params` (incl. these callables) to `Redesigner`.
- The descent UI forms produce these callables.

The new engine deliberately replaces callable injection with typed params (`L4toL3Params(prebuilt_graph=…)`, `L3toL2Params(domains=…)`) per FR-009. Therefore the cutover is a **coordinated change across UI forms + session + the E2E harness pipelines**, not a `session.py` edit. Deleting legacy before that coordinated change breaks 20 passing E2E tests + the deployed app.

**Resolution**: the safe cutover sequence is:
1. ✅ **Done** — prove engine ≡ legacy on deterministic edges (T044) and self-describing artifacts E2E (T021).
2. Rewrite the **graph-edge transforms** (`graph_builder.py`/`unfold.py`, T008/T009) to be payload-pure functions the engine calls — so L4→L3/L3→L2 no longer need injected callables.
3. Update the **UI descent forms** to pass typed params (built graph / domains) instead of callables.
4. Update the **E2E harness pipelines** (`test_full_pipeline.py`, `test_domain_specific_pipeline.py`) to the typed-param API — these become the *new* regression net.
5. Rewire `session.py` + `interactive.py` to the engine; run E2E green.
6. Only then delete `redesign_legacy` (T042) and `AscentOperation` (T031); T043 grep-guard passes.

**AscentOperation note**: it is publicly re-exported (`intuitiveness/__init__.py`, `ascent/__init__.py`) and used by `tests/test_descent_synthetic_ascent.py`. Its fields are already absorbed into `SourceReference`, but deletion is a public-API break that must land with step 6 + a test migration, not blindly.

---

## Cutover progress (commit 2)

**Session DESCENT path cut over to the unified Engine — verified, behavior-preserving.**

- Built the missing **session-path regression net** first (`tests/integration/test_session_cutover.py`): drives a full L4→L0 descent through `NavigationSession(use_tree=True)` exactly as the deployed app does (`streamlit_app.py:1050`). Greened against legacy, then against the engine.
- `NavigationSession.descend` now routes through `Engine` via `_descent_params()`, which adapts the UI's callable/kwarg inputs into typed params. For graph edges it **invokes `builder_func`/`query_func` exactly as legacy did** and passes the produced payload as `prebuilt_graph`/`prebuilt_table` — so the payload (and behavior) is identical; the engine just wraps it + stamps lineage.
- Added `L3toL2Params.prebuilt_table` + engine support for it.
- 92 tests green (incl. 20 pure-Python E2E + the new session net). Deployed app descent path unchanged in behavior, now lineage-stamped.

**Still on legacy (deliberately, pending verification):**
- **Session ASCENT** (`NavigationSession.ascend`) — the engine's ascent reconstructs from `parent_data` while legacy uses enrichment/dimension semantics; cutting over changes app behavior and needs the **Playwright E2E** + an ascent regression net first. Left on legacy.
- **`interactive.py`** (the 979-line god-class) and **legacy/`AscentOperation` deletion** — gated on the ascent cutover + browser E2E (step 5–6).

## What was safely delivered (additive, tested)

| Area | Status |
|------|--------|
| Extended `SourceReference` (single provenance type) | ✅ tested |
| Typed transition params | ✅ tested |
| Unified `Engine` (deepcopy, invariants, sole constructor) | ✅ tested; proven ≡ legacy (T044) |
| Symmetric self-describing levels (`lineage`+`summary()`) | ✅ tested |
| Tree: full-payload nodes, `summary()` snapshot, generator query API | ✅ tested |
| Branching isolation / time-travel / divergence_point | ✅ tested |

All shipped beside legacy. `from intuitiveness.redesign import Engine` (new) vs `Redesigner` (legacy, transitional).
