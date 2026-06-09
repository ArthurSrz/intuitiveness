# Railway Deployment Guide — spec 017 (Phase C)

Two new Railway services (`backend`, `frontend`) join the existing `intuitiveness`
project alongside `Postgres` and `memgraph`. The repo is a **monorepo**: each
service uses a **Root Directory** so Railway builds the right folder while still
seeing the whole repo (the backend installs the core via `-e ..[postgres,graph]`,
which needs the parent directory present — so `railway up` from inside `backend/`
will NOT work; use the GitHub-connected build below).

> Local readiness is already verified: the backend boots under uvicorn
> (`/healthz`→200, `POST /sessions`→201) and the frontend `npm run build` passes
> with no TypeScript errors.

## 0. Prerequisites
- Project `intuitiveness` exists with `Postgres` + `memgraph` (confirmed).
- The branch with `backend/` + `frontend/` is pushed to GitHub
  (`ArthurSrz/intuitiveness`). Railway deploys from a branch.

## 1. Backend service
1. Railway dashboard → project `intuitiveness` → **New** → **GitHub Repo** →
   `ArthurSrz/intuitiveness` → pick the deploy branch.
2. Service **Settings → Root Directory** = `backend`.
   (Railway still checks out the whole repo, so `requirements.txt`'s
   `-e ..[postgres,graph]` resolves against the repo root.)
3. `backend/railway.json` + `backend/nixpacks.toml` are picked up automatically:
   - build: Nixpacks (Python 3.11), `pip install -r requirements.txt`
   - start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - healthcheck: `/healthz`
4. **Variables** (Settings → Variables):
   - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}` ← Railway service reference
     (private network, no egress).
   - `ALLOWED_ORIGINS` = the frontend's public domain (fill in after step 2 below;
     e.g. `https://frontend-production-xxxx.up.railway.app`).
   - Optional: `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL`, `EMBEDDING_MODEL`
     (OpenRouter `baai/bge-m3`) for semantic L3↔L2 matching.
   - Optional: `MEMGRAPH_URI` = `bolt://${{memgraph.RAILWAY_PRIVATE_DOMAIN}}:7687`
     (+ `MEMGRAPH_USERNAME` / `MEMGRAPH_PASSWORD` if set).
5. **Networking → Generate Domain** to get the backend public URL.
6. Verify: open `https://<backend-domain>/healthz` → `postgres.ok: true`.

## 2. Frontend service
1. Same project → **New** → **GitHub Repo** → same repo/branch.
2. Service **Settings → Root Directory** = `frontend`.
3. `frontend/railway.json` is picked up:
   - build: `npm run gen:api && npm run build`
   - start: `npm run start` (Next.js reads `$PORT`).
4. **Variables**:
   - `NEXT_PUBLIC_API_URL` = the backend public domain from step 1.5
     (e.g. `https://backend-production-xxxx.up.railway.app`).
     This is baked at build time, so set it **before** the first build (redeploy
     if you set it later).
5. **Networking → Generate Domain** to get the frontend public URL.
6. Go back to the **backend**'s `ALLOWED_ORIGINS` (step 1.4) and set it to this
   frontend domain; redeploy the backend.

## 3. End-to-end check (SC-005)
- Open the frontend domain → pick "School Scores" → descend L4→L0 (datum **55.0**)
  → ascend L0→L3 → Export. The backend uses the **internal** `DATABASE_URL`.

## CLI alternative (per service, from the repo root)
The dashboard is recommended for the first setup (Root Directory + domain wiring).
Afterwards, redeploys are just `git push` (Railway auto-deploys the branch), or:
```bash
railway link            # select: intuitiveness / production / backend
railway up              # run from the REPO ROOT so the whole repo is the context
```
Set the same Root Directory on the service first, or the build context will be
wrong. Do NOT `railway up` from inside `backend/` — the core install needs `..`.

## Env var reference (also in backend/.env.example)
| Var | Service | Value | Required |
|---|---|---|---|
| `DATABASE_URL` | backend | `${{Postgres.DATABASE_URL}}` | for persistence (else file backend) |
| `ALLOWED_ORIGINS` | backend | frontend domain(s), comma-sep | yes (CORS) |
| `EMBEDDING_API_KEY` | backend | OpenRouter key | optional (semantic matching) |
| `MEMGRAPH_URI` | backend | `bolt://…railway.internal:7687` | optional (graph) |
| `NEXT_PUBLIC_API_URL` | frontend | backend public domain | yes |
