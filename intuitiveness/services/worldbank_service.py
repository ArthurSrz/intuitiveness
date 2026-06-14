"""
World Bank Data360 Service
============================

Searches and fetches indicator data from the World Bank Data360 API
(https://data360api.worldbank.org) and returns pandas DataFrames
compatible with the Level4Dataset ingestion path.

Usage:
    svc = WorldBankService()
    results = svc.search_indicators("GDP per capita")
    df = svc.fetch_indicator("WB_WDI_NY_GDP_PCAP_CD", database_id="WB_WDI")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

_BASE = "https://data360api.worldbank.org/data360"
_TIMEOUT = 15

_DIMENSION_COLS = {
    "REF_AREA": "country",
    "TIME_PERIOD": "year",
    "OBS_VALUE": "value",
    "SEX": "sex",
    "AGE": "age",
    "URBANISATION": "urbanisation",
    "UNIT_MEASURE": "unit",
}


@dataclass
class IndicatorInfo:
    id: str
    name: str
    database_id: str
    score: float = 0.0


class WorldBankService:
    """Wrapper around the World Bank Data360 API."""

    def search_indicators(self, query: str, max_results: int = 8) -> List[IndicatorInfo]:
        """Full-text search via Data360 searchv2 (server-side, relevance-ranked)."""
        try:
            resp = requests.post(
                f"{_BASE}/searchv2",
                json={
                    "search": query,
                    "searchFields": "series_description/name",
                    "select": "series_description/idno, series_description/name, series_description/database_id",
                    "top": max_results,
                    "count": True,
                },
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            payload = resp.json()
            return [
                IndicatorInfo(
                    id=hit["series_description"]["idno"],
                    name=hit["series_description"]["name"],
                    database_id=hit["series_description"]["database_id"],
                    score=hit.get("@search.score", 0),
                )
                for hit in payload.get("value", [])
                if hit.get("series_description", {}).get("idno")
                and hit.get("series_description", {}).get("database_id")
            ]
        except Exception as exc:
            logger.warning("Data360 search failed: %s", exc)
            return []

    def fetch_indicator(
        self,
        indicator_id: str,
        database_id: str,
    ) -> pd.DataFrame:
        """Download a Data360 indicator as a DataFrame.

        Dimension columns (sex, age, urbanisation) are kept when they
        carry meaningful variation; sentinel-only columns are dropped.
        """
        rows: list = []
        skip = 0
        page_size = 1000
        while True:
            resp = requests.get(
                f"{_BASE}/data",
                params={
                    "DATABASE_ID": database_id,
                    "INDICATOR": indicator_id,
                    "top": page_size,
                    "skip": skip,
                },
                timeout=30,
            )
            resp.raise_for_status()
            batch = resp.json().get("value", [])
            if not batch:
                break
            rows.extend(batch)
            if len(batch) < page_size:
                break
            skip += page_size

        records = []
        for r in rows:
            if r.get("OBS_VALUE") is None:
                continue
            record = {}
            for api_key, col_name in _DIMENSION_COLS.items():
                val = r.get(api_key)
                if val is not None:
                    record[col_name] = val
            records.append(record)

        if not records:
            return pd.DataFrame(columns=["country", "year", "value"])

        df = pd.DataFrame(records)
        if "value" in df.columns:
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
        if "year" in df.columns:
            df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

        for col in ["sex", "age", "urbanisation"]:
            if col in df.columns and df[col].nunique() <= 1:
                df.drop(columns=col, inplace=True)

        return df
