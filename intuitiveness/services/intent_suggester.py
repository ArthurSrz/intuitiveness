"""
LLM-powered Intent Suggestion for the L0 pivot.

AI sees the descent path (what data was reduced to what datum) and proposes
analytical questions the user could answer by rebuilding the data with intent.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List

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
    _sys = "You write questions like a normal person — a teacher, parent, or school principal. Never use data science jargon. Respond only with JSON."
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
            model=os.getenv("INTENT_SUGGEST_MODEL", _CHAT_MODEL),
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


def suggest_intents(descent_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Propose analytical intents based on the descent path."""
    client = _get_chat_client()

    if client is None:
        return {
            "intents": [
                {"question": "Which groups have the highest values?", "short": "Top groups"},
                {"question": "Are there regional differences?", "short": "Regional differences"},
                {"question": "How does this compare over time?", "short": "Trends over time"},
            ],
            "error": None,
        }

    prompt = f"""A user has been exploring a dataset and reduced it to a single number.

## What they found
{json.dumps(descent_summary, indent=2, default=str)}

## Your Task
Suggest 3-4 questions this person might want to answer NEXT by rebuilding the data with a purpose.

CRITICAL RULES:
- Write questions like a NORMAL PERSON curious about THIS data — not like a data scientist.
- Use the actual column names, values, and descriptions from the descent summary to make questions SPECIFIC.
- NO jargon: no "correlate", "factor", "dimension", "categorical", "predictive".
- The short label should be plain: "By region", "Over time", not "Factor Analysis".
- Questions should be answerable by adding groups or comparisons to the data.

Respond in JSON:
{{
  "intents": [
    {{"question": "A question a normal person would ask about this data", "short": "plain 3-5 word label"}},
    {{"question": "...", "short": "..."}},
    {{"question": "...", "short": "..."}}
  ]
}}"""

    try:
        content = _call_llm(client, prompt)
        result = json.loads(content.strip())
        return {"intents": result.get("intents", []), "error": None}
    except Exception as exc:
        logger.warning("Intent suggestion failed: %s", exc)
        return {
            "intents": [
                {"question": "Which groups have the highest values?", "short": "Top groups"},
                {"question": "Are there regional differences?", "short": "Regional differences"},
                {"question": "How does this compare over time?", "short": "Trends over time"},
            ],
            "error": None,
        }
