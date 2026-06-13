"""
LLM-powered Aggregation Suggestion for L1→L0 descent.

AI sees the feature vector profile, suggests the best aggregation method,
and writes Python code to compute the atomic datum.
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
            model=os.getenv("AGGREGATION_SUGGEST_MODEL", _CHAT_MODEL),
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


def _to_series(data: Any) -> pd.Series:
    if isinstance(data, pd.Series):
        return data.copy()
    if isinstance(data, pd.DataFrame):
        return data.iloc[:, 0]
    return pd.Series(data)


def _build_vector_profile(series: pd.Series) -> dict:
    profile: Dict[str, Any] = {
        "name": series.name or "value",
        "dtype": str(series.dtype),
        "length": len(series),
        "non_null": int(series.notna().sum()),
        "unique_count": int(series.nunique()),
    }
    if pd.api.types.is_numeric_dtype(series) and series.notna().any():
        profile["min"] = round(float(series.min()), 2)
        profile["max"] = round(float(series.max()), 2)
        profile["mean"] = round(float(series.mean()), 2)
        profile["median"] = round(float(series.median()), 2)
        profile["sum"] = round(float(series.sum()), 2)
        profile["std"] = round(float(series.std()), 2)
    vals = series.dropna().unique()[:8]
    profile["samples"] = [str(v) for v in vals]
    return profile


def suggest_aggregation(data: Any, intent: str = "") -> Dict[str, Any]:
    """Analyze L1 vector and suggest how to compress it to a single datum."""
    series = _to_series(data)
    if series.empty:
        return {"error": "Empty vector", "proposed_aggregation": "mean", "columns": []}

    client = _get_chat_client()
    profile = _build_vector_profile(series)

    if client is None:
        agg = "mean" if pd.api.types.is_numeric_dtype(series) else "count"
        try:
            import numpy as np
            local_vars: Dict[str, Any] = {"series": series, "pd": pd, "np": np}
            val = float(series.mean()) if agg == "mean" else int(series.count())
        except Exception:
            val = None
        return {
            "proposed_aggregation": agg,
            "explanation": f"Auto-selected '{agg}' for the '{profile['name']}' vector.",
            "confidence": "heuristic",
            "code": f"datum = series.{agg}()",
            "preview_value": round(val, 2) if val is not None else None,
            "vector_profile": profile,
            "error": None,
        }

    prompt = f"""You are a data analyst. You have a feature vector (one value per entity):

{json.dumps(profile, indent=2, default=str)}

## User's Analysis Intent
{intent if intent else "Not specified — choose the most meaningful aggregation."}

## Your Task
The user wants to compress this vector into a SINGLE atomic value — the core datum. Orient your choice toward their intent above.
This is the final step of data reduction: from many values to one truth.

1. Choose the best aggregation that captures the essence of this vector.
   Options include mean, median, sum, count, min, max, std, or a custom computation.
2. Write Python code that computes a single value called `datum` from a pandas Series called `series`.
   You have access to `pd` (pandas) and `np` (numpy).

Examples:
- `datum = series.mean()`
- `datum = series.median()`
- `datum = float(series.sum()) / series.count()`
- `datum = np.percentile(series.dropna(), 75)`

Respond in JSON:
{{
  "proposed_aggregation": "name of the aggregation (e.g. mean, median, weighted average)",
  "code": "Python code that creates a `datum` variable from `series`",
  "explanation": "2-3 sentences explaining why this aggregation best captures the essence of the data."
}}"""

    try:
        content = _call_llm(client, prompt)
        result = json.loads(content.strip())
    except Exception as exc:
        logger.warning("Aggregation suggestion LLM call failed: %s", exc)
        return {
            "proposed_aggregation": "mean",
            "explanation": "LLM unavailable. Defaulting to mean.",
            "confidence": "heuristic",
            "code": "datum = series.mean()",
            "preview_value": round(float(series.mean()), 2) if series.notna().any() else None,
            "vector_profile": profile,
            "error": None,
        }

    # Run code to compute preview value
    code = result.get("code", "datum = series.mean()")
    preview_value = None
    try:
        import numpy as np
        local_vars = {"series": series, "pd": pd, "np": np}
        exec(code, local_vars)
        datum = local_vars.get("datum")
        if datum is not None:
            preview_value = round(float(datum), 2)
    except Exception as exc:
        logger.warning("Aggregation code failed: %s", exc)

    return {
        "proposed_aggregation": result.get("proposed_aggregation", "mean"),
        "explanation": result.get("explanation", ""),
        "confidence": "high",
        "code": code,
        "preview_value": preview_value,
        "vector_profile": profile,
        "error": None,
    }


def execute_aggregation(data: Any, code: str) -> float:
    """Execute AI's aggregation code on the full vector."""
    import numpy as np

    series = _to_series(data)
    local_vars: Dict[str, Any] = {"series": series, "pd": pd, "np": np}
    exec(code, local_vars)
    datum = local_vars.get("datum")
    if datum is None:
        raise ValueError("Code did not produce a 'datum' variable.")
    return float(datum)
