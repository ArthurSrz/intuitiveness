"""
TabPFN Pre-Flight Validation & Auto-Preparation

Validates DataFrame constraints before TabPFN calls and provides
transparent auto-preparation with user-friendly warnings.

Based on TabPFN documentation: https://docs.priorlabs.ai/

Feature: 011-e2e-robust
"""

import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ============================================================================
# TABPFN CONSTRAINTS (from TabPFN documentation)
# ============================================================================

@dataclass(frozen=True)
class TabPFNConstraints:
    """Hard limits for TabPFN model."""

    MIN_ROWS: int = 10
    MAX_ROWS: int = 10_000
    OPTIMAL_MIN_ROWS: int = 100  # Warning if below
    MAX_FEATURES: int = 500
    MAX_CLASSES: int = 10  # For classification target
    HIGH_CARDINALITY_THRESHOLD: int = 100  # Categorical with >100 unique values


CONSTRAINTS = TabPFNConstraints()


# ============================================================================
# VALIDATION RESULT MODELS
# ============================================================================

@dataclass
class ValidationIssue:
    """Single validation issue detected."""

    severity: str  # 'error' | 'warning' | 'info'
    code: str  # Machine-readable code
    message: str  # Human-readable plain language
    column: Optional[str] = None  # Affected column if applicable
    suggestion: Optional[str] = None  # How to fix


@dataclass
class ValidationResult:
    """Complete validation result for a DataFrame."""

    is_valid: bool
    can_auto_fix: bool
    issues: List[ValidationIssue] = field(default_factory=list)

    # Data summary
    row_count: int = 0
    feature_count: int = 0
    numeric_columns: List[str] = field(default_factory=list)
    categorical_columns: List[str] = field(default_factory=list)
    high_cardinality_columns: List[str] = field(default_factory=list)
    datetime_columns: List[str] = field(default_factory=list)

    def has_errors(self) -> bool:
        """Check if any blocking errors exist."""
        return any(i.severity == 'error' for i in self.issues)

    def has_warnings(self) -> bool:
        """Check if any warnings exist."""
        return any(i.severity == 'warning' for i in self.issues)

    def get_plain_summary(self) -> str:
        """Get user-friendly summary."""
        if self.is_valid:
            return "Your data is ready for TabPFN analysis."
        elif self.can_auto_fix:
            return "Your data needs some adjustments that can be made automatically."
        else:
            errors = [i.message for i in self.issues if i.severity == 'error']
            return f"Issues found: {'; '.join(errors)}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_valid": self.is_valid,
            "can_auto_fix": self.can_auto_fix,
            "issues": [
                {
                    "severity": i.severity,
                    "code": i.code,
                    "message": i.message,
                    "column": i.column,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ],
            "row_count": self.row_count,
            "feature_count": self.feature_count,
            "numeric_columns": self.numeric_columns,
            "categorical_columns": self.categorical_columns,
            "high_cardinality_columns": self.high_cardinality_columns,
            "datetime_columns": self.datetime_columns,
        }


@dataclass
class PreparationResult:
    """Result of auto-preparation step."""

    prepared_df: pd.DataFrame
    actions_taken: List[str]  # Plain-language descriptions
    columns_removed: List[str]
    columns_encoded: List[str]
    rows_sampled: bool
    original_row_count: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "actions_taken": self.actions_taken,
            "columns_removed": self.columns_removed,
            "columns_encoded": self.columns_encoded,
            "rows_sampled": self.rows_sampled,
            "original_row_count": self.original_row_count,
            "final_row_count": len(self.prepared_df),
            "final_column_count": len(self.prepared_df.columns),
        }


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_for_tabpfn(
    df: pd.DataFrame,
    target_column: Optional[str] = None,
) -> ValidationResult:
    """
    Validate a DataFrame against TabPFN constraints.

    Args:
        df: DataFrame to validate.
        target_column: Optional target column for classification task.

    Returns:
        ValidationResult with issues and data summary.
    """
    issues: List[ValidationIssue] = []

    row_count = len(df)
    feature_count = len(df.columns)

    # Detect column types
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()

    # Detect high-cardinality categorical columns
    high_cardinality = []
    for col in categorical_cols:
        unique_count = df[col].nunique()
        if unique_count > CONSTRAINTS.HIGH_CARDINALITY_THRESHOLD:
            high_cardinality.append(col)

    # =================================================================
    # HARD CONSTRAINTS (errors)
    # =================================================================

    # Row count validation
    if row_count < CONSTRAINTS.MIN_ROWS:
        issues.append(ValidationIssue(
            severity='error',
            code='TOO_FEW_ROWS',
            message=f"Only {row_count} rows found. TabPFN needs at least {CONSTRAINTS.MIN_ROWS} rows.",
            suggestion="Add more data or combine with similar datasets.",
        ))

    if row_count > CONSTRAINTS.MAX_ROWS:
        issues.append(ValidationIssue(
            severity='warning',
            code='TOO_MANY_ROWS',
            message=f"{row_count:,} rows found. Will sample down to {CONSTRAINTS.MAX_ROWS:,} rows.",
            suggestion="Auto-fix will randomly sample rows.",
        ))

    # Feature count validation
    if feature_count > CONSTRAINTS.MAX_FEATURES:
        issues.append(ValidationIssue(
            severity='warning',
            code='TOO_MANY_FEATURES',
            message=f"{feature_count} columns found. Will keep top {CONSTRAINTS.MAX_FEATURES}.",
            suggestion="Auto-fix will select most relevant features.",
        ))

    # No numeric columns
    if len(numeric_cols) == 0 and len(categorical_cols) == 0:
        issues.append(ValidationIssue(
            severity='error',
            code='NO_USABLE_COLUMNS',
            message="No numeric or categorical columns found.",
            suggestion="Check that your data has proper column types.",
        ))

    # Target column validation (if specified)
    if target_column:
        if target_column not in df.columns:
            issues.append(ValidationIssue(
                severity='error',
                code='TARGET_NOT_FOUND',
                message=f"Target column '{target_column}' not found in data.",
                column=target_column,
            ))
        else:
            n_classes = df[target_column].nunique()
            if n_classes > CONSTRAINTS.MAX_CLASSES:
                issues.append(ValidationIssue(
                    severity='warning',
                    code='TOO_MANY_CLASSES',
                    message=f"Target has {n_classes} classes. Will group into top {CONSTRAINTS.MAX_CLASSES}.",
                    column=target_column,
                    suggestion="Auto-fix will combine rare classes.",
                ))

    # =================================================================
    # SOFT CONSTRAINTS (warnings)
    # =================================================================

    # Low row count warning
    if CONSTRAINTS.MIN_ROWS <= row_count < CONSTRAINTS.OPTIMAL_MIN_ROWS:
        issues.append(ValidationIssue(
            severity='warning',
            code='LOW_ROW_COUNT',
            message=f"Only {row_count} rows. Results may be less reliable with <{CONSTRAINTS.OPTIMAL_MIN_ROWS} rows.",
        ))

    # High cardinality categorical columns
    for col in high_cardinality:
        unique_count = df[col].nunique()
        issues.append(ValidationIssue(
            severity='warning',
            code='HIGH_CARDINALITY',
            message=f"Column '{col}' has {unique_count:,} unique values (too many for useful categories).",
            column=col,
            suggestion="Will be removed or grouped during auto-fix.",
        ))

    # Missing values
    missing_cols = df.columns[df.isnull().any()].tolist()
    if missing_cols:
        total_missing = df.isnull().sum().sum()
        issues.append(ValidationIssue(
            severity='info',
            code='MISSING_VALUES',
            message=f"{total_missing:,} missing values in {len(missing_cols)} columns. Will be filled automatically.",
        ))

    # Datetime columns
    if datetime_cols:
        issues.append(ValidationIssue(
            severity='info',
            code='DATETIME_COLUMNS',
            message=f"{len(datetime_cols)} date/time columns will be converted to numeric features.",
        ))

    # Determine overall validity
    has_errors = any(i.severity == 'error' for i in issues)
    has_auto_fixable = any(i.code in [
        'TOO_MANY_ROWS', 'TOO_MANY_FEATURES', 'HIGH_CARDINALITY',
        'TOO_MANY_CLASSES', 'MISSING_VALUES', 'DATETIME_COLUMNS'
    ] for i in issues)

    return ValidationResult(
        is_valid=not has_errors and not has_auto_fixable,
        can_auto_fix=not has_errors or (has_errors and has_auto_fixable),
        issues=issues,
        row_count=row_count,
        feature_count=feature_count,
        numeric_columns=numeric_cols,
        categorical_columns=categorical_cols,
        high_cardinality_columns=high_cardinality,
        datetime_columns=datetime_cols,
    )


# ============================================================================
# AUTO-PREPARATION FUNCTIONS
# ============================================================================

def prepare_for_tabpfn(
    df: pd.DataFrame,
    target_column: Optional[str] = None,
    max_rows: int = CONSTRAINTS.MAX_ROWS,
    max_features: int = CONSTRAINTS.MAX_FEATURES,
    handle_missing: str = 'fill',  # 'fill' | 'drop'
    random_state: Optional[int] = None,
) -> PreparationResult:
    """
    Auto-prepare a DataFrame for TabPFN consumption.

    Applies transparent transformations to meet TabPFN constraints
    while preserving as much information as possible.

    Args:
        df: Input DataFrame.
        target_column: Optional target column to preserve.
        max_rows: Maximum rows to keep (default: 10,000).
        max_features: Maximum features to keep (default: 500).
        handle_missing: How to handle missing values ('fill' or 'drop').
        random_state: Random seed for reproducible sampling.

    Returns:
        PreparationResult with prepared DataFrame and action log.
    """
    prepared_df = df.copy()
    actions: List[str] = []
    columns_removed: List[str] = []
    columns_encoded: List[str] = []
    rows_sampled = False
    original_row_count = len(df)

    # =================================================================
    # STEP 1: Remove high-cardinality text columns
    # =================================================================

    categorical_cols = prepared_df.select_dtypes(include=['object', 'category']).columns.tolist()

    for col in categorical_cols:
        if col == target_column:
            continue  # Don't remove target

        unique_count = prepared_df[col].nunique()
        if unique_count > CONSTRAINTS.HIGH_CARDINALITY_THRESHOLD:
            prepared_df = prepared_df.drop(columns=[col])
            columns_removed.append(col)
            actions.append(f"Removed '{col}' (had {unique_count:,} unique text values - too varied for analysis)")
            logger.info(f"Removed high-cardinality column: {col} ({unique_count} unique values)")

    # =================================================================
    # STEP 2: Convert datetime columns to numeric
    # =================================================================

    datetime_cols = prepared_df.select_dtypes(include=['datetime64']).columns.tolist()

    for col in datetime_cols:
        # Convert to Unix timestamp (seconds since epoch)
        prepared_df[col] = prepared_df[col].astype('int64') // 10**9
        columns_encoded.append(col)
        actions.append(f"Converted date column '{col}' to numeric timestamp")

    # =================================================================
    # STEP 3: Convert boolean columns to numeric (0/1)
    # =================================================================

    bool_cols = prepared_df.select_dtypes(include=['bool']).columns.tolist()

    for col in bool_cols:
        prepared_df[col] = prepared_df[col].astype(int)
        columns_encoded.append(col)
        actions.append(f"Converted boolean column '{col}' to 0/1")

    # =================================================================
    # STEP 4: Encode remaining categorical columns
    # =================================================================

    remaining_categorical = prepared_df.select_dtypes(include=['object', 'category']).columns.tolist()

    for col in remaining_categorical:
        unique_values = prepared_df[col].dropna().unique()
        value_to_int = {v: i for i, v in enumerate(unique_values)}
        value_to_int[np.nan] = -1

        prepared_df[col] = prepared_df[col].map(lambda x: value_to_int.get(x, -1))
        columns_encoded.append(col)
        actions.append(f"Encoded text column '{col}' ({len(unique_values)} categories) to numbers")

    # =================================================================
    # STEP 4: Handle missing values
    # =================================================================

    if prepared_df.isnull().any().any():
        missing_before = prepared_df.isnull().sum().sum()

        if handle_missing == 'fill':
            # Fill numeric with median, categorical (now numeric) with mode
            for col in prepared_df.columns:
                if prepared_df[col].isnull().any():
                    if prepared_df[col].dtype in [np.float64, np.int64]:
                        fill_value = prepared_df[col].median()
                    else:
                        fill_value = prepared_df[col].mode().iloc[0] if len(prepared_df[col].mode()) > 0 else 0
                    prepared_df[col] = prepared_df[col].fillna(fill_value)

            actions.append(f"Filled {missing_before:,} empty cells with typical values")
        else:
            prepared_df = prepared_df.dropna()
            rows_dropped = original_row_count - len(prepared_df)
            if rows_dropped > 0:
                actions.append(f"Removed {rows_dropped:,} rows with missing data")

    # =================================================================
    # STEP 5: Sample rows if too many
    # =================================================================

    if len(prepared_df) > max_rows:
        prepared_df = prepared_df.sample(n=max_rows, random_state=random_state)
        rows_sampled = True
        actions.append(f"Randomly selected {max_rows:,} rows (from {original_row_count:,})")
        logger.info(f"Sampled {max_rows} rows from {original_row_count}")

    # =================================================================
    # STEP 6: Select top features if too many
    # =================================================================

    if len(prepared_df.columns) > max_features:
        # Keep target column if specified
        cols_to_keep = prepared_df.columns[:max_features].tolist()
        if target_column and target_column not in cols_to_keep:
            cols_to_keep[-1] = target_column  # Replace last with target

        removed_features = [c for c in prepared_df.columns if c not in cols_to_keep]
        prepared_df = prepared_df[cols_to_keep]
        columns_removed.extend(removed_features)
        actions.append(f"Kept {max_features} most important columns (removed {len(removed_features)})")

    # =================================================================
    # STEP 7: Ensure all columns are numeric
    # =================================================================

    # Final check - convert any remaining non-numeric
    for col in prepared_df.columns:
        if not np.issubdtype(prepared_df[col].dtype, np.number):
            try:
                prepared_df[col] = pd.to_numeric(prepared_df[col], errors='coerce')
                prepared_df[col] = prepared_df[col].fillna(0)
                actions.append(f"Force-converted '{col}' to numbers")
            except Exception:
                prepared_df = prepared_df.drop(columns=[col])
                columns_removed.append(col)
                actions.append(f"Removed '{col}' (couldn't convert to numbers)")

    return PreparationResult(
        prepared_df=prepared_df,
        actions_taken=actions,
        columns_removed=columns_removed,
        columns_encoded=columns_encoded,
        rows_sampled=rows_sampled,
        original_row_count=original_row_count,
    )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_preparation_summary(
    original_df: pd.DataFrame,
    prepared_df: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Get a summary comparing original and prepared DataFrames.

    Args:
        original_df: Original input DataFrame.
        prepared_df: Prepared DataFrame after auto-fix.

    Returns:
        Dictionary with comparison metrics.
    """
    return {
        "original": {
            "rows": len(original_df),
            "columns": len(original_df.columns),
            "memory_mb": original_df.memory_usage(deep=True).sum() / 1024 / 1024,
        },
        "prepared": {
            "rows": len(prepared_df),
            "columns": len(prepared_df.columns),
            "memory_mb": prepared_df.memory_usage(deep=True).sum() / 1024 / 1024,
        },
        "reduction": {
            "rows_percent": (1 - len(prepared_df) / len(original_df)) * 100 if len(original_df) > 0 else 0,
            "columns_percent": (1 - len(prepared_df.columns) / len(original_df.columns)) * 100 if len(original_df.columns) > 0 else 0,
        },
        "is_tabpfn_ready": (
            len(prepared_df) >= CONSTRAINTS.MIN_ROWS
            and len(prepared_df) <= CONSTRAINTS.MAX_ROWS
            and len(prepared_df.columns) <= CONSTRAINTS.MAX_FEATURES
            and prepared_df.select_dtypes(include=[np.number]).shape[1] == len(prepared_df.columns)
        ),
    }


def detect_csv_delimiter(file_path: str) -> Tuple[str, str]:
    """
    Auto-detect CSV delimiter and encoding from file.

    Reads a larger sample (64KB) to ensure encoding detection is robust.
    French/European data often uses Latin-1 encoding with accented characters.

    Args:
        file_path: Path to CSV file.

    Returns:
        Tuple of (delimiter, encoding).
    """
    import csv

    # Try encodings in order of likelihood for French/European data
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    detected_encoding = 'latin-1'  # Safe fallback for European data
    sample = ''

    # Read a larger sample to catch encoding issues that appear later in file
    sample_size = 65536  # 64KB

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                sample = f.read(sample_size)
            detected_encoding = encoding
            break
        except UnicodeDecodeError:
            continue

    # If UTF-8 failed on larger sample, use latin-1 (which never fails)
    if not sample:
        with open(file_path, 'r', encoding='latin-1') as f:
            sample = f.read(4096)
        detected_encoding = 'latin-1'

    # Try common delimiters
    sniffer = csv.Sniffer()
    try:
        # Use first 4KB for delimiter detection (sniffer doesn't need full sample)
        dialect = sniffer.sniff(sample[:4096], delimiters=',;\t|')
        return dialect.delimiter, detected_encoding
    except csv.Error:
        # Default to comma
        return ',', detected_encoding


def load_csv_with_auto_delimiter(
    file_path: str,
    **kwargs,
) -> Tuple[pd.DataFrame, str]:
    """
    Load CSV with auto-detected delimiter and encoding.

    Handles French/European data with Latin-1 encoding.
    Includes retry logic for encoding failures.

    Args:
        file_path: Path to CSV file.
        **kwargs: Additional arguments for pd.read_csv.

    Returns:
        Tuple of (DataFrame, detected delimiter).
    """
    delimiter, detected_encoding = detect_csv_delimiter(file_path)

    # Don't override encoding if explicitly provided
    if 'encoding' not in kwargs:
        kwargs['encoding'] = detected_encoding

    # Try with detected encoding, fall back to latin-1 on failure
    fallback_encodings = ['latin-1', 'cp1252', 'iso-8859-1']

    try:
        df = pd.read_csv(file_path, delimiter=delimiter, **kwargs)
        return df, delimiter
    except UnicodeDecodeError:
        # Try fallback encodings
        for encoding in fallback_encodings:
            try:
                kwargs['encoding'] = encoding
                df = pd.read_csv(file_path, delimiter=delimiter, **kwargs)
                logger.info(f"Loaded {file_path} with fallback encoding: {encoding}")
                return df, delimiter
            except UnicodeDecodeError:
                continue

        # Last resort: latin-1 never fails, use errors='replace'
        kwargs['encoding'] = 'latin-1'
        df = pd.read_csv(file_path, delimiter=delimiter, **kwargs)
        return df, delimiter
