"""
LLM-powered Domain Categorization for L3→L2 descent.

Claude sees the data profile, writes a Python snippet that creates a
'category' column on the DataFrame, and the backend executes it.
This replaces dumb quantile bins with intelligent, data-aware categorization.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

import pandas as pd

logger = logging.getLogger(__name__)

from intuitiveness.services.llm_client import call_llm_structured
from intuitiveness.services.transition_models import DomainSuggestion


def _safe_category_to_str(series: "pd.Series") -> "pd.Series":
    """Convert any Series (including Categorical) to clean string categories."""
    if hasattr(series, "cat"):
        if "uncategorized" not in series.cat.categories:
            series = series.cat.add_categories("uncategorized")
        series = series.fillna("uncategorized")
    return series.fillna("uncategorized").astype(str)


def _run_categorize_preview(code: str, sample: pd.DataFrame) -> Dict[str, int]:
    """Run categorization code on sample, return distribution or empty dict."""
    try:
        import numpy as np

        # Monkey-patch fillna on Categorical to prevent the crash inside exec
        _orig_fillna = pd.Categorical.fillna

        def _safe_fillna(self, value=None, **kwargs):
            if value is not None and value not in self.categories:
                self = self.add_categories(value)
            return _orig_fillna(self, value=value, **kwargs)

        pd.Categorical.fillna = _safe_fillna
        try:
            local_ns: Dict[str, Any] = {"df": sample, "pd": pd, "np": np}
            exec(code, local_ns)
        finally:
            pd.Categorical.fillna = _orig_fillna

        out_df = local_ns["df"]
        if "category" in out_df.columns:
            cat = _safe_category_to_str(out_df["category"])
            out_df["category"] = cat
            d = cat.value_counts().to_dict()
            return {str(k): int(v) for k, v in d.items()}
    except Exception as exc:
        logger.warning("Domain code preview failed: %s — code: %s", exc, code[:200])
    return {}


def _build_fallback_code(df: pd.DataFrame, col: str, domains: list) -> str:
    """Build simple categorization code when Claude's code fails."""
    if col not in df.columns:
        return ""
    n = len(domains)
    labels = ", ".join(f"'{d}'" for d in domains)
    esc_col = col.replace("'", "\\'")
    is_numeric = pd.api.types.is_numeric_dtype(df[col]) and df[col].notna().any()
    can_coerce = False
    if not is_numeric:
        try:
            coerced = pd.to_numeric(df[col].astype(str).str.replace('%', '').str.replace(',', '.').str.strip(), errors='coerce')
            can_coerce = coerced.notna().sum() > len(df) * 0.5
        except Exception:
            pass
    if is_numeric:
        return f"df['category'] = pd.qcut(df['{esc_col}'].rank(method='first'), q={n}, labels=[{labels}]).fillna('uncategorized').astype(str)"
    elif can_coerce:
        return (
            f"_num = pd.to_numeric(df['{esc_col}'].astype(str).str.replace('%','').str.replace(',','.').str.strip(), errors='coerce')\n"
            f"df['category'] = pd.qcut(_num.rank(method='first'), q={n}, labels=[{labels}]).fillna('uncategorized').astype(str)"
        )
    else:
        return f"df['category'] = df['{esc_col}'].fillna('uncategorized').astype(str)"


def _sanitize_code(code: str) -> str:
    """Auto-patch common LLM code issues."""
    if not code:
        return code
    lines = code.strip().split("\n")
    patched = []
    for line in lines:
        s = line.rstrip()
        if "df['category']" in s and "=" in s and ".astype(str)" not in s:
            s = s + ".fillna('uncategorized').astype(str)"
        if "df[\"category\"]" in s and "=" in s and ".astype(str)" not in s:
            s = s + ".fillna('uncategorized').astype(str)"
        patched.append(s)
    return "\n".join(patched)


_SYSTEM_PROMPT = """You are a Python data analyst that writes pandas code to categorize datasets.

ABSOLUTE RULES for your code:
1. When using pd.cut(), the number of labels MUST equal the number of bins minus 1. Example: bins=[0,80,90,100] needs exactly 3 labels.
2. ALWAYS call .fillna('uncategorized').astype(str) at the very end of the assignment.
3. If a column contains text that looks numeric (e.g. "83,90%" or "1 234"), convert it first with:
   pd.to_numeric(df['col'].astype(str).str.replace('%','').str.replace(',','.').str.strip(), errors='coerce')
4. Use meaningful thresholds in pd.cut based on the data's actual range and domain meaning — do NOT use pd.qcut (it just makes equal-sized groups with no analytical meaning).
5. Respond ONLY with valid JSON, no markdown."""




def _sample_values(df: pd.DataFrame, col: str, n: int = 8) -> list:
    vals = df[col].dropna().unique()[:n]
    return [str(v) for v in vals]


def _to_frame(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if hasattr(data, "nodes"):
        rows = [{"node": n, **(attrs or {})} for n, attrs in data.nodes(data=True)]
        return pd.DataFrame(rows)
    return pd.DataFrame(data)


def _build_data_profile(df: pd.DataFrame) -> dict:
    profile_cols = []
    for col in df.columns:
        info: Dict[str, Any] = {
            "name": col,
            "dtype": str(df[col].dtype),
            "non_null": int(df[col].notna().sum()),
            "unique_count": int(df[col].nunique()),
            "samples": _sample_values(df, col),
        }
        if pd.api.types.is_numeric_dtype(df[col]) and df[col].notna().any():
            info["min"] = float(df[col].min())
            info["max"] = float(df[col].max())
            info["mean"] = round(float(df[col].mean()), 2)
            info["median"] = round(float(df[col].median()), 2)
        profile_cols.append(info)
    return {"rows": len(df), "columns": profile_cols}


def _pick_column_heuristic(df: pd.DataFrame) -> str:
    numeric = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c]) and df[c].notna().any()
    ]
    if numeric:
        for c in numeric:
            if any(k in str(c).lower() for k in ("value", "amount", "price", "score", "count")):
                return c
        return numeric[0]
    text = [c for c in df.columns if c != "node" and df[c].notna().any()]
    return text[0] if text else (df.columns[0] if len(df.columns) else "value")


def _heuristic_fallback(df: pd.DataFrame) -> Dict[str, Any]:
    col = _pick_column_heuristic(df)
    is_numeric = col in df.columns and pd.api.types.is_numeric_dtype(df[col])
    if is_numeric:
        code = f"df['category'] = pd.qcut(df['{col}'].rank(method='first'), q=2, labels=['low', 'high']).astype(str)"
    else:
        code = f"df['category'] = df['{col}'].fillna('uncategorized').astype(str)"

    dist = {}
    try:
        import numpy as np
        sample = df.head(200).copy()
        exec(code, {"df": sample, "pd": pd, "np": np})
        if "category" in sample.columns:
            dist = {str(k): int(v) for k, v in sample["category"].value_counts().to_dict().items()}
    except Exception:
        pass

    return {
        "proposed_column": col,
        "proposed_domains": ["low", "high"] if is_numeric else list(df[col].dropna().unique()[:4].astype(str)),
        "explanation": f"Auto-detected '{col}' as the best column for categorization.",
        "confidence": "heuristic",
        "code": code,
        "columns": list(df.columns),
        "sample_distribution": dist,
        "error": None,
    }


def suggest_domains(data: Any, intent: str = "") -> Dict[str, Any]:
    """Analyze L3 data and return domain categories + executable Python code."""
    df = _to_frame(data)
    if df.empty:
        return {"error": "Empty dataset", "proposed_domains": [], "columns": []}

    columns = list(df.columns)
    profile = _build_data_profile(df)

    prompt = f"""You are a data analyst. You have a dataset with {profile['rows']} rows.

Here is the full column profile:
{json.dumps(profile['columns'], indent=2, default=str)}

## User's Analysis Intent
{intent if intent else "Not specified — choose the most analytically useful categorization."}

## Your Task
The user wants to categorize this data into meaningful domain groups for analysis. Orient your suggestions toward their intent above.

1. Look at the columns, their dtypes, and SAMPLE VALUES carefully. Pick the BEST column to categorize by.
   ONLY use columns with actual data (non_null > 0).
2. Write Python code that creates a 'category' column on a DataFrame called `df`.
3. Propose 2-4 domain category names that are meaningful and plain-language.

You have access to `pd` (pandas) and `np` (numpy). The code runs via exec().

RULES:
- Use pd.cut with MEANINGFUL thresholds based on domain knowledge (not pd.qcut which just makes equal groups).
- Number of labels MUST equal number of bins minus 1. Example: bins=[0,80,90,100] → 3 labels.
- If the column is text that looks numeric (e.g. "83,90%"), clean it first with str.replace.
- ALWAYS end with .fillna('uncategorized').astype(str).

Respond ONLY with JSON:
{{
  "proposed_column": "the column you chose",
  "proposed_domains": ["category A", "category B"],
  "code": "Python code that creates df['category']. End with .fillna('uncategorized').astype(str).",
  "explanation": "2-3 sentences explaining why these thresholds are meaningful."
}}"""

    try:
        suggestion = call_llm_structured(
            _SYSTEM_PROMPT, prompt, DomainSuggestion,
            model_env_var="DOMAIN_SUGGEST_MODEL",
        )
    except Exception as exc:
        logger.warning("Domain suggestion LLM call failed: %s", exc)
        return _heuristic_fallback(df)

    code = _sanitize_code(suggestion.code)
    logger.warning("LLM_CODE: %s", code[:300])
    sample = df.head(200).copy()
    dist = {}
    if code:
        dist = _run_categorize_preview(code, sample)
        if not dist:
            col = suggestion.proposed_column
            if col and col in sample.columns and suggestion.proposed_domains:
                fallback = _build_fallback_code(sample, col, suggestion.proposed_domains)
                if fallback:
                    code = fallback
                    dist = _run_categorize_preview(code, sample.copy())

    logger.warning("FINAL_DIST: %s — code: %s", dist, code[:200])
    return {
        "proposed_column": suggestion.proposed_column,
        "proposed_domains": suggestion.proposed_domains,
        "explanation": suggestion.explanation,
        "confidence": "high",
        "code": code,
        "columns": columns,
        "sample_distribution": dist,
        "error": None,
    }


def execute_categorization(data: Any, code: str) -> pd.DataFrame:
    """Execute AI's categorization code on the full dataset."""
    import numpy as np

    df = _to_frame(data)
    code = _sanitize_code(code)

    _orig_fillna = pd.Categorical.fillna

    def _safe_fillna(self, value=None, **kwargs):
        if value is not None and value not in self.categories:
            self = self.add_categories(value)
        return _orig_fillna(self, value=value, **kwargs)

    pd.Categorical.fillna = _safe_fillna
    try:
        exec(code, {"df": df, "pd": pd, "np": np})
    finally:
        pd.Categorical.fillna = _orig_fillna

    if "category" not in df.columns:
        df["category"] = "uncategorized"
    else:
        df["category"] = _safe_category_to_str(df["category"])
    return df
