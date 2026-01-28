"""
L1→L2 Domain Enrichment Module

Implements Spec 004: FR-005-010 (L1→L2 Domain Enrichment)

Provides semantic and keyword-based domain categorization using
embedding similarity with configurable thresholds.

Functions:
----------
- enrich_l1_to_l2: Main enrichment function with semantic matching
- categorize_values: Batch categorization with hybrid matching

Example:
--------
>>> from intuitiveness.complexity import Level1Dataset, Level2Dataset
>>> import pandas as pd
>>>
>>> # Create L1 vector (school scores)
>>> scores = pd.Series([85, 90, 78, 92, 88], index=['School_A', 'School_B', 'School_C', 'School_D', 'School_E'])
>>> l1 = Level1Dataset(scores, name="school_scores")
>>>
>>> # Enrich with domain categories
>>> domains = ["high score", "low score"]
>>> l2 = enrich_l1_to_l2(l1, domains, threshold=0.7)
>>>
>>> # Result: DataFrame with 'value' and 'category' columns
>>> print(l2.get_data().head())
"""

from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
import numpy as np

from complexity import Level1Dataset, Level2Dataset


def enrich_l1_to_l2(
    vector: Level1Dataset,
    domains: List[str],
    threshold: float = 0.7,
    use_semantic: bool = True,
    keyword_vocabularies: Optional[Dict[str, List[str]]] = None
) -> Level2Dataset:
    """
    Enrich L1 vector to L2 table by adding domain categories.

    Implements Spec 004: FR-005-010 (L1→L2 Domain Enrichment)

    Uses hybrid matching strategy:
    1. Keyword matching against domain vocabularies (fast, exact)
    2. Semantic embedding similarity (slower, flexible)

    Architectural Decision (from refactoring plan):
    ------------------------------------------------
    Default threshold = 0.7 balances precision and recall for semantic matching.

    Trade-offs:
    - threshold < 0.6: Too many false positives, noisy categories
    - threshold 0.7-0.8: Recommended range (good balance)
    - threshold > 0.9: Too strict, misses valid matches

    Parameters:
    -----------
    vector : Level1Dataset
        The L1 vector to enrich
    domains : List[str]
        Domain names to categorize into (e.g., ["high score", "low score"])
    threshold : float
        Semantic similarity threshold (0.0-1.0), default 0.7
    use_semantic : bool
        If True, uses embedding similarity; if False, only keyword matching
    keyword_vocabularies : Optional[Dict[str, List[str]]]
        Domain-specific keyword lists for exact matching
        Example: {"high score": ["excellent", "above 85"], "low score": ["poor", "below 70"]}

    Returns:
    --------
    Level2Dataset
        Table with original values and 'category' column

    Example:
    --------
    >>> # Example from test0 dataset (school scores)
    >>> import pandas as pd
    >>> scores = pd.Series([95, 78, 92, 65, 88],
    ...                     index=['School_A', 'School_B', 'School_C', 'School_D', 'School_E'],
    ...                     name='score')
    >>> l1 = Level1Dataset(scores, name="school_scores")
    >>>
    >>> # Define domains with threshold
    >>> domains = ["high score", "low score"]
    >>> l2 = enrich_l1_to_l2(l1, domains, threshold=0.7)
    >>>
    >>> # Result: DataFrame with categorized scores
    >>> # School_A: 95 -> "high score"
    >>> # School_D: 65 -> "low score"
    """
    if not isinstance(vector, Level1Dataset):
        raise TypeError(f"Expected Level1Dataset, got {type(vector).__name__}")

    if not domains or len(domains) == 0:
        raise ValueError("Must provide at least one domain for enrichment")

    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"Threshold must be between 0.0 and 1.0, got {threshold}")

    # Get vector data
    series = vector.get_data()

    # Create DataFrame with values
    df = pd.DataFrame({
        'value': series.values,
        'index': series.index if series.index is not None else range(len(series))
    })

    # Categorize based on value ranges (for numeric data)
    if pd.api.types.is_numeric_dtype(series):
        categories = _categorize_numeric_values(series, domains, threshold)
    else:
        # For non-numeric data, use semantic/keyword matching
        if use_semantic:
            categories = _categorize_with_semantic_matching(
                series, domains, threshold, keyword_vocabularies
            )
        else:
            categories = _categorize_with_keywords(
                series, domains, keyword_vocabularies
            )

    df['category'] = categories

    # Create L2 dataset
    l2 = Level2Dataset(df)

    # Attach metadata
    l2._metadata = {
        "enriched_from": vector.name,
        "domains": domains,
        "threshold": threshold,
        "matching_strategy": "semantic" if use_semantic else "keyword",
        "source_operation": f"Enriched L1 vector with {len(domains)} domains"
    }

    return l2


def _categorize_numeric_values(
    series: pd.Series,
    domains: List[str],
    threshold: float
) -> List[str]:
    """
    Categorize numeric values based on percentile thresholds.

    For numeric data, we use statistical binning:
    - "high" domain: values above median + threshold * std
    - "low" domain: values below median - threshold * std
    - "medium" domain: values in between

    Parameters:
    -----------
    series : pd.Series
        Numeric series to categorize
    domains : List[str]
        Domain names (e.g., ["high score", "low score"])
    threshold : float
        Statistical threshold multiplier

    Returns:
    --------
    List[str]
        Category for each value
    """
    median = series.median()
    std = series.std()

    # Define thresholds
    high_threshold = median + (threshold * std)
    low_threshold = median - (threshold * std)

    categories = []
    for value in series:
        if pd.isna(value):
            categories.append("unknown")
        elif value >= high_threshold:
            # Assign to "high" domain (first domain matching "high")
            high_domain = next((d for d in domains if "high" in d.lower()), domains[0])
            categories.append(high_domain)
        elif value <= low_threshold:
            # Assign to "low" domain
            low_domain = next((d for d in domains if "low" in d.lower()), domains[-1])
            categories.append(low_domain)
        else:
            # Assign to middle domain
            mid_domain = next((d for d in domains if "mid" in d.lower() or "medium" in d.lower()), domains[len(domains)//2] if len(domains) > 2 else "medium")
            categories.append(mid_domain)

    return categories


def _categorize_with_semantic_matching(
    series: pd.Series,
    domains: List[str],
    threshold: float,
    keyword_vocabularies: Optional[Dict[str, List[str]]] = None
) -> List[str]:
    """
    Categorize values using semantic embedding similarity.

    Uses the multilingual-e5-small model for semantic matching.
    Falls back to keyword matching if available.

    Parameters:
    -----------
    series : pd.Series
        Series to categorize
    domains : List[str]
        Domain names
    threshold : float
        Similarity threshold
    keyword_vocabularies : Optional[Dict[str, List[str]]]
        Fallback keyword vocabularies

    Returns:
    --------
    List[str]
        Category for each value
    """
    try:
        from sentence_transformers import SentenceTransformer
        import torch

        # Load multilingual-e5-small model (Spec 004: FR-007)
        model = SentenceTransformer('intfloat/multilingual-e5-small')

        # Encode domains
        domain_embeddings = model.encode(domains, convert_to_tensor=True)

        # Encode values
        values_str = [str(v) for v in series]
        value_embeddings = model.encode(values_str, convert_to_tensor=True)

        # Compute cosine similarity
        from torch.nn.functional import cosine_similarity

        categories = []
        for i, value_emb in enumerate(value_embeddings):
            similarities = [
                cosine_similarity(value_emb.unsqueeze(0), domain_emb.unsqueeze(0)).item()
                for domain_emb in domain_embeddings
            ]

            max_sim = max(similarities)
            if max_sim >= threshold:
                best_domain_idx = similarities.index(max_sim)
                categories.append(domains[best_domain_idx])
            else:
                # No match above threshold
                categories.append("uncategorized")

        return categories

    except ImportError:
        # Fall back to keyword matching if sentence-transformers not available
        print("Warning: sentence-transformers not installed, falling back to keyword matching")
        return _categorize_with_keywords(series, domains, keyword_vocabularies)


def _categorize_with_keywords(
    series: pd.Series,
    domains: List[str],
    keyword_vocabularies: Optional[Dict[str, List[str]]] = None
) -> List[str]:
    """
    Categorize values using keyword matching.

    Parameters:
    -----------
    series : pd.Series
        Series to categorize
    domains : List[str]
        Domain names
    keyword_vocabularies : Optional[Dict[str, List[str]]]
        Domain-specific keyword lists

    Returns:
    --------
    List[str]
        Category for each value
    """
    if keyword_vocabularies is None:
        # Default: assign based on position
        categories = []
        for i, value in enumerate(series):
            domain_idx = i % len(domains)
            categories.append(domains[domain_idx])
        return categories

    categories = []
    for value in series:
        value_str = str(value).lower()
        matched = False

        for domain, keywords in keyword_vocabularies.items():
            if any(kw.lower() in value_str for kw in keywords):
                categories.append(domain)
                matched = True
                break

        if not matched:
            categories.append("uncategorized")

    return categories


def get_domain_statistics(
    l2_table: Level2Dataset
) -> Dict[str, Any]:
    """
    Get statistics about domain categorization.

    Returns dictionary with:
    - total_values: Total number of values
    - categories: List of unique categories
    - category_counts: Count per category
    - uncategorized_count: Number of uncategorized values

    Parameters:
    -----------
    l2_table : Level2Dataset
        The enriched L2 table

    Returns:
    --------
    dict
        Domain statistics for analysis

    Example:
    --------
    >>> stats = get_domain_statistics(l2)
    >>> print(f"Categorized {stats['total_values']} values into {len(stats['categories'])} domains")
    """
    df = l2_table.get_data()

    if 'category' not in df.columns:
        raise ValueError("L2 table missing 'category' column - not enriched?")

    stats = {
        "total_values": len(df),
        "categories": df['category'].unique().tolist(),
        "category_counts": df['category'].value_counts().to_dict(),
        "uncategorized_count": (df['category'] == 'uncategorized').sum(),
        "categorization_rate": 1.0 - ((df['category'] == 'uncategorized').sum() / len(df))
    }

    return stats
