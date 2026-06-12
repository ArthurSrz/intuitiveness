# Quickstart: data.gouv.fr MCP Search Integration

**Feature**: 014-datagouv-mcp-search
**Date**: 2026-03-08

## What This Feature Does

Replaces the current keyword-by-keyword REST API search with the official data.gouv.fr MCP server, giving users:
- **Better search results** — the MCP server uses the platform's optimized search index
- **Data preview** — see actual rows before downloading (via Tabular API)
- **Usage metrics** — downloads/visits to help choose well-maintained datasets
- **Automatic fallback** — if MCP is down, transparently switches to the existing REST API

## Architecture Overview

```
User types query
       │
       ▼
NL Engine (Qwen2.5-72B) extracts keywords
       │
       ▼
DataGouvSearchService.search()
       │
       ├── TRY: DataGouvMCPService.search_datasets()  ← NEW
       │         │
       │         ▼
       │   MCPClient → https://mcp.data.gouv.fr/mcp
       │         │
       │         ▼
       │   Parse text response → DatasetInfo[]
       │
       └── FALLBACK: DataGouvAPI (existing REST)       ← UNCHANGED
                │
                ▼
          https://www.data.gouv.fr/api/1/datasets/
```

## Files to Create/Modify

| Action | File | What Changes |
|--------|------|-------------|
| **CREATE** | `intuitiveness/services/datagouv_mcp.py` | New MCP service adapter (~200 lines) |
| **MODIFY** | `intuitiveness/services/datagouv_client.py` | Add MCP-first search with REST fallback |
| **MODIFY** | `intuitiveness/ui/datagouv_search.py` | Add preview button, metrics chips, backend indicator |
| **CREATE** | `tests/unit/test_datagouv_mcp.py` | Unit tests with mocked MCP responses |
| **CREATE** | `tests/integration/test_mcp_live.py` | Live integration test against public MCP |

## Key Implementation Decisions

1. **No new dependencies** — reuse existing `MCPClient` + `requests`
2. **Synchronous** — Streamlit reruns are synchronous; no async needed
3. **Session-level fallback** — once MCP fails, stay on REST for the session
4. **Text parsing** — MCP returns text, not JSON; regex extracts structured data
5. **Lazy initialization** — MCP client created on first search, not at app startup

## How to Test

```bash
# Unit tests (mocked)
cd /Users/arthursarazin/Documents/data_redesign_method
myenv311/bin/python -m pytest tests/unit/test_datagouv_mcp.py -v

# Live integration test (requires internet)
myenv311/bin/python -m pytest tests/integration/test_mcp_live.py -v

# E2E test (Playwright)
# Search "résultats scolaires collèges" → expect ≥5 results (SC-001)
```

## Success Criteria Verification

| Criterion | How to Verify |
|-----------|--------------|
| SC-001: "résultats scolaires collèges" returns ≥5 results | Run search in app, count results |
| SC-002: Results in <3s for 95% of queries | Time the search in integration test |
| SC-003: Preview data rows | Click "Preview Data" on a CSV dataset |
| SC-004: Fallback within 5s | Mock MCP timeout, verify REST results appear |
| SC-005: Metrics on cards | Check download/visit counts on result cards |
| SC-006: Existing functionality preserved | Run full E2E test (search → cart → descent) |
