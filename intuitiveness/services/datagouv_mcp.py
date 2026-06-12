"""
DataGouv MCP Service Adapter
==============================

Wraps the generic MCPClient to provide typed search results, data preview,
and metrics from the official data.gouv.fr MCP server.

Returns DatasetInfo/SearchResult objects compatible with the existing UI,
so the UI doesn't need to know whether results came from MCP or REST.

Feature: 014-datagouv-mcp-search
Reference: https://github.com/datagouv/datagouv-mcp
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Any

from intuitiveness.data_sources.mcp_client import MCPClient, MCPResponse

# Late-import DatasetInfo, ResourceInfo, SearchResult to avoid circular import
# (datagouv_client.py imports from this module)
# These are imported inside functions that need them.

logger = logging.getLogger(__name__)


# =============================================================================
# MCP-specific Data Classes (T002)
# =============================================================================

@dataclass
class MCPDatasetResult:
    """A dataset result parsed from MCP search_datasets text response."""
    dataset_id: str
    title: str
    organization: str
    tags: List[str] = field(default_factory=list)
    resource_count: int = 0
    url: str = ""


@dataclass
class MCPResourceInfo:
    """A resource (file) within a dataset, from list_dataset_resources."""
    resource_id: str
    title: str
    format: str
    size: Optional[int] = None
    url: str = ""
    tabular_api: bool = False


@dataclass
class MCPDataPreview:
    """Tabular data preview from query_resource_data."""
    resource_id: str
    columns: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    total_rows: Optional[int] = None
    page: int = 1
    page_size: int = 20


@dataclass
class MCPMetrics:
    """Usage metrics from get_metrics."""
    dataset_id: str
    monthly_downloads: int = 0
    monthly_visits: int = 0


# =============================================================================
# Exception (T009)
# =============================================================================

class MCPServiceError(Exception):
    """Raised when MCP communication fails."""
    def __init__(self, message: str, fallback_hint: bool = True):
        self.fallback_hint = fallback_hint
        super().__init__(message)


# =============================================================================
# Response Parsers (T003-T006)
# =============================================================================

# Regex for search_datasets text output
DATASET_PATTERN = re.compile(
    r'(\d+)\.\s+(.+?)\n'
    r'\s+ID:\s+(\S+)\n'
    r'\s+Organization:\s+(.+?)\n'
    r'\s+Tags:\s*(.*?)\n'
    r'\s+Resources:\s+(\d+)\n'
    r'\s+URL:\s+(\S+)',
    re.MULTILINE
)
TOTAL_PATTERN = re.compile(r'Found\s+(\d+)\s+dataset')

# Regex for list_dataset_resources text output
# Format: "1. filename\n   Resource ID: xxx\n   Format: csv\n   ...   URL: xxx"
RESOURCE_PATTERN = re.compile(
    r'(\d+)\.\s+(.+?)\n'
    r'\s+Resource ID:\s+(\S+)\n'
    r'\s+Format:\s+(\S+)\n'
    r'(?:.*?\n)*?'  # Skip optional lines (MIME type, Type, Size, etc.)
    r'\s+URL:\s+(\S+)',
    re.MULTILINE
)

# Regex for get_metrics text output
METRICS_DOWNLOADS_PATTERN = re.compile(r'Downloads?:\s*([\d,]+)', re.IGNORECASE)
METRICS_VISITS_PATTERN = re.compile(r'Visits?:\s*([\d,]+)', re.IGNORECASE)


def _extract_text(response: MCPResponse) -> str:
    """Extract text content from an MCPResponse."""
    if not response.success or not response.data:
        return ""
    content = response.data.get("content", [])
    if content and isinstance(content, list):
        return content[0].get("text", "")
    return ""


def _parse_search_response(text: str) -> tuple[List[MCPDatasetResult], int]:
    """Parse MCP search_datasets text output into structured results. (T003)"""
    results = []
    for match in DATASET_PATTERN.finditer(text):
        tags_raw = match.group(5).strip()
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
        results.append(MCPDatasetResult(
            dataset_id=match.group(3),
            title=match.group(2).strip(),
            organization=match.group(4).strip(),
            tags=tags,
            resource_count=int(match.group(6)),
            url=match.group(7).strip(),
        ))

    total_match = TOTAL_PATTERN.search(text)
    total = int(total_match.group(1)) if total_match else len(results)

    return results, total


def _parse_resources_response(text: str) -> List[MCPResourceInfo]:
    """Parse MCP list_dataset_resources text output. (T004)"""
    results = []
    for match in RESOURCE_PATTERN.finditer(text):
        results.append(MCPResourceInfo(
            resource_id=match.group(3),
            title=match.group(2).strip(),
            format=match.group(4).strip().lower(),
            size=None,
            url=match.group(5).strip(),
        ))
    return results


def _parse_preview_response(text: str, resource_id: str) -> MCPDataPreview:
    """Parse MCP query_resource_data text output into tabular preview. (T005)"""
    lines = text.strip().split("\n")
    columns = []
    rows = []
    total_rows = None

    # Look for total count
    total_match = re.search(r'Total:\s*(\d+)', text)
    if total_match:
        total_rows = int(total_match.group(1))

    # Find table-like content: look for header row (pipe-separated or tab-separated)
    in_table = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Detect pipe-separated table
        if "|" in stripped:
            cells = [c.strip() for c in stripped.split("|") if c.strip()]
            # Skip separator lines like |---|---|
            if cells and all(set(c) <= {"-", ":"} for c in cells):
                continue
            if not columns:
                columns = cells
                in_table = True
            elif in_table:
                rows.append(cells)
        # Detect tab-separated or comma-separated tabular data
        elif "\t" in stripped and not columns:
            columns = [c.strip() for c in stripped.split("\t")]
            in_table = True
        elif "\t" in stripped and in_table:
            rows.append([c.strip() for c in stripped.split("\t")])

    return MCPDataPreview(
        resource_id=resource_id,
        columns=columns,
        rows=rows,
        total_rows=total_rows,
    )


def _parse_metrics_response(text: str, dataset_id: str) -> MCPMetrics:
    """Parse MCP get_metrics text output. (T006)"""
    downloads = 0
    visits = 0

    dl_match = METRICS_DOWNLOADS_PATTERN.search(text)
    if dl_match:
        downloads = int(dl_match.group(1).replace(",", ""))

    vis_match = METRICS_VISITS_PATTERN.search(text)
    if vis_match:
        visits = int(vis_match.group(1).replace(",", ""))

    return MCPMetrics(
        dataset_id=dataset_id,
        monthly_downloads=downloads,
        monthly_visits=visits,
    )


# =============================================================================
# Mapping Functions (T010)
# =============================================================================

def _mcp_result_to_dataset_info(mcp_result: MCPDatasetResult):
    """Convert MCPDatasetResult to existing DatasetInfo for UI compatibility."""
    from intuitiveness.services.datagouv_client import DatasetInfo
    return DatasetInfo(
        id=mcp_result.dataset_id,
        title=mcp_result.title,
        description="",  # Not in search results; fetched on expand
        organization_name=mcp_result.organization,
        last_modified=None,  # Not in search results
        resource_count=mcp_result.resource_count,
        has_csv=None,  # Unknown from search; determined on expand
    )


def _mcp_resource_to_resource_info(mcp_resource: MCPResourceInfo):
    """Convert MCPResourceInfo to existing ResourceInfo for UI compatibility."""
    from intuitiveness.services.datagouv_client import ResourceInfo
    return ResourceInfo(
        id=mcp_resource.resource_id,
        title=mcp_resource.title,
        url=mcp_resource.url,
        format=mcp_resource.format,
        filesize_bytes=mcp_resource.size,
        filesize_display="Unknown size",
        last_modified=None,
    )


# =============================================================================
# MCP Service (T007, T008)
# =============================================================================

class DataGouvMCPService:
    """
    MCP-based adapter for data.gouv.fr search, preview, and metrics.
    Wraps MCPClient to provide typed search results compatible with existing UI.
    """

    MCP_ENDPOINT = "https://mcp.data.gouv.fr/mcp"

    def __init__(self, endpoint: str = MCP_ENDPOINT, timeout: int = 5):
        self._endpoint = endpoint
        self._timeout = timeout
        self._client: Optional[MCPClient] = None
        self._available: Optional[bool] = None

    def _get_client(self) -> MCPClient:
        """Lazy-load MCPClient."""
        if self._client is None:
            self._client = MCPClient(self._endpoint, timeout=self._timeout)
        return self._client

    def is_available(self) -> bool:
        """
        Check if MCP server is reachable by attempting initialize.
        Caches result for session lifetime.
        """
        if self._available is not None:
            return self._available

        try:
            client = self._get_client()
            resp = client.initialize()
            self._available = resp.success
        except Exception as e:
            logger.warning(f"MCP availability check failed: {e}")
            self._available = False

        return self._available

    def search_datasets(self, query: str, page: int = 1, page_size: int = 10):
        """
        Search datasets via MCP search_datasets tool.

        If the full query returns 0 results, splits into individual keywords
        and merges unique results (same strategy as REST API to work around
        the MCP server's AND logic for multi-word queries).

        Returns SearchResult with DatasetInfo objects compatible with existing UI.
        Raises MCPServiceError on communication failure.
        """
        # Try the full query first
        datasets, total = self._search_single_query(query, page, page_size)

        # If no results and query has multiple words, try per-keyword search
        if not datasets and len(query.split()) > 1:
            datasets, total = self._search_multi_keyword(query, page, page_size)

        from intuitiveness.services.datagouv_client import SearchResult
        has_more = (page * page_size) < total

        return SearchResult(
            datasets=datasets,
            total=total,
            page=page,
            page_size=page_size,
            has_more=has_more,
        )

    def _search_single_query(self, query: str, page: int, page_size: int):
        """Execute a single search query against MCP."""
        client = self._get_client()
        response = client.call_tool("search_datasets", {
            "query": query,
            "page": page,
            "page_size": page_size,
        })

        if not response.success:
            raise MCPServiceError(
                f"MCP search failed: {response.error}",
                fallback_hint=True,
            )

        text = _extract_text(response)
        if not text:
            return [], 0

        mcp_results, total = _parse_search_response(text)
        datasets = [_mcp_result_to_dataset_info(r) for r in mcp_results]
        return datasets, total

    def _search_multi_keyword(self, query: str, page: int, page_size: int):
        """Search per keyword and merge unique results."""
        keywords = query.split()
        all_datasets = []
        seen_ids = set()
        max_total = 0

        for keyword in keywords[:4]:  # Limit to 4 keywords
            if len(keyword) <= 2:
                continue
            try:
                datasets, total = self._search_single_query(keyword, page, page_size)
                max_total = max(max_total, total)
                for ds in datasets:
                    if ds.id and ds.id not in seen_ids:
                        seen_ids.add(ds.id)
                        all_datasets.append(ds)
                        if len(all_datasets) >= page_size:
                            break
            except MCPServiceError:
                continue
            if len(all_datasets) >= page_size:
                break

        return all_datasets[:page_size], max_total

    def get_dataset_resources(self, dataset_id: str):
        """List resources for a dataset via MCP list_dataset_resources tool."""
        client = self._get_client()
        response = client.call_tool("list_dataset_resources", {
            "dataset_id": dataset_id,
        })

        if not response.success:
            logger.warning(f"MCP list_dataset_resources failed: {response.error}")
            return []

        text = _extract_text(response)
        mcp_resources = _parse_resources_response(text)
        return [_mcp_resource_to_resource_info(r) for r in mcp_resources]

    def preview_resource(self, resource_id: str, page: int = 1, page_size: int = 20) -> MCPDataPreview:
        """
        Preview tabular data via MCP query_resource_data tool.
        Raises MCPServiceError if resource doesn't support Tabular API.
        """
        client = self._get_client()
        response = client.call_tool("query_resource_data", {
            "resource_id": resource_id,
            "question": "Show all columns",
            "page": page,
            "page_size": page_size,
        })

        if not response.success:
            raise MCPServiceError(
                f"Preview failed: {response.error}",
                fallback_hint=False,
            )

        text = _extract_text(response)
        return _parse_preview_response(text, resource_id)

    def get_metrics(self, dataset_id: str) -> MCPMetrics:
        """Get usage metrics via MCP get_metrics tool."""
        client = self._get_client()
        response = client.call_tool("get_metrics", {
            "dataset_id": dataset_id,
        })

        if not response.success:
            logger.warning(f"MCP get_metrics failed: {response.error}")
            return MCPMetrics(dataset_id=dataset_id)

        text = _extract_text(response)
        return _parse_metrics_response(text, dataset_id)

    def close(self):
        """Close the MCP session."""
        if self._client:
            self._client.close()
            self._client = None
            self._available = None


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "DataGouvMCPService",
    "MCPServiceError",
    "MCPDatasetResult",
    "MCPResourceInfo",
    "MCPDataPreview",
    "MCPMetrics",
]
