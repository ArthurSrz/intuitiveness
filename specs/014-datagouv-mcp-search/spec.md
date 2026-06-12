# Feature Specification: Replace REST API with Official data.gouv.fr MCP Server

**Feature Branch**: `014-datagouv-mcp-search`
**Created**: 2026-03-08
**Status**: Draft
**Input**: User description: "The search results from the current data.gouv.fr integration are poor. Replace the custom REST API wrapper with the official data.gouv.fr MCP server (https://github.com/datagouv/datagouv-mcp) for significantly better search relevance, richer metadata, and access to the Tabular API for direct data querying."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Better Search Results via MCP (Priority: P1)

A user types a natural language query or keywords on the welcome page. The system routes the query through the official data.gouv.fr MCP server instead of the custom REST wrapper, returning more relevant datasets with richer metadata.

**Why this priority**: This is the core problem — current search results are poor because the custom REST wrapper uses naive keyword-by-keyword search against the raw API. The official MCP server has built-in search optimization tuned by the data.gouv.fr team.

**Independent Test**: Can be fully tested by typing "résultats scolaires collèges" in the search bar and verifying that relevant education datasets appear (instead of 0 results as currently happens with the phrase search).

**Acceptance Scenarios**:

1. **Given** I am on the welcome page, **When** I search for "résultats scolaires des collèges", **Then** I see relevant education datasets from data.gouv.fr (non-zero results).

2. **Given** I search with a natural language French question, **When** the NL engine extracts keywords, **Then** the MCP `search_datasets` tool is called with those keywords and returns results ranked by relevance.

3. **Given** the MCP server returns dataset results, **When** I view the result cards, **Then** each card shows title, description, organization, last modified, and CSV availability.

---

### User Story 2 - Direct Data Preview via Tabular API (Priority: P2)

After finding a dataset, the user can preview its actual data through the MCP's `query_resource_data` tool, which queries the Tabular API. This lets users see real rows before committing to load the full dataset.

**Why this priority**: The Tabular API is a unique capability of the MCP server that the REST wrapper cannot offer. It enables data preview and filtering before download, reducing wasted time on irrelevant datasets.

**Independent Test**: Can be tested by selecting a dataset, clicking a preview action, and seeing the first rows of data rendered in a table.

**Acceptance Scenarios**:

1. **Given** I see a dataset card in search results, **When** I expand it, **Then** I have the option to preview the data.

2. **Given** I click preview, **When** the MCP queries the Tabular API, **Then** I see the first rows displayed as a table.

3. **Given** I see the preview, **When** I decide this dataset is relevant, **Then** I can load the full dataset into the redesign workflow with one click.

---

### User Story 3 - Dataset Usage Metrics (Priority: P3)

Users can see popularity metrics (downloads, visits) for each dataset, helping them choose well-maintained and widely-used datasets.

**Why this priority**: Helps users make informed decisions by seeing which datasets are actively maintained and trusted by the community.

**Independent Test**: Can be tested by checking that dataset cards show download/visit counts from the MCP `get_metrics` tool.

**Acceptance Scenarios**:

1. **Given** search results are displayed, **When** I view a dataset card, **Then** I see download count and visit metrics.

2. **Given** two similar datasets appear, **When** I compare their metrics, **Then** I can choose the more actively maintained one.

---

### Edge Cases

- What happens when the MCP server at `mcp.data.gouv.fr` is unreachable? Fall back to the existing REST API wrapper silently.
- What happens when a dataset has no Tabular API support? Show a message and offer direct CSV download instead.
- What happens when the MCP returns an error for a specific query? Display a user-friendly error and suggest simpler keywords.
- What happens when the user's query returns 0 results from MCP? Try a broader search with fewer keywords before showing "no results."

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST connect to the official data.gouv.fr MCP server at `https://mcp.data.gouv.fr/mcp` using Streamable HTTP transport.
- **FR-002**: System MUST use the MCP `search_datasets` tool for all dataset searches, replacing the current custom REST API calls.
- **FR-003**: System MUST pass keywords extracted by the NL engine (Qwen2.5-72B) to the MCP `search_datasets` tool.
- **FR-004**: System MUST display search results with metadata from the MCP response: title, description, organization, last modified, CSV availability.
- **FR-005**: System MUST use the MCP `list_dataset_resources` tool to retrieve resource details when a user expands a dataset card.
- **FR-006**: System MUST use the MCP `query_resource_data` tool to preview tabular data before full download.
- **FR-007**: System MUST fall back to the existing REST API when the MCP server is unavailable.
- **FR-008**: System MUST preserve the existing UI layout, card design, and search bar from feature 008.
- **FR-009**: System MUST use the MCP `get_metrics` tool to display dataset popularity metrics on result cards.
- **FR-010**: System MUST handle MCP connection errors gracefully with user-friendly messages.

### Key Entities

- **MCP Connection**: A persistent connection to the data.gouv.fr MCP server via Streamable HTTP, managing the JSON-RPC protocol.
- **MCP Tool Call**: A structured request to one of the MCP tools (search_datasets, query_resource_data, etc.) with parameters and response handling.
- **Dataset Result (enriched)**: Search results with richer metadata from MCP including metrics, resource details, and tabular data preview capability.
- **Fallback Strategy**: Logic that detects MCP unavailability and transparently switches to the existing REST API.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The query "résultats scolaires collèges" returns at least 5 relevant datasets (currently returns 0).
- **SC-002**: Search results appear within 3 seconds for 95% of queries.
- **SC-003**: Users can preview actual data rows for any dataset that supports the Tabular API.
- **SC-004**: When the MCP server is down, the system falls back to REST API search within 5 seconds with no user-visible error beyond a subtle indicator.
- **SC-005**: Dataset cards show download/visit metrics from the official platform.
- **SC-006**: All existing search functionality (keyword search, NL query, CSV loading into workflow) continues to work identically.

## Assumptions

- The public MCP instance at `https://mcp.data.gouv.fr/mcp` is stable and free to use.
- Streamable HTTP transport is supported by the Python MCP SDK.
- The MCP `search_datasets` tool provides better relevance ranking than raw REST API calls because it uses the platform's optimized search index.
- The NL engine (Qwen2.5-72B-Instruct) continues to extract keywords; only the search backend changes.
- The existing UI components (card layout, search bar, basket) are reused as-is.

## Out of Scope

- Self-hosting the datagouv-mcp server (use the public instance).
- Searching for dataservices/APIs (datasets only for now).
- Advanced Tabular API filtering or SQL-like queries (just preview for now).
- Modifying the NL query engine — it feeds keywords to whatever backend is active.
- Changing the existing file upload flow.
