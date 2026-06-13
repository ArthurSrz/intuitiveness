"""
LLM-powered Enrichment Suggestion for L0→L1 ascent.

AI sees the datum + parent data and suggests how to rebuild
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
    _sys = "You help rebuild data from a single value back into a vector. Write plain language, no jargon. Respond only with JSON."
    kind, client = client_tuple
    if kind == "anthropic":
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=_sys,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text
    else:
        response = client.chat.completions.create(
            model=os.getenv("ENRICHMENT_SUGGEST_MODEL", _CHAT_MODEL),
            messages=[
                {"role": "system", "content": _sys},
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
    """Suggest how to rebuild a vector from the L0 datum."""
    client = _get_chat_client()

    if client is None:
        return {
            "method": "source_expansion",
            "explanation": "Rebuild the full vector from the parent data.",
            "confidence": "heuristic",
            "preview_length": parent_info.get("parent_length", 0),
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
The ascent REVERSES the descent. L0→L1 "amplifies variation along a dimension at the cost of atomic isolation."
The user trades their certainty about one number for seeing how each entity varies — guided by their intent.

## Your Task
The user wants to unfold this single value back into a vector — one number per entity.
This is the "incubation" stage: the user makes unusual connections by seeing individual variation.

Methods available:
- source_expansion: restore the original vector (each entity's raw value)
- normalize: rebuild as percentages relative to the datum (who's above/below average?)
- rank: rebuild as rankings (1st, 2nd, 3rd...)
- distance: rebuild as distance from the datum (how far is each entity from the center?)

Choose the method that best serves the user's INTENT. If they want to compare, use normalize. If they want to find the best/worst, use rank.

Respond in JSON:
{{
  "method": "source_expansion or normalize or rank or distance",
  "explanation": "2-3 sentences in plain language explaining what the user will see and why it helps answer their question.",
  "preview_description": "One sentence describing the rebuilt vector"
}}"""

    try:
        content = _call_llm(client, prompt)
        result = json.loads(content.strip())
    except Exception as exc:
        logger.warning("Enrichment suggestion failed: %s", exc)
        return {
            "method": "source_expansion",
            "explanation": "Rebuild the full vector from the parent data.",
            "confidence": "heuristic",
            "preview_length": parent_info.get("parent_length", 0),
            "error": None,
        }

    return {
        "method": result.get("method", "source_expansion"),
        "explanation": result.get("explanation", ""),
        "confidence": "high",
        "preview_length": parent_info.get("parent_length", 0),
        "preview_description": result.get("preview_description", ""),
        "error": None,
    }
