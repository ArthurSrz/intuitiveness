"""
LLM-powered Intent Suggestion for the L0 pivot.

AI sees the descent path (what data was reduced to what datum) and proposes
analytical questions the user could answer by rebuilding the data with intent.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from intuitiveness.services.llm_client import call_llm_structured
from intuitiveness.services.transition_models import IntentSuggestion

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = "You write questions like a normal person — a teacher, parent, or school principal. Never use data science jargon. Respond only with JSON."


def suggest_intents(descent_story: Dict[str, Any]) -> Dict[str, Any]:
    """Propose analytical intents based on the full descent path."""
    steps = descent_story.get("steps", [])

    # Build a human-readable narrative of what happened at each level
    level_descriptions = []
    for step in steps:
        lvl = step.get("level")
        if lvl == 4:
            sources = step.get("sources", {})
            names = list(sources.keys())
            level_descriptions.append(f"L4 (raw data): uploaded {len(names)} source(s): {', '.join(names)}. " +
                "; ".join(f"{n}: {s.get('rows',0)} rows, columns {s.get('columns',[])}" for n, s in sources.items()))
        elif lvl == 3:
            cols = step.get("columns", [])
            nodes = step.get("node_count")
            if nodes:
                level_descriptions.append(f"L3 (knowledge graph): {nodes} nodes, {step.get('edge_count',0)} edges")
            elif cols:
                level_descriptions.append(f"L3 (linked table): columns {cols}")
        elif lvl == 2:
            cats = step.get("categories", [])
            cols = step.get("columns", [])
            desc = f"L2 (categorized table): {step.get('row_count',0)} rows, columns {cols}"
            if cats:
                desc += f", categories: {cats}"
            level_descriptions.append(desc)
        elif lvl == 1:
            stats = step.get("stats", {})
            name = step.get("name", "value")
            level_descriptions.append(f"L1 (vector): extracted '{name}' — " +
                f"count={stats.get('count')}, min={stats.get('min')}, max={stats.get('max')}, mean={stats.get('mean')}")
        elif lvl == 0:
            level_descriptions.append(f"L0 (datum): {step.get('description', '')} = {step.get('value')}, " +
                f"aggregation: {step.get('aggregation', 'unknown')}")

    descent_narrative = "\n".join(f"  Step {i+1}. {d}" for i, d in enumerate(level_descriptions))

    # Collect decisions made at each step
    decisions = [s.get("decision", "") for s in steps if s.get("decision")]
    decisions_text = "\n".join(f"  - {d}" for d in decisions) if decisions else "  (no decisions recorded)"

    prompt = f"""A user explored a dataset step by step, reducing it from raw data to a single number.

## The full descent path
{descent_narrative}

## Decisions they made along the way
{decisions_text}

## Your task
Suggest 3-4 questions this person might want to answer NEXT by rebuilding the data with a specific purpose.

CRITICAL RULES:
- Use the ACTUAL column names, category names, source names, and values from the descent path above.
- Write questions like a NORMAL PERSON curious about THIS specific data — a teacher, a mayor, a journalist.
- NO jargon: no "correlate", "factor", "dimension", "categorical", "predictive", "distribution".
- Each question should reference something concrete from the descent: a category, a source, a column.
- The short label should be plain: "By school size", "Urban vs rural", not "Factor Analysis"."""

    try:
        suggestion = call_llm_structured(_SYSTEM_PROMPT, prompt, IntentSuggestion, model_env_var="INTENT_SUGGEST_MODEL")
        return {"intents": suggestion.intents, "error": None}
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
