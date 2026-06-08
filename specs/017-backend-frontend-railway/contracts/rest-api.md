# REST API Contract (sketch) — spec 017

FastAPI auto-generates the authoritative OpenAPI schema at `/openapi.json`; this
sketch defines the intended surface. Every mutating call follows the same
lifecycle (research R1): **load session from Postgres → engine transition → save**.

All request/response bodies are JSON. Level payloads use the spec-015
`session_export` encodings (dataframe/graph/vector/value/unlinkable) for fidelity,
plus a lightweight `summary` for display.

## Sessions

- `POST /sessions` → create a session.
  - body: `{ source: "demo:school_scores" | "demo:ademe" | "demo:energy" }` OR an uploaded L4 payload.
  - 201 → `{ session_id, current_level: 4, summary, available_moves }`
- `GET /sessions/{id}` → current state: `{ session_id, current_level, current_node_id, summary, available_moves }`
- `DELETE /sessions/{id}` → delete the durable record.
- `GET /sessions` → session index: `[{ session_id, title, updated_at }]` (from `list_sessions()`).

## Transitions (engine)

- `POST /sessions/{id}/descend` → `reduce_complexity(target = current-1)`.
  - body: typed per current edge (mirrors `params.py`), e.g.
    - L4→L3: `{ builder: "row_vector"|..., columns: [...] }`
    - L3→L2: `{ domains: ["high score","low score"], use_semantic: true, threshold: 0.7 }`  ← uses embeddings
    - L2→L1: `{ column: "value", filter_query?: "..." }`
    - L1→L0: `{ aggregation: "mean"|"sum"|"count" }`
  - 200 → `{ current_level, current_node_id, summary, available_moves }`
- `POST /sessions/{id}/ascend` → `increase_complexity(target = current+1)`.
  - body per edge: L0→L1 `{ enrichment_function? }`; L1→L2 `{ dimensions|categories, use_semantic, threshold }`; L2→L3 `{ item_type, relationship, source_column }`
- Errors: `409` for illegal transition (non-adjacent, ascent→L4, row-count violation) with the engine's message; `422` for bad params.

## Navigation tree (branching / time-travel)

- `GET /sessions/{id}/tree` → `{ root_id, current_id, nodes: { <id>: { level, parent_id, children_ids, action, decision_description, summary, archived } } }` (flat map = export schema shape; frontend builds the tree).
- `POST /sessions/{id}/time-travel` → `{ node_id }` → moves `current` to an existing node.
- `POST /sessions/{id}/branch-from` → `{ node_id, action: "descend"|"ascend", params: {...} }` → restore + new transition.
- `POST /sessions/{id}/prune` → `{ node_id }` → remove subtree (409 if on current branch / root).
- `POST /sessions/{id}/archive` → `{ node_id }` → soft-hide subtree.

## Level artifacts (for rendering)

- `GET /sessions/{id}/nodes/{node_id}` → full node: `{ level, payload_kind, payload, lineage, edge_decision, summary }`.
- `GET /sessions/{id}/nodes/{node_id}/table?format=records` → L2/L3 tabular view for the grid (paginated).
- Level-specific renderers consume `summary` (counts/shape/value) for headers and `payload` for the body.

## Export / import (spec-015 contract)

- `GET /sessions/{id}/export` → the full-fidelity versioned record (`session_export.export_session`); `Content-Disposition` attachment.
- `POST /sessions/import` → body: a record → `import_session` → new `session_id`. `409` on unknown major `schema_version`.

## Graph feature (Memgraph) — optional

- `POST /sessions/{id}/graph/sync` → push the current L3 graph to Memgraph (uses `neo4j_client`).
- `POST /sessions/{id}/graph/query` → `{ cypher }` → results (read). Gated; off if Memgraph unconfigured.

## Health / meta

- `GET /healthz` → `{ status, deps: { postgres, memgraph, embeddings } }` (mirrors the three verify scripts; powers a status badge).
- `GET /openapi.json`, `GET /docs` → schema + Swagger UI (frontend codegen source).

## Cross-cutting
- CORS: allow `ALLOWED_ORIGINS` (frontend domain).
- Errors: RFC-7807-ish `{ detail, code }`; map `TransitionError`/`NavigationError` → 409/422.
- Idempotency: transitions are not idempotent (they branch); the frontend disables a control while a call is in flight.
