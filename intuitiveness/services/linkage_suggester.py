"""
LLM-powered Linkage Code for L2->L3 ascent.

"Amplifies inter-domain linkage at the cost of domain isolation."
AI sees the L2 table + user intent, writes Python code that adds
linkage columns to connect domains in the evaluation stage.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

import pandas as pd

from intuitiveness.services.llm_client import call_llm_structured
from intuitiveness.services.transition_models import LinkageSuggestion

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = """You are a Python data analyst. You write pandas code to add linkage columns that connect a domain table to other domains.

RULES:
1. You receive a DataFrame `df` (the L2 categorized table). It has various columns including a 'value' column and category columns.
2. Your code MUST produce a variable `linked_df` that is a copy of `df` with new columns added.
3. Start with `linked_df = df.copy()`.
4. Add columns that create cross-domain linkages: computed ratios, derived categories, rank-based groupings, interaction terms between existing columns.
5. ALWAYS end categorical columns with .fillna('uncategorized').astype(str).
6. You have `df`, `pd`, and `np` available. The code runs via exec().
7. Respond ONLY with valid JSON, no markdown.

CRITICAL NAMING RULES — the user is non-technical:
8. Column names MUST be plain, descriptive English (or match the user's language). Use names like 'price_level', 'size_group', 'above_average', 'share_of_total'.
9. NEVER use abstract business jargon like 'client_segment', 'financial_view', 'segment_performance_ratio', 'cross_domain_tier', 'quartile_segment_interaction'.
10. Each new column name should clearly describe WHAT it measures. A non-programmer should understand the column name without explanation.
11. ONLY derive columns from data that actually exists in df. Never invent data that is not present. If the user asks to link to external data (e.g., World Bank indicators), explain in the explanation field that external data must be imported first — do NOT fabricate columns to simulate it."""


def _sample_values(df: pd.DataFrame, col: str, n: int = 5) -> list:
    vals = df[col].dropna().unique()[:n]
    return [str(v) for v in vals]


def suggest_linkage(
    table_info: Dict[str, Any],
    available_dimensions: List[str],
    intent: str = "",
    sibling_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Ask the LLM for executable Python code to link the L2 table for L2->L3 ascent.

    When sibling_context is provided (from session.get_ascent_context()),
    the LLM can reconnect columns from the original L3 graph — e.g. life
    expectancy data that was dropped during the L2→L1 feature projection.
    """
    client = _get_chat_client()

    has_siblings = sibling_context and sibling_context.get("sibling_columns")

    if client is None:
        if has_siblings:
            sibling_cols = sibling_context["sibling_columns"]
            join_code = "linked_df = df.merge(sibling_df, left_index=True, right_index=True, how='left')"
            return {
                "code": join_code,
                "proposed_columns": sibling_cols,
                "explanation": f"Reconnected columns from the original linked data: {', '.join(sibling_cols)}.",
                "graph_description": "Your table enriched with the related data from the original dataset.",
                "confidence": "heuristic",
                "error": None,
            }
        return {
            "code": "linked_df = df.copy()\nlinked_df['linkage_group'] = np.where(linked_df['value'] > linked_df['value'].median(), 'above average', 'below average')",
            "proposed_columns": ["value_level"],
            "explanation": "Split values into above/below average groups based on the median.",
            "graph_description": "Your table with an additional column showing whether each value is above or below the average.",
            "confidence": "heuristic",
            "error": None,
        }

    columns_info = json.dumps(table_info.get("columns", []))
    categories_info = json.dumps(table_info.get("categories", []))
    dtypes_info = json.dumps(table_info.get("dtypes", {}))

    sibling_section = ""
    if has_siblings:
        sib_cols = sibling_context["sibling_columns"]
        l3_cols = sibling_context.get("l3_columns", [])
        sibling_section = f"""
## Related data available (from the original linked dataset)
You also have access to a DataFrame called `sibling_df` which contains columns from the original linked data that were dropped during simplification.
Sibling columns: {json.dumps(sib_cols)}
Original L3 columns: {json.dumps(l3_cols)}

PRIORITY: If sibling_df contains related variables (e.g. life expectancy alongside GDP, or population alongside income),
your FIRST action should be to merge those columns back into the table. This reconnects the data the user originally linked.
Use: `linked_df = df.merge(sibling_df[relevant_cols], left_index=True, right_index=True, how='left')` or join on shared keys.
THEN add computed columns (ratios, correlations, ranks) that leverage BOTH the current and sibling data.
"""

    prompt = f"""A user has a categorized table (L2) and wants to add computed columns that help evaluate their insight from different angles.

## The Table
Columns: {columns_info}
Column types: {dtypes_info}
Rows: {table_info.get('row_count', 'unknown')}
Categories: {categories_info}

IMPORTANT: Only use numeric operations (mean, sum, rank, qcut) on NUMERIC columns (int64, float64).
String/object columns can only be used for groupby keys, value_counts, or categorical mapping — NEVER for arithmetic.
{sibling_section}
## User's Intent
{intent if intent else "Not specified -- suggest the most useful computed columns."}

## What's happening
The user has grouped their data and now wants to evaluate their insight by looking at it from additional angles.
{"If sibling_df is available, RECONNECT those columns first — they contain related data the user originally loaded." if has_siblings else ""}

## Your Task
Write Python code that:
1. Starts with `linked_df = df.copy()`
{"2. Merge relevant sibling columns from sibling_df back into linked_df" if has_siblings else ""}
{"3" if has_siblings else "2"}. Adds new columns to `linked_df` computed from {"existing + sibling" if has_siblings else "existing"} data

NAMING: Use plain, descriptive names that a non-technical user would understand:
- Good: 'rank', 'share_of_total', 'above_average', 'life_expectancy', 'gdp_per_capita'
- Bad: 'cross_domain_tier', 'segment_performance_ratio', 'quartile_segment_interaction'

Example:
```
linked_df = df.copy()
linked_df['rank'] = linked_df['value'].rank(ascending=False).astype(int)
linked_df['share_of_total'] = (linked_df['value'] / linked_df['value'].sum() * 100).round(1)
linked_df['level'] = pd.qcut(linked_df['value'], q=3, labels=['low', 'medium', 'high'], duplicates='drop').fillna('uncategorized').astype(str)
```

Respond in JSON:
{{
  "code": "Python code that creates linked_df from df",
  "proposed_columns": ["names of new columns added"],
  "explanation": "2-3 sentences in plain language explaining what each new column shows and how it helps answer the user's question. If the user asked for external data, mention that they need to import it first.",
  "graph_description": "What the resulting table will show"
}}"""

    try:
        suggestion = call_llm_structured(_SYSTEM_PROMPT, prompt, LinkageSuggestion, model_env_var="LINKAGE_SUGGEST_MODEL")
    except RuntimeError:
        return {
            "code": "linked_df = df.copy()\nlinked_df['linkage_group'] = np.where(linked_df['value'] > linked_df['value'].median(), 'above average', 'below average')",
            "proposed_columns": ["value_level"],
            "explanation": "Split values into above/below average groups based on the median.",
            "graph_description": "Your table with an additional column showing whether each value is above or below the average.",
            "confidence": "heuristic",
            "error": None,
        }
    except Exception as exc:
        logger.warning("Linkage suggestion failed: %s", exc)
        return {
            "code": "linked_df = df.copy()\nlinked_df['linkage_group'] = np.where(linked_df['value'] > linked_df['value'].median(), 'above average', 'below average')",
            "proposed_columns": ["value_level"],
            "explanation": "Split values into above/below average groups based on the median.",
            "graph_description": "Your table with an additional column showing whether each value is above or below the average.",
            "confidence": "heuristic",
            "error": None,
        }

    return {
        "code": suggestion.code,
        "proposed_columns": suggestion.proposed_columns,
        "explanation": suggestion.explanation,
        "graph_description": suggestion.graph_description,
        "confidence": "high",
        "error": None,
    }


def execute_linkage_code(
    df: pd.DataFrame,
    code: str,
    sibling_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Execute AI's linkage code on the L2 DataFrame.

    When sibling_df is provided, it is injected into the exec namespace
    so the LLM-generated code can merge columns from the original L3 data.
    """
    import numpy as np

    logger.warning("EXECUTE-LINKAGE: df shape=%s columns=%s", df.shape, list(df.columns))
    if sibling_df is not None:
        logger.warning("EXECUTE-LINKAGE: sibling_df shape=%s columns=%s", sibling_df.shape, list(sibling_df.columns))
    logger.warning("EXECUTE-LINKAGE: code (first 400):\n%s", code[:400])

    namespace = {"df": df, "pd": pd, "np": np}
    if sibling_df is not None:
        namespace["sibling_df"] = sibling_df
    exec(code, namespace)

    linked_df = namespace.get("linked_df")
    if linked_df is None:
        raise ValueError("Code did not produce a 'linked_df' variable.")
    if not isinstance(linked_df, pd.DataFrame):
        raise ValueError(f"'linked_df' is not a DataFrame, got {type(linked_df).__name__}.")

    logger.warning("EXECUTE-LINKAGE: linked_df shape=%s columns=%s", linked_df.shape, list(linked_df.columns))

    # Clean up new categorical columns
    original_cols = set(df.columns)
    for col in linked_df.columns:
        if col in original_cols:
            continue
        s = linked_df[col]
        if s.dtype == object or hasattr(s, "cat"):
            try:
                if hasattr(s, "cat"):
                    if "uncategorized" not in s.cat.categories:
                        s = s.cat.add_categories("uncategorized")
                    linked_df[col] = s.fillna("uncategorized").astype(str)
                else:
                    linked_df[col] = s.fillna("uncategorized").astype(str)
            except Exception:
                linked_df[col] = linked_df[col].astype(str).replace("nan", "uncategorized")

    return linked_df
