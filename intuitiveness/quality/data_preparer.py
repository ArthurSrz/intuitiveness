"""
Data Preparation Utilities for TabPFN Assessment.

Implements Spec 009: FR-009 (Handle Mixed Data Types)

Extracted from assessor.py (Code Simplification Phase 4.1)

Provides functions for:
- Handling high-cardinality categorical features
- Feature selection when too many features
- Edge case detection and warnings
- Data preparation for TabPFN (missing values, encoding)
"""

import logging
import numpy as np
import pandas as pd
from typing import Optional, Tuple, List

from intuitiveness.utils import (
    detect_feature_type,
    MIN_ROWS_FOR_ASSESSMENT,
    MAX_ROWS_FOR_TABPFN,
    MAX_FEATURES_FOR_TABPFN,
    HIGH_CARDINALITY_THRESHOLD,
)

logger = logging.getLogger(__name__)


class DatasetWarning:
    """Container for dataset warnings during assessment."""

    def __init__(self):
        self.warnings: List[str] = []

    def add(self, message: str):
        self.warnings.append(message)
        logger.warning(message)

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


def handle_high_cardinality_categorical(
    series: pd.Series,
    threshold: int = HIGH_CARDINALITY_THRESHOLD,
) -> pd.Series:
    """
    Handle high-cardinality categorical features by binning rare values.

    Args:
        series: Categorical series.
        threshold: Maximum number of unique values to keep.

    Returns:
        Series with rare values grouped as 'other'.
    """
    value_counts = series.value_counts()

    if len(value_counts) <= threshold:
        return series

    # Keep top N-1 values, group rest as 'other'
    top_values = set(value_counts.head(threshold - 1).index)

    return series.apply(lambda x: x if x in top_values else "_other_")


def select_top_features(
    X: pd.DataFrame,
    y: pd.Series,
    max_features: int = MAX_FEATURES_FOR_TABPFN,
) -> pd.DataFrame:
    """
    Select top features when dataset has too many.

    Uses variance-based selection for efficiency.

    Args:
        X: Feature DataFrame.
        y: Target Series.
        max_features: Maximum number of features to keep.

    Returns:
        DataFrame with selected features.
    """
    if X.shape[1] <= max_features:
        return X

    logger.info(f"Selecting top {max_features} features from {X.shape[1]}")

    # Use variance as simple feature importance proxy
    variances = X.var().sort_values(ascending=False)
    top_features = variances.head(max_features).index.tolist()

    return X[top_features]


def check_dataset_edge_cases(
    df: pd.DataFrame,
    target_column: str,
) -> DatasetWarning:
    """
    Check for edge cases and generate warnings.

    Implements Spec 009: Edge case detection

    Args:
        df: DataFrame to check.
        target_column: Target column name.

    Returns:
        DatasetWarning with any warnings.
    """
    warnings = DatasetWarning()

    # Check row count
    if len(df) < MIN_ROWS_FOR_ASSESSMENT:
        warnings.add(
            f"Dataset has only {len(df)} rows. "
            f"Minimum {MIN_ROWS_FOR_ASSESSMENT} recommended for reliable assessment."
        )

    # Check feature count
    feature_count = len(df.columns) - 1  # Exclude target
    if feature_count > MAX_FEATURES_FOR_TABPFN:
        warnings.add(
            f"Dataset has {feature_count} features. "
            f"Top {MAX_FEATURES_FOR_TABPFN} will be selected for assessment."
        )

    # Check for only-categorical or only-numeric
    feature_cols = [c for c in df.columns if c != target_column]
    numeric_cols = df[feature_cols].select_dtypes(include=[np.number]).columns
    categorical_cols = df[feature_cols].select_dtypes(exclude=[np.number]).columns

    if len(numeric_cols) == 0 and len(categorical_cols) > 0:
        warnings.add(
            "Dataset contains only categorical features. "
            "Consider adding numeric features for better ML performance."
        )
    elif len(categorical_cols) == 0 and len(numeric_cols) > 0:
        warnings.add(
            "Dataset contains only numeric features. "
            "This is fine but diversity score will be lower."
        )

    # Check for high-cardinality categoricals
    for col in categorical_cols:
        n_unique = df[col].nunique()
        if n_unique > HIGH_CARDINALITY_THRESHOLD:
            warnings.add(
                f"Feature '{col}' has {n_unique} unique values (high cardinality). "
                f"Rare values will be grouped for encoding."
            )

    return warnings


def prepare_data_for_tabpfn(
    df: pd.DataFrame,
    target_column: str,
    warnings: Optional[DatasetWarning] = None,
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Prepare DataFrame for TabPFN by handling missing values and encoding.

    Implements Spec 009: FR-009 (Handle Mixed Data Types)

    Handles edge cases:
    - High-cardinality categoricals (>100 unique values)
    - Too many features (>500)
    - Only categorical or only numeric datasets

    Args:
        df: Input DataFrame.
        target_column: Target column name.
        warnings: Optional DatasetWarning to collect warnings.

    Returns:
        Tuple of (X, y) ready for TabPFN.
    """
    # Separate features and target
    feature_columns = [c for c in df.columns if c != target_column]
    X = df[feature_columns].copy()
    y = df[target_column].copy()

    # Handle missing values in target
    valid_mask = ~y.isna()
    X = X[valid_mask]
    y = y[valid_mask]

    # Handle missing values in features
    for col in X.columns:
        if X[col].isna().any():
            if pd.api.types.is_numeric_dtype(X[col]):
                X[col] = X[col].fillna(X[col].median())
            else:
                X[col] = X[col].fillna(X[col].mode().iloc[0] if len(X[col].mode()) > 0 else "missing")

    # Handle high-cardinality categoricals
    for col in X.columns:
        if X[col].dtype == "object" or X[col].dtype.name == "category":
            if X[col].nunique() > HIGH_CARDINALITY_THRESHOLD:
                X[col] = handle_high_cardinality_categorical(X[col])

    # Encode categorical features
    for col in X.columns:
        if X[col].dtype == "object" or X[col].dtype.name == "category":
            # Simple label encoding
            X[col] = pd.Categorical(X[col]).codes

    # Handle too many features
    if X.shape[1] > MAX_FEATURES_FOR_TABPFN:
        X = select_top_features(X, y)

    return X, y
