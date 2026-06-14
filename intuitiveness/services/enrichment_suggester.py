"""
LLM-powered Enrichment Code for L0→L1 ascent.

"Amplifies variation along a dimension at the cost of atomic isolation."
AI sees the datum + parent data and writes Python code that rebuilds
the vector with purpose, guided by the user's intent.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

import pandas as pd

from intuitiveness.services.llm_client import call_llm

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = """You are a Python data analyst. You write pandas code to rebuild a vector from a single datum value.

RULES:
1. You receive `scalar` (a single numeric value — the L0 datum) and `parent_series` (a pd.Series of the original L1 data).
2. Your code MUST produce a variable called `series` (a pd.Series).
3. You have `scalar`, `parent_series`, `pd`, and `np` available.
4. Respond ONLY with valid JSON, no markdown."""


def suggest_enrichment(datum_value: Any, parent_info: Dict[str, Any], intent: str = "") -> Dict[str, Any]:
    """AI writes code to rebuild a vector from the L0 datum for L0->L1 ascent."""
    prompt = f"""A user reduced their data to a single value and now wants to rebuild it with purpose.

## The Datum
Value: {datum_value}
How it was computed: {parent_info.get('aggregation_method', 'unknown')}
Original column: {parent_info.get('parent_name', 'unknown')}
Number of entities: {parent_info.get('parent_length', 'unknown')}

## User's Intent
{intent if intent else "Not specified — suggest the most useful way to rebuild."}

## What's happening (from the paper)
The ascent REVERSES the descent. L0->L1 "amplifies variation along a dimension at the cost of atomic isolation."
The user trades their certainty about one number for seeing how each entity varies — guided by their intent.

## Your Task
Write Python code that produces a variable `series` (a pd.Series) from `scalar` (the L0 value) and `parent_series` (the original L1 data).
This is the "incubation" stage: the user makes unusual connections by seeing individual variation.

You have `scalar`, `parent_series`, `pd`, and `np`. The code runs via exec().

Examples of what the code could do:
- Source expansion (restore the original vector): `series = parent_series.copy()`
- Normalize (percentages relative to the datum): `series = parent_series / scalar * 100`
- Rank (1st, 2nd, 3rd...): `series = parent_series.rank(ascending=False)`
- Distance (how far from the center): `series = (parent_series - scalar).abs()`

Choose the approach that best serves the user's INTENT. If they want to compare, use normalize. If they want to find the best/worst, use rank.

Respond in JSON:
{{
  "code": "Python code that produces a `series` variable",
  "explanation": "2-3 sentences in plain language explaining what the user will see and why it helps answer their question.",
  "preview_description": "One sentence describing the rebuilt vector"
}}"""

    try:
        content = call_llm(_SYSTEM_PROMPT, prompt, model_env_var="ENRICHMENT_SUGGEST_MODEL")
        result = json.loads(content.strip())
    except (RuntimeError, Exception) as exc:
        logger.warning("Enrichment suggestion failed: %s", exc)
        return {
            "code": "series = parent_series.copy()",
            "explanation": "Rebuild the full vector from the parent data.",
            "confidence": "heuristic",
            "preview_description": "Restoring the original vector as-is.",
            "error": None,
        }

    return {
        "code": result.get("code", "series = parent_series.copy()"),
        "explanation": result.get("explanation", ""),
        "confidence": "high",
        "preview_description": result.get("preview_description", ""),
        "error": None,
    }


def execute_enrichment_code(scalar: Any, parent_series: pd.Series, code: str) -> pd.Series:
    """Execute AI's enrichment code on the real data."""
    import numpy as np

    logger.warning("EXECUTE-ENRICHMENT: scalar=%s parent_series len=%d code=%s",
                   scalar, len(parent_series), code[:200])

    namespace = {
        "scalar": scalar,
        "parent_series": parent_series.copy(),
        "pd": pd,
        "np": np,
    }

    try:
        exec(code, namespace)
    except Exception as exec_exc:
        logger.warning("EXECUTE-ENRICHMENT: exec FAILED: %s", exec_exc, exc_info=True)
        raise

    series = namespace.get("series")
    if series is None:
        raise ValueError("Code did not produce a `series` variable.")
    if not isinstance(series, pd.Series):
        series = pd.Series(series)

    return series
