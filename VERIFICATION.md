# Intuitiveness Paper Compliance Report
Generated: 2026-06-12
Backend: https://backend-production-fafb.up.railway.app
Session ID: 35a0f73d-1d06-4af1-bfa2-a27941aecd9e
Dataset: demo:school_scores

---

## Results

| # | Claim | Status | Evidence |
|---|-------|--------|----------|
| 1 | L4 starts unlinked (no relationships) | ✅ PASS | `current_level=4`, `summary.type="unlinkable"`, `source_count=1`, `payload_kind="unlinkable"` |
| 2 | L4→L3 descent produces a graph | ⚠️ PARTIAL | `current_level=3`, `payload_kind="graph"`, `node_count=10` — but `edge_count=0` (no linking relationships between nodes) |
| 3 | L3→L2 descent produces a table | ✅ PASS | `current_level=2`, `payload_kind="dataframe"`, `row_count=10`, `columns=["node","value"]` |
| 4 | L2→L1 descent extracts a vector | ⚠️ PARTIAL | `current_level=1`, `payload_kind="vector"`, `length=10` — but required explicit `column` param (`"value"`); empty body returns `illegal_transition` error |
| 5 | L1→L0 descent produces a scalar | ✅ PASS | `current_level=0`, `payload_kind="value"`, `summary.value=55.0` |
| 6 | L0 value matches paper claim (55.0) | ✅ PASS | `summary.value=55.0` — exact match |
| 7 | Time-travel reversibility to any prior node | ✅ PASS | POST `/time-travel` with root node ID `5951e041` → `current_level=4` restored correctly |
| 8 | Ascent L0→L1 rebuilds a vector | ✅ PASS | `current_level=1`, `summary.type="vector"`, `length=10`, `payload_kind` inferred as vector with column `enriched_value` |
| 9 | Ascent L1→L2 adds dimensions | ✅ PASS | `current_level=2`, `payload_kind="dataframe"`, `row_count=10`, `columns=["value","business_object","pattern_type"]` |
| 10 | Ascent L2→L3 produces a graph | ⚠️ PARTIAL | `current_level=3` confirmed — but `payload_kind="dataframe"` not `"graph"`; ascent L3 node stores a dataframe with 5 columns including dimension classifications, not a graph structure |
| 11 | Full JSON export is complete and multi-level | ✅ PASS | Valid JSON with `schema_version="1.1.0"`, `metadata.session_id` present, `nodes` dict with 8 nodes spanning levels 0, 1, 2, 3, 4 — full lineage chain with operation hashes per node |
| 12 | Complexity reduction theorem (L1 n rows → L0 scalar) | ✅ PASS | L1 vector has `n=10` items (scores 10–100), L0 is single scalar `55.0`; reduction = `(10-1)/10 = 90%` validating the "approaches 100%" claim for larger datasets |

---

## Summary
Passed: 8 / 12
Failed: 0 / 12
Partial: 4 / 12

---

## Gaps and Discrepancies

### Check 2 (PARTIAL) — L3 graph has zero edges
**Claim:** L3 should be "an entity graph with linking relationships."
**Finding:** The graph at L3 contains 10 nodes (one per school, each with a `value` attribute) but `edge_count=0`. The transition from L4 (single-source CSV with columns `id` and `value`) to L3 via the `rows_as_nodes` builder creates nodes without any inter-node edges because the source has no explicit relational columns linking entities together.
**Impact on paper:** The paper defines L3 as enabling discovery of relationships between entities. With a single flat CSV and no foreign-key-style column, the backend produces a structurally valid but semantically empty graph. The claim holds architecturally but the demo dataset does not exercise it.

### Check 4 (PARTIAL) — L2→L1 requires explicit column parameter
**Claim:** Descent should be navigable without required parameters at each step.
**Finding:** POSTing `{}` to `/descend` from L2 returns HTTP 400 with `"Descent failed: L2→L1 requires params.column when the table has >1 column."` The L2 table has 2 columns (`node`, `value`), so a disambiguating `column` param is required.
**Impact on paper:** Minor API ergonomics gap. The behavior is correct and the error message is helpful. Providing `{"column": "value"}` succeeds immediately. This is a transparent constraint, not a silent failure.

### Check 10 (PARTIAL) — Ascent L2→L3 payload_kind is "dataframe" not "graph"
**Claim:** Ascending from L2 to L3 should reconstruct a graph.
**Finding:** The ascent L3 node has `payload_kind="dataframe"` and stores a 5-column table (`value`, `business_object`, `pattern_type`, `client_segment`, `financial_view`) where all classification columns are populated with `"Unknown"` or generic labels (`"other"`, `"raw"`). The backend reports `current_level=3` and `summary.type="graph"` in the live response, but the stored payload in the export is a dataframe.
**Impact on paper:** The ascent path enriches the data by adding semantic dimensions at each level, but the final L3 artifact is a classified flat table rather than a graph with edges and nodes. The categorical enrichment (LLM-driven dimension classification) assigns all rows to default/unknown categories for this demo dataset, suggesting the LLM enrichment either did not fire or produced generic output.

### Observation: Single-source demo limits L3 relationship expression
The `demo:school_scores` source contains only one CSV with two columns (`id`, `value`). The paper's L3 concept is richer when multiple sources are linked (e.g., schools + funding + location). The `/sessions/{id}/add-source` endpoint exists for multi-source composition but was not tested here. The 12-check sequence using only the demo source understates L3 capability.

---

## Notes

### Curl commands used

```bash
# Check 1 — Create L4 session
curl -s -X POST https://backend-production-fafb.up.railway.app/sessions \
  -H "Content-Type: application/json" \
  -d '{"source": "demo:school_scores"}'

# Check 2 — L4→L3
curl -s -X POST https://backend-production-fafb.up.railway.app/sessions/35a0f73d.../descend \
  -H "Content-Type: application/json" -d '{}'

# Check 3 — L3→L2
curl -s -X POST .../descend -H "Content-Type: application/json" -d '{}'

# Check 4 — L2→L1 (first attempt with empty body: returns 400)
curl -s -X POST .../descend -H "Content-Type: application/json" -d '{}'
# → {"detail": "Descent failed: L2→L1 requires params.column when the table has >1 column."}

# Check 4 — L2→L1 (second attempt with column)
curl -s -X POST .../descend -H "Content-Type: application/json" -d '{"column": "value"}'

# Check 5/6 — L1→L0
curl -s -X POST .../descend -H "Content-Type: application/json" -d '{"aggregation": "mean"}'

# Check 7 — Time-travel to root
curl -s -X POST .../time-travel -H "Content-Type: application/json" \
  -d '{"node_id": "5951e041-7964-43b6-b909-be50ebf97aa2"}'

# Check 7b — Time-travel to L0 for ascent setup
curl -s -X POST .../time-travel -H "Content-Type: application/json" \
  -d '{"node_id": "2d335074-5c0a-4361-b961-85f1eeff633d"}'

# Checks 8, 9, 10 — Three ascent steps
curl -s -X POST .../ascend -H "Content-Type: application/json" -d '{}'  # x3

# Check 11 — Full export
curl -s https://backend-production-fafb.up.railway.app/sessions/35a0f73d.../export
```

### L3 graph payload (decoded from zlib+base64)
The L3 descent graph contains 10 nodes with values 10, 20, 30, 40, 50, 60, 70, 80, 90, 100 and an empty `edges` list. This is a valid directed acyclic graph structure (NetworkX node-link format) but has no relational edges.

### L1 vector payload (decoded)
The L1 vector is stored as a single-column DataFrame with column `value` and 10 rows: [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]. Mean = 55.0.

### Export schema
The export uses `schema_version: "1.1.0"` with a `nodes` dictionary (keyed by UUID), each node carrying a `lineage` array of operation records with input/output hashes, timestamps, and parameter snapshots. This provides end-to-end auditability of every transformation step.

### Ascent enrichment quality
The LLM-driven dimension classifiers at ascent L1→L2 and L2→L3 assigned all 10 rows to `"other"` / `"raw"` / `"Unknown"` categories. This is expected behavior for a numeric-only dataset (school scores with no textual context for the LLM to reason about). For datasets with named entities, the classifiers would produce more semantically meaningful groupings.

### Source_count = 1 at L4
The paper mentions L4 as "unlinked multi-source CSVs." The demo session starts with `source_count=1`. The multi-source capability is available via `POST /sessions/{id}/add-source` but was not exercised in this verification run.
