"""Real L3→L2 domain categorization.

The spec-015 engine's L3→L2 step only *labels* the table with `domains[0]` — it
never assigns rows to categories (the "everything maps to the first domain" bug).
We fix it in the service layer (no engine change) by building a `query_func` whose
result the engine wraps as the L2 table — the same `prebuilt_table` seam the
Streamlit UI used.

Two strategies, picked per column dtype:
  • numeric measure  → quantile bins labelled by the domains in order
    (lowest bin → first domain). This is what actually categorises the numeric
    demos (school scores, ADEME amounts, energy prices) into distinct groups.
  • text column      → keyword match (domain token appears in the cell), with an
    optional embedding match via the configured embeddings API
    (`intuitiveness.models`, best-effort — falls back to keyword if no API key).
"""

from __future__ import annotations

from typing import Any, List, Optional

import pandas as pd

UNMATCHED = "uncategorized"


def _to_frame(data: Any) -> pd.DataFrame:
    """L3 payload → table. Mirrors the engine's graph→rows extraction."""
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if hasattr(data, "nodes"):  # networkx graph
        rows = [{"node": n, **(attrs or {})} for n, attrs in data.nodes(data=True)]
        return pd.DataFrame(rows)
    return pd.DataFrame(data)


def _pick_column(df: pd.DataFrame, column: Optional[str]) -> Optional[str]:
    if column and column in df.columns and df[column].notna().any():
        return column
    # Prefer a numeric measure column with actual values.
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and df[c].notna().any()]
    if numeric:
        for c in numeric:
            if any(k in str(c).lower() for k in ("value", "amount", "price", "score", "count")):
                return c
        return numeric[0]
    text = [c for c in df.columns if c != "node" and df[c].notna().any()]
    return text[0] if text else (df.columns[0] if len(df.columns) else None)


def _quantile_categorize(df: pd.DataFrame, col: str, domains: List[str]) -> pd.Series:
    """Split `col` into len(domains) quantile bins; lowest bin → domains[0]."""
    n = len(domains)
    mask = df[col].notna()
    if not mask.any():
        return pd.Series(UNMATCHED, index=df.index)

    try:
        cats = pd.qcut(df.loc[mask, col].rank(method="first"), q=n, labels=domains)
        result = pd.Series(UNMATCHED, index=df.index)
        result.loc[mask] = cats.astype(str)
        return result
    except Exception:
        ranks = df.loc[mask, col].rank(method="first")
        edges = [ranks.quantile(i / n) for i in range(1, n)]

        def bucket(r: float) -> str:
            for i, e in enumerate(edges):
                if r <= e:
                    return domains[i]
            return domains[-1]

        result = pd.Series(UNMATCHED, index=df.index)
        result.loc[mask] = ranks.apply(bucket)
        return result


def _keyword_categorize(df: pd.DataFrame, col: str, domains: List[str]) -> pd.Series:
    lowered = [(d, d.lower()) for d in domains]
    return df[col].apply(
        lambda x: next((d for d, dl in lowered if dl in str(x).lower()), UNMATCHED)
    )


def _semantic_categorize(
    df: pd.DataFrame, col: str, domains: List[str], threshold: float
) -> Optional[pd.Series]:
    """Best-effort embedding match; returns None if the API is unavailable."""
    try:
        import numpy as np
        from intuitiveness.models import get_batch_similarities

        values = df[col].fillna("").astype(str).tolist()
        sims = get_batch_similarities(values, domains)
        if sims is None:
            return None
        out = []
        for row in sims:
            idx = int(np.argmax(row))
            out.append(domains[idx] if row[idx] >= threshold else UNMATCHED)
        return pd.Series(out, index=df.index)
    except Exception:
        return None


def categorize(
    data: Any,
    domains: List[str],
    *,
    use_semantic: bool = False,
    threshold: float = 0.6,
    column: Optional[str] = None,
) -> pd.DataFrame:
    """Return the L3 data as a table with a real `category` column."""
    df = _to_frame(data)
    if not domains or df.empty:
        return df
    col = _pick_column(df, column)
    if col is None:
        return df

    if pd.api.types.is_numeric_dtype(df[col]):
        category = _quantile_categorize(df, col, domains)
    else:
        category = None
        if use_semantic:
            category = _semantic_categorize(df, col, domains, threshold)
        if category is None:  # keyword (also the no-semantic path)
            category = _keyword_categorize(df, col, domains)

    out = df.copy()
    out["category"] = list(category)
    return out
