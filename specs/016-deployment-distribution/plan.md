# Implementation Plan: Deployment & Distribution (Railway + OpenRouter + PyPI)

**Branch**: `015-adaptive-typed-levels` (rides PR #112) | **Date**: 2026-06-08 | **Spec**: [spec.md](./spec.md)
**Research**: [research.md](./research.md)

## Summary

Make spec-015's three external dependencies — **graph DB (Memgraph)**, **durable session store (PostgreSQL)**, **embeddings (OpenRouter `baai/bge-m3`)** — deployable on Railway/OpenRouter via **secrets only**, while keeping `intuitiveness` a **lean, opt-in PyPI package**. The package code is already config-driven with graceful fallbacks; the work here is (a) a Railway/OpenRouter runbook + verifiers, and (b) `pyproject.toml` dependency restructuring so a `pip` consumer installs only what they use and the distributable carries no secrets or hosted infra.

The decisive insight (research R5): the *only* difference between a PyPI consumer and the Streamlit Cloud deploy is **where config values come from** — env vars vs the Secrets UI — not the code. So "integration with PyPI distribution" reduces to two things: a clean **dependency/extras layout** and a clear **config contract**.

## Technical Context

**Language/Version**: Python 3.9+ (package); 3.11.9 (app/dev).
**External services**: Memgraph (Railway Docker image + TCP proxy, Bolt), PostgreSQL (Railway managed plugin, `DATABASE_URL`), OpenRouter embeddings (`baai/bge-m3`, 1024-dim, OpenAI-compatible).
**Existing building blocks (no code change needed to wire infra)**: `neo4j_client.get_graph_db_credentials()`, `persistence/durable_backend.get_durable_backend()` (Postgres+File factory), `models._embedding_config()`/`get_embeddings()`, `verify_graph_db.py`, `verify_session_db.py`, `.streamlit/secrets.toml.example`, `MEMGRAPH_DEPLOYMENT.md`.
**Distribution**: `pyproject.toml` (setuptools) → PyPI; `requirements.txt` → Streamlit Cloud + local app.
**Constraints**: no secret/endpoint in the sdist/wheel (FR-005); bare install must not pull torch/DB drivers (FR-003); same key names local vs Cloud (FR-007).

## Constitution Check

- **Graceful degradation / target users** (non-technical, "domain curious"): every capability is optional and falls back silently — a consumer never hits a hard infra requirement. PASS.
- **No hardcoded infra/secrets**: already true; this plan locks it in for the distributable. PASS.
- **Reproducibility (kernel theory §5.3)**: a reviewer needs only an API key + a connection string, not a multi-GB local model or a local DB. PASS.
- No new violations. Gate: PASS.

## The core deliverable — Config / Distribution matrix

How each capability is enabled, what it costs to install, and how it behaves unconfigured. This is the contract a PyPI consumer reads:

| Capability | Driver (where it lives) | Config keys (`st.secrets` → env) | Unconfigured fallback | PyPI consumer | Streamlit Cloud |
|---|---|---|---|---|---|
| **Embeddings** (semantic L3↔L2 matching) | `openai` (core, ~small) | `EMBEDDING_API_KEY` \|`OPENROUTER_API_KEY`\|`OPENAI_API_KEY`; `EMBEDDING_BASE_URL`; `EMBEDDING_MODEL` | keyword / positional matching | `pip install intuitiveness` + set env | Secrets UI (key + `baai/bge-m3`) |
| **Graph DB** (L4→L3 graph + Cypher agent) | `neo4j` (extra `[graph]`) | `MEMGRAPH_URI/USER/PASSWORD/DATABASE` (`NEO4J_*` aliases) | feature off (no-op) | `pip install intuitiveness[graph]` + env | Secrets + driver in `requirements.txt` |
| **Durable session store** | `psycopg2-binary` (extra `[postgres]`) | `SESSION_DATABASE_URL` \|`DATABASE_URL`\|`POSTGRES_URL` | local JSON files (`~/.intuitiveness/sessions/`) | `pip install intuitiveness[postgres]` + env | Secrets (`DATABASE_URL` auto from Railway) + driver in `requirements.txt` |
| **App UI** | streamlit stack (extra `[app]`) | — | n/a (engine usable headless) | `pip install intuitiveness[app]` | bundled (`requirements.txt`) |

Precedence everywhere: **`st.secrets` first, then environment** (streamlit import is optional, so env-only works headless).

## Work items

### WI-1 — Restructure `pyproject.toml` (the PyPI integration)
Current `pyproject.toml` forces `neo4j` + `sentence-transformers`(→torch) on all consumers and omits `psycopg2`. Target:

```toml
[project]
dependencies = [
    "pandas", "networkx", "numpy", "scipy", "scikit-learn",
    "openai>=1.0.0",            # small, pure-python embeddings client
]

[project.optional-dependencies]
app      = ["streamlit>=1.28.0", "streamlit-agraph>=0.0.45", "matplotlib", "requests"]
graph    = ["neo4j>=5.0.0"]
postgres = ["psycopg2-binary>=2.9.0"]
all      = ["intuitiveness[app,graph,postgres]"]
dev      = ["pytest", "behave"]
```

- **Remove** `sentence-transformers` (stale; code no longer imports it).
- **Move** `neo4j`→`[graph]`, streamlit stack→`[app]`; **add** `psycopg2-binary`→`[postgres]`.
- Bump `version` (0.1.0 → 0.2.0) — dependency surface changed.
- Verify the lazy imports tolerate absence: `neo4j_client` (neo4j), `durable_backend._import_psycopg()` (psycopg), and the app modules (streamlit). The durable factory + graph client already no-op/fall back; confirm with the bare-install test (SC-001/SC-002).

### WI-2 — Streamlit Cloud / app requirements
- `requirements.txt` (app deploy) keeps the drivers explicit so the Cloud app has the full feature set: `neo4j`, `psycopg2-binary` (added), streamlit stack, `openai`. Optionally switch to `-e .[all]` to derive from `pyproject` and avoid drift.
- Confirm `psycopg2-binary` wheel installs on Streamlit Cloud (research R2: yes).

### WI-3 — Railway deploy runbooks + verifiers
- **Memgraph**: reuse `MEMGRAPH_DEPLOYMENT.md` (Docker image + TCP proxy on 7687, `bolt+s://`). Verify: `python3 -m intuitiveness.verify_graph_db` → PASS.
- **Postgres**: add `POSTGRES_DEPLOYMENT.md` (mirror): Railway → add **PostgreSQL plugin** → it provisions `DATABASE_URL` → reference from the app service (or copy into secrets as `SESSION_DATABASE_URL`). Verify: `python3 -m intuitiveness.verify_session_db` → PASS.
- **OpenRouter**: get a key; set `EMBEDDING_API_KEY` (base_url/model already default to OpenRouter/`baai/bge-m3`). Verify: `python3 -c "from intuitiveness.models import get_embeddings; print(get_embeddings(['chiffre d affaires','revenue']).shape)"` → `(2, 1024)`.

### WI-4 — Secrets contract + parity
- Update `.streamlit/secrets.toml.example` (already includes Postgres + `baai/bge-m3`) to be the single source of truth for key names; cross-link from both runbooks.
- Set the same keys in Streamlit Cloud **Settings → Secrets** before merge (merging to `main` triggers the Cloud redeploy).
- Local non-Streamlit/CI use: document the equivalent env vars.

### WI-5 — Distribution hygiene checks (CI-friendly)
- Clean-venv test: `pip install dist/intuitiveness-*.whl` (no extras) → assert `pip freeze` excludes `torch`, `sentence-transformers`, `psycopg2*`, `neo4j` (SC-001); run a descent→ascent + file session save (SC-002).
- Build check: `python -m build` then `grep -r` the sdist/wheel for any connection string / key → none (SC-004).
- Remove the dead `intuitiveness/streamlit_app.py.old` + `.backup` (stale SentenceTransformer refs) before publishing.

## Verification (end-to-end)
1. `python3 -m intuitiveness.verify_graph_db` → PASS (Memgraph).
2. `python3 -m intuitiveness.verify_session_db` → PASS (Railway Postgres).
3. embeddings one-liner → `(2, 1024)` (OpenRouter `baai/bge-m3`).
4. Bare-install clean-venv test → lean (SC-001) + degraded-mode run (SC-002).
5. Built artifact contains no secrets (SC-004); `pyproject` deps match code (SC-005).
6. Live app walkthrough with all secrets set: graph via Memgraph, domain matching via BGE-M3 (categories populate), session save → Postgres row.

## Rollout sequence (minimizes a broken deploy)
1. Land WI-1 (pyproject extras) + WI-5 cruft removal on the branch.
2. Deploy Railway Memgraph + Postgres; get OpenRouter key; set **local** secrets; pass all verifiers (WI-3).
3. Set the **same secrets in Streamlit Cloud** (WI-4) — *before* any merge to `main`.
4. Merge PR #112 → Cloud redeploys with full infra.
5. (Optional, later) publish `0.2.0` to PyPI after the bare-install checks pass.

## Risks & mitigations
- **OpenRouter `/embeddings` regression**: low (research R1 confirms support); mitigation = secrets-only switch to OVH/IONOS/OpenAI, no code change.
- **Merging before Cloud secrets set** → deployed app degrades (no graph/embeddings/Postgres) but does not crash (FR-002). Mitigation = step 3 before step 4.
- **`streamlit` moved out of core** could surprise someone doing `pip install intuitiveness` then `streamlit run` → document `[app]` extra; Cloud uses `requirements.txt` so unaffected.
- **Leaked Neo4j password** `1&Coalplelat` in git history: never reuse; rotate; consider history scrub before public PyPI release.

## Open question for the user
- Keep `streamlit` in **core** deps (simpler for app-first users) or move to **`[app]`** (leaner library, recommended)? Plan assumes `[app]`.
