# Research: Backend/Frontend Migration to Railway

Phase 0 for spec 017. Each item: **Decision / Rationale / Alternatives**.

## R1 — Stateless backend over stateful navigation (the crux)

**Decision**: The FastAPI backend is **stateless**. Every mutating request = `load session from Postgres → run one engine transition → save the updated tree`. Read requests just load + project.

**Rationale**: Spec 015/016 already made the navigation tree a **self-contained, versioned record** and built `get_durable_backend()` (Postgres JSONB) + `session_export.import_session`/`export_session` + `NavigationSession.save()/_from_tree()`. So per request:
1. `record = get_durable_backend().load_record(session_id)`
2. `tree = import_session(record)` → `session = NavigationSession._from_tree(tree, meta)`
3. `session.descend(**params)` / `ascend` / `branch_from` / `prune` …  (the unified engine)
4. `session.save()` (writes the JSONB row back)

This means **no server-side session memory, no sticky sessions, horizontal scalability for free**, and restarting the backend mid-session loses nothing (SC-002). The hardest problem in porting Streamlit (its per-script rerun state model) is already solved by the durable store.

**Cost note**: load+save per request serializes the whole tree. For the reference datasets (tiny) this is negligible. If sessions grow large later, add (a) a short-lived in-process LRU cache keyed by session_id+version, or (b) per-node lazy loading. Not needed for the first cut.

**Alternatives**: In-memory `NavigationSession._sessions` registry (the current class-level dict) — rejected: it doesn't survive restarts or scale horizontally, and re-creates Streamlit's fragility. Redis session store — unnecessary; Postgres already holds the durable record.

## R2 — Railway deployment topology

**Decision**: One Railway project (`intuitiveness`, already created) with **four services**: `backend` (FastAPI), `frontend` (Next.js), `Postgres` (existing), `memgraph` (existing). Monorepo with **root-directory-per-service** (`backend/`, `frontend/`).

**Rationale**: Railway publishes an official **Next.js + FastAPI full-stack starter** and documents monorepo deploys via per-service root directories. Backend reaches Postgres/Memgraph over the **private network** (`postgres.railway.internal:5432`, the internal Memgraph host) — no egress, lower latency; Railway injects `DATABASE_URL`. Frontend reaches backend via `NEXT_PUBLIC_API_URL` = backend's public domain; backend sets `ALLOWED_ORIGINS` = frontend's domain (CORS). `RAILWAY_PUBLIC_DOMAIN` auto-updates on deploy.

**Rationale for monorepo**: keeps the Python core, the FastAPI app (which imports it), and the frontend versioned together; simplest for a solo dev.

**Alternatives**: Separate repos per service (more CI overhead, version drift). Single combined service (FastAPI serving the Next.js build) — couples deploy cadence and loses Next.js SSR/edge benefits; rejected.

Sources: [Railway Next.js+FastAPI starter](https://railway.com/deploy/nextjs-fastapi-full-stack-starter), [Railway monorepo guide](https://docs.railway.com/guides/monorepo), [Railway FastAPI guide](https://docs.railway.com/guides/fastapi).

## R3 — FastAPI app structure & dependency injection

**Decision**: Thin FastAPI app under `backend/app/`. Routers per resource (`sessions`, `transitions`, `tree`, `export`). A `get_session_service` dependency wraps `load → mutate → save`. Connection pooling for Postgres via FastAPI **lifespan** (startup pool init). Pydantic models mirror the existing `params.py` edge dataclasses and the level summaries.

**Rationale**: FastAPI's dependency-injection + lifespan are the documented pattern for DB-backed apps; pooling at startup beats per-request connect. The backend imports `intuitiveness[postgres,graph]` (the extras from spec 016) — no business logic duplicated (FR-003).

**Alternatives**: Sync Flask (no async, hand-rolled OpenAPI) — rejected per stack decision. Heavy SQLAlchemy ORM layer — unnecessary; the durable backend already owns persistence (one JSONB table), so the API uses it directly rather than a second ORM.

Sources: [FastAPI SQL/sessions](https://fastapi.tiangolo.com/tutorial/sql-databases/), [FastAPI session-per-request discussion](https://github.com/fastapi/fastapi/discussions/10622).

## R4 — Frontend: typed client + design-token seam

**Decision**: Next.js (App Router) + TypeScript. Generate a **typed API client from the backend OpenAPI** (e.g. `openapi-typescript` + a thin fetch wrapper, or `orval`). All styling flows through a **design-token layer** (CSS variables / Tailwind theme) the user owns; components read tokens, never hardcode colors/spacing (FR-005, SC-004).

**Rationale**: OpenAPI→TS codegen makes the frontend break at **build time** on contract drift (SC-003). A token seam lets the user drop in their design system without touching component logic. Tailwind + CSS variables is the most common, lowest-friction token mechanism for a React design system (shadcn/Radix optional, user's call).

**Alternatives**: Hand-written API types (drift risk). GraphQL client (richer for the tree, but heavier — deferred, see R5). CSS-in-JS — viable but tokens-as-CSS-vars is framework-agnostic and SSR-friendly.

## R5 — API style: REST now, GraphQL later if the tree demands it

**Decision**: **REST + OpenAPI**. Model the branch tree as `GET /sessions/{id}/tree` returning the flat node map (the export schema's shape) + a `current_id`; the frontend builds the tree client-side.

**Rationale**: FastAPI auto-generates OpenAPI; the existing `session_export` already defines the tree's flat-node JSON shape, so the tree endpoint is almost free. REST keeps the first cut simple.

**When to revisit**: if the frontend needs to fetch arbitrary subtrees/partial payloads efficiently (large sessions), a single GraphQL query endpoint becomes attractive. Not now.

## R6 — Migration strategy (strangler-fig) + Streamlit's fate

**Decision**: Incremental. Phase the build so the **API reaches engine parity first** (headless tests), then the **frontend reaches screen parity**, with the Streamlit app (`intuitiveness[app]`) staying runnable as the reference throughout. Remove Streamlit (`[app]` extra, `streamlit_app.py`, `ui/`) only once parity + the E2E suite pass on the new stack.

**Rationale**: De-risks the migration — the working Streamlit app is the oracle to diff against, and nothing is deleted until the replacement is proven. Matches the constitution's incremental ethos.

**Alternatives**: Big-bang rewrite (delete Streamlit, build new) — rejected: loses the reference and risks a long broken period.

## Resolved unknowns
| Unknown | Status |
|---|---|
| Stateful nav over stateless REST | RESOLVED — durable Postgres record + import/export already do it |
| Railway topology | RESOLVED — 4 services, monorepo root-dirs, private network |
| FastAPI structure / pooling | RESOLVED — thin routers + lifespan pool, reuse core via extras |
| Frontend typing + token seam | RESOLVED — OpenAPI→TS client + CSS-var/Tailwind tokens |
| API style | RESOLVED — REST/OpenAPI now; GraphQL deferred |
| Streamlit removal timing | RESOLVED — strangler-fig, remove after parity |
