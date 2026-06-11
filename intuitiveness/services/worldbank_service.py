"""
World Bank Data Service
========================

Fetches indicator data from the World Bank REST API (v2) and returns
pandas DataFrames compatible with the Level4Dataset ingestion path.

No MCP server exists for the World Bank as of mid-2025; this service
wraps the official JSON API directly instead.

Usage:
    svc = WorldBankService()
    df = svc.fetch_indicator("NY.GDP.PCAP.CD", countries="all", year_range=(2018, 2023))
    results = svc.search_indicators("GDP per capita")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pandas as pd
import requests

logger = logging.getLogger(__name__)

_BASE = "https://api.worldbank.org/v2"
_TIMEOUT = 15


@dataclass
class IndicatorInfo:
    id: str
    name: str
    source: str
    topics: List[str]


class WorldBankService:
    """Thin wrapper around the World Bank REST API v2."""

    def search_indicators(self, query: str, max_results: int = 8) -> List[IndicatorInfo]:
        """Full-text search across all WB indicators."""
        url = f"{_BASE}/indicator?format=json&per_page={max_results}&mrv=1&q={requests.utils.quote(query)}"
        try:
            resp = requests.get(url, timeout=_TIMEOUT)
            resp.raise_for_status()
            pages, items = resp.json()
            return [
                IndicatorInfo(
                    id=it["id"],
                    name=it.get("name", ""),
                    source=it.get("source", {}).get("value", ""),
                    topics=[t.get("value", "") for t in it.get("topics", [])],
                )
                for it in (items or [])
            ]
        except Exception as exc:
            logger.warning("WB indicator search failed: %s", exc)
            return []

    def fetch_indicator(
        self,
        indicator_id: str,
        countries: str = "all",
        year_range: Tuple[int, int] = (2018, 2023),
    ) -> pd.DataFrame:
        """
        Download a World Bank indicator as a DataFrame.

        Columns: country_code, country_name, year, <indicator_id>
        """
        start, end = year_range
        url = (
            f"{_BASE}/country/{countries}/indicator/{indicator_id}"
            f"?format=json&per_page=1000&date={start}:{end}"
        )
        rows = []
        page = 1
        while True:
            try:
                resp = requests.get(f"{url}&page={page}", timeout=_TIMEOUT)
                resp.raise_for_status()
                payload = resp.json()
                if not isinstance(payload, list) or len(payload) < 2:
                    break
                meta, data = payload
                if not data:
                    break
                for item in data:
                    if item.get("value") is not None:
                        rows.append({
                            "country_code": item["country"]["id"],
                            "country_name": item["country"]["value"],
                            "year": int(item["date"]),
                            indicator_id: item["value"],
                        })
                if page >= meta.get("pages", 1):
                    break
                page += 1
            except Exception as exc:
                logger.warning("WB fetch page %d failed: %s", page, exc)
                break

        if not rows:
            return pd.DataFrame(columns=["country_code", "country_name", "year", indicator_id])
        return pd.DataFrame(rows)
