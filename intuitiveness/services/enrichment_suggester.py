"""
LLM-powered Enrichment Code for L0→L1 ascent.

"Amplifies variation along a dimension at the cost of atomic isolation."
AI sees the datum + parent data and writes Python code that rebuilds
the vector with purpose, guided by the user's intent.
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
    # OpenRouter first (preferred), then Anthropic as fallback
    or_key = os.getenv("OPENROUTER_API_KEY")
    if or_key:
        try:
            from openai import OpenAI
            return ("openai", OpenAI(
                api_key=or_key,
                base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            ))
        except ImportError:
            pass
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            import anthropic
            return ("anthropic", anthropic.Anthropic(api_key=anthropic_key))
        except ImportError:
            pass
    api_key = os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY")
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


_SYSTEM_PROMPT = """You are a Python data analyst. You write pandas code to rebuild a vector from a single datum value.

RULES:
1. You receive `scalar` (a single numeric value — the L0 datum) and `parent_series` (a pd.Series of the original L1 data).
2. Your code MUST produce a variable called `series` (a pd.Series).
3. You have `scalar`, `parent_series`, `pd`, and `np` available.
4. Respond ONLY with valid JSON, no markdown."""


def _call_llm(client_tuple, prompt: str) -> str:
    kind, client = client_tuple
    if kind == "anthropic":
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text
    else:
        response = client.chat.completions.create(
            model=os.getenv("ENRICHMENT_SUGGEST_MODEL", _CHAT_MODEL),
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
    if "```json" in content:
        content = content.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in content:
        content = content.split("```", 1)[1].split("```", 1)[0]
    return content


def suggest_enrichment(datum_value: Any, parent_info: Dict[str, Any], intent: str = "") -> Dict[str, Any]:
    """AI writes code to rebuild a vector from the L0 datum for L0->L1 ascent."""
    client = _get_chat_client()

    if client is None:
        return {
            "code": "series = parent_series.copy()",
            "explanation": "Rebuild the full vector from the parent data.",
            "confidence": "heuristic",
            "preview_description": "Restoring the original vector as-is.",
            "error": None,
        }

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
        content = _call_llm(client, prompt)
        result = json.loads(content.strip())
    except Exception as exc:
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
