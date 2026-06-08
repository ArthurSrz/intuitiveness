# Feature Specification: Backend/Frontend Migration to Railway (away from Streamlit)

**Feature Branch**: TBD (new milestone after PR #112) | **Created**: 2026-06-08 | **Status**: Draft
**Input**: Migrate the `intuitiveness` app off Streamlit to a full backend/frontend deployed on Railway. Backend = FastAPI wrapping the headless `intuitiveness` core; frontend = Next.js (React) onto which the user layers their own design system. REST + OpenAPI between them. Single-user, no auth, for the first cut. Memgraph + PostgreSQL + OpenRouter already live on Railway.

## Overview

The descent–ascent methodology currently ships as a Streamlit app. Streamlit couples UI and server, reruns the whole script per interaction, renders through an iframe that fights automation, and gives no real control over visual design — a blocker for a bespoke design system. Spec 016 already decoupled the package: the engine/navigation/persistence core imports and runs **headless**, reads config from env, and persists full-fidelity sessions to **PostgreSQL**. This feature builds the two halves that consume that core: a **FastAPI** REST backend and a **Next.js** frontend, both deployed as Railway services alongside the existing Memgraph + Postgres, replacing Streamlit.

The decisive enabler (from spec 015/016): navigation state is a **self-contained, versioned record in Postgres**. So the backend can be **stateless** — every request loads the session from Postgres, runs one engine transition, and saves it back. No server-side session affinity, no Streamlit rerun model.

## User Scenarios & Testing

### User Story 1 - Drive a full descent→ascent over the API (Priority: P1)

A client (the Next.js app, or any HTTP client) creates a session from a dataset, then descends L4→L0 and ascends L0→L3 by calling REST endpoints. Each call returns the new current level, the artifact at that level, and the available next moves. The whole session — every branch, each point's data and lineage — is persisted in Postgres and can be exported as one self-contained record.

**Why this priority**: This is parity with the Streamlit app's core value, delivered over a clean API the frontend (and future services) consume.

**Independent Test**: Without any UI, `POST /sessions` (School Scores), then descend through L4→L0 and ascend L0→L3 via endpoints; assert the L0 datum = 55.0 and the final tree has the expected 5 levels; `GET /sessions/{id}/export` returns a schema-valid full-fidelity record.

**Acceptance Scenarios**:
1. **Given** a new session at L4, **When** the client descends one level with valid params, **Then** the response includes the new level, a summary of the produced artifact, and the available moves; and the session in Postgres reflects the new tree node.
2. **Given** a session at L0, **When** the client ascends, **Then** the engine reconstructs the next level and the response/state update accordingly.
3. **Given** any session, **When** the client requests the export, **Then** it receives a versioned record readable without importing the package (the spec-015 contract).

### User Story 2 - Branch, time-travel, prune via the API (Priority: P1)

A client branches a new exploration from an earlier node, time-travels between branches, and prunes/archives branches — the spec-015 navigation tree, exposed over REST.

**Independent Test**: From a session, `POST /sessions/{id}/branch-from` an earlier node with a different decision; `GET /sessions/{id}/tree` shows two branches; `POST .../time-travel` moves the current pointer; `POST .../prune` removes an off-path branch.

**Acceptance Scenarios**:
1. **Given** a node with one child, **When** the client branches a different decision from it, **Then** the tree gains a sibling and the original path is unchanged.
2. **Given** a node off the current branch, **When** the client prunes it, **Then** it's removed; pruning the current branch or root is rejected with a clear error.

### User Story 3 - Next.js frontend renders each level and the navigation tree (Priority: P1)

The frontend renders the five level artifacts (L4 sources, L3 graph, L2 table, L1 vector, L0 datum), a navigation rail, and the branch tree, talking to the backend through a typed client generated from the OpenAPI schema. The user's design system supplies all visual styling via design tokens; the components consume tokens, not hardcoded styles.

**Independent Test**: With the backend running, the frontend completes a descent→ascent visually; each level view renders the artifact returned by the API; switching tokens restyles the app without component changes.

**Acceptance Scenarios**:
1. **Given** the OpenAPI schema, **When** the TS client is generated, **Then** the frontend calls are fully typed and a contract change surfaces as a type error.
2. **Given** the design-token layer, **When** a token (color/spacing/font) changes, **Then** the UI updates with no component edits.

### User Story 4 - Deployed on Railway, secrets-only config (Priority: P1)

Backend and frontend run as two Railway services in the existing `intuitiveness` project, alongside Memgraph and Postgres. The backend reaches Postgres/Memgraph over Railway's **private network**; the frontend reaches the backend over its domain. All config is environment variables — no code change between local and Railway.

**Acceptance Scenarios**:
1. **Given** the two services deployed, **When** a user drives a session in the browser, **Then** the backend uses the **internal** `DATABASE_URL` (no egress) and Memgraph, and reads `EMBEDDING_*` for domain matching.
2. **Given** a missing optional secret, **When** the app runs, **Then** it degrades gracefully (per spec 016) rather than crashing.

## Requirements

### Functional Requirements
- **FR-001**: The backend MUST expose REST endpoints covering session lifecycle, descend, ascend, branch-from, time-travel, prune/archive, per-level artifact retrieval, and full-fidelity export/import.
- **FR-002**: The backend MUST be stateless: each request loads the session from the durable store, runs the transition through the unified engine, and persists the updated tree. No in-memory session affinity.
- **FR-003**: The backend MUST reuse the existing core unchanged — `Redesigner` engine, `NavigationSession` (tree), `session_export`, `get_durable_backend()`, `neo4j_client`, `models` (embeddings). No business logic is reimplemented in the API layer.
- **FR-004**: The backend MUST publish an OpenAPI schema; the frontend MUST consume a TypeScript client generated from it.
- **FR-005**: The frontend MUST render all five level artifacts + the navigation rail + the branch tree, styled entirely via design tokens (the user's design system), with zero hardcoded visual constants in components.
- **FR-006**: Both services MUST read all configuration from environment variables (Railway secrets), using the private network for backend↔DB where available.
- **FR-007**: The migration MUST be incremental (strangler-fig): the Streamlit app (the `[app]` extra) stays runnable until the new stack reaches parity, then is deprecated/removed.
- **FR-008**: The export record produced by the API MUST be byte-compatible with the spec-015 `session_export` contract (a separate service can still consume it).

### Key Entities
- **Session**: a navigation tree persisted as one Postgres JSONB record (existing `session_records` table). Identified by `session_id`.
- **Node**: a point in the tree — level, payload (table/graph/vector/datum/sources), lineage, incoming edge decision (existing `NavigationTreeNode` / export schema).
- **Transition request**: typed params per edge (existing `params.py` dataclasses → Pydantic models).
- **Design token set**: colors, typography, spacing, radii, motion — the contract between the user's design system and the components.

## Success Criteria
- **SC-001**: A headless API test drives L4→L0→L3 and asserts L0 = 55.0 and a valid exported record — no browser.
- **SC-002**: The backend holds no session state between requests (restarting it mid-session loses nothing; the next request rehydrates from Postgres).
- **SC-003**: The frontend is fully typed against the OpenAPI schema; a backend contract change breaks the frontend build, not runtime.
- **SC-004**: Restyling via tokens changes the look with no component code changes.
- **SC-005**: Deployed on Railway, the backend uses the internal DB URL and the app runs end-to-end in the browser.
- **SC-006**: The exported record validates against `contracts/session_export.schema.json` (spec 015).

## Out of Scope (first cut)
- Authentication / multi-user isolation (planned follow-up; sessions are id-keyed now).
- Realtime collaboration / WebSocket sync (REST only first; add later if needed).
- The visual design itself (the user owns the design system; this feature provides the token-consuming structure).
- Synthetic-data generation UI (separate feature; the export contract already feeds it).
