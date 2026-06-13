# Implementation Plan: Backend/Frontend Migration to Railway (away from Streamlit)

**Date**: 2026-06-08 | **Spec**: [spec.md](./spec.md) | **Research**: [research.md](./research.md) | **API**: [contracts/rest-api.md](./contracts/rest-api.md)
**Status**: Draft — new milestone, starts after PR #112 merges.

## Summary

Replace the Streamlit app with a **FastAPI** REST backend (wrapping the headless `intuitiveness` core) and a **Next.js** frontend (onto which the user layers a design system), both deployed as Railway services next to the existing Memgraph + PostgreSQL. REST + OpenAPI between them; single-user, no auth, first cut. The migration is **strangler-fig**: API parity first, frontend parity next, Streamlit removed last.

The architecture is unlocked by prior work: the core is headless (spec 016), and navigation state is a self-contained Postgres record (spec 015). So the **backend is stateless** — each request loads the session from Postgres, runs one engine transition, and saves it back. There is **no new business logic** in the API: it adapts HTTP ↔ the existing `Redesigner` engine, `NavigationSession`, `session_export`, `durable_backend`, `neo4j_client`, and `models`. **Exception (Phase A)**: `intuitiveness/persistence/session_export.py` received one justified fix — persisting the parent vector so L0 exports round-trip correctly (schema bumped 1.0.0→1.1.0, backward-compatible). This is the only core change; all engine/navigation logic is untouched.

## Technical Context

**Backend**: Python 3.11, FastAPI, uvicorn, Pydantic v2, psycopg2 (via `intuitiveness[postgres]`), neo4j (`[graph]`). Imports `intuitiveness` core. Stateless.
**Frontend**: Next.js (App Router) + TypeScript + a design-token layer (Tailwind/CSS vars, user-owned). Typed API client generated from `/openapi.json`.
**Data store**: existing Railway PostgreSQL (`session_records` JSONB = sessions); Memgraph (optional graph feature); OpenRouter `baai/bge-m3` (embeddings). All via env/secrets.
**Deploy**: Railway project `intuitiveness`, 4 services (backend, frontend, Postgres, memgraph), monorepo root-dirs; backend↔DB over private network.
**Repo shape**: monorepo — `backend/` (FastAPI), `frontend/` (Next.js), `intuitiveness/` (the existing package, unchanged).

## Constitution Check

- **Intuitiveness / abstraction levels**: the level model (L0–L4) and navigation rules are unchanged — they live in the core; the API/UI only expose them. PASS.
- **Target users (non-technical, "domain-curious")**: a real design system + responsive frontend serves them better than Streamlit's constrained UI. PASS.
- **Graceful degradation / no hardcoded secrets**: inherited from spec 016 (config from env; optional features degrade). PASS.
- **Spec-driven / kernel theory §5.3**: the engine + export contract are reused verbatim; nothing in §5.3 changes. PASS.
- Gate: PASS (no new violations).

## Phased work (each phase independently testable)

### Phase A — FastAPI backend reaches engine parity (P1)
- `backend/app/main.py`: FastAPI app, CORS (`ALLOWED_ORIGINS`), lifespan Postgres pool, mount routers.
- `backend/app/deps.py`: `get_session_service()` → load (`get_durable_backend().load_record`) → `import_session` → `NavigationSession._from_tree` → (mutate) → `session.save()`.
- Routers: `sessions`, `transitions` (descend/ascend), `tree` (tree/time-travel/branch-from/prune/archive), `nodes` (per-level artifacts), `export`, `graph` (Memgraph), `health`.
- Pydantic request models mirror `intuitiveness/redesign/params.py` edges; map `TransitionError`/`NavigationError` → 409/422.
- Demo-data loader endpoints (School Scores / ADEME / Energy) reusing the package's demo datasets.
- **Test (SC-001/SC-002)**: pytest + httpx — drive L4→L0→L3 over the API, assert L0 = 55.0 + valid export; restart the app mid-session and confirm the next call rehydrates from Postgres.

### Phase B — Next.js frontend reaches screen parity (P1)
- `frontend/` Next.js app; `npm run gen:api` → `openapi-typescript` against the backend `/openapi.json` → typed client.
- **Design-token layer first**: `tokens.css`/Tailwind theme (colors, type, spacing, radii, motion) — the seam the user's design system plugs into. Components consume tokens only.
- Views: L4 sources, L3 graph (a graph lib, e.g. react-flow/cytoscape), L2 table (data grid), L1 vector, L0 datum; the descent/ascent **level rail**; the **branch tree** (from `GET /tree`); export/import controls; a deps **status badge** (`/healthz`).
- State: a thin client store (React Query/SWR) over the typed client; the server is the source of truth (no client-side engine).
- **Test (SC-003/SC-004)**: Chrome MCP walkthrough (per CLAUDE.md) — full descent→ascent in the browser; flip a token and confirm restyle with no component edits.

### Phase C — Railway deployment (P1)
- Add `backend` service (root `backend/`, start `uvicorn app.main:app`), install `intuitiveness[postgres,graph]` + API deps; set `DATABASE_URL` (private ref), `MEMGRAPH_*`, `EMBEDDING_*`, `ALLOWED_ORIGINS`.
- Add `frontend` service (root `frontend/`, Next.js build); set `NEXT_PUBLIC_API_URL` = backend public domain.
- Wire backend→Postgres/Memgraph over the **internal** network; verify `/healthz` green on Railway.
- **Test (SC-005)**: browser walkthrough against the deployed services.

### Phase D — Cut over & retire Streamlit (P1)
- Once A–C reach parity and the E2E suite is green on the new stack: deprecate then delete `intuitiveness/streamlit_app.py`, `intuitiveness/ui/`, `intuitiveness/app/` (Streamlit pages), and the `[app]` extra; drop the `streamlit*` lines from `requirements.txt`. The headless core + `[graph]`/`[postgres]` extras remain.
- Update docs/README to the new run commands; remove the Chrome-MCP Streamlit-specific notes that no longer apply.

## Repo structure (target)
```
backend/            # FastAPI — imports intuitiveness core, stateless
  app/{main,deps}.py, app/routers/*.py, app/models/*.py, tests/
frontend/           # Next.js + TS, design-token layer, generated API client
  app/, components/, lib/api/ (generated), styles/tokens.css
intuitiveness/      # existing package (engine/nav/persistence) — unchanged except session_export.py (schema 1.0.0→1.1.0, Phase A justified fix)
specs/017-backend-frontend-railway/  # this spec
```

## Verification (end-to-end)
1. Backend API test: L4→L0→L3 → L0 = 55.0, export schema-valid; stateless restart test passes.
2. `GET /healthz` reports postgres+memgraph+embeddings all up (mirrors the three verify scripts).
3. Frontend typed against OpenAPI (build breaks on contract drift); token flip restyles with no component change.
4. Railway: backend uses internal `DATABASE_URL`; browser walkthrough (descent→ascent, branch/prune, export) passes.
5. Export record validates against `contracts/session_export.schema.json` (spec 015).
6. Streamlit removed; full pytest suite + new API/E2E tests green.

## Risks & mitigations
- **Engine parity gaps** (a Streamlit-only behavior not in the engine): mitigate by diffing against the running Streamlit app during Phase A/B (strangler-fig keeps it as the oracle).
- **Large-session load/save cost** (stateless load per request): negligible for reference datasets; add an LRU/version cache only if needed (research R1).
- **CORS / Railway domain wiring**: follow the Railway Next.js+FastAPI starter pattern; `RAILWAY_PUBLIC_DOMAIN` + `ALLOWED_ORIGINS`.
- **Design-system scope creep**: the feature delivers the **token seam + structural components**, not the visual design (user-owned) — keep that boundary explicit.

## Open questions for the user
- Repo layout: **monorepo** (recommended — `backend/` + `frontend/` beside `intuitiveness/`) vs separate repos?
- Graph visualization library preference (react-flow vs cytoscape vs sigma) for the L3 view?
- Does the design system come with a component primitive set (e.g. shadcn/Radix) the components should target, or raw tokens + your own primitives?

## Next step
This is a new milestone. Recommended: merge PR #112 first (it ships the headless core + extras this depends on), then start Phase A (the FastAPI backend) — it's fully testable headless before any frontend exists.
