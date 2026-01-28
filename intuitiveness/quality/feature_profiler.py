"""
Feature Profiling Utilities.

Implements Spec 009: FR-002 (Feature Importance Ranking)

Extracted from assessor.py (Code Simplification Phase 4.1)

Provides functions for:
- Computing feature statistics and profiles
- Calculating data quality scores
- Assessing dataset usability
"""

import logging
import numpy as np
import pandas as pd
from scipy import stats
from typing import Optional

from intuitiveness.quality.models import FeatureProfile
from intuitiveness.utils import (
    detect_feature_type,
    MIN_ROWS_FOR_ASSESSMENT,
    MAX_ROWS_FOR_TABPFN,
)

logger = logging.getLogger(__name__)


def compute_feature_profile(
    df: pd.DataFrame,
    feature_name: str,
    importance_score: float = 0.0,
    shap_mean: float = 0.0,
) -> FeatureProfile:
    """
    Compute statistics for a single feature.

    Args:
        df: DataFrame containing the feature.
        feature_name: Column name.
        importance_score: Pre-computed importance score.
        shap_mean: Pre-computed mean SHAP value.

    Returns:
        FeatureProfile instance.
    """
    series = df[feature_name]
    feature_type = detect_feature_type(series)

    missing_count = series.isna().sum()
    missing_ratio = missing_count / len(series)
    unique_count = series.nunique()

    # Compute skewness for numeric features
    distribution_skew = 0.0
    suggested_transform = None
    if feature_type == "numeric":
        clean_series = series.dropna()
        if len(clean_series) > 0:
            try:
                distribution_skew = float(stats.skew(clean_series))
                # Suggest log transform for highly skewed distributions
                if abs(distribution_skew) > 2:
                    suggested_transform = "log"
                elif abs(distribution_skew) > 1:
                    suggested_transform = "sqrt"
            except Exception:
                pass

    return FeatureProfile(
        feature_name=feature_name,
        feature_type=feature_type,
        missing_count=int(missing_count),
        missing_ratio=float(missing_ratio),
        unique_count=int(unique_count),
        importance_score=importance_score,
        shap_mean=shap_mean,
        distribution_skew=distribution_skew,
        suggested_transform=suggested_transform,
    )


def compute_data_completeness(df: pd.DataFrame) -> float:
    """
    Compute data completeness score (0-100).

    Score = (1 - overall_missing_ratio) * 100

    Args:
        df: DataFrame to assess.

    Returns:
        Completeness score 0-100.
    """
    total_cells = df.shape[0] * df.shape[1]
    if total_cells == 0:
        return 0.0
    missing_cells = df.isna().sum().sum()
    return (1 - missing_cells / total_cells) * 100


def compute_feature_diversity(df: pd.DataFrame, target_column: str) -> float:
    """
    Compute feature type diversity score (0-100).

    Based on entropy of feature type distribution.
    Higher diversity = better for ML (different types capture different aspects).

    Args:
        df: DataFrame to assess.
        target_column: Target column to exclude.

    Returns:
        Diversity score 0-100.
    """
    feature_columns = [c for c in df.columns if c != target_column]
    if not feature_columns:
        return 0.0

    # Count feature types
    type_counts = {"numeric": 0, "categorical": 0, "boolean": 0, "datetime": 0}
    for col in feature_columns:
        ftype = detect_feature_type(df[col])
        type_counts[ftype] += 1

    # Compute entropy
    total = sum(type_counts.values())
    if total == 0:
        return 0.0

    probs = [count / total for count in type_counts.values() if count > 0]
    if len(probs) <= 1:
        return 25.0  # Only one type = low diversity

    entropy = -sum(p * np.log2(p) for p in probs)
    max_entropy = np.log2(len(probs))  # Maximum possible entropy

    # Normalize to 0-100
    return (entropy / max_entropy) * 100 if max_entropy > 0 else 0.0


def compute_size_appropriateness(row_count: int) -> float:
    """
    Compute size appropriateness score (0-100).

    TabPFN works best with 50-10,000 rows.
    Score penalizes datasets outside this range.

    Args:
        row_count: Number of rows in dataset.

    Returns:
        Size score 0-100.
    """
    if row_count < MIN_ROWS_FOR_ASSESSMENT:
        # Linear penalty for too few rows
        return max(0, (row_count / MIN_ROWS_FOR_ASSESSMENT) * 50)
    elif row_count <= MAX_ROWS_FOR_TABPFN:
        # Optimal range
        return 100.0
    else:
        # Gradual penalty for large datasets (still usable via sampling)
        # Drops to 70 at 50k rows, 50 at 100k rows
        excess = row_count - MAX_ROWS_FOR_TABPFN
        penalty = min(50, excess / 2000)  # Max 50 point penalty
        return 100 - penalty


def compute_usability_score(
    prediction_quality: float,
    data_completeness: float,
    feature_diversity: float,
    size_appropriateness: float,
) -> float:
    """
    Compute composite usability score (0-100).

    Implements Spec 009: FR-001 (Usability Score Calculation)

    Formula: 40% prediction + 30% completeness + 20% diversity + 10% size

    Args:
        prediction_quality: TabPFN cross-validation score (0-100).
        data_completeness: Missing value score (0-100).
        feature_diversity: Feature type entropy (0-100).
        size_appropriateness: Size penalty score (0-100).

    Returns:
        Usability score 0-100.
    """
    return (
        0.4 * prediction_quality
        + 0.3 * data_completeness
        + 0.2 * feature_diversity
        + 0.1 * size_appropriateness
    )


def build_feature_profiles(
    df: pd.DataFrame,
    target_column: str,
    importance_scores: Optional[dict] = None,
    shap_values: Optional[dict] = None,
) -> list[FeatureProfile]:
    """
    Build feature profiles for all features in dataset.

    Args:
        df: DataFrame to profile.
        target_column: Target column to exclude.
        importance_scores: Optional dict mapping feature names to importance scores.
        shap_values: Optional dict mapping feature names to SHAP mean values.

    Returns:
        List of FeatureProfile objects.
    """
    importance_scores = importance_scores or {}
    shap_values = shap_values or {}

    profiles = []
    for col in df.columns:
        if col == target_column:
            continue

        profile = compute_feature_profile(
            df,
            col,
            importance_score=importance_scores.get(col, 0.0),
            shap_mean=shap_values.get(col, 0.0),
        )
        profiles.append(profile)

    # Sort by importance score
    profiles.sort(key=lambda p: p.importance_score, reverse=True)

    return profiles
