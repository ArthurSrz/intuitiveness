"""
LLM-powered Linkage Suggestion for L2→L3 ascent.

"Amplifies inter-domain linkage at the cost of domain isolation."
AI suggests which relationships and dimensions to add to link
the domain table back into a knowledge graph.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List

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
    _sys = "You help users link their data to other domains. Write plain language, no jargon. Respond only with JSON."
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
            model=os.getenv("LINKAGE_SUGGEST_MODEL", _CHAT_MODEL),
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


def _sample_values(df: pd.DataFrame, col: str, n: int = 5) -> list:
    vals = df[col].dropna().unique()[:n]
    return [str(v) for v in vals]


def suggest_linkage(
    table_info: Dict[str, Any],
    available_dimensions: List[str],
    intent: str = "",
) -> Dict[str, Any]:
    """Suggest how to link the L2 table into an L3 graph."""
    client = _get_chat_client()

    if client is None:
        return {
            "proposed_dimensions": available_dimensions[:2] if available_dimensions else [],
            "proposed_relationships": [],
            "explanation": "Link the table to other domains to test your insight.",
            "confidence": "heuristic",
            "available_dimensions": available_dimensions,
            "error": None,
        }

    prompt = f"""A user has a categorized table and wants to link it to other data domains.

## The Table
Columns: {json.dumps(table_info.get('columns', []))}
Rows: {table_info.get('row_count', 'unknown')}
Categories: {json.dumps(table_info.get('categories', []))}

## Available Dimensions to Add
{json.dumps(available_dimensions, indent=2) if available_dimensions else "No pre-registered dimensions. Suggest what external data would strengthen the analysis."}

## User's Intent
{intent if intent else "Not specified — suggest the most useful linkages."}

## What's happening (from the paper)
L2→L3 "amplifies inter-domain linkage at the cost of domain isolation."
The user trades focus on one coherent domain for connecting to OTHER domains.
This is the "evaluation" stage: putting the insight on trial by bringing in external evidence.

For example, if the user found that some schools perform better, L2→L3 would link school performance
to school size, location, or funding — testing WHETHER the pattern holds against other variables.

## Your Task
Suggest 1-3 dimensions or relationships to add. These should help the user TEST their insight
by connecting to a different data domain.

Respond in JSON:
{{
  "proposed_dimensions": ["dimension1", "dimension2"],
  "proposed_relationships": ["relationship between entities"],
  "explanation": "2-3 sentences explaining how this linkage helps test the user's insight.",
  "graph_description": "What the resulting knowledge graph will show"
}}"""

    try:
        content = _call_llm(client, prompt)
        result = json.loads(content.strip())
    except Exception as exc:
        logger.warning("Linkage suggestion failed: %s", exc)
        return {
            "proposed_dimensions": available_dimensions[:2] if available_dimensions else [],
            "proposed_relationships": [],
            "explanation": "Link to other domains to test your insight.",
            "confidence": "heuristic",
            "available_dimensions": available_dimensions,
            "error": None,
        }

    return {
        "proposed_dimensions": result.get("proposed_dimensions", []),
        "proposed_relationships": result.get("proposed_relationships", []),
        "explanation": result.get("explanation", ""),
        "confidence": "high",
        "graph_description": result.get("graph_description", ""),
        "available_dimensions": available_dimensions,
        "error": None,
    }
