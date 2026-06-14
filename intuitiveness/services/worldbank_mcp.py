"""
World Bank Data360 MCP Service
================================

Wraps the generic MCPClient to search and fetch indicator data from the
Data360 MCP server deployed on Railway.

Falls back to the direct REST API (WorldBankService) when the MCP
server is unavailable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from intuitiveness.data_sources.mcp_client import MCPClient, MCPResponse
from intuitiveness.services.worldbank_service import IndicatorInfo

logger = logging.getLogger(__name__)

MCP_ENDPOINT = "https://data360-mcp-production.up.railway.app/mcp"


def _extract_text(response: MCPResponse) -> str:
    if not response.success or not response.data:
        return ""
    content = response.data.get("content", [])
    if content and isinstance(content, list):
        return content[0].get("text", "")
    return ""


class WorldBankMCPService:
    """MCP-based adapter for the World Bank Data360 search API."""

    def __init__(self, endpoint: str = MCP_ENDPOINT, timeout: int = 15):
        self._endpoint = endpoint
        self._timeout = timeout
        self._client: Optional[MCPClient] = None
        self._available: Optional[bool] = None

    def _get_client(self) -> MCPClient:
        if self._client is None:
            self._client = MCPClient(self._endpoint, timeout=self._timeout)
        return self._client

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            client = self._get_client()
            resp = client.initialize()
            self._available = resp.success
        except Exception as exc:
            logger.warning("Data360 MCP availability check failed: %s", exc)
            self._available = False
        return self._available

    def search_indicators(
        self, query: str, max_results: int = 8
    ) -> List[IndicatorInfo]:
        """Search indicators via the data360_search MCP tool."""
        client = self._get_client()
        response = client.call_tool("data360_search_indicators", {
            "query": query,
            "limit": max_results,
        })

        if not response.success:
            logger.warning("Data360 MCP search failed: %s", response.error)
            return []

        text = _extract_text(response)
        if not text:
            return []

        return self._parse_search_results(text)

    def _parse_search_results(self, text: str) -> List[IndicatorInfo]:
        """Parse MCP search results into IndicatorInfo objects.

        The Data360 MCP returns JSON with an `indicators` array.
        """
        import json
        try:
            data = json.loads(text)
            indicators = data.get("indicators", [])
            return [
                IndicatorInfo(
                    id=ind["idno"],
                    name=ind["name"],
                    database_id=ind["database_id"],
                )
                for ind in indicators
                if ind.get("idno") and ind.get("database_id")
            ]
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
        return []

    def close(self):
        if self._client:
            self._client.close()
            self._client = None
            self._available = None


__all__ = ["WorldBankMCPService"]
