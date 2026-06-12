# Implementation Plan: Replace REST API with Official data.gouv.fr MCP Server

**Branch**: `014-datagouv-mcp-search` | **Date**: 2026-03-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/014-datagouv-mcp-search/spec.md`

## Summary

Replace the custom REST API wrapper (`DataGouvSearchService` + `DataGouvAPI`) with the official data.gouv.fr MCP server at `https://mcp.data.gouv.fr/mcp` for dataset search, data preview, and metrics. The existing `MCPClient` (Streamable HTTP transport) already exists in the codebase — the work is creating a `DataGouvMCPService` adapter, integrating it into the search flow, adding Tabular API preview, metrics display, and a REST API fallback when the MCP server is unreachable.

## Technical Context

**Language/Version**: Python 3.11 (existing `myenv311` virtual environment)
**Primary Dependencies**: Streamlit >=1.28.0, requests, pandas (all installed); `mcp_client.py` already implements Streamable HTTP
**Storage**: Session state for search results; local file cache `~/.cache/datagouv/` for downloaded CSVs
**Testing**: pytest (unit), Playwright (E2E via MCP)
**Target Platform**: Streamlit Cloud (Linux) + local macOS development
**Project Type**: Single project (Streamlit web app)
**Performance Goals**: Search results in <3 seconds for 95% of queries (SC-002)
**Constraints**: MCP server is public, free, no auth required; fallback to REST within 5 seconds (SC-004)
**Scale/Scope**: Single-user Streamlit app, ~10 search queries per session

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Justification |
|-----------|--------|---------------|
| **I. Abstraction Levels (L0-L4)** | PASS | Feature operates at L4 entry point (dataset search/discovery). Users enter at L4, select datasets, then enter descent. No change to level navigation. |
| **II. Descent-Ascent Cycle** | PASS | Search is pre-cycle (dataset selection). The loaded CSV feeds into the existing descent flow. No change to the cycle itself. |
| **III. Complexity Quantification** | PASS | N/A — search does not transform data between levels. |
| **IV. Human-Data Interaction Granularity** | PASS | Tabular API preview lets users see actual data rows before committing — improves ground-truth anchoring. |
| **V. Diverse Data Publics** | PASS | Natural language search + domain keywords shield users from technical query syntax. Metrics help non-technical users choose well-maintained datasets. UI uses domain terms, not technical data terms. |
| **Target User Assumption** | PASS | Non-technical domain experts type questions in French, see results as cards with domain metadata (org, description), never see MCP/REST/API internals. |
| **Quality Gate: Domain terminology** | PASS | UI preserves existing card design with title, description, organization — all domain-native. |

**Pre-Phase 0 Gate: PASS** — No violations. Proceed to research.

## Project Structure

### Documentation (this feature)

```text
specs/014-datagouv-mcp-search/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── mcp-service.md   # MCP service contract
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
intuitiveness/
├── data_sources/
│   ├── mcp_client.py          # EXISTING — generic MCP Streamable HTTP client
│   └── nl_query.py            # EXISTING — NL engine (Qwen2.5-72B)
├── services/
│   ├── datagouv_api.py        # EXISTING — REST API wrapper (becomes fallback)
│   ├── datagouv_client.py     # MODIFY  — orchestrator, add MCP-first strategy
│   └── datagouv_mcp.py        # NEW     — MCP service adapter
└── ui/
    └── datagouv_search.py     # MODIFY  — add preview button, metrics display

tests/
├── unit/
│   └── test_datagouv_mcp.py   # NEW — unit tests for MCP service
└── integration/
    └── test_mcp_live.py       # NEW — live integration test against public MCP
```

**Structure Decision**: Single project, extending existing `intuitiveness/` package. One new file (`datagouv_mcp.py`), two modified files (`datagouv_client.py`, `datagouv_search.py`).

## Complexity Tracking

> No violations to justify — Constitution Check passed cleanly.
