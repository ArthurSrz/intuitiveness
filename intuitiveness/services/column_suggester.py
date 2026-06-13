"""
LLM-powered Column Selection for L2→L1 descent.

AI sees the L2 table profile, suggests the best column to extract as a
feature vector, and writes Python code to do the extraction (with optional
filtering).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

import pandas as pd

logger = logging.getLogger(__name__)

_CHAT_MODEL = "anthropic/claude-sonnet-4"


def _get_chat_client():
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            import anthropic
            return ("anthropic", anthropic.Anthropic(api_key=anthropic_key))
        except ImportError:
            pass
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
    return ("openai", OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    ))


def _call_llm(client_tuple, prompt: str) -> str:
    kind, client = client_tuple
    if kind == "anthropic":
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text
    else:
        response = client.chat.completions.create(
            model=os.getenv("COLUMN_SUGGEST_MODEL", _CHAT_MODEL),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
    if "```json" in content:
        content = content.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in content:
        content = content.split("```", 1)[1].split("```", 1)[0]
    return content


def _sample_values(df: pd.DataFrame, col: str, n: int = 8) -> list:
    vals = df[col].dropna().unique()[:n]
    return [str(v) for v in vals]


def _to_frame(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    return pd.DataFrame(data)


def _build_data_profile(df: pd.DataFrame) -> dict:
    profile_cols = []
    for col in df.columns:
        info: Dict[str, Any] = {
            "name": col,
            "dtype": str(df[col].dtype),
            "non_null": int(df[col].notna().sum()),
            "unique_count": int(df[col].nunique()),
            "samples": _sample_values(df, col),
        }
        if pd.api.types.is_numeric_dtype(df[col]) and df[col].notna().any():
            info["min"] = float(df[col].min())
            info["max"] = float(df[col].max())
            info["mean"] = round(float(df[col].mean()), 2)
            info["median"] = round(float(df[col].median()), 2)
        profile_cols.append(info)
    return {"rows": len(df), "columns": profile_cols}


def _pick_column_heuristic(df: pd.DataFrame) -> str:
    numeric = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c]) and df[c].notna().any()
    ]
    if numeric:
        for c in numeric:
            if any(k in str(c).lower() for k in ("value", "amount", "price", "score", "count")):
                return c
        return numeric[0]
    text = [c for c in df.columns if c != "node" and c != "category" and df[c].notna().any()]
    return text[0] if text else (df.columns[0] if len(df.columns) else "value")


def suggest_column(data: Any, intent: str = "") -> Dict[str, Any]:
    """Analyze L2 data and suggest which column to extract as L1 vector."""
    df = _to_frame(data)
    if df.empty:
        return {"error": "Empty dataset", "proposed_column": "", "columns": []}

    columns = list(df.columns)
    client = _get_chat_client()

    if client is None:
        col = _pick_column_heuristic(df)
        return {
            "proposed_column": col,
            "proposed_filter": "",
            "explanation": f"Auto-detected '{col}' as the best variable to isolate.",
            "confidence": "heuristic",
            "code": f"series = df['{col}'].dropna()",
            "columns": columns,
            "preview_stats": {},
            "error": None,
        }

    profile = _build_data_profile(df)

    prompt = f"""You are a data analyst. You have a categorized table with {profile['rows']} rows.

Here is the full column profile:
{json.dumps(profile['columns'], indent=2, default=str)}

## User's Analysis Intent
{intent if intent else "Not specified — choose the most analytically useful column."}

## Your Task
The user wants to extract ONE column from this table as a feature vector for analysis. Orient your choice toward their intent above.
This reduces the table to a single variable — one value per entity.

1. Pick the BEST column to extract — the one most useful as a single analytical measure.
   Prefer numeric columns with meaningful variation. Skip id/key/category columns.
   ONLY pick columns with actual data (non_null > 0).
2. Optionally suggest a filter to focus on a meaningful subset (e.g. only rows where category == 'high').
3. Write Python code that extracts the column as a pandas Series called `series` from a DataFrame `df`.
   Handle NaN values. You have access to `pd` (pandas) and `np` (numpy).

Examples of good extraction code:
- Simple: `series = df['score'].dropna()`
- Filtered: `series = df.loc[df['category'] == 'high', 'score'].dropna()`
- Computed: `series = (df['value_A'] / df['value_B']).dropna()`

Respond in JSON:
{{
  "proposed_column": "the column you chose",
  "proposed_filter": "optional filter description or empty string",
  "code": "Python code that creates a `series` variable from `df`",
  "explanation": "2-3 sentences explaining why this column is the best feature to isolate."
}}"""

    try:
        content = _call_llm(client, prompt)
        result = json.loads(content.strip())
    except Exception as exc:
        logger.warning("Column suggestion LLM call failed: %s", exc)
        col = _pick_column_heuristic(df)
        return {
            "proposed_column": col,
            "proposed_filter": "",
            "explanation": f"LLM unavailable. Auto-detected '{col}'.",
            "confidence": "heuristic",
            "code": f"series = df['{col}'].dropna()",
            "columns": columns,
            "preview_stats": {},
            "error": None,
        }

    # Run the code on a sample to compute preview stats
    code = result.get("code", "")
    preview_stats: Dict[str, Any] = {}
    if code:
        try:
            import numpy as np
            sample = df.head(200).copy()
            local_vars: Dict[str, Any] = {"df": sample, "pd": pd, "np": np}
            exec(code, local_vars)
            s = local_vars.get("series")
            if s is not None and hasattr(s, "describe"):
                desc = s.describe()
                preview_stats = {
                    "count": int(desc.get("count", 0)),
                    "mean": round(float(desc.get("mean", 0)), 2) if "mean" in desc.index else None,
                    "min": round(float(desc.get("min", 0)), 2) if "min" in desc.index else None,
                    "max": round(float(desc.get("max", 0)), 2) if "max" in desc.index else None,
                }
        except Exception as exc:
            logger.warning("Column suggestion code failed on sample: %s", exc)

    return {
        "proposed_column": result.get("proposed_column", ""),
        "proposed_filter": result.get("proposed_filter", ""),
        "explanation": result.get("explanation", ""),
        "confidence": "high",
        "code": code,
        "columns": columns,
        "preview_stats": preview_stats,
        "error": None,
    }


def execute_column_extraction(data: Any, code: str) -> pd.Series:
    """Execute AI's extraction code on the full dataset, return a Series."""
    import numpy as np

    df = _to_frame(data)
    local_vars: Dict[str, Any] = {"df": df, "pd": pd, "np": np}
    exec(code, local_vars)
    series = local_vars.get("series")
    if series is None:
        raise ValueError("Code did not produce a 'series' variable.")
    return series
