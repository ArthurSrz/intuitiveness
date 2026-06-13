"""
LLM-powered Dimension Code for L1→L2 ascent.

"Amplifies attribute coverage at the cost of feature isolation."
AI sees the vector + user intent, writes Python code that adds
categorical columns to create a table for group comparison.
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


_SYSTEM_PROMPT = """You are a Python data analyst. You write pandas code to add categorical dimensions to a feature vector.

RULES:
1. You receive a DataFrame `df` with a 'value' column (numeric) and an index (entity names/IDs).
2. Your code MUST add one or more new columns to `df` that create meaningful groups.
3. ALWAYS end categorical columns with .fillna('uncategorized').astype(str).
4. Use pd.qcut for equal-count bins, np.where for threshold splits.
5. The df index may contain entity names — use them if relevant to the user's intent.
6. Respond ONLY with valid JSON, no markdown."""


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
            model=os.getenv("DIMENSION_SUGGEST_MODEL", _CHAT_MODEL),
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
    if "```json" in content:
        content = content.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in content:
        content = content.split("```", 1)[1].split("```", 1)[0]
    return content


def _sample_index(series: pd.Series, n: int = 10) -> list:
    idx = series.index[:n]
    return [str(i) for i in idx]


def _sample_values(series: pd.Series, n: int = 10) -> list:
    vals = series.dropna()[:n]
    return [str(v) for v in vals]


def suggest_dimensions(vector_info: Dict[str, Any], intent: str = "") -> Dict[str, Any]:
    """AI writes code to add dimensions to a vector for L1→L2 ascent."""
    logger.warning("DIMENSION-SUGGEST START: intent=%r vector_name=%r length=%s min=%s max=%s mean=%s",
                   intent, vector_info.get("name"), vector_info.get("length"),
                   vector_info.get("min"), vector_info.get("max"), vector_info.get("mean"))
    logger.warning("DIMENSION-SUGGEST sample_index=%s sample_values=%s",
                   vector_info.get("sample_index"), vector_info.get("sample_values"))

    client = _get_chat_client()
    logger.warning("DIMENSION-SUGGEST client=%s", "None (no API key)" if client is None else client[0])

    if client is None:
        logger.warning("DIMENSION-SUGGEST: no API key — returning heuristic fallback")
        return {
            "explanation": "Split values into above/below median.",
            "confidence": "heuristic",
            "code": "df['category'] = np.where(df['value'] > df['value'].median(), 'above median', 'below median').astype(str)",
            "proposed_columns": ["category"],
            "sample_distribution": {},
            "error": None,
        }

    prompt = f"""A user has a feature vector and wants to add categorical dimensions for group comparison.

## The Vector
Name: {vector_info.get('name', 'value')}
Length: {vector_info.get('length', '?')} entities
Min: {vector_info.get('min', '?')}, Max: {vector_info.get('max', '?')}, Mean: {vector_info.get('mean', '?')}
Sample entity names (index): {json.dumps(vector_info.get('sample_index', []))}
Sample values: {json.dumps(vector_info.get('sample_values', []))}

## User's Intent
{intent if intent else "Not specified — suggest the most useful dimension to compare groups."}

## What's happening (from the paper)
L1→L2 "amplifies attribute coverage at the cost of feature isolation."
The user trades seeing one clean variable for seeing it SPLIT across meaningful groups.
This is the "insight" stage: putting pieces together by comparing groups.

## Your Task
Write Python code that adds one or more categorical columns to `df` (a DataFrame with column 'value' and entity names as index).
The code should create groups that help the user answer their question.

You have `df`, `pd`, and `np`. The code runs via exec().

Example:
```
df['category'] = np.where(df['value'] > df['value'].median(), 'above median', 'below median')
df['category'] = df['category'].fillna('uncategorized').astype(str)
```

Respond in JSON:
{{
  "code": "Python code that adds columns to df",
  "proposed_columns": ["names of new columns added"],
  "explanation": "2-3 sentences explaining how these dimensions help answer the user's question."
}}"""

    logger.warning("DIMENSION-SUGGEST: sending prompt to LLM (len=%d)", len(prompt))
    try:
        content = _call_llm(client, prompt)
        logger.warning("DIMENSION-SUGGEST LLM raw response (first 500): %s", content[:500])
        result = json.loads(content.strip())
        logger.warning("DIMENSION-SUGGEST parsed result keys=%s proposed_columns=%s",
                       list(result.keys()), result.get("proposed_columns"))
    except Exception as exc:
        logger.warning("DIMENSION-SUGGEST LLM failed: %s", exc, exc_info=True)
        return {
            "explanation": "Split values into above/below median.",
            "confidence": "heuristic",
            "code": "df['category'] = np.where(df['value'] > df['value'].median(), 'above median', 'below median')",
            "proposed_columns": ["category"],
            "sample_distribution": {},
            "error": None,
        }

    # Run code on sample to preview
    code = result.get("code", "")
    logger.warning("DIMENSION LLM_CODE: %s", code[:300])
    dist = {}
    if code:
        try:
            import numpy as np
            sample_df = pd.DataFrame({"value": range(10)})
            # We can't preview without real data — dist stays empty
            # The router will run it on real data
        except Exception:
            pass

    return {
        "explanation": result.get("explanation", ""),
        "confidence": "high",
        "code": code,
        "proposed_columns": result.get("proposed_columns", []),
        "sample_distribution": dist,
        "error": None,
    }


def _find_matching_paren(code: str, start: int) -> int:
    """Return index just past the closing ')' that matches the '(' at start-1."""
    depth = 1
    i = start
    while i < len(code) and depth > 0:
        if code[i] == "(":
            depth += 1
        elif code[i] == ")":
            depth -= 1
        i += 1
    return i  # points one past the closing ')'


def _sanitize_dimension_code(code: str) -> str:
    """Rewrite pd.qcut chains so .fillna() is never called on the raw qcut return value.

    pd.qcut can return a numpy ndarray (not a Categorical) when bin edges
    duplicate even with duplicates='drop'. Splitting the assignment into two
    lines ensures .fillna() runs on the Series (which always has the method).

    Before: df['col'] = pd.qcut(...).fillna('uncategorized').astype(str)
    After:
        df['col'] = pd.qcut(..., duplicates='drop')
        df['col'] = df['col'].fillna('uncategorized').astype(str)
    """
    import re

    lines = []
    for line in code.splitlines():
        if "pd.qcut(" not in line:
            lines.append(line)
            continue

        # Find the pd.qcut( call and locate its matching closing paren
        needle = "pd.qcut("
        qcut_start = line.find(needle)
        if qcut_start == -1:
            lines.append(line)
            continue

        args_start = qcut_start + len(needle)
        args_end = _find_matching_paren(line, args_start)  # index just past ')'
        inner = line[args_start:args_end - 1]
        if "duplicates=" not in inner:
            inner = inner + ", duplicates='drop'"

        # Everything before pd.qcut(
        prefix = line[:qcut_start]
        # Everything after the closing ')' of pd.qcut(...)
        suffix = line[args_end:]

        # Extract the assignment target from prefix (e.g. "df['col'] = ")
        assign_match = re.match(r"^(\s*)(df\[[^\]]+\])\s*=\s*$", prefix)
        if assign_match and suffix.lstrip().startswith(".fillna("):
            indent = assign_match.group(1)
            col_ref = assign_match.group(2)
            lines.append(f"{indent}{col_ref} = pd.qcut({inner})")
            lines.append(f"{indent}{col_ref} = {col_ref}{suffix.lstrip()}")
        else:
            # No chain or no assignment — just add duplicates='drop'
            lines.append(f"{prefix}pd.qcut({inner}){suffix}")

    return "\n".join(lines)


def execute_dimension_code(series: pd.Series, code: str) -> pd.DataFrame:
    """Execute AI's dimension code on the real vector."""
    import numpy as np

    logger.warning("EXECUTE-DIMENSION: series name=%r len=%d dtype=%s",
                   getattr(series, "name", "?"), len(series), series.dtype)
    logger.warning("EXECUTE-DIMENSION: code (first 400):\n%s", code[:400])

    sanitized = _sanitize_dimension_code(code)
    if sanitized != code:
        logger.warning("EXECUTE-DIMENSION: code was sanitized (qcut fix applied)")
        logger.warning("EXECUTE-DIMENSION: sanitized code:\n%s", sanitized[:400])
    code = sanitized

    df = pd.DataFrame({"value": series})
    logger.warning("EXECUTE-DIMENSION: df shape before exec=%s", df.shape)

    # Monkey-patch Categorical.fillna for safety
    _orig = pd.Categorical.fillna
    def _safe(self, value=None, **kw):
        if value is not None and value not in self.categories:
            self = self.add_categories(value)
        return _orig(self, value=value, **kw)
    pd.Categorical.fillna = _safe
    try:
        exec(code, {"df": df, "pd": pd, "np": np})
        logger.warning("EXECUTE-DIMENSION: exec succeeded — df columns=%s shape=%s", list(df.columns), df.shape)
    except Exception as exec_exc:
        logger.warning("EXECUTE-DIMENSION: exec FAILED: %s", exec_exc, exc_info=True)
        raise
    finally:
        pd.Categorical.fillna = _orig

    # Ensure all new columns are clean strings regardless of dtype
    for col in df.columns:
        if col == "value":
            continue
        s = df[col]
        try:
            if hasattr(s, "cat"):
                if "uncategorized" not in s.cat.categories:
                    s = s.cat.add_categories("uncategorized")
                df[col] = s.fillna("uncategorized").astype(str)
            else:
                df[col] = s.fillna("uncategorized").astype(str)
        except Exception:
            df[col] = df[col].astype(str).replace("nan", "uncategorized")

    return df
