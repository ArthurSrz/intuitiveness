# Contract: DataGouvMCPService

**Feature**: 014-datagouv-mcp-search
**Date**: 2026-03-08
**Module**: `intuitiveness/services/datagouv_mcp.py`

## Interface

```python
class DataGouvMCPService:
    """
    MCP-based adapter for data.gouv.fr search, preview, and metrics.
    Wraps MCPClient to provide typed search results compatible with existing UI.
    """

    def __init__(self, endpoint: str = "https://mcp.data.gouv.fr/mcp", timeout: int = 5):
        """
        Args:
            endpoint: MCP server URL
            timeout: Connection timeout in seconds (5s for fallback compliance)
        """

    def is_available(self) -> bool:
        """
        Check if MCP server is reachable by attempting initialize.
        Returns False on timeout or connection error.
        Caches result for session lifetime.
        """

    def search_datasets(self, query: str, page: int = 1, page_size: int = 10) -> SearchResult:
        """
        Search datasets via MCP search_datasets tool.

        Args:
            query: Search keywords (space-separated)
            page: Page number (1-indexed)
            page_size: Results per page (max 100)

        Returns:
            SearchResult with list of DatasetInfo objects

        Raises:
            MCPServiceError: On MCP communication failure
        """

    def get_dataset_resources(self, dataset_id: str) -> List[ResourceInfo]:
        """
        List resources for a dataset via MCP list_dataset_resources tool.

        Args:
            dataset_id: data.gouv.fr dataset ID

        Returns:
            List of ResourceInfo objects with tabular_api availability flag
        """

    def preview_resource(self, resource_id: str, page: int = 1, page_size: int = 20) -> MCPDataPreview:
        """
        Preview tabular data via MCP query_resource_data tool.

        Args:
            resource_id: data.gouv.fr resource ID
            page: Page number
            page_size: Rows per page (max 200)

        Returns:
            MCPDataPreview with columns, rows, total count

        Raises:
            MCPServiceError: If resource doesn't support Tabular API
        """

    def get_metrics(self, dataset_id: str) -> MCPMetrics:
        """
        Get usage metrics via MCP get_metrics tool.

        Args:
            dataset_id: data.gouv.fr dataset ID

        Returns:
            MCPMetrics with monthly downloads and visits
        """
```

## Response Parsing Contract

### search_datasets Response → DatasetInfo[]

**Input text format** (from MCP):
```
Found N dataset(s) for query: 'QUERY'
Page P of results:

1. TITLE
   ID: DATASET_ID
   Organization: ORG_NAME
   Tags: tag1, tag2
   Resources: N
   URL: FULL_URL
```

**Regex patterns**:
```python
DATASET_PATTERN = re.compile(
    r'(\d+)\.\s+(.+?)\n'           # number + title
    r'\s+ID:\s+(\S+)\n'             # dataset ID
    r'\s+Organization:\s+(.+?)\n'    # org name
    r'\s+Tags:\s+(.*?)\n'            # tags (comma-separated)
    r'\s+Resources:\s+(\d+)\n'       # resource count
    r'\s+URL:\s+(\S+)',              # URL
    re.MULTILINE
)
TOTAL_PATTERN = re.compile(r'Found\s+(\d+)\s+dataset')
```

**Output mapping**:
```python
DatasetInfo(
    id=match.group(3),
    title=match.group(2),
    description="",  # Not in search results; fetched on expand via get_dataset_info
    organization=match.group(4),
    tags=match.group(5).split(", "),
    resources_count=int(match.group(6)),
    url=match.group(7),
    last_modified=None,  # Not in search results
    has_csv=None,  # Determined from resources on expand
)
```

## Error Contract

```python
class MCPServiceError(Exception):
    """Raised when MCP communication fails."""
    def __init__(self, message: str, fallback_hint: bool = True):
        self.fallback_hint = fallback_hint  # True = caller should try REST fallback
        super().__init__(message)
```

## Integration Contract with DataGouvSearchService

```python
# In datagouv_client.py — modified search() method:

def search(self, query, page=1, page_size=10) -> SearchResult:
    # 1. Try MCP first (if not in fallback mode)
    if not st.session_state.get("datagouv_mcp_fallback", False):
        try:
            mcp_service = self._get_mcp_service()
            if mcp_service.is_available():
                result = mcp_service.search_datasets(query, page, page_size)
                st.session_state["datagouv_search_backend"] = "mcp"
                return result
        except MCPServiceError:
            st.session_state["datagouv_mcp_fallback"] = True
            st.session_state["datagouv_search_backend"] = "rest"

    # 2. Fallback to existing REST API (unchanged code path)
    st.session_state["datagouv_search_backend"] = "rest"
    return self._search_rest(query, page, page_size)
```

## UI Contract

### Dataset Card Additions

| Element | Trigger | MCP Tool | Fallback |
|---------|---------|----------|----------|
| Metrics chips (downloads/visits) | Card render | `get_metrics` | Hide chips |
| "Preview Data" button | Card expanded + CSV resource | `query_resource_data` | "Download CSV" button |
| Backend indicator | Always | N/A | Subtle text: "via MCP" or "via REST API" |

### Preview Panel

```python
# Renders inside dataset card expander
if st.button("Preview Data", key=f"preview_{resource_id}"):
    preview = mcp_service.preview_resource(resource_id)
    st.dataframe(
        pd.DataFrame(preview.rows, columns=preview.columns),
        use_container_width=True
    )
```
