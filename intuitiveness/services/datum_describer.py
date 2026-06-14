"""
LLM-powered Datum Description for L0.

AI sees the datum value + descent context and writes a human-readable
explanation of what the number means.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from intuitiveness.services.llm_client import call_llm

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = "You explain data insights in plain language. Be concise, specific, and helpful. No jargon."


def describe_datum(context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a human-readable description of the L0 datum."""
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
        content = call_llm(_SYSTEM_PROMPT, prompt, model_env_var="DATUM_DESCRIBE_MODEL")
        result = json.loads(content.strip())
        return {
            "title": result.get("title", ""),
            "description": result.get("description", ""),
            "error": None,
        }
    except (RuntimeError, Exception) as exc:
        logger.warning("Datum description failed: %s", exc)
        return {
            "title": f"{context.get('aggregation', 'Value')}: {context.get('value', '?')}",
            "description": "This is the atomic value at the bottom of the descent.",
            "error": None,
        }
