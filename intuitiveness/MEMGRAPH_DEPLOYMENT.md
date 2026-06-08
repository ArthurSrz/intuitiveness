# Memgraph on Railway — deployment runbook

Replaces the old local Neo4j (`neo4j://localhost:7687`) with a hosted, reproducible
graph database. The app code is already wired to read connection details from
secrets/env (`get_graph_db_credentials()` in `neo4j_client.py`) — you only need to
deploy Memgraph, then paste the connection values.

The graph feature (L4→L3 knowledge graph + the Cypher agent) is **optional**: if the
values below are unset, the app runs fine without it.

---

## 1. Deploy Memgraph on Railway

1. Railway project → **New → Deploy from Docker Image**.
2. Image: `memgraph/memgraph:latest` (lean; Bolt on port **7687**).
   - Want a browser query console too? Use `memgraph/memgraph-platform` (bundles Memgraph Lab on :3000) — heavier.
3. **Networking → enable TCP Proxy** on container port **7687**. Railway gives you a public `host:port` — note it.
4. **Auth** (Memgraph ships with auth OFF). Two paths:
   - *Quick first test:* leave auth off, do the smoke test below, then lock down.
   - *Secured (do before sharing):* set the start command to require auth, then in a Memgraph console run:
     ```cypher
     CREATE USER neo4j IDENTIFIED BY '<NEW_STRONG_PASSWORD>';
     ```
     (Set Railway start args per Memgraph docs to enforce auth, e.g. `--auth-module-executable` / requiring a user.)

## 2. Collect connection values

- **URI**: `bolt+s://<railway-host>:<proxy-port>` (use `bolt+s://` if Railway terminates TLS; otherwise `bolt://`).
- **user** / **password**: the ones from step 4 (or empty if auth left off).
- **database**: `memgraph`.

## 3. Wire the app

**Local** — put in repo-root `.streamlit/secrets.toml` (gitignored; see `secrets.toml.example`):
```toml
MEMGRAPH_URI = "bolt+s://<railway-host>:<proxy-port>"
MEMGRAPH_USER = "neo4j"
MEMGRAPH_PASSWORD = "<NEW_STRONG_PASSWORD>"
MEMGRAPH_DATABASE = "memgraph"
```

**Streamlit Cloud** — paste the same four keys in the app's **Settings → Secrets**.

(`NEO4J_*` names also work as aliases. Env vars work too, for non-Streamlit runs.)

## 4. Verify (one command)

With the secrets/env set:
```bash
python3 -m intuitiveness.verify_graph_db
```
It connects, runs `RETURN 1`, creates+counts+deletes a temp node, and prints PASS/FAIL.
Then exercise the graph feature in the running app (`python3 -m streamlit run intuitiveness/streamlit_app.py` from repo root).

## 5. Security — rotate the leaked password

The old hardcoded password `1&Coalplelat` is in this repo's **git history**. Treat it as
compromised: do **not** reuse it for Memgraph, and disable/rotate it on any Neo4j it ever
protected. (Optional, separate task: scrub git history.)

---

### How the code resolves credentials
`Neo4jClient()` (no args) → `get_graph_db_credentials()` reads, per key:
`st.secrets` first, then environment; `MEMGRAPH_*` first, then `NEO4J_*` aliases.
Nothing is hardcoded; an unset URI makes `connect()` a graceful no-op.
