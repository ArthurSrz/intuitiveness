"""
Instant Export - Simplified TabPFN Quality Check & Export

Spec: 012-tabpfn-instant-export

Rethinks TabPFN integration from comprehensive assessment suite to simple
"check & export" workflow for non-technical domain experts.

Key Differences from Full Assessment (assessor.py):
---------------------------------------------------
| Full Assessment          | Instant Export              |
|--------------------------|----------------------------|
| 50-100+ API calls        | Max 5 API calls (FR-008)   |
| 15-30+ seconds           | <10 seconds (FR-001)       |
| Complex ablation study   | Heuristic validation       |
| SHAP computation         | Skipped (unreliable)       |
| 6 quality metrics        | Binary ready/needs_work    |
| ML terminology           | Plain language only        |

Target Users: Domain experts with NO familiarity with data structures
(Constitution Principle V: Target User Assumption)

Author: Intuitiveness Framework
"""

import logging
import time
from typing import Optional, Literal, Callable, List
import numpy as np
import pandas as pd

from intuitiveness.quality.models import (
    ExportResult,
    CleaningAction,
)
from intuitiveness.quality.tabpfn_wrapper import TabPFNWrapper, is_tabpfn_available
from intuitiveness.utils import (
    detect_task_type,
    detect_feature_type,
    MIN_ROWS_FOR_ASSESSMENT,
    MAX_ROWS_FOR_TABPFN,
    HIGH_CARDINALITY_THRESHOLD,
)

logger = logging.getLogger(__name__)

# ============================================================================
# PLAIN LANGUAGE TEMPLATES (No ML Jargon - FR-002, SC-004)
# ============================================================================

PLAIN_SUMMARIES = {
    "ready": "Your data is ready to use! You can export it now.",
    "ready_with_fixes": "Your data is ready after some automatic fixes. You can export it now.",
    "needs_target": "Please select which column you want to predict or analyze.",
    "too_small": "Your data has very few rows. You may need more data for reliable analysis.",
    "too_messy": "Your data has significant issues that need manual review.",
    "no_numeric": "Your data has no number columns. Consider adding some numeric data.",
}

PLAIN_WARNINGS = {
    "missing_values": "Some cells were empty - we filled them with typical values.",
    "text_encoded": "Text columns were converted to numbers for analysis.",
    "high_cardinality": "Some columns had too many different values and were simplified.",
    "column_removed": "Some columns couldn't be used and were removed.",
    "rows_with_issues": "Some rows had problems and were excluded.",
    "small_dataset": "With few rows, results may be less reliable.",
    "many_columns": "Your data has many columns - only the most useful ones are kept.",
}


# ============================================================================
# INSTANT EXPORTER CLASS
# ============================================================================


class InstantExporter:
    """
    Simplified check & export workflow for domain experts.

    Usage:
        exporter = InstantExporter()
        result = exporter.check_and_export(df, target_col="outcome")

        if result.is_ready:
            # Export result.cleaned_df
        else:
            # Show result.warnings to user
    """

    def __init__(
        self,
        enable_tabpfn_validation: bool = True,
        max_api_calls: int = 5,
    ):
        """
        Initialize instant exporter.

        Args:
            enable_tabpfn_validation: If True, run single TabPFN prediction check.
                                     Set False for fastest possible export.
            max_api_calls: Maximum TabPFN API calls allowed (spec: ≤5).
        """
        self.enable_tabpfn_validation = enable_tabpfn_validation
        self.max_api_calls = max_api_calls
        self._api_calls_used = 0

    def check_and_export(
        self,
        df: pd.DataFrame,
        target_column: str,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> ExportResult:
        """
        Check data readiness and prepare for export in <10 seconds.

        This is the main entry point for the instant export workflow.

        Workflow:
        1. Basic validation (immediate) - no API calls
        2. Auto-clean data (missing values, encoding) - no API calls
        3. Optional TabPFN quick check (1-2 API calls max)
        4. Return ExportResult with cleaned DataFrame

        Args:
            df: Input DataFrame to check and clean.
            target_column: Column to use for prediction/analysis.
            progress_callback: Optional callback(message, progress 0-1).

        Returns:
            ExportResult with cleaned DataFrame and readiness status.
        """
        start_time = time.time()
        self._api_calls_used = 0

        def report(message: str, progress: float):
            if progress_callback:
                progress_callback(message, progress)
            logger.info(f"InstantExport: {message} ({progress:.0%})")

        # ────────────────────────────────────────────────────────────────────
        # PHASE 1: VALIDATION (0-20%)
        # ────────────────────────────────────────────────────────────────────
        report("Checking your data...", 0.0)

        validation_issues = self._validate_basic(df, target_column)
        if validation_issues:
            return ExportResult(
                is_ready=False,
                summary=validation_issues[0],
                warnings=validation_issues,
                original_row_count=len(df),
                original_col_count=len(df.columns),
                target_column=target_column,
                processing_time_seconds=time.time() - start_time,
            )

        report("Data structure looks good", 0.2)

        # ────────────────────────────────────────────────────────────────────
        # PHASE 2: AUTO-CLEANING (20-60%)
        # ────────────────────────────────────────────────────────────────────
        report("Auto-fixing common issues...", 0.25)

        cleaned_df, cleaning_actions, warnings = self._auto_clean(
            df, target_column, progress_callback=lambda m, p: report(m, 0.3 + p * 0.3)
        )

        report("Data cleaned", 0.6)

        # ────────────────────────────────────────────────────────────────────
        # PHASE 3: OPTIONAL TABPFN VALIDATION (60-90%)
        # ────────────────────────────────────────────────────────────────────
        validation_score = None
        task_type = detect_task_type(cleaned_df[target_column])

        if self.enable_tabpfn_validation and self._api_calls_used < self.max_api_calls:
            report("Running quick quality check...", 0.7)
            validation_score = self._quick_tabpfn_check(
                cleaned_df, target_column, task_type
            )
            if validation_score is not None:
                report(f"Quality check complete", 0.9)

        # ────────────────────────────────────────────────────────────────────
        # PHASE 4: BUILD RESULT (90-100%)
        # ────────────────────────────────────────────────────────────────────
        report("Preparing export...", 0.95)

        # Determine readiness
        is_ready = self._determine_readiness(
            cleaned_df, cleaning_actions, warnings, validation_score
        )

        # Build summary
        if is_ready:
            if cleaning_actions:
                summary = PLAIN_SUMMARIES["ready_with_fixes"]
            else:
                summary = PLAIN_SUMMARIES["ready"]
        else:
            summary = PLAIN_SUMMARIES["too_messy"]

        processing_time = time.time() - start_time
        report("Done!", 1.0)

        return ExportResult(
            is_ready=is_ready,
            summary=summary,
            warnings=warnings,
            cleaning_actions=cleaning_actions,
            cleaned_df=cleaned_df,
            original_row_count=len(df),
            cleaned_row_count=len(cleaned_df),
            original_col_count=len(df.columns),
            cleaned_col_count=len(cleaned_df.columns),
            target_column=target_column,
            task_type=task_type,
            validation_score=validation_score,
            processing_time_seconds=processing_time,
            api_calls_used=self._api_calls_used,
        )

    # ========================================================================
    # PHASE 1: VALIDATION
    # ========================================================================

    def _validate_basic(
        self,
        df: pd.DataFrame,
        target_column: str,
    ) -> List[str]:
        """
        Run basic validation checks (no API calls).

        Returns list of blocking issues (empty = valid).
        """
        issues = []

        # Check target column exists
        if target_column not in df.columns:
            issues.append(f"Column '{target_column}' not found in your data.")
            return issues

        # Check minimum rows
        if len(df) < 10:
            issues.append(PLAIN_SUMMARIES["too_small"])
            return issues

        # Check target has variation
        if df[target_column].nunique() < 2:
            issues.append("The column you selected has only one value - nothing to analyze.")
            return issues

        # Check we have at least one usable feature
        feature_cols = [c for c in df.columns if c != target_column]
        if not feature_cols:
            issues.append("Your data needs at least one column besides the target.")
            return issues

        return issues

    # ========================================================================
    # PHASE 2: AUTO-CLEANING
    # ========================================================================

    def _auto_clean(
        self,
        df: pd.DataFrame,
        target_column: str,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> tuple[pd.DataFrame, List[CleaningAction], List[str]]:
        """
        Auto-clean data with plain-language logging.

        Handles:
        - Infinite values (Inf/-Inf converted to missing)
        - Missing values (median for numbers, mode for text)
        - High-cardinality categoricals (bin rare values)
        - Categorical encoding (simple label encoding)
        - Unusable columns (all-null, single-value)

        Returns:
            (cleaned_df, cleaning_actions, warnings)
        """
        cleaned = df.copy()
        actions = []
        warnings = []

        def report(message: str, progress: float):
            if progress_callback:
                progress_callback(message, progress)

        feature_cols = [c for c in cleaned.columns if c != target_column]
        total_cols = len(feature_cols)

        # ────────────────────────────────────────────────────────────────────
        # Step 0: Handle Inf/-Inf values (CRITICAL - crashes TabPFN otherwise)
        # ────────────────────────────────────────────────────────────────────
        for col in cleaned.columns:
            if pd.api.types.is_numeric_dtype(cleaned[col]):
                inf_count = np.isinf(cleaned[col]).sum()
                if inf_count > 0:
                    cleaned[col] = cleaned[col].replace([np.inf, -np.inf], np.nan)
                    actions.append(CleaningAction(
                        action_type="convert_type",
                        column=col,
                        description=f"Replaced {inf_count} extreme values in '{col}' with empty cells",
                        rows_affected=inf_count,
                    ))

        # ────────────────────────────────────────────────────────────────────
        # Step 1: Remove target rows with missing values
        # ────────────────────────────────────────────────────────────────────
        target_missing = cleaned[target_column].isna().sum()
        if target_missing > 0:
            cleaned = cleaned.dropna(subset=[target_column])
            actions.append(CleaningAction(
                action_type="remove_rows",
                column=target_column,
                description=f"Removed {target_missing} rows with missing target values",
                rows_affected=target_missing,
            ))
            if target_missing > len(df) * 0.1:
                warnings.append(PLAIN_WARNINGS["rows_with_issues"])

        # ────────────────────────────────────────────────────────────────────
        # Step 2: Process each feature column
        # ────────────────────────────────────────────────────────────────────
        cols_to_drop = []

        for i, col in enumerate(feature_cols):
            report(f"Processing column {i+1}/{total_cols}", i / total_cols)

            # Check if column is usable
            n_unique = cleaned[col].nunique()
            n_missing = cleaned[col].isna().sum()
            missing_ratio = n_missing / len(cleaned) if len(cleaned) > 0 else 1.0

            # Drop unusable columns
            if n_unique <= 1:
                cols_to_drop.append(col)
                actions.append(CleaningAction(
                    action_type="remove_column",
                    column=col,
                    description=f"Removed '{col}' - only one value",
                    rows_affected=0,
                ))
                continue

            if missing_ratio > 0.9:
                cols_to_drop.append(col)
                actions.append(CleaningAction(
                    action_type="remove_column",
                    column=col,
                    description=f"Removed '{col}' - too many empty cells",
                    rows_affected=0,
                ))
                continue

            # Handle missing values
            if n_missing > 0:
                feature_type = detect_feature_type(cleaned[col])
                if feature_type == "numeric":
                    fill_value = cleaned[col].median()
                    cleaned[col] = cleaned[col].fillna(fill_value)
                    actions.append(CleaningAction(
                        action_type="fill_missing",
                        column=col,
                        description=f"Filled {n_missing} empty cells in '{col}' with typical value",
                        rows_affected=n_missing,
                    ))
                else:
                    mode_values = cleaned[col].mode()
                    fill_value = mode_values.iloc[0] if len(mode_values) > 0 else "unknown"
                    cleaned[col] = cleaned[col].fillna(fill_value)
                    actions.append(CleaningAction(
                        action_type="fill_missing",
                        column=col,
                        description=f"Filled {n_missing} empty cells in '{col}' with most common value",
                        rows_affected=n_missing,
                    ))

            # Handle high-cardinality categoricals
            feature_type = detect_feature_type(cleaned[col])
            if feature_type == "categorical" and n_unique > HIGH_CARDINALITY_THRESHOLD:
                # Keep top 99 values, group rest as "other"
                top_values = set(cleaned[col].value_counts().head(99).index)
                cleaned[col] = cleaned[col].apply(
                    lambda x: x if x in top_values else "_other_"
                )
                actions.append(CleaningAction(
                    action_type="encode_category",
                    column=col,
                    description=f"Simplified '{col}' by grouping rare values",
                    rows_affected=0,
                ))
                warnings.append(PLAIN_WARNINGS["high_cardinality"])

            # Encode categoricals for export
            if feature_type == "categorical":
                cleaned[col] = pd.Categorical(cleaned[col]).codes
                actions.append(CleaningAction(
                    action_type="encode_category",
                    column=col,
                    description=f"Converted text in '{col}' to numbers",
                    rows_affected=0,
                ))

        # Drop unusable columns
        if cols_to_drop:
            cleaned = cleaned.drop(columns=cols_to_drop)
            if len(cols_to_drop) > 1:
                warnings.append(PLAIN_WARNINGS["column_removed"])

        # Add general warnings
        if any(a.action_type == "fill_missing" for a in actions):
            if PLAIN_WARNINGS["missing_values"] not in warnings:
                warnings.insert(0, PLAIN_WARNINGS["missing_values"])

        if any(a.action_type == "encode_category" for a in actions):
            if PLAIN_WARNINGS["text_encoded"] not in warnings:
                warnings.append(PLAIN_WARNINGS["text_encoded"])

        # Warn about small datasets
        if len(cleaned) < MIN_ROWS_FOR_ASSESSMENT:
            warnings.append(PLAIN_WARNINGS["small_dataset"])

        report("Cleaning complete", 1.0)
        return cleaned, actions, warnings

    # ========================================================================
    # PHASE 3: OPTIONAL TABPFN VALIDATION
    # ========================================================================

    def _quick_tabpfn_check(
        self,
        df: pd.DataFrame,
        target_column: str,
        task_type: Literal["classification", "regression"],
    ) -> Optional[float]:
        """
        Run single TabPFN prediction to validate data quality.

        Uses only 1-2 API calls (vs 50-100+ in full assessment).

        Returns validation score (0-100) or None if unavailable.
        """
        available, _ = is_tabpfn_available()
        if not available:
            logger.info("TabPFN not available, skipping validation")
            return None

        try:
            # Prepare data
            X = df.drop(columns=[target_column])
            y = df[target_column]

            # Sample if too large (TabPFN optimal ≤10K rows)
            if len(X) > MAX_ROWS_FOR_TABPFN:
                sample_idx = np.random.choice(len(X), MAX_ROWS_FOR_TABPFN, replace=False)
                X = X.iloc[sample_idx]
                y = y.iloc[sample_idx]

            # Simple train/test split (no CV to minimize API calls)
            # Use stratification for classification to handle class imbalance
            from sklearn.model_selection import train_test_split

            stratify_param = y.values if task_type == "classification" else None
            try:
                X_train, X_test, y_train, y_test = train_test_split(
                    X.values, y.values, test_size=0.2, random_state=42,
                    stratify=stratify_param
                )
            except ValueError:
                # Fallback to non-stratified if class count is too small
                logger.warning("Stratification failed (rare classes), using simple split")
                X_train, X_test, y_train, y_test = train_test_split(
                    X.values, y.values, test_size=0.2, random_state=42
                )

            # Single TabPFN fit & score
            wrapper = TabPFNWrapper(task_type=task_type)
            wrapper.fit(X_train, y_train)
            self._api_calls_used += 1

            score = wrapper.score(X_test, y_test)
            self._api_calls_used += 1

            # Convert to 0-100 scale
            validation_score = score * 100
            logger.info(f"Quick TabPFN validation: {validation_score:.1f}%")
            return validation_score

        except Exception as e:
            logger.warning(f"TabPFN validation failed: {e}")
            return None

    # ========================================================================
    # PHASE 4: DETERMINE READINESS
    # ========================================================================

    def _determine_readiness(
        self,
        cleaned_df: pd.DataFrame,
        cleaning_actions: List[CleaningAction],
        warnings: List[str],
        validation_score: Optional[float],
    ) -> bool:
        """
        Determine if data is ready for export.

        Binary decision (FR-005):
        - Ready: Export immediately
        - Needs Work: Show warnings and suggest manual review

        Readiness criteria:
        1. At least 2 feature columns remaining
        2. At least 10 rows remaining
        3. If validation ran: score ≥ 50% (better than random)
        4. No critical warnings (e.g., all columns removed)
        """
        # Check we have usable data
        if len(cleaned_df) < 10:
            return False

        if len(cleaned_df.columns) < 3:  # target + at least 2 features
            return False

        # Check validation score if available
        if validation_score is not None and validation_score < 50:
            return False

        # Check for critical issues
        critical_warnings = [
            "too many empty",
            "couldn't be used",
            "need more data",
        ]
        for warning in warnings:
            if any(crit in warning.lower() for crit in critical_warnings):
                return False

        return True


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def instant_check_and_export(
    df: pd.DataFrame,
    target_column: str,
    enable_validation: bool = True,
    progress_callback: Optional[Callable[[str, float], None]] = None,
) -> ExportResult:
    """
    One-liner for instant export workflow.

    Args:
        df: Input DataFrame.
        target_column: Column to predict/analyze.
        enable_validation: Whether to run TabPFN validation.
        progress_callback: Optional progress callback.

    Returns:
        ExportResult with cleaned DataFrame and readiness status.
    """
    exporter = InstantExporter(enable_tabpfn_validation=enable_validation)
    return exporter.check_and_export(df, target_column, progress_callback)


def export_clean_csv(result: ExportResult) -> bytes:
    """
    Export cleaned DataFrame as CSV bytes.

    Args:
        result: ExportResult from check_and_export.

    Returns:
        CSV file contents as bytes.
    """
    if result.cleaned_df is None:
        raise ValueError("No cleaned DataFrame available")

    return result.cleaned_df.to_csv(index=False).encode("utf-8")
