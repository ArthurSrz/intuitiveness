# Phase 0 Research: data.gouv.fr MCP Server Integration

**Feature**: 014-datagouv-mcp-search
**Date**: 2026-03-08

## Research Questions & Findings

### RQ-1: MCP Server Capabilities & Tools

**Decision**: Use the 9 tools exposed by the public MCP server at `https://mcp.data.gouv.fr/mcp`

**Findings** (verified via live SSE testing against the server):

| Tool | Parameters | Purpose |
|------|-----------|---------|
| `search_datasets` | `query` (req), `page`, `page_size` (max 100) | Keyword search — returns text-formatted results |
| `get_dataset_info` | `dataset_id` (req) | Full metadata for one dataset |
| `list_dataset_resources` | `dataset_id` (req) | List files (CSV, XLSX, etc.) in a dataset |
| `get_resource_info` | `resource_id` (req) | Detailed file info + Tabular API availability |
| `query_resource_data` | `resource_id` (req), `question` (req), `page`, `page_size`, `filter_*`, `sort_*` | Preview tabular data without downloading |
| `get_metrics` | `dataset_id` or `resource_id`, `limit` | Monthly visits/downloads (production only) |
| `search_dataservices` | `query`, `page`, `page_size` | Search APIs (out of scope) |
| `get_dataservice_info` | `dataservice_id` | API metadata (out of scope) |
| `get_dataservice_openapi_spec` | `dataservice_id` | OpenAPI spec (out of scope) |

**Rationale**: The MCP server wraps the same data.gouv.fr backend but adds Tabular API access and metrics — two capabilities the raw REST API lacks.

**Alternatives considered**:
- Official Python MCP SDK (`mcp` package): Would require async (`anyio`, `httpx`). Rejected because the existing `MCPClient` in `mcp_client.py` already handles Streamable HTTP synchronously with `requests`, which is simpler for Streamlit.
- Self-hosting datagouv-mcp: Unnecessary complexity — the public instance is free and stable.

### RQ-2: Response Format & Parsing

**Decision**: Parse text-formatted responses from MCP tools to extract structured metadata.

**Findings**: The MCP `search_datasets` tool returns **text**, not JSON:

```
Found 31 dataset(s) for query: 'vaccination'
Page 1 of results:

1. Données vaccination par lieu de vaccination
   ID: 60bdce48a2532086182ee2c1
   Organization: Caisse nationale de l'Assurance Maladie
   Tags: covid-19, vaccination
   Resources: 2
   URL: https://www.data.gouv.fr/datasets/donnees-vaccination-par-lieu-de-vaccination
```

**Rationale**: A regex parser can reliably extract ID, title, organization, tags, resource count, and URL from this fixed format. This is simpler than switching to the raw REST API for structured JSON.

**Alternatives considered**:
- Use raw REST API for structured results, MCP only for preview/metrics: Adds complexity with two protocols. Rejected.
- Request the MCP server maintainers to add JSON output: Out of our control. Rejected.

### RQ-3: Transport Protocol & Existing Code

**Decision**: Reuse the existing `MCPClient` class in `intuitiveness/data_sources/mcp_client.py`.

**Findings**: The existing client already implements:
- JSON-RPC 2.0 over HTTP POST
- `Accept: application/json, text/event-stream` (critical — server requires both)
- SSE response parsing
- Session management (`Mcp-Session-Id` header)
- Context manager support
- Protocol version `2025-06-18`

**Rationale**: No new dependencies needed. The client is tested and matches the server's protocol.

**Alternatives considered**:
- Official `mcp` Python SDK: Requires async (`anyio`, `httpx-sse`). Streamlit's execution model is synchronous per-rerun — async would add complexity with `asyncio.run()` wrappers. Rejected.
- `httpx` with SSE: Would replace `requests` but add a dependency for no benefit given the existing working code. Rejected.

### RQ-4: Fallback Strategy

**Decision**: MCP-first with transparent fallback to existing REST API.

**Findings**: The fallback must be:
1. **Automatic**: Detect MCP unavailability within 5 seconds (SC-004)
2. **Transparent**: User sees a subtle indicator, not an error
3. **Stateful**: Once fallback is triggered, remember it for the session (avoid retrying every query)

**Design**:
```
search(query) →
  IF mcp_available AND NOT session_fallback:
    TRY mcp.search_datasets(query)
      → parse text response
      → return DatasetInfo[]
    ON TIMEOUT/ERROR:
      SET session_fallback = True
      → fall through to REST
  ELSE:
    → existing REST API path (unchanged)
```

**Rationale**: Session-level fallback avoids repeated 5-second timeouts if the server is down for the whole session. Users can force-retry by refreshing.

**Alternatives considered**:
- Per-query fallback (retry MCP every time): Adds 5s latency per query when server is down. Rejected.
- Circuit breaker pattern: Overkill for a single-user Streamlit app. Rejected.

### RQ-5: Tabular API Preview Integration

**Decision**: Add a "Preview Data" button on dataset cards that calls `query_resource_data`.

**Findings**:
- The MCP `query_resource_data` tool requires `resource_id` (not `dataset_id`)
- Workflow: `search_datasets` → user clicks dataset → `list_dataset_resources` → find first CSV resource → `query_resource_data`
- Supports pagination, filtering, sorting
- Size limits: CSV ≤ 100 MB, XLSX ≤ 12.5 MB
- Not all resources support Tabular API — check via `get_resource_info`

**Rationale**: Preview before download is a key differentiator from the REST API approach and directly serves non-technical users who want to see what's in a dataset before committing.

### RQ-6: Metrics Display

**Decision**: Call `get_metrics` for each displayed dataset and show monthly visits/downloads on cards.

**Findings**:
- `get_metrics` only works in production environment
- Returns monthly statistics sorted by most recent
- Can be called per-dataset or per-resource
- Response is text-formatted (needs parsing)

**Rationale**: Metrics help non-technical users choose well-maintained datasets (SC-005).

## Resolved Unknowns

| Unknown | Resolution |
|---------|-----------|
| Python MCP SDK needed? | No — existing `MCPClient` is sufficient |
| Async required? | No — synchronous `requests` works |
| Response format? | Text, needs regex parsing |
| New dependencies? | None — all existing |
| Fallback mechanism? | Session-level flag with 5s timeout |
| Tabular API access? | Via `query_resource_data` MCP tool |
