# Phase 1 Data Model: data.gouv.fr MCP Search Integration

**Feature**: 014-datagouv-mcp-search
**Date**: 2026-03-08

## Entities

### MCPDatasetResult

Represents a single dataset result parsed from MCP `search_datasets` text response.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `dataset_id` | `str` | Parsed from MCP text (`ID:` line) | data.gouv.fr dataset identifier |
| `title` | `str` | Parsed from MCP text (numbered line) | Dataset title |
| `organization` | `str` | Parsed from MCP text (`Organization:` line) | Publishing organization |
| `tags` | `List[str]` | Parsed from MCP text (`Tags:` line) | Dataset tags |
| `resource_count` | `int` | Parsed from MCP text (`Resources:` line) | Number of files |
| `url` | `str` | Parsed from MCP text (`URL:` line) | data.gouv.fr URL |

**Relationship**: Maps 1:1 to existing `DatasetInfo` (in `datagouv_client.py`) for UI compatibility.

### MCPResourceInfo

Represents a resource (file) within a dataset, from `list_dataset_resources`.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `resource_id` | `str` | Parsed from MCP text | Resource identifier |
| `title` | `str` | Parsed from MCP text | File title |
| `format` | `str` | Parsed from MCP text | File format (csv, xlsx, etc.) |
| `size` | `Optional[int]` | Parsed from MCP text | File size in bytes |
| `url` | `str` | Parsed from MCP text | Download URL |
| `tabular_api` | `bool` | From `get_resource_info` | Whether Tabular API is available |

**Relationship**: Many MCPResourceInfo belong to one MCPDatasetResult (via `dataset_id`).

### MCPDataPreview

Represents a tabular data preview from `query_resource_data`.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `resource_id` | `str` | Input parameter | Resource being previewed |
| `columns` | `List[str]` | Parsed from MCP text | Column headers |
| `rows` | `List[List[str]]` | Parsed from MCP text | Data rows |
| `total_rows` | `Optional[int]` | Parsed from MCP text | Total row count |
| `page` | `int` | Input parameter | Current page |
| `page_size` | `int` | Input parameter | Rows per page |

**Relationship**: One MCPDataPreview belongs to one MCPResourceInfo (via `resource_id`).

### MCPMetrics

Represents usage metrics from `get_metrics`.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `dataset_id` | `str` | Input parameter | Dataset being measured |
| `monthly_downloads` | `int` | Parsed from MCP text | Latest month download count |
| `monthly_visits` | `int` | Parsed from MCP text | Latest month visit count |

**Relationship**: One MCPMetrics belongs to one MCPDatasetResult (via `dataset_id`).

## Entity Relationship Diagram

```
MCPDatasetResult (1) ──── (N) MCPResourceInfo
       │                           │
       │                           │
  (1)──┤                      (1)──┤
       │                           │
  MCPMetrics                MCPDataPreview
```

## Mapping to Existing Entities

The new MCP entities map to existing UI entities:

| MCP Entity | Existing Entity | Mapping |
|------------|----------------|---------|
| `MCPDatasetResult` | `DatasetInfo` | Direct field mapping (title, org, etc.) |
| `MCPResourceInfo` | `ResourceInfo` | Direct field mapping (id, format, url) |
| `MCPDataPreview` | *NEW* | No existing equivalent — renders as `st.dataframe()` |
| `MCPMetrics` | *NEW* | No existing equivalent — renders as metric chips on cards |

## State Transitions

### Search Backend State

```
                  ┌─── MCP available ──→ MCP_ACTIVE
                  │
APP_START ───────┤
                  │
                  └─── MCP timeout ───→ REST_FALLBACK
                                              │
                                    (session refresh)
                                              │
                                        APP_START
```

Session state key: `datagouv_mcp_fallback` (bool, default `False`)

### Dataset Card State

```
COLLAPSED ──(click expand)──→ EXPANDED ──(click preview)──→ PREVIEWING
    │                              │                              │
    └──(click add)──→ ADDED        └──(click add)──→ ADDED       └──(click add)──→ ADDED
```
