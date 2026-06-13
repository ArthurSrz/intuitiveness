"""
LLM-powered Datum Description for L0.

AI sees the datum value + descent context and writes a human-readable
explanation of what the number means.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

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
            max_tokens=512,
            system="You explain data insights in plain language. Be concise, specific, and helpful. No jargon.",
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text
    else:
        response = client.chat.completions.create(
            model=os.getenv("DATUM_DESCRIBE_MODEL", _CHAT_MODEL),
            messages=[
                {"role": "system", "content": "You explain data insights in plain language. Be concise, specific, and helpful. No jargon."},
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


def describe_datum(context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a human-readable description of the L0 datum."""
    client = _get_chat_client()

    if client is None:
        return {
            "title": f"{context.get('aggregation', 'Value')}: {context.get('value', '?')}",
            "description": "This is the atomic value at the bottom of the descent.",
            "error": None,
        }

    prompt = f"""A user just completed a data descent and reached a single atomic value:

Value: {context.get('value')}
Aggregation method: {context.get('aggregation', 'unknown')}
Column extracted: {context.get('column_name', 'unknown')}
Categories used: {context.get('categories', 'unknown')}
Dataset description: {context.get('dataset_description', 'unknown')}
Number of entities: {context.get('entity_count', 'unknown')}

Explain this number to the user in 2-3 sentences:
- What does this number represent concretely?
- Is it high, low, or average for this kind of data?
- What does it tell us at a glance?

Also give a short title (5-8 words) that names this datum meaningfully.

Respond in JSON:
{{
  "title": "Short meaningful title for this datum",
  "description": "2-3 sentence explanation in plain language"
}}"""

    try:
        content = _call_llm(client, prompt)
        result = json.loads(content.strip())
        return {
            "title": result.get("title", ""),
            "description": result.get("description", ""),
            "error": None,
        }
    except Exception as exc:
        logger.warning("Datum description failed: %s", exc)
        return {
            "title": f"{context.get('aggregation', 'Value')}: {context.get('value', '?')}",
            "description": "This is the atomic value at the bottom of the descent.",
            "error": None,
        }
