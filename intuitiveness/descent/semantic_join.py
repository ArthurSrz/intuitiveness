"""
Semantic Table Join for L4→L3 Descent.

This module implements the semantic join operation that transforms
unlinkable L4 datasets into a linked L3 table using embedding similarity
on semantic columns.

The core insight from the research paper:
- L4: Unlinkable, multi-level datasets (infinite complexity)
- L3: Linkable, multi-level datasets

The transition L4→L3 is achieved by finding semantic connections
between datasets that share conceptual meaning but different naming conventions.
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Any
import pandas as pd
import numpy as np

# Import HuggingFace API-based similarity from models module
from intuitiveness.models import get_batch_similarities, get_sentence_similarity


@dataclass
class SemanticJoinConfig:
    """Configuration for semantic table join operation."""

    # Column names for semantic matching
    left_column: str
    right_column: str

    # Similarity threshold (0.0 to 1.0)
    similarity_threshold: float = 0.8

    # Join type: 'inner', 'left', 'outer'
    join_type: str = 'inner'

    # Whether to add similarity score column
    include_similarity_score: bool = True

    # Column prefix for right dataset (to avoid name collisions)
    right_prefix: str = ''

    # Keep only the best match for each left row (prevents match explosion)
    best_match_only: bool = True


def semantic_table_join(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    config: SemanticJoinConfig
) -> pd.DataFrame:
    """
    Join two DataFrames using semantic similarity on specified columns.

    This function implements the L4→L3 descent by creating a single table
    that merges columns from two previously unlinkable datasets.

    Args:
        left_df: First DataFrame (left side of join)
        right_df: Second DataFrame (right side of join)
        config: SemanticJoinConfig with join parameters

    Returns:
        pd.DataFrame: Joined table with columns from both datasets

    Example:
        >>> config = SemanticJoinConfig(
        ...     left_column='Dénomination principale',
        ...     right_column='Nom de l\\'établissement',
        ...     similarity_threshold=0.8
        ... )
        >>> l3_table = semantic_table_join(df1, df2, config)
    """
    print(f"[L4→L3] Using the configured embeddings API for semantic join")

    # Validate columns exist
    if config.left_column not in left_df.columns:
        raise ValueError(f"Column '{config.left_column}' not found in left DataFrame. "
                        f"Available: {list(left_df.columns)}")
    if config.right_column not in right_df.columns:
        raise ValueError(f"Column '{config.right_column}' not found in right DataFrame. "
                        f"Available: {list(right_df.columns)}")

    # Extract join column values
    left_values = left_df[config.left_column].fillna('').astype(str).tolist()
    right_values = right_df[config.right_column].fillna('').astype(str).tolist()

    print(f"[L4→L3] Computing embeddings for {len(left_values)} left values, {len(right_values)} right values")

    # Get unique values to reduce computation
    unique_left = list(set(left_values))
    unique_right = list(set(right_values))

    print(f"[L4→L3] Unique values: {len(unique_left)} left, {len(unique_right)} right")

    # Compute similarity matrix using HuggingFace API
    print(f"[L4→L3] Computing similarity matrix via HuggingFace API ({len(unique_left)} x {len(unique_right)})", flush=True)
    similarity_matrix = get_batch_similarities(unique_left, unique_right)

    if similarity_matrix is None:
        raise RuntimeError("[L4→L3] Failed to compute similarities via HuggingFace API. "
                          "Check your HF_TOKEN and network connection.")

    # Create lookup from value to embedding index
    left_value_to_idx = {v: i for i, v in enumerate(unique_left)}
    right_value_to_idx = {v: i for i, v in enumerate(unique_right)}

    # Find matches above threshold - vectorized using numpy
    print(f"[L4→L3] Finding matches with threshold >= {config.similarity_threshold}", flush=True)

    # Use numpy to find all pairs above threshold (vectorized)
    mask = similarity_matrix >= config.similarity_threshold
    left_match_indices, right_match_indices = np.where(mask)

    print(f"[L4→L3] Found {len(left_match_indices)} unique value matches", flush=True)

    # Build lookup tables: value -> row indices
    left_value_to_rows: Dict[str, List[int]] = {}
    for idx, val in enumerate(left_values):
        if val not in left_value_to_rows:
            left_value_to_rows[val] = []
        left_value_to_rows[val].append(idx)

    right_value_to_rows: Dict[str, List[int]] = {}
    for idx, val in enumerate(right_values):
        if val not in right_value_to_rows:
            right_value_to_rows[val] = []
        right_value_to_rows[val].append(idx)

    # Map unique matches back to actual row pairs
    matches: List[Tuple[int, int, float]] = []  # (left_idx, right_idx, similarity)

    for left_emb_idx, right_emb_idx in zip(left_match_indices, right_match_indices):
        left_val = unique_left[left_emb_idx]
        right_val = unique_right[right_emb_idx]
        sim = similarity_matrix[left_emb_idx, right_emb_idx]

        for left_row_idx in left_value_to_rows.get(left_val, []):
            for right_row_idx in right_value_to_rows.get(right_val, []):
                matches.append((left_row_idx, right_row_idx, float(sim)))

    print(f"[L4→L3] Found {len(matches)} row-level matches above threshold", flush=True)

    # If best_match_only, keep only the best match for each left row
    if config.best_match_only and len(matches) > 0:
        print(f"[L4→L3] Filtering to best match per left row...", flush=True)
        best_matches: Dict[int, Tuple[int, int, float]] = {}  # left_idx -> (left_idx, right_idx, sim)
        for left_idx, right_idx, sim in matches:
            if left_idx not in best_matches or sim > best_matches[left_idx][2]:
                best_matches[left_idx] = (left_idx, right_idx, sim)
        matches = list(best_matches.values())
        print(f"[L4→L3] After filtering: {len(matches)} best matches", flush=True)

    if len(matches) == 0:
        print(f"[L4→L3] WARNING: No matches found! Consider lowering the threshold.", flush=True)
        # Return empty DataFrame with all columns
        all_columns = list(left_df.columns)
        for col in right_df.columns:
            if col not in all_columns:
                new_col = f"{config.right_prefix}{col}" if config.right_prefix else col
                all_columns.append(new_col)
        if config.include_similarity_score:
            all_columns.append('_semantic_similarity')
        return pd.DataFrame(columns=all_columns)

    # Build the joined DataFrame - optimized using vectorized indexing
    print(f"[L4→L3] Building joined table...", flush=True)

    # Extract match indices and similarities
    left_indices = [m[0] for m in matches]
    right_indices = [m[1] for m in matches]
    similarities = [m[2] for m in matches]

    # Get left rows using vectorized indexing
    left_rows = left_df.iloc[left_indices].reset_index(drop=True)

    # Get right rows and rename columns to avoid conflicts
    right_rows = right_df.iloc[right_indices].reset_index(drop=True)

    # Rename right columns to avoid conflicts
    right_rename = {}
    for col in right_rows.columns:
        if col in left_rows.columns and not config.right_prefix:
            right_rename[col] = f"{col}_right"
        elif config.right_prefix:
            right_rename[col] = f"{config.right_prefix}{col}"
    if right_rename:
        right_rows = right_rows.rename(columns=right_rename)

    # Concatenate horizontally
    result_df = pd.concat([left_rows, right_rows], axis=1)

    # Add similarity score if requested
    if config.include_similarity_score:
        result_df['_semantic_similarity'] = similarities

    print(f"[L4→L3] Created L3 table with {len(result_df)} rows and {len(result_df.columns)} columns", flush=True)

    return result_df


def find_best_join_columns(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    top_k: int = 5
) -> List[Tuple[str, str, float]]:
    """
    Automatically find the best columns to join on based on column name similarity.

    Uses the configured embeddings API (intuitiveness.models).

    Args:
        left_df: First DataFrame
        right_df: Second DataFrame
        top_k: Number of top column pairs to return

    Returns:
        List of (left_col, right_col, similarity) tuples
    """
    left_cols = list(left_df.columns)
    right_cols = list(right_df.columns)

    # Compute similarity matrix using HuggingFace API
    sim_matrix = get_batch_similarities(left_cols, right_cols)

    if sim_matrix is None:
        raise RuntimeError("Failed to compute column similarities via HuggingFace API. "
                          "Check your HF_TOKEN and network connection.")

    # Find top-k pairs
    pairs = []
    for i, left_col in enumerate(left_cols):
        for j, right_col in enumerate(right_cols):
            pairs.append((left_col, right_col, float(sim_matrix[i, j])))

    # Sort by similarity descending
    pairs.sort(key=lambda x: x[2], reverse=True)

    return pairs[:top_k]
