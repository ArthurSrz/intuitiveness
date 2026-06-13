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
{json.dumps(relationships, indent=2) if relationships else "None declared — discover ALL meaningful relationships between the sources automatically. Look at column names, data types, and sample values to find columns that represent the same real-world thing."}

## Your Task
1. Analyze what real-world concepts each column represents.
2. Find columns that are ROW IDENTIFIERS — columns whose values uniquely identify a row (like a school code, country name, year, department code, person ID). ONLY these should go in the catalog as join keys.
3. DO NOT add measurement/value columns to the catalog (numbers like counts, rates, scores, amounts). Even if two sources measure the same thing, joining on measurements produces 0 rows because the values will differ.
4. Propose a join plan with EXECUTABLE column transforms so the join actually works.

RULE: A join key must be an IDENTIFIER (something that labels a row), NOT a MEASUREMENT (something that describes a row).
- GOOD join keys: school code, year, country name, department code, person ID, session year
- BAD join keys: number of candidates, success rate, score, amount, count

CRITICAL: The columns may have different types (dates vs years, country codes vs names, etc).
You MUST provide column_transforms that normalize them to a common format BEFORE joining.

IMPORTANT: Write ALL descriptions in plain, non-technical language that anyone can understand.
Do NOT use jargon. Write things a normal person would say: "The year", "Which school", "Which country".

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
    import unicodedata
    out = {name: df.copy() for name, df in sources.items()}
    for key, transform_name in column_transforms.items():
        parts = key.split(":", 1)
        if len(parts) != 2:
            continue
        source_name, col_name = parts
        col_name = unicodedata.normalize("NFC", col_name)
        if source_name not in out:
            continue
        # Match column with NFC normalization to handle accented names
        col_match = next((c for c in out[source_name].columns if unicodedata.normalize("NFC", c) == col_name), None)
        if col_match is None:
            continue
        col_name = col_match
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
) -> "tuple[pd.DataFrame, Dict[str, str]]":
    """Execute the join using ALL shared concepts as multi-key join.

    Returns (merged_df, col_source_map) where col_source_map maps each
    non-key column in the result to the short source name it came from.
    This explicit mapping lets callers group columns by source without
    relying on string-matching heuristics.
    """
    if column_transforms:
        sources = _apply_transforms(sources, column_transforms)

    frames = list(sources.values())
    if len(frames) == 1:
        return frames[0], {}

    join_type = join_plan.get("join_type", "inner")
    source_names = list(sources.keys())

    # Find ALL shared concepts from the catalog — each becomes a join key
    shared_keys: List[Dict[str, str]] = []
    for entry in catalog:
        mappings = entry.get("mappings", [])
        if len(mappings) < 2:
            continue
        key_map = {}
        for m in mappings:
            src = m.get("source", "")
            col = m.get("column", "")
            if src in sources and col in sources[src].columns:
                key_map[src] = col
        if len(key_map) >= 2:
            shared_keys.append(key_map)

    # Fallback: same-name columns across all sources
    if not shared_keys:
        for col in sources[source_names[0]].columns:
            if all(col in sources[s].columns for s in source_names[1:]):
                shared_keys.append({s: col for s in source_names})

    if not shared_keys:
        logger.info("No join keys found — concatenating all sources")
        return pd.concat(frames, ignore_index=True), {}

    logger.warning("JOIN: %d shared keys found: %s", len(shared_keys),
                    [{v for v in k.values()} for k in shared_keys])

    # col_source_map: final_column_name → short_source_name (built as we rename)
    col_source_map: Dict[str, str] = {}

    left_src = source_names[0]
    left_name = left_src.replace(".csv", "").replace(".CSV", "")
    merged = sources[left_src].copy()

    # Track non-key columns from the left source
    key_cols_global: set = set()
    for km in shared_keys:
        key_cols_global.update(km.values())
    for col in merged.columns:
        if col not in key_cols_global:
            col_source_map[col] = left_name

    for right_src in source_names[1:]:
        right_name = right_src.replace(".csv", "").replace(".CSV", "")
        other = sources[right_src].copy()

        left_on = []
        right_on = []
        key_cols_set: set = set()
        for key_map in shared_keys:
            l_col = key_map.get(left_src)
            r_col = key_map.get(right_src)
            if l_col and r_col:
                left_on.append(l_col)
                right_on.append(r_col)
                key_cols_set.add(l_col)
                key_cols_set.add(r_col)

        if not left_on:
            logger.warning("JOIN: no keys between %s and %s — skipping", left_src, right_src)
            continue

        # Normalise key columns to stripped strings so "01" == "1" and " UAI " == "UAI"
        for l_col, r_col in zip(left_on, right_on):
            merged[l_col] = merged[l_col].astype(str).str.strip()
            other[r_col] = other[r_col].astype(str).str.strip()

        # Rename overlapping non-key columns and update col_source_map
        overlap = set(merged.columns) & set(other.columns) - key_cols_set
        if overlap:
            left_renames = {c: f"{c}_{left_name}" for c in overlap}
            right_renames = {c: f"{c}_{right_name}" for c in overlap}
            # Update map for renamed left cols
            for old, new in left_renames.items():
                if old in col_source_map:
                    col_source_map[new] = col_source_map.pop(old)
                else:
                    col_source_map[new] = left_name
            merged = merged.rename(columns=left_renames)
            other = other.rename(columns=right_renames)
            # Register right source's renamed cols
            for old, new in right_renames.items():
                col_source_map[new] = right_name
        else:
            # Register right source's non-key cols directly
            for col in other.columns:
                if col not in key_cols_set:
                    col_source_map[col] = right_name

        logger.warning("JOIN: merging %s ← %s on %s = %s (overlap renamed: %s)",
                        left_name, right_name, left_on, right_on, overlap)

        attempt = merged.merge(other, left_on=left_on, right_on=right_on, how=join_type)

        # Multi-key join produced no rows — retry each key alone, pick best
        if attempt.empty and len(left_on) > 1:
            logger.warning("JOIN: multi-key produced 0 rows — trying each key individually")
            best, best_n = None, 0
            for l_col, r_col in zip(left_on, right_on):
                # Normalise both sides to stripped strings before comparing
                m_try = merged.copy()
                o_try = other.copy()
                m_try[l_col] = m_try[l_col].astype(str).str.strip()
                o_try[r_col] = o_try[r_col].astype(str).str.strip()
                candidate = m_try.merge(o_try, left_on=l_col, right_on=r_col, how=join_type)
                logger.warning("JOIN: single-key %s=%s → %d rows", l_col, r_col, len(candidate))
                if len(candidate) > best_n:
                    best, best_n = candidate, len(candidate)
            if best is not None and best_n > 0:
                attempt = best
                logger.warning("JOIN: best single-key produced %d rows", best_n)

        merged = attempt

    # Drop rows where ALL columns from any one source are null (outer join artifacts)
    source_col_groups: Dict[str, List[str]] = {}
    for src_name in set(col_source_map.values()):
        source_col_groups[src_name] = [c for c, s in col_source_map.items() if s == src_name and c in merged.columns]
    before = len(merged)
    for src_name, cols in source_col_groups.items():
        if cols:
            merged = merged[~merged[cols].isnull().all(axis=1)]
    after = len(merged)
    if before != after:
        logger.warning("JOIN: dropped %d rows with no data from one source", before - after)

    logger.warning("JOIN result: %d rows × %d cols — %s", len(merged), len(merged.columns), list(merged.columns))
    return merged, col_source_map


__all__ = ["match_entities", "execute_join"]
