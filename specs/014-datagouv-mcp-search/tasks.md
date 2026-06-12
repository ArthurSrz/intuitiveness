# Tasks: Replace REST API with Official data.gouv.fr MCP Server

**Input**: Design documents from `/specs/014-datagouv-mcp-search/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/mcp-service.md, quickstart.md

**Tests**: Not explicitly requested in spec. Test tasks omitted. Live integration tests included in Polish phase for SC verification.

**Organization**: Tasks grouped by user story (P1→P2→P3) for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No new dependencies or project restructuring needed. Existing `MCPClient` and project structure are sufficient.

- [x] T001 Verify `MCPClient` connectivity by running a test initialize + `tools/list` call against `https://mcp.data.gouv.fr/mcp` in `intuitiveness/data_sources/mcp_client.py`

**Checkpoint**: MCP server reachable, tools list returned (9 tools expected)

---

## Phase 2: Foundational (MCP Service Adapter)

**Purpose**: Create the `DataGouvMCPService` adapter that wraps `MCPClient` with typed responses. ALL user stories depend on this.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 Create `MCPDatasetResult`, `MCPResourceInfo`, `MCPDataPreview`, `MCPMetrics` dataclasses in `intuitiveness/services/datagouv_mcp.py` per data-model.md entities
- [x] T003 Implement `_parse_search_response()` in `intuitiveness/services/datagouv_mcp.py` — regex parser that extracts `MCPDatasetResult[]` from MCP `search_datasets` text output using patterns from contracts/mcp-service.md
- [x] T004 Implement `_parse_resources_response()` in `intuitiveness/services/datagouv_mcp.py` — parser for `list_dataset_resources` text output → `MCPResourceInfo[]`
- [x] T005 Implement `_parse_preview_response()` in `intuitiveness/services/datagouv_mcp.py` — parser for `query_resource_data` text output → `MCPDataPreview`
- [x] T006 Implement `_parse_metrics_response()` in `intuitiveness/services/datagouv_mcp.py` — parser for `get_metrics` text output → `MCPMetrics`
- [x] T007 Implement `DataGouvMCPService.__init__()` and `is_available()` in `intuitiveness/services/datagouv_mcp.py` — lazy MCPClient initialization with 5s timeout, availability check with session-level caching
- [x] T008 Implement `DataGouvMCPService.search_datasets()` in `intuitiveness/services/datagouv_mcp.py` — calls MCPClient.call_tool("search_datasets"), parses response, returns `SearchResult` compatible with existing UI
- [x] T009 Create `MCPServiceError` exception class in `intuitiveness/services/datagouv_mcp.py` with `fallback_hint` attribute per error contract
- [x] T010 Implement mapping function `_mcp_result_to_dataset_info()` in `intuitiveness/services/datagouv_mcp.py` — converts `MCPDatasetResult` to existing `DatasetInfo` for UI compatibility

**Checkpoint**: `DataGouvMCPService.search_datasets("vaccination")` returns a `SearchResult` with `DatasetInfo[]` objects parseable by existing UI code.

---

## Phase 3: User Story 1 — Better Search Results via MCP (Priority: P1) 🎯 MVP

**Goal**: Route all dataset searches through the MCP server instead of the REST API, with transparent fallback.

**Independent Test**: Search "résultats scolaires collèges" → expect ≥5 relevant education datasets (SC-001). Currently returns 0 results.

### Implementation for User Story 1

- [x] T011 [US1] Add `_get_mcp_service()` lazy initializer to `DataGouvSearchService` in `intuitiveness/services/datagouv_client.py` — creates and caches a `DataGouvMCPService` instance
- [x] T012 [US1] Refactor `DataGouvSearchService.search()` in `intuitiveness/services/datagouv_client.py` — extract current REST search logic into `_search_rest()` private method (no behavior change)
- [x] T013 [US1] Implement MCP-first search strategy in `DataGouvSearchService.search()` in `intuitiveness/services/datagouv_client.py` — try MCP first, catch `MCPServiceError`, set `st.session_state["datagouv_mcp_fallback"] = True`, fall through to `_search_rest()` per integration contract
- [x] T014 [US1] Store search backend indicator in `st.session_state["datagouv_search_backend"]` ("mcp" or "rest") in `intuitiveness/services/datagouv_client.py` for UI display
- [x] T015 [US1] Add subtle backend indicator text ("via MCP" / "via data.gouv.fr API") below search results count in `intuitiveness/ui/datagouv_search.py`
- [x] T016 [US1] Handle MCP error edge cases in `intuitiveness/services/datagouv_client.py` — empty results from MCP trigger broader search retry with fewer keywords (spec edge case: "try broader search with fewer keywords before showing no results")

**Checkpoint**: Search "résultats scolaires collèges" returns ≥5 results via MCP. If MCP is unreachable, results still appear via REST fallback within 5 seconds (SC-004).

---

## Phase 4: User Story 2 — Direct Data Preview via Tabular API (Priority: P2)

**Goal**: Users can preview actual data rows for any dataset that supports the Tabular API, without downloading the full CSV.

**Independent Test**: Select a dataset → expand card → click "Preview Data" → see first 20 rows in a table.

### Implementation for User Story 2

- [x] T017 [US2] Implement `DataGouvMCPService.get_dataset_resources()` in `intuitiveness/services/datagouv_mcp.py` — calls `list_dataset_resources` MCP tool, parses response, returns `List[ResourceInfo]`
- [x] T018 [US2] Implement `DataGouvMCPService.preview_resource()` in `intuitiveness/services/datagouv_mcp.py` — calls `query_resource_data` MCP tool with `page_size=20`, parses tabular response, returns `MCPDataPreview`
- [x] T019 [US2] Add "Preview Data" button inside dataset card expander in `intuitiveness/ui/datagouv_search.py` — visible only when search backend is "mcp" and dataset has CSV resources
- [x] T020 [US2] Render preview data as `st.dataframe()` inside card expander in `intuitiveness/ui/datagouv_search.py` — converts `MCPDataPreview.rows` + `MCPDataPreview.columns` to `pd.DataFrame`
- [x] T021 [US2] Handle Tabular API unavailability in `intuitiveness/ui/datagouv_search.py` — when resource doesn't support Tabular API, show message "Preview not available for this resource" and offer direct CSV download instead (spec edge case)
- [x] T022 [US2] Add resource listing to dataset card expansion in `intuitiveness/ui/datagouv_search.py` — when user expands a card, call `get_dataset_resources()` to show available files with format indicators

**Checkpoint**: Expanding a dataset card shows its resources. Clicking "Preview Data" on a CSV resource shows first 20 rows inline. Non-tabular resources show download fallback.

---

## Phase 5: User Story 3 — Dataset Usage Metrics (Priority: P3)

**Goal**: Display download count and visit metrics on each dataset card to help users choose well-maintained datasets.

**Independent Test**: View search results → each card shows monthly download and visit counts.

### Implementation for User Story 3

- [x] T023 [US3] Implement `DataGouvMCPService.get_metrics()` in `intuitiveness/services/datagouv_mcp.py` — calls `get_metrics` MCP tool with `dataset_id`, parses response, returns `MCPMetrics` with latest month's downloads and visits
- [x] T024 [US3] Add metrics display on dataset cards in `intuitiveness/ui/datagouv_search.py` — show download count (📥) and visit count (👁) as small chips/badges on each card, only when search backend is "mcp"
- [x] T025 [US3] Handle metrics fetch errors gracefully in `intuitiveness/ui/datagouv_search.py` — if `get_metrics` fails for a dataset, hide metrics chips silently (don't break the card)
- [x] T026 [US3] Batch metrics fetching in `intuitiveness/ui/datagouv_search.py` — fetch metrics for all displayed datasets after search results render, cache in session state to avoid re-fetching on rerun

**Checkpoint**: Dataset cards show download/visit counts. Cards without metrics data render normally without chips.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, edge cases, and validation across all stories.

- [x] T027 Add graceful MCP connection error messages in `intuitiveness/ui/datagouv_search.py` — user-friendly toast/info when MCP is down, suggest simpler keywords on MCP query errors (FR-010)
- [x] T028 Verify NL engine integration with MCP search in `intuitiveness/services/datagouv_client.py` — ensure `parse_query()` keywords feed correctly into `mcp_service.search_datasets()` (FR-003)
- [x] T029 Create live integration test `tests/integration/test_mcp_live.py` — test `search_datasets("vaccination")` returns results, `is_available()` returns True, response parsing produces valid `DatasetInfo` objects
- [x] T030 Verify SC-001: search "résultats scolaires collèges" returns ≥5 results in `tests/integration/test_mcp_live.py`
- [x] T031 Verify SC-002: search results appear within 3 seconds in `tests/integration/test_mcp_live.py`
- [x] T032 Verify SC-006: existing search → cart → descent workflow still works end-to-end (manual or Playwright)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — verify connectivity first
- **Foundational (Phase 2)**: Depends on Phase 1 — creates the MCP adapter all stories use
- **US1 (Phase 3)**: Depends on Phase 2 — integrates MCP adapter into search flow
- **US2 (Phase 4)**: Depends on Phase 2 — uses MCP adapter for preview (independent of US1 search integration, but practically benefits from it)
- **US3 (Phase 5)**: Depends on Phase 2 — uses MCP adapter for metrics (independent of US1/US2)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Depends only on Foundational (Phase 2). No dependencies on other stories.
- **US2 (P2)**: Depends only on Foundational (Phase 2). Can start in parallel with US1. However, the "Preview Data" button is only shown when MCP backend is active (US1), so full UX requires US1.
- **US3 (P3)**: Depends only on Foundational (Phase 2). Can start in parallel with US1/US2. Metrics chips only show when MCP backend is active (US1), so full UX requires US1.

### Within Each User Story

- Models/dataclasses before services
- Services before UI modifications
- Core implementation before edge case handling

### Parallel Opportunities

**Phase 2 (Foundational)**:
- T002 (dataclasses) must complete first
- T003, T004, T005, T006 (parsers) can all run in parallel after T002
- T007, T008, T009, T010 (service methods) can run in parallel after parsers

**Phase 3-5 (User Stories)**:
- US2 and US3 implementation tasks can run in parallel with US1
- Within US2: T017 and T018 (service methods) can run in parallel
- Within US3: T023 is prerequisite; T024, T025, T026 can run in parallel after it

---

## Parallel Example: Phase 2 (Foundational)

```bash
# After T002 (dataclasses) completes, launch all parsers together:
Task T003: "_parse_search_response() in datagouv_mcp.py"
Task T004: "_parse_resources_response() in datagouv_mcp.py"
Task T005: "_parse_preview_response() in datagouv_mcp.py"
Task T006: "_parse_metrics_response() in datagouv_mcp.py"
```

## Parallel Example: User Stories (after Phase 2)

```bash
# US1, US2, US3 service methods can be implemented in parallel:
Task T008: "DataGouvMCPService.search_datasets() [US1 foundation]"
Task T017: "DataGouvMCPService.get_dataset_resources() [US2]"
Task T018: "DataGouvMCPService.preview_resource() [US2]"
Task T023: "DataGouvMCPService.get_metrics() [US3]"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001) — verify MCP connectivity
2. Complete Phase 2: Foundational (T002-T010) — build MCP adapter
3. Complete Phase 3: User Story 1 (T011-T016) — MCP search with fallback
4. **STOP and VALIDATE**: Search "résultats scolaires collèges" → ≥5 results (SC-001)
5. Deploy/demo if ready — already a massive improvement over current 0 results

### Incremental Delivery

1. **MVP**: Phase 1 + 2 + 3 → MCP search with fallback (core value)
2. **+Preview**: Phase 4 → Users can preview data before downloading
3. **+Metrics**: Phase 5 → Users see popularity signals on cards
4. **+Polish**: Phase 6 → Error messages, integration tests, SC verification

### Suggested MVP Scope

**Phase 1 + Phase 2 + Phase 3 (T001-T016)**: 16 tasks delivering the core search improvement. This alone resolves the primary user complaint ("results are poor") and satisfies SC-001, SC-002, SC-004, SC-006.

---

## Notes

- All code changes are in the `intuitiveness/` directory (existing package)
- Only **one new file** created: `intuitiveness/services/datagouv_mcp.py`
- Two existing files modified: `datagouv_client.py` (orchestrator) and `datagouv_search.py` (UI)
- No new dependencies — reuses existing `MCPClient` + `requests`
- MCP response format is **text** (not JSON) — parsers use regex
- Session-level fallback: once MCP fails, stays on REST for the session
- Commit after each task or logical group
