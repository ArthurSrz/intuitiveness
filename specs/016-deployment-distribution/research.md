# Research: Deployment & Distribution

Phase 0 for spec 016. Each item: **Decision / Rationale / Alternatives**.

## R1 — Does OpenRouter serve an OpenAI-compatible `/embeddings` endpoint, and host `baai/bge-m3`?

**Decision**: YES. Keep the existing default (`EMBEDDING_BASE_URL=https://openrouter.ai/api/v1`, `EMBEDDING_MODEL=baai/bge-m3`); call it with the OpenAI SDK exactly as `models.py` already does.

**Evidence**:
- OpenRouter documents `POST https://openrouter.ai/api/v1/embeddings`, OpenAI-schema compatible (works by swapping base_url + key in any OpenAI SDK). Non-streaming; batch multiple inputs per request.
- `baai/bge-m3` has a dedicated OpenRouter model page; model id is `baai/bge-m3`; it encodes into a **1024-dimensional** dense space.

**Impact**: This *reverses* the earlier roadmap risk ("OpenRouter may 404 on /embeddings"). The endpoint exists; no code change needed. `get_embeddings(["chiffre d'affaires","revenue"]).shape` should return `(2, 1024)` once the key is set.

**Alternatives (kept as documented fallbacks, secrets-only switch — no code change)**:
- OVHcloud, IONOS, Cloudflare Workers AI, DeepInfra all expose `baai/bge-m3` over an OpenAI-compatible `/v1/embeddings`.
- OpenAI `text-embedding-3-small` (`EMBEDDING_BASE_URL=https://api.openai.com/v1`) if a non-OpenRouter provider is preferred.

Sources:
- [OpenRouter Embeddings API](https://openrouter.ai/docs/api/reference/embeddings)
- [BAAI bge-m3 on OpenRouter](https://openrouter.ai/baai/bge-m3/api)
- [bge-m3 providers (OVHcloud)](https://www.ovhcloud.com/en/public-cloud/ai-endpoints/catalog/bge-m3/), [IONOS](https://docs.ionos.com/cloud/ai/ai-model-hub/models/embedding-models/bge-m3), [Cloudflare](https://developers.cloudflare.com/workers-ai/models/bge-m3/), [DeepInfra](https://deepinfra.com/BAAI/bge-m3-multi/api)

## R2 — `psycopg2-binary` on Streamlit Cloud and as a PyPI extra

**Decision**: Ship the Postgres driver as an **optional extra** `intuitiveness[postgres]` in `pyproject.toml`, and include `psycopg2-binary` in the app's `requirements.txt` (already added) so the Cloud deploy has it.

**Rationale**: `psycopg2-binary` ships prebuilt manylinux wheels — installs on Streamlit Cloud (Debian Linux) with no system `libpq`/build toolchain. A library consumer who uses the file session store should not be forced to install it, so it belongs in an extra, not core deps. The durable backend imports the driver lazily and the factory falls back to files when it's absent — so a bare install never breaks.

**Alternatives**: `psycopg` (v3) — the backend already tries v3 then v2; either works. `psycopg2-binary` chosen for the widest prebuilt-wheel coverage. SQLAlchemy — rejected as unnecessary weight for a single JSONB upsert/select.

## R3 — Railway deployment shape (Memgraph + Postgres)

**Decision**:
- **Memgraph**: deploy `memgraph/memgraph:latest` from a Docker image; enable a **TCP proxy** on port 7687; connect with `bolt+s://host:port`. (Already documented in `MEMGRAPH_DEPLOYMENT.md`; reuse verbatim.)
- **Postgres**: use Railway's **managed PostgreSQL plugin** (not a raw Docker image). Railway provisions it and exposes `DATABASE_URL` automatically; reference it from the app service. The durable backend reads `SESSION_DATABASE_URL` → `DATABASE_URL` → `POSTGRES_URL`.

**Rationale**: Memgraph has no managed Railway plugin → Docker image + TCP proxy. Postgres does → use the managed plugin (backups, `DATABASE_URL` injection, less ops). Both keep creds in secrets/env; both have a one-command verifier.

**Alternatives**: Postgres via raw Docker image (more ops, no managed backups) — rejected. Supabase/Neon for Postgres — viable, same `DATABASE_URL` contract, but Railway chosen for parity with Memgraph (one platform).

## R4 — PyPI dependency hygiene (the core distribution concern)

**Decision**: Restructure `pyproject.toml` so **core deps = what the library genuinely needs**, and hosted-infra/UI drivers move to extras:
- **Remove** `sentence-transformers` from dependencies (stale — code + `requirements.txt` already dropped it; it pulls `torch`, the single biggest install).
- **Move** `neo4j` → extra `[graph]`.
- **Add** `psycopg2-binary` → extra `[postgres]`.
- **Move** the Streamlit UI stack (`streamlit`, `streamlit-agraph`, …) → extra `[app]`.
- **Keep** in core: `pandas`, `networkx`, `numpy`, `scikit-learn` (used by `models.py` cosine similarity), `openai` (small, pure-Python; the embeddings client) — or push `openai` into `[embeddings]` if a fully-offline core is desired.
- Add `[all]` = graph + postgres + app.

**Rationale**: FR-003 — a bare install must be lean. Today `pyproject` forces `neo4j` + `sentence-transformers`(→torch) on every consumer and *omits* `psycopg2`, so it's both too heavy and inconsistent with the code. Extras make each capability opt-in and self-documenting.

**Open question (flag to user)**: whether `streamlit` stays core (the bundled app assumes it) or moves to `[app]`. Recommended: move to `[app]`, since the library/engine is usable headless and that's the whole point of the distribution contract. The Cloud `requirements.txt` installs `intuitiveness[all]` (or lists the drivers explicitly), so the app deploy is unaffected.

**Alternatives**: Keep everything in core (simplest, but violates FR-003) — rejected. Split into separate PyPI packages (`intuitiveness-core`, `-graph`, …) — overkill for current scale.

## R5 — Secrets model parity (Streamlit vs pip consumer vs CI)

**Decision**: Keep the single resolution rule already implemented everywhere: **`st.secrets` first, then environment**. No Streamlit dependency is required for env resolution — each resolver imports streamlit inside a `try/except`, so a headless pip consumer relies purely on env vars.

**Evidence (already in code)**: `neo4j_client.get_graph_db_credentials()`, `durable_backend._secret()`/`get_database_url()`, `models._secret()`/`_embedding_config()` all follow this precedence and tolerate a missing streamlit. The verifiers (`verify_graph_db`, `verify_session_db`) read the same resolvers, so they work in CI/headless too.

**Impact**: The "PyPI consumer vs Streamlit Cloud" difference is purely *where the values come from* (env vars vs Secrets UI), not *what the code does*. This is the crux the plan's config matrix documents.

## Resolved unknowns summary
| Unknown | Status |
|---|---|
| OpenRouter `/embeddings` + bge-m3 | RESOLVED — supported, `baai/bge-m3`, 1024-dim |
| psycopg2 on Streamlit Cloud | RESOLVED — manylinux wheel installs; ship as extra |
| Railway Postgres shape | RESOLVED — managed plugin, `DATABASE_URL` |
| PyPI lean-install contract | RESOLVED — extras + remove stale torch dep |
| Secrets parity across runtimes | RESOLVED — secrets→env, streamlit optional |
