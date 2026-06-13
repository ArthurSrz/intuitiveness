"""
LLM-powered Entity Matching
==============================

Given multiple L4 source DataFrames and user-declared column relationships,
uses an LLM (via OpenRouter / OpenAI-compatible API) to build a semantic
metadata catalog that bridges the sources, then executes the join to
produce a merged DataFrame suitable for L3 graph construction.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

_CHAT_MODEL = "anthropic/claude-sonnet-4"


def _get_chat_client():
    api_key = (
        os.getenv("OPENROUTER_API_KEY")
        or os.getenv("EMBEDDING_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    return OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    )


def _sample_values(df: pd.DataFrame, col: str, n: int = 5) -> list:
    vals = df[col].dropna().unique()[:n]
    return [str(v) for v in vals]


def _build_source_profile(name: str, df: pd.DataFrame) -> dict:
    return {
        "name": name,
        "rows": len(df),
        "columns": [
            {
                "name": col,
                "dtype": str(df[col].dtype),
                "unique_count": int(df[col].nunique()),
                "samples": _sample_values(df, col),
            }
            for col in df.columns
        ],
    }


def match_entities(
    sources: Dict[str, pd.DataFrame],
    relationships: List[Dict[str, str]],
) -> Dict[str, Any]:
    client = _get_chat_client()
    if client is None:
        return {"error": "No API key configured. Set OPENROUTER_API_KEY.", "catalog": [], "join_plan": {}}

    profiles = {name: _build_source_profile(name, df) for name, df in sources.items()}

    prompt = f"""You are a data integration expert. You have {len(sources)} datasets that a user wants to connect.

## Source Profiles
{json.dumps(list(profiles.values()), indent=2, default=str)}

## User-Declared Relationships
The user says these columns are deeply related:
{json.dumps(relationships, indent=2)}

## Your Task
1. Analyze what real-world concepts each column represents.
2. For each declared relationship, explain WHY these columns connect semantically.
3. Propose a unified metadata catalog mapping columns to shared concepts.
4. Propose a join plan with EXECUTABLE column transforms so the join actually works.

CRITICAL: The columns may have different types (dates vs years, country codes vs names, etc).
You MUST provide column_transforms that normalize them to a common format BEFORE joining.

Respond in JSON:
{{
  "catalog": [
    {{
      "concept": "Time Period",
      "description": "...",
      "mappings": [
        {{"source": "A.csv", "column": "date_col", "notes": "..."}},
        {{"source": "B.csv", "column": "year_col", "notes": "..."}}
      ]
    }}
  ],
  "join_plan": {{
    "strategy": "description",
    "join_key": "the concept name to join on (must match a catalog concept)",
    "join_type": "outer",
    "confidence": "high|medium|low"
  }},
  "column_transforms": {{
    "A.csv:date_col": "extract_year",
    "B.csv:country_code": "uppercase"
  }},
  "explanation": "2-3 sentences explaining the semantic bridge"
}}

Available transform operations (use these exact names):
- "extract_year": parse as date, extract year as integer
- "extract_month": parse as date, extract month
- "to_string": convert to string
- "to_numeric": convert to number
- "uppercase": uppercase text
- "lowercase": lowercase text
- "strip": strip whitespace
- "none": no transform needed"""

    try:
        response = client.chat.completions.create(
            model=os.getenv("ENTITY_MATCH_MODEL", _CHAT_MODEL),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        if "```json" in content:
            content = content.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in content:
            content = content.split("```", 1)[1].split("```", 1)[0]
        return json.loads(content.strip())
    except Exception as exc:
        logger.warning("Entity matching LLM call failed: %s", exc)
        return {"error": str(exc), "catalog": [], "join_plan": {}}


_TRANSFORMS = {
    "extract_year": lambda s: pd.to_datetime(s, errors="coerce").dt.year.astype("Int64"),
    "extract_month": lambda s: pd.to_datetime(s, errors="coerce").dt.month.astype("Int64"),
    "to_string": lambda s: s.astype(str),
    "to_numeric": lambda s: pd.to_numeric(s, errors="coerce"),
    "uppercase": lambda s: s.astype(str).str.upper(),
    "lowercase": lambda s: s.astype(str).str.lower(),
    "strip": lambda s: s.astype(str).str.strip(),
    "none": lambda s: s,
}


def _apply_transforms(
    sources: Dict[str, pd.DataFrame],
    column_transforms: Dict[str, str],
) -> Dict[str, pd.DataFrame]:
    """Apply LLM-prescribed transforms to source columns in-place (copies)."""
    out = {name: df.copy() for name, df in sources.items()}
    for key, transform_name in column_transforms.items():
        parts = key.split(":", 1)
        if len(parts) != 2:
            continue
        source_name, col_name = parts
        if source_name not in out or col_name not in out[source_name].columns:
            continue
        fn = _TRANSFORMS.get(transform_name.strip().lower())
        if fn is None:
            logger.warning("Unknown transform '%s' for %s — skipping", transform_name, key)
            continue
        try:
            out[source_name][col_name] = fn(out[source_name][col_name])
            logger.info("Applied transform '%s' to %s:%s", transform_name, source_name, col_name)
        except Exception as exc:
            logger.warning("Transform '%s' failed on %s:%s: %s", transform_name, source_name, col_name, exc)
    return out


def execute_join(
    sources: Dict[str, pd.DataFrame],
    join_plan: Dict[str, Any],
    catalog: List[Dict[str, Any]],
    column_transforms: Dict[str, str] | None = None,
) -> pd.DataFrame:
    """Execute the LLM-proposed join plan with transforms applied first."""
    if column_transforms:
        sources = _apply_transforms(sources, column_transforms)

    frames = list(sources.values())
    if len(frames) == 1:
        return frames[0]

    join_key = join_plan.get("join_key", "")
    join_type = join_plan.get("join_type", "outer")

    key_cols: List[Tuple[str, str]] = []
    for entry in catalog:
        if entry.get("concept", "").lower() == join_key.lower():
            for m in entry.get("mappings", []):
                key_cols.append((m["source"], m["column"]))
            break

    if len(key_cols) < 2:
        source_names = list(sources.keys())
        for col in sources[source_names[0]].columns:
            if all(col in sources[s].columns for s in source_names[1:]):
                key_cols = [(s, col) for s in source_names]
                break

    if len(key_cols) < 2:
        logger.info("No join key found — concatenating all sources")
        return pd.concat(frames, ignore_index=True)

    merged = sources[key_cols[0][0]]
    for src_name, col_name in key_cols[1:]:
        other = sources[src_name]
        left_col = key_cols[0][1]
        merged = merged.merge(
            other,
            left_on=left_col,
            right_on=col_name,
            how=join_type,
            suffixes=("", f"_{src_name.split('.')[0]}"),
        )

    if merged.empty:
        logger.info("Merge produced 0 rows — falling back to concat")
        return pd.concat(frames, ignore_index=True)

    logger.info("Entity match join: %d rows × %d cols", len(merged), len(merged.columns))
    return merged


__all__ = ["match_entities", "execute_join"]
