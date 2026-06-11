# Tasks: Backend/Frontend Migration to Railway (FastAPI + Next.js)

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **API**: [contracts/rest-api.md](./contracts/rest-api.md)

Organized by user story (US1–US4, all P1). Tests are included because the spec
defines explicit Independent Tests + Success Criteria. `[x]` = already done this
session (commit `6563435` unless noted). File paths are relative to repo root.

Stack: FastAPI (backend/), Next.js+TS (frontend/), the existing `intuitiveness`
package (core, reused), PostgreSQL + Memgraph + OpenRouter (live on Railway).

---

## Phase 1: Setup

- [x] T001 Create backend package structure in backend/app/__init__.py
- [x] T002 Create backend/requirements.txt (fastapi>=0.110, uvicorn[standard]>=0.29, httpx, pytest, and `-e .[postgres,graph]` for the core) in backend/requirements.txt
- [ ] T003 [P] Scaffold Next.js App Router + TypeScript + Tailwind in frontend/ (package.json, tsconfig, app/, tailwind.config)

## Phase 2: Foundational (blocking — must precede all user stories)

- [x] T004 Stateless SessionService (load→transition→save) in backend/app/service.py
- [x] T005 Demo L4 dataset loader (School Scores = mean 55) in backend/app/demo.py
- [x] T006 Named L4→L3 graph builders registry in backend/app/builders.py
- [x] T007 L0 export-fidelity fix (persist parent vector; schema 1.0.0→1.1.0) in intuitiveness/persistence/session_export.py
- [x] T008 Pydantic request/response models (CreateSession, TransitionParams, State, TreeView, ExportRecord) in backend/app/models.py

## Phase 3: User Story 1 — Drive a full descent→ascent over the API (P1)

**Goal**: A client creates a session and descends L4→L0 + ascends L0→L3 via REST; each call returns level, artifact summary, and available moves; the whole session is persisted and exportable.
**Independent test**: `POST /sessions` (School Scores) → descend to L0 (assert datum=55.0) → ascend to L3 → `GET /export` is schema-valid; restart the app mid-session and confirm rehydration.

- [x] T009 [US1] FastAPI app: CORS (ALLOWED_ORIGINS), Postgres-pool lifespan, SessionService dependency, router mounting in backend/app/main.py
- [x] T010 [P] [US1] Sessions router (POST create, GET state, GET list, DELETE) in backend/app/routers/sessions.py
- [x] T011 [P] [US1] Transitions router (POST /sessions/{id}/descend, /ascend); map TransitionError/NavigationError → 409, validation → 422 in backend/app/routers/transitions.py
- [x] T012 [P] [US1] Nodes + export router (GET /sessions/{id}/nodes/{node_id}, GET /export, POST /sessions/import) in backend/app/routers/artifacts.py
- [x] T013 [US1] httpx ASGI test: full descent→ascent over HTTP (assert L0=55.0 + schema-valid export) and statelessness (fresh service rehydrates), using a temp FileDurableBackend, in backend/tests/test_api_cycle.py

## Phase 4: User Story 2 — Branch, time-travel, prune via the API (P1)

**Goal**: The spec-015 navigation tree exposed over REST.
**Independent test**: `branch-from` an earlier node → `GET /tree` shows two branches; `time-travel` moves current; `prune` removes an off-path branch; pruning current/root → 409.

- [x] T014 [US2] Tree router (GET /sessions/{id}/tree, POST /time-travel, /branch-from, /prune, /archive) in backend/app/routers/tree.py
- [x] T015 [US2] httpx test: branch-from → 2 branches, time-travel, prune off-path; prune current/root rejected (409) in backend/tests/test_api_tree.py

## Phase 5: User Story 3 — Next.js frontend renders levels + navigation tree (P1)

**Goal**: The frontend drives a session and renders all five level artifacts + rail + branch tree via a typed client; styling flows entirely through design tokens.
**Independent test**: complete a descent→ascent in the browser; flip a token → restyle with no component edits.

- [ ] T016 [US3] OpenAPI→TypeScript client: `gen:api` script (openapi-typescript) + typed fetch wrapper in frontend/lib/api/
- [ ] T017 [P] [US3] Design-token layer (CSS variables + Tailwind theme: color/type/space/radii/motion) — the seam for the user's design system — in frontend/styles/tokens.css
- [ ] T018 [P] [US3] Level views (L4 sources, L3 graph via react-flow, L2 table, L1 vector, L0 datum), tokens-only styling, in frontend/components/levels/
- [ ] T019 [US3] Navigation rail + branch-tree components (from GET /tree) in frontend/components/nav/
- [ ] T020 [US3] Session page wiring (create → descend/ascend → branch/prune → export) with React Query over the typed client in frontend/app/session/
- [ ] T021 [US3] Chrome MCP walkthrough: full descent→ascent in browser + token-flip restyle (per CLAUDE.md UI-test rule)

## Phase 6: User Story 4 — Deployed on Railway, secrets-only config (P1)

**Goal**: Backend + frontend as two Railway services beside Memgraph + Postgres; backend↔DB over the private network; all config via env.
**Independent test**: in the browser against the deployed services, drive a session; backend uses internal DATABASE_URL; `/healthz` green.

- [x] T022 [US4] /healthz endpoint mirroring the three verify scripts (postgres/memgraph/embeddings) in backend/app/routers/health.py
- [x] T023 [US4] Railway backend service: root backend/, start `uvicorn app.main:app`, env DATABASE_URL (internal ref) + MEMGRAPH_* + EMBEDDING_* + ALLOWED_ORIGINS; verify /healthz on Railway
- [x] T024 [US4] Railway frontend service: root frontend/, NEXT_PUBLIC_API_URL → backend public domain; browser walkthrough on Railway green

## Phase 7: Polish & Cross-Cutting (Phase D — retire Streamlit)

- [ ] T025 Reconcile plan.md "intuitiveness/ unchanged" claim with the justified L0 core fix (analyze C1) in specs/017-backend-frontend-railway/plan.md
- [ ] T026 [P] Decide + implement (or explicitly defer) L3→L2 embeddings categorization in the API (analyze U3) in backend/app/service.py
- [ ] T027 [P] Standardize `available_moves` shape across contract + code (analyze I2) in specs/017-backend-frontend-railway/contracts/rest-api.md + backend/app/service.py
- [ ] T028 Retire Streamlit AFTER parity + E2E green: delete intuitiveness/streamlit_app.py, intuitiveness/ui/, intuitiveness/app/ pages, the `[app]` extra in pyproject.toml, and streamlit lines in requirements.txt
- [ ] T029 [P] Update README/docs with new run commands; remove Streamlit-specific notes

---

## Dependencies (story completion order)
- Setup (T001–T003) → Foundational (T004–T008) → **US1** (T009–T013) → **US2** (T014–T015, needs the app+routers from US1) → **US3** (T016–T021, needs the API) → **US4** (T022–T024, deploys API+frontend) → **Polish/D** (T025–T029; T028 only after US1–US4 + E2E green).

## Parallel opportunities
- Setup: T003 (frontend scaffold) ∥ backend setup.
- US1: T010 ∥ T011 ∥ T012 (separate router files) after T009.
- US3: T017 ∥ T018 (tokens + level views, distinct files).
- Polish: T026 ∥ T027 ∥ T029.

## MVP scope
**US1 (Phase 3)** is the MVP: the engine driveable over HTTP, headless-testable, no frontend required. Foundational layer (T004–T007) is already done, so MVP = T002, T008, T009–T013.

## Status note
Foundational service layer + L0 fix (T001, T004–T007) are **done and verified** (commit `6563435`): full descent=55.0 + ascent + statelessness pass headless. Remaining MVP work is the FastAPI shell (T008–T013) around the working service.
