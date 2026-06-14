"""
LLM-powered Intent Suggestion for the L0 pivot.

AI sees the descent path (what data was reduced to what datum) and proposes
analytical questions the user could answer by rebuilding the data with intent.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from intuitiveness.services.llm_client import call_llm

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = "You write questions like a normal person — a teacher, parent, or school principal. Never use data science jargon. Respond only with JSON."


def suggest_intents(descent_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Propose analytical intents based on the descent path."""
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
        content = call_llm(_SYSTEM_PROMPT, prompt, model_env_var="INTENT_SUGGEST_MODEL")
        result = json.loads(content.strip())
        return {"intents": result.get("intents", []), "error": None}
    except (RuntimeError, Exception) as exc:
        logger.warning("Intent suggestion failed: %s", exc)
        return {
            "intents": [
                {"question": "Which groups have the highest values?", "short": "Top groups"},
                {"question": "Are there regional differences?", "short": "Regional differences"},
                {"question": "How does this compare over time?", "short": "Trends over time"},
            ],
            "error": None,
        }
