# Feature Specification: Deployment & Distribution (Railway infra + OpenRouter + PyPI)

**Feature Branch**: `015-adaptive-typed-levels` (rides PR #112)
**Created**: 2026-06-08
**Status**: Draft
**Input**: Deploy the spec-015 hosted dependencies (graph DB, durable session store) on Railway and configure external embeddings (OpenRouter `baai/bge-m3`), AND keep `intuitiveness` cleanly distributable on PyPI — a `pip` consumer brings their own config and installs only the capabilities they use; deployment secrets and hosted infra are never baked into the distributable.

## Overview

Spec-015 introduced three runtime dependencies that live *outside* the Python package: a **graph database** (Memgraph, for the L4→L3 knowledge graph + Cypher agent), a **durable session store** (PostgreSQL, for full-fidelity session records), and an **embeddings API** (for semantic domain matching). All three are read from configuration (`st.secrets` → environment) with graceful fallbacks, so the library runs with none of them.

This feature defines **how that infra is deployed** (Railway + OpenRouter) and — the user's central concern — **how it coexists with PyPI distribution**: the package must remain installable and usable without forcing multi-GB ML stacks or database drivers on consumers who don't use those features, while the bundled Streamlit Cloud deployment gets the full feature set through secrets only (no code change).

## User Scenarios & Testing

### User Story 1 - A PyPI consumer installs the package and it just works, lean (Priority: P1)

A developer runs `pip install intuitiveness` and uses the library headlessly (or builds their own UI). With no hosted infra and no secrets configured, every optional capability degrades gracefully: semantic matching falls back to keyword/positional matching, the session store falls back to local JSON files, and the graph feature is simply off. The install does **not** pull `torch`/`sentence-transformers`, a database driver, or `neo4j` unless the consumer opts in.

**Why this priority**: The package's value as a distributable library collapses if a bare install drags in a multi-GB ML stack and DB drivers for features the consumer never touches. This is the core distribution contract.

**Independent Test**: In a clean venv, `pip install intuitiveness` (no extras); confirm `import intuitiveness` works, a descent→ascent runs, a session saves to a local file, and `pip freeze` contains no `torch`, `sentence-transformers`, `psycopg2`, or `neo4j`.

**Acceptance Scenarios**:
1. **Given** a clean environment with no secrets/env vars, **When** the consumer runs a descent→ascent and saves the session, **Then** it succeeds using the file session store and keyword matching, with no network calls required.
2. **Given** a bare `pip install intuitiveness`, **When** the consumer inspects installed packages, **Then** no graph driver, database driver, or local embedding model is present.

### User Story 2 - An operator deploys the full app via secrets only (Priority: P1)

An operator deploys the Streamlit app (locally or on Streamlit Cloud) backed by Railway-hosted Memgraph + PostgreSQL and OpenRouter embeddings. They set connection values in `.streamlit/secrets.toml` (local) or the Cloud Secrets UI — **no code change** — and confirm each dependency with a one-command verifier before using the app.

**Why this priority**: Closes the two editor concerns (hosted graph DB, API embeddings) end-to-end and makes the deployed app reproducible.

**Independent Test**: With Railway Memgraph + Postgres deployed and OpenRouter key set, run the three verifiers (`verify_graph_db`, `verify_session_db`, an embeddings one-liner) and get PASS/valid output for each; then exercise graph, domain matching, and session save in the running app.

**Acceptance Scenarios**:
1. **Given** the four secret groups are set, **When** the operator runs each verifier, **Then** each reports success (graph reachable/writable; session store reachable/writable; embeddings return a 1024-dim vector).
2. **Given** the same code with secrets unset, **When** the app runs, **Then** it starts and works in degraded mode (no crashes), proving secrets — not code — toggle the capabilities.

### User Story 3 - A consumer opts into one capability (Priority: P2)

A consumer who wants only the durable Postgres store installs `intuitiveness[postgres]` and supplies their own `DATABASE_URL`; a consumer who wants the graph installs `intuitiveness[graph]` with their own Memgraph/Neo4j endpoint. Each extra pulls exactly one driver.

**Acceptance Scenarios**:
1. **Given** `pip install intuitiveness[postgres]` + a `DATABASE_URL`, **When** a session is saved, **Then** it is written to the consumer's PostgreSQL, not local files.
2. **Given** `pip install intuitiveness[graph]` + Memgraph creds, **When** the graph feature runs, **Then** it connects to the consumer's database.

## Requirements

### Functional Requirements
- **FR-001**: All hosted-infra and embeddings configuration MUST be read from `st.secrets` first, then environment variables, with no values hardcoded.
- **FR-002**: With any capability unconfigured, the package MUST degrade gracefully (embeddings→keyword/positional; session store→local files; graph→off) without raising.
- **FR-003**: A bare `pip install intuitiveness` MUST NOT install `sentence-transformers`/`torch`, a graph driver, or a database driver.
- **FR-004**: Optional capabilities MUST be installable as extras: `intuitiveness[graph]` (graph driver), `intuitiveness[postgres]` (Postgres driver), `intuitiveness[app]` (Streamlit UI stack); a meta `intuitiveness[all]` MAY combine them.
- **FR-005**: The distributable MUST NOT contain any secret, connection string, or hosted endpoint; only example/templated config (`secrets.toml.example`) ships.
- **FR-006**: Each external dependency MUST have a one-command verifier usable both locally and in CI/headless (`verify_graph_db`, `verify_session_db`, embeddings check).
- **FR-007**: Local (`.streamlit/secrets.toml`) and Streamlit Cloud (Secrets UI) MUST accept the same key names; env vars MUST work for non-Streamlit consumers.
- **FR-008**: The Streamlit Cloud `requirements.txt` MUST include the drivers the deployed app needs (graph + postgres), while `pyproject.toml` keeps them as extras for library consumers.

### Key Entities
- **Secrets contract**: the canonical key set (`EMBEDDING_*`, `MEMGRAPH_*`/`NEO4J_*`, `SESSION_DATABASE_URL`/`DATABASE_URL`/`POSTGRES_URL`) + resolution precedence + fallback behavior.
- **Distribution profiles**: bare library, `[graph]`, `[postgres]`, `[app]`, `[all]`, and the Streamlit Cloud profile (requirements.txt).

## Success Criteria
- **SC-001**: Clean-venv bare install pulls none of: `torch`, `sentence-transformers`, `psycopg2*`, `neo4j`.
- **SC-002**: With no secrets, the app starts and a descent→ascent + session save succeed (degraded mode).
- **SC-003**: With secrets set, all three verifiers pass and the live app uses Memgraph, Postgres, and OpenRouter embeddings.
- **SC-004**: No secret or hosted endpoint appears in the built sdist/wheel.
- **SC-005**: `pyproject.toml` dependency list matches the code's actual hard requirements (no stale `sentence-transformers`).
