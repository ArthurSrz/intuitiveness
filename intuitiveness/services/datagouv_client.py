"""
DataGouv Search Service
=======================

Wrapper around the DataGouvAPI library providing a simplified interface for the
Streamlit UI. Handles search, dataset resource listing, and CSV loading.

Enhanced with NL understanding (Qwen2.5-72B) for French queries.
Flow: User NL query → Qwen2.5-72B extracts keywords → MCP search (with REST fallback)

Feature: 014-datagouv-mcp-search (upgraded from 008-datagouv-mcp)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Tuple
import pandas as pd
import logging

# Import NL query engine for natural language understanding
from intuitiveness.data_sources.nl_query import NLQueryEngine, NLQueryResult

# Import DataGouvAPI from local copy (now used as fallback)
from intuitiveness.services.datagouv_api import DataGouvAPI

# Import MCP service adapter (primary search backend)
from intuitiveness.services.datagouv_mcp import DataGouvMCPService, MCPServiceError

# Import consolidated utilities (Phase 2 - 011-code-simplification)
from intuitiveness.utils import format_filesize, parse_iso_datetime, truncate_text

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class DatasetInfo:
    """Summary info about a dataset from search results."""
    id: str
    title: str
    description: str  # Truncated to 200 chars for display
    organization_name: str
    last_modified: Optional[datetime]
    resource_count: int
    has_csv: bool


@dataclass
class ResourceInfo:
    """Info about a downloadable resource within a dataset."""
    id: str
    title: str
    url: str
    format: str
    filesize_bytes: Optional[int]
    filesize_display: str  # Human-readable, e.g., "2.5 MB"
    last_modified: Optional[datetime]


@dataclass
class SearchResult:
    """Result of a dataset search."""
    datasets: List[DatasetInfo]
    total: int
    page: int
    page_size: int
    has_more: bool


# =============================================================================
# Exceptions
# =============================================================================

class DataGouvAPIError(Exception):
    """Raised when API call fails."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class DataGouvLoadError(Exception):
    """Raised when resource loading fails."""
    def __init__(self, message: str, url: str):
        self.message = message
        self.url = url
        super().__init__(message)


# =============================================================================
# Helper Functions - Use consolidated utilities from intuitiveness.utils
# =============================================================================

# Local aliases for backward compatibility (delegates to utils/common.py)
def _format_filesize(size_bytes: Optional[int]) -> str:
    """Convert bytes to human-readable format. Delegates to utils.format_filesize."""
    return format_filesize(size_bytes) if size_bytes is not None else "Unknown size"


def _parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetime string. Delegates to utils.parse_iso_datetime."""
    return parse_iso_datetime(date_str)


def _truncate_description(description: Optional[str], max_length: int = 400) -> str:
    """Truncate description. Delegates to utils.truncate_text with newline cleanup."""
    if not description:
        return ""
    # Clean up newlines before truncating
    cleaned = description.strip().replace('\n', ' ').replace('\r', ' ')
    return truncate_text(cleaned, max_length)


# =============================================================================
# Main Service Class
# =============================================================================

class DataGouvSearchService:
    """
    Service for searching and loading data.gouv.fr datasets.

    Wraps the DataGouvAPI library with a cleaner interface for UI components.
    Enhanced with SmolLM3-3B for natural language query understanding.

    Example:
        >>> service = DataGouvSearchService()
        >>> # Simple keyword search
        >>> results = service.search("vaccination")
        >>> # Natural language query (French)
        >>> results = service.search("Quels sont les résultats scolaires des collèges?")
        >>> for dataset in results.datasets:
        ...     print(dataset.title)
    """

    def __init__(self, cache_dir: Optional[str] = None, hf_token: Optional[str] = None):
        """
        Initialize the search service.

        Args:
            cache_dir: Optional custom cache directory. Defaults to ~/.cache/datagouv
            hf_token: Optional HuggingFace token for NL queries. If not provided,
                      looks for HF_TOKEN env var or Streamlit secrets.
        """
        self._api = DataGouvAPI(cache_dir=cache_dir)
        self._hf_token = hf_token
        self._nl_engine: Optional[NLQueryEngine] = None
        self._last_nl_result: Optional[NLQueryResult] = None
        self._mcp_service: Optional[DataGouvMCPService] = None

    def _get_mcp_service(self) -> DataGouvMCPService:
        """Lazy-load MCP service. (T011)"""
        if self._mcp_service is None:
            self._mcp_service = DataGouvMCPService(timeout=5)
        return self._mcp_service

    def _get_nl_engine(self) -> Optional[NLQueryEngine]:
        """Lazy-load NL engine (only when needed)."""
        if self._nl_engine is None:
            try:
                self._nl_engine = NLQueryEngine(self._hf_token)
            except ValueError:
                # No HF token available - NL disabled
                logger.warning("No HF_TOKEN found - NL query enhancement disabled. "
                               "Set HF_TOKEN in .env or .streamlit/secrets.toml")
                return None
            except Exception as e:
                logger.warning(f"NL engine init failed: {e}")
                return None
        return self._nl_engine

    def _is_natural_language(self, query: str) -> bool:
        """
        Detect if query is natural language (vs simple keywords).

        Heuristics:
        - Contains question words (quels, quelles, comment, où, etc.)
        - Contains verbs (sont, est, contient, donne, etc.)
        - Has 5+ words
        - Ends with "?"
        """
        query_lower = query.lower().strip()

        # Question words (French)
        question_words = {
            'quels', 'quelles', 'quel', 'quelle', 'comment', 'où', 'ou',
            'pourquoi', 'combien', 'qui', 'que', 'quoi', 'lesquels', 'lesquelles'
        }

        # Common verbs in French questions
        verbs = {
            'sont', 'est', 'ont', 'a', 'contient', 'contiennent',
            'donne', 'donnent', 'montre', 'montrent', 'liste',
            'trouve', 'trouver', 'cherche', 'chercher', 'indique'
        }

        words = query_lower.replace('?', '').split()

        # Check heuristics
        if query_lower.endswith('?'):
            return True
        if any(w in question_words for w in words):
            return True
        if any(w in verbs for w in words) and len(words) >= 4:
            return True
        if len(words) >= 6:
            return True

        return False

    def _search_with_keywords(
        self,
        keywords: List[str],
        page: int,
        page_size: int
    ) -> Tuple[List[dict], int]:
        """
        Search with multiple keywords, combining unique results.

        data.gouv.fr is picky with multi-word queries, so we search
        each keyword individually and merge results.
        """
        all_results = []
        seen_ids = set()
        total = 0

        for keyword in keywords[:4]:  # Limit to 4 keywords
            try:
                raw = self._api.search_datasets(
                    query=keyword.strip(),
                    page_size=page_size,
                    page=page
                )
                total = max(total, raw.get('total', 0))

                for dataset in raw.get('data', []):
                    did = dataset.get('id')
                    if did and did not in seen_ids:
                        seen_ids.add(did)
                        all_results.append(dataset)

                        if len(all_results) >= page_size:
                            break

            except Exception as e:
                logger.warning(f"Search failed for keyword '{keyword}': {e}")
                continue

            if len(all_results) >= page_size:
                break

        return all_results[:page_size], total

    @property
    def last_nl_result(self) -> Optional[NLQueryResult]:
        """Get the last NL parsing result (keywords, intent, etc.)."""
        return self._last_nl_result

    def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 10,
        use_nl: Optional[bool] = None
    ) -> SearchResult:
        """
        Search for datasets matching the query.

        Strategy: MCP-first with transparent REST API fallback.
        1. Try MCP server (if not in fallback mode)
        2. On MCP failure, set session-level fallback flag and use REST API

        Automatically detects natural language queries and uses Qwen2.5-72B
        to extract keywords for better search results.

        Args:
            query: Search query (keywords or natural language French)
            page: Page number (1-indexed)
            page_size: Results per page (max 20)
            use_nl: Force NL processing on/off. If None, auto-detect.

        Returns:
            SearchResult containing datasets and pagination info

        Raises:
            DataGouvAPIError: If all search backends fail
        """
        self._last_nl_result = None

        if not query or not query.strip():
            return SearchResult(
                datasets=[], total=0, page=page,
                page_size=page_size, has_more=False
            )

        # Clamp page_size to reasonable limits
        page_size = min(max(1, page_size), 20)

        # Extract keywords from NL queries (used by both MCP and REST)
        should_use_nl = use_nl if use_nl is not None else self._is_natural_language(query)
        search_query = query.strip()

        if should_use_nl:
            nl_engine = self._get_nl_engine()
            if nl_engine:
                logger.info(f"NL query detected: '{query}'")
                nl_result = nl_engine.parse_query(query)
                self._last_nl_result = nl_result
                logger.info(f"Extracted keywords: {nl_result.keywords}")
                search_query = " ".join(nl_result.keywords)

        # T013: MCP-first search with REST fallback
        try:
            import streamlit as st
            mcp_fallback = st.session_state.get("datagouv_mcp_fallback", False)
        except Exception:
            mcp_fallback = False

        if not mcp_fallback:
            try:
                mcp_service = self._get_mcp_service()
                if mcp_service.is_available():
                    result = mcp_service.search_datasets(search_query, page, page_size)

                    # T016: If MCP returns 0 results for a multi-word query,
                    # try broader search with fewer keywords
                    if not result.datasets and self._last_nl_result and len(self._last_nl_result.keywords) > 2:
                        fewer_keywords = " ".join(self._last_nl_result.keywords[:2])
                        result = mcp_service.search_datasets(fewer_keywords, page, page_size)

                    # T014: Store backend indicator
                    try:
                        st.session_state["datagouv_search_backend"] = "mcp"
                    except Exception:
                        pass

                    return result
            except MCPServiceError as e:
                logger.warning(f"MCP search failed, falling back to REST: {e}")
                try:
                    st.session_state["datagouv_mcp_fallback"] = True
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"MCP unavailable, falling back to REST: {e}")
                try:
                    st.session_state["datagouv_mcp_fallback"] = True
                except Exception:
                    pass

        # T012/T014: REST API fallback path
        try:
            import streamlit as st
            st.session_state["datagouv_search_backend"] = "rest"
        except Exception:
            pass

        return self._search_rest(query, page, page_size, search_query)

    def _search_rest(
        self,
        original_query: str,
        page: int,
        page_size: int,
        search_query: str
    ) -> SearchResult:
        """REST API search path (original implementation, now used as fallback). (T012)"""
        try:
            if self._last_nl_result and self._last_nl_result.keywords:
                raw_data, total = self._search_with_keywords(
                    self._last_nl_result.keywords, page, page_size
                )
                raw_results = {'data': raw_data, 'total': total}
            else:
                raw_results = self._api.search_datasets(
                    query=search_query,
                    page_size=page_size,
                    page=page
                )
        except Exception as e:
            logger.error(f"REST API search failed: {e}")
            raise DataGouvAPIError(f"Search failed: {str(e)}")

        # Transform raw API response to our data classes
        datasets = []
        for raw_dataset in raw_results.get('data', []):
            resources = raw_dataset.get('resources', [])
            has_csv = any(
                (r.get('format') or '').lower() == 'csv'
                for r in resources
            )
            org = raw_dataset.get('organization')
            org_name = org.get('name', 'Unknown') if org else 'Unknown'

            dataset = DatasetInfo(
                id=raw_dataset.get('id', ''),
                title=raw_dataset.get('title', 'Untitled'),
                description=_truncate_description(raw_dataset.get('description')),
                organization_name=org_name,
                last_modified=_parse_datetime(raw_dataset.get('last_modified')),
                resource_count=len(resources),
                has_csv=has_csv
            )
            datasets.append(dataset)

        total = raw_results.get('total', 0)
        has_more = (page * page_size) < total

        return SearchResult(
            datasets=datasets, total=total, page=page,
            page_size=page_size, has_more=has_more
        )

    def get_dataset_resources(
        self,
        dataset_id: str,
        format_filter: str = "csv"
    ) -> List[ResourceInfo]:
        """
        Get resources for a specific dataset, filtered by format.

        Args:
            dataset_id: Dataset ID from search results
            format_filter: File format to filter (default: csv)

        Returns:
            List of resources matching the format filter
        """
        try:
            raw_dataset = self._api.get_dataset(dataset_id)
        except Exception as e:
            logger.error(f"Failed to get dataset {dataset_id}: {e}")
            return []

        if not raw_dataset:
            return []

        resources = []
        for raw_resource in raw_dataset.get('resources', []):
            resource_format = (raw_resource.get('format') or '').lower()

            # Apply format filter
            if format_filter and resource_format != format_filter.lower():
                continue

            filesize = raw_resource.get('filesize')

            resource = ResourceInfo(
                id=raw_resource.get('id', ''),
                title=raw_resource.get('title', 'Untitled'),
                url=raw_resource.get('url', ''),
                format=resource_format,
                filesize_bytes=filesize,
                filesize_display=_format_filesize(filesize),
                last_modified=_parse_datetime(raw_resource.get('last_modified'))
            )
            resources.append(resource)

        # Sort by last_modified (most recent first)
        resources.sort(
            key=lambda r: r.last_modified or datetime.min,
            reverse=True
        )

        return resources

    def load_resource(
        self,
        resource_url: str,
        filename: str
    ) -> pd.DataFrame:
        """
        Download and load a resource as a DataFrame.

        Args:
            resource_url: URL of the resource to download
            filename: Display name for the loaded data

        Returns:
            Loaded DataFrame ready for L4 workflow

        Raises:
            DataGouvLoadError: If download or parsing fails
        """
        if not resource_url:
            raise DataGouvLoadError("No resource URL provided", resource_url)

        try:
            df = self._api.load_csv(resource_url)
        except Exception as e:
            logger.error(f"Failed to load resource from {resource_url}: {e}")
            raise DataGouvLoadError(f"Failed to load: {str(e)}", resource_url)

        if df is None:
            raise DataGouvLoadError(
                "Could not parse CSV file. The format may be incompatible.",
                resource_url
            )

        logger.info(f"Loaded {len(df)} rows from {filename}")
        return df

    def is_available(self) -> bool:
        """
        Check if data.gouv.fr API is reachable.

        Returns:
            True if API responds, False otherwise
        """
        try:
            # Try a minimal search to test connectivity
            result = self._api.search_datasets("test", page_size=1)
            return 'data' in result
        except Exception as e:
            logger.warning(f"API availability check failed: {e}")
            return False
