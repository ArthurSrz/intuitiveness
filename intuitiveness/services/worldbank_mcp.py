"""
World Bank Data360 MCP Service
================================

Wraps the generic MCPClient to search and fetch indicator data from a
Data360 MCP server (https://github.com/worldbank/data360-mcp).

The MCP server must be deployed separately (e.g. on Railway).
Endpoint URL is read from DATA360_MCP_URL env var.

Falls back to the direct REST API (WorldBankService) when the MCP
server is unavailable.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

from intuitiveness.data_sources.mcp_client import MCPClient, MCPResponse
from intuitiveness.services.worldbank_service import IndicatorInfo

logger = logging.getLogger(__name__)

_DEFAULT_ENDPOINT = "http://localhost:8021/mcp"


def _extract_text(response: MCPResponse) -> str:
    if not response.success or not response.data:
        return ""
    content = response.data.get("content", [])
    if content and isinstance(content, list):
        return content[0].get("text", "")
    return ""


class WorldBankMCPService:
    """MCP-based adapter for the World Bank Data360 search API."""

    def __init__(self, endpoint: str | None = None, timeout: int = 15):
        self._endpoint = endpoint or os.environ.get(
            "DATA360_MCP_URL", _DEFAULT_ENDPOINT
        )
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
        response = client.call_tool("data360_search", {
            "query": query,
            "n_results": max_results,
        })

        if not response.success:
            logger.warning("Data360 MCP search failed: %s", response.error)
            return []

        text = _extract_text(response)
        if not text:
            return []

        return self._parse_search_results(text)

    def _parse_search_results(self, text: str) -> List[IndicatorInfo]:
        """Parse MCP search results text into IndicatorInfo objects.

        The Data360 MCP returns structured text with indicator metadata.
        We try JSON first, then fall back to regex patterns.
        """
        import json
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "value" in data:
                return [
                    IndicatorInfo(
                        id=hit["series_description"]["idno"],
                        name=hit["series_description"]["name"],
                        database_id=hit["series_description"]["database_id"],
                        score=hit.get("@search.score", 0),
                    )
                    for hit in data["value"]
                ]
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

        results = []
        pattern = re.compile(
            r"(?:idno|ID)[:\s]+(\S+).*?"
            r"(?:name|Name)[:\s]+(.+?)(?:\n|$).*?"
            r"(?:database_id|Database)[:\s]+(\S+)",
            re.DOTALL | re.IGNORECASE,
        )
        for m in pattern.finditer(text):
            results.append(IndicatorInfo(
                id=m.group(1).strip(),
                name=m.group(2).strip(),
                database_id=m.group(3).strip(),
            ))
        return results

    def close(self):
        if self._client:
            self._client.close()
            self._client = None
            self._available = None


__all__ = ["WorldBankMCPService"]
