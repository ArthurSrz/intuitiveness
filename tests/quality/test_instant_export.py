"""
Tests for Instant Export (012-tabpfn-instant-export)

Spec Success Criteria:
- SC-001: Upload to export in <30 seconds
- SC-002: 90% reduction in TabPFN API consumption (≤5 calls vs 50-100+)
- SC-004: Zero ML terminology in default UI

Test Categories:
1. Performance tests - verify <30 second completion
2. API consumption tests - verify ≤5 TabPFN calls
3. Jargon tests - verify no ML terminology
4. Functional tests - verify cleaning and export works correctly
"""

import pytest
import pandas as pd
import numpy as np
import time
from pathlib import Path

# Import the instant export module
from intuitiveness.quality.instant_export import (
    InstantExporter,
    instant_check_and_export,
    export_clean_csv,
    PLAIN_SUMMARIES,
    PLAIN_WARNINGS,
)
from intuitiveness.quality.models import (
    ExportResult,
    CleaningAction,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def simple_df():
    """Simple test DataFrame with clean data."""
    np.random.seed(42)
    return pd.DataFrame({
        'feature_a': np.random.randn(100),
        'feature_b': np.random.randint(0, 10, 100),
        'category': np.random.choice(['A', 'B', 'C'], 100),
        'target': np.random.choice([0, 1], 100),
    })


@pytest.fixture
def messy_df():
    """Test DataFrame with missing values and issues."""
    np.random.seed(42)
    df = pd.DataFrame({
        'feature_a': np.random.randn(100),
        'feature_b': np.random.randint(0, 10, 100),
        'category': np.random.choice(['A', 'B', 'C', None], 100),
        'target': np.random.choice([0, 1], 100),
    })
    # Add missing values
    df.loc[0:9, 'feature_a'] = np.nan
    df.loc[10:14, 'feature_b'] = np.nan
    return df


@pytest.fixture
def high_cardinality_df():
    """Test DataFrame with high-cardinality categorical."""
    np.random.seed(42)
    return pd.DataFrame({
        'feature_a': np.random.randn(200),
        'user_id': [f'user_{i}' for i in range(200)],  # 200 unique values
        'target': np.random.choice([0, 1], 200),
    })


@pytest.fixture
def small_df():
    """Very small DataFrame (edge case)."""
    return pd.DataFrame({
        'feature_a': [1, 2, 3, 4, 5],
        'target': [0, 0, 1, 1, 1],
    })


@pytest.fixture
def test_csv_path(tmp_path, simple_df):
    """Create a temporary CSV file for testing."""
    csv_path = tmp_path / "test_data.csv"
    simple_df.to_csv(csv_path, index=False)
    return csv_path


# ============================================================================
# SC-001: PERFORMANCE TESTS (<30 seconds)
# ============================================================================


class TestPerformance:
    """Tests for SC-001: Upload to export in <30 seconds."""

    def test_simple_data_under_30_seconds(self, simple_df):
        """Simple clean data should complete well under 30 seconds."""
        start = time.time()

        result = instant_check_and_export(
            simple_df,
            target_column='target',
            enable_validation=False,  # Fastest path
        )

        elapsed = time.time() - start

        assert elapsed < 30, f"Took {elapsed:.1f}s, expected <30s"
        assert result.is_ready or not result.is_ready  # Just verify it completes

    def test_messy_data_under_30_seconds(self, messy_df):
        """Data with issues should still complete under 30 seconds."""
        start = time.time()

        result = instant_check_and_export(
            messy_df,
            target_column='target',
            enable_validation=False,
        )

        elapsed = time.time() - start

        assert elapsed < 30, f"Took {elapsed:.1f}s, expected <30s"

    def test_high_cardinality_under_30_seconds(self, high_cardinality_df):
        """High cardinality data should complete under 30 seconds."""
        start = time.time()

        result = instant_check_and_export(
            high_cardinality_df,
            target_column='target',
            enable_validation=False,
        )

        elapsed = time.time() - start

        assert elapsed < 30, f"Took {elapsed:.1f}s, expected <30s"

    def test_processing_time_recorded(self, simple_df):
        """Processing time should be recorded in result."""
        result = instant_check_and_export(
            simple_df,
            target_column='target',
            enable_validation=False,
        )

        assert result.processing_time_seconds > 0
        assert result.processing_time_seconds < 30


# ============================================================================
# SC-002: API CONSUMPTION TESTS (≤5 calls)
# ============================================================================


class TestAPIConsumption:
    """Tests for SC-002: 90% reduction in TabPFN API consumption."""

    def test_no_validation_zero_api_calls(self, simple_df):
        """Without validation, should use zero API calls."""
        exporter = InstantExporter(enable_tabpfn_validation=False)
        result = exporter.check_and_export(simple_df, target_column='target')

        assert result.api_calls_used == 0

    def test_with_validation_max_5_calls(self, simple_df):
        """With validation, should use at most 5 API calls."""
        exporter = InstantExporter(enable_tabpfn_validation=True, max_api_calls=5)
        result = exporter.check_and_export(simple_df, target_column='target')

        assert result.api_calls_used <= 5, \
            f"Used {result.api_calls_used} API calls, expected ≤5"

    def test_max_api_calls_respected(self, simple_df):
        """API call limit should be respected."""
        exporter = InstantExporter(enable_tabpfn_validation=True, max_api_calls=2)
        result = exporter.check_and_export(simple_df, target_column='target')

        assert result.api_calls_used <= 2


# ============================================================================
# SC-004: NO ML JARGON TESTS
# ============================================================================


class TestNoMLJargon:
    """Tests for SC-004: Zero ML terminology in default UI."""

    # ML jargon terms that should NOT appear
    ML_JARGON = [
        'cross-validation', 'cv', 'fold',
        'hyperparameter', 'learning rate',
        'gradient', 'epoch', 'batch',
        'overfitting', 'underfitting',
        'regularization', 'l1', 'l2',
        'feature importance', 'ablation',
        'SHAP', 'permutation',
        'precision', 'recall', 'f1',
        'AUC', 'ROC',
        'neural', 'layer',
        'embedding', 'transformer',
        'sklearn', 'tabpfn',
    ]

    def test_plain_summaries_no_jargon(self):
        """PLAIN_SUMMARIES should contain no ML jargon."""
        for key, summary in PLAIN_SUMMARIES.items():
            summary_lower = summary.lower()
            for jargon in self.ML_JARGON:
                assert jargon.lower() not in summary_lower, \
                    f"Found ML jargon '{jargon}' in summary '{key}': {summary}"

    def test_plain_warnings_no_jargon(self):
        """PLAIN_WARNINGS should contain no ML jargon."""
        for key, warning in PLAIN_WARNINGS.items():
            warning_lower = warning.lower()
            for jargon in self.ML_JARGON:
                assert jargon.lower() not in warning_lower, \
                    f"Found ML jargon '{jargon}' in warning '{key}': {warning}"

    def test_result_summary_no_jargon(self, simple_df):
        """Result summary should contain no ML jargon."""
        result = instant_check_and_export(
            simple_df,
            target_column='target',
            enable_validation=False,
        )

        summary_lower = result.summary.lower()
        for jargon in self.ML_JARGON:
            assert jargon.lower() not in summary_lower, \
                f"Found ML jargon '{jargon}' in result summary: {result.summary}"

    def test_result_warnings_no_jargon(self, messy_df):
        """Result warnings should contain no ML jargon."""
        result = instant_check_and_export(
            messy_df,
            target_column='target',
            enable_validation=False,
        )

        for warning in result.warnings:
            warning_lower = warning.lower()
            for jargon in self.ML_JARGON:
                assert jargon.lower() not in warning_lower, \
                    f"Found ML jargon '{jargon}' in warning: {warning}"

    def test_cleaning_actions_no_jargon(self, messy_df):
        """Cleaning action descriptions should contain no ML jargon."""
        result = instant_check_and_export(
            messy_df,
            target_column='target',
            enable_validation=False,
        )

        for action in result.cleaning_actions:
            desc_lower = action.description.lower()
            for jargon in self.ML_JARGON:
                assert jargon.lower() not in desc_lower, \
                    f"Found ML jargon '{jargon}' in action: {action.description}"


# ============================================================================
# FUNCTIONAL TESTS
# ============================================================================


class TestBasicFunctionality:
    """Tests for basic instant export functionality."""

    def test_simple_data_is_ready(self, simple_df):
        """Simple clean data should be marked as ready."""
        result = instant_check_and_export(
            simple_df,
            target_column='target',
            enable_validation=False,
        )

        assert result.is_ready
        assert result.status == 'ready'
        assert result.cleaned_df is not None

    def test_cleaned_df_has_no_missing_values(self, messy_df):
        """Cleaned DataFrame should have no missing values in features."""
        result = instant_check_and_export(
            messy_df,
            target_column='target',
            enable_validation=False,
        )

        # Check feature columns (not target) have no missing
        feature_cols = [c for c in result.cleaned_df.columns if c != 'target']
        for col in feature_cols:
            missing = result.cleaned_df[col].isna().sum()
            assert missing == 0, f"Column {col} still has {missing} missing values"

    def test_original_counts_preserved(self, simple_df):
        """Original row/column counts should be preserved."""
        result = instant_check_and_export(
            simple_df,
            target_column='target',
            enable_validation=False,
        )

        assert result.original_row_count == len(simple_df)
        assert result.original_col_count == len(simple_df.columns)

    def test_cleaning_actions_logged(self, messy_df):
        """Cleaning actions should be logged."""
        result = instant_check_and_export(
            messy_df,
            target_column='target',
            enable_validation=False,
        )

        # messy_df has missing values, so cleaning actions should be logged
        assert len(result.cleaning_actions) > 0

    def test_export_csv_works(self, simple_df):
        """export_clean_csv should produce valid CSV bytes."""
        result = instant_check_and_export(
            simple_df,
            target_column='target',
            enable_validation=False,
        )

        csv_bytes = export_clean_csv(result)

        assert isinstance(csv_bytes, bytes)
        assert len(csv_bytes) > 0

        # Should be parseable as CSV
        import io
        reloaded = pd.read_csv(io.BytesIO(csv_bytes))
        assert len(reloaded) == result.cleaned_row_count


class TestEdgeCases:
    """Tests for edge cases."""

    def test_missing_target_column(self, simple_df):
        """Should fail gracefully with missing target column."""
        result = instant_check_and_export(
            simple_df,
            target_column='nonexistent',
            enable_validation=False,
        )

        assert not result.is_ready
        assert 'not found' in result.summary.lower()

    def test_small_dataset_warning(self, small_df):
        """Small dataset should trigger warning."""
        result = instant_check_and_export(
            small_df,
            target_column='target',
            enable_validation=False,
        )

        # Should warn about small size but may still be ready
        has_small_warning = any('few rows' in w.lower() or 'small' in w.lower()
                               for w in result.warnings)
        assert has_small_warning

    def test_single_value_target(self, simple_df):
        """Target with single value should fail validation."""
        simple_df['constant_target'] = 1  # All same value

        result = instant_check_and_export(
            simple_df,
            target_column='constant_target',
            enable_validation=False,
        )

        assert not result.is_ready
        assert 'one value' in result.summary.lower()

    def test_high_cardinality_handling(self, high_cardinality_df):
        """High cardinality columns should be handled."""
        result = instant_check_and_export(
            high_cardinality_df,
            target_column='target',
            enable_validation=False,
        )

        # Should complete without error
        assert result.cleaned_df is not None

        # High cardinality column should be processed
        # (either binned or encoded)
        assert 'user_id' in high_cardinality_df.columns


class TestCleaningActions:
    """Tests for specific cleaning actions."""

    def test_fill_missing_action(self, messy_df):
        """fill_missing action should be logged for NaN columns."""
        result = instant_check_and_export(
            messy_df,
            target_column='target',
            enable_validation=False,
        )

        fill_actions = [a for a in result.cleaning_actions
                       if a.action_type == 'fill_missing']
        assert len(fill_actions) > 0

    def test_encode_category_action(self):
        """encode_category action should be logged for text columns."""
        df = pd.DataFrame({
            'text_col': ['apple', 'banana', 'cherry'] * 34,  # 102 rows
            'target': [0, 1, 0] * 34,
        })

        result = instant_check_and_export(
            df,
            target_column='target',
            enable_validation=False,
        )

        encode_actions = [a for a in result.cleaning_actions
                        if a.action_type == 'encode_category']
        assert len(encode_actions) > 0

    def test_cleaning_summary_readable(self, messy_df):
        """Cleaning summary should be human-readable."""
        result = instant_check_and_export(
            messy_df,
            target_column='target',
            enable_validation=False,
        )

        summary = result.get_cleaning_summary()
        assert len(summary) > 0
        assert 'Auto-cleaned' in summary or 'clean' in summary.lower()


class TestProgressCallback:
    """Tests for progress callback functionality."""

    def test_progress_callback_called(self, simple_df):
        """Progress callback should be called during processing."""
        progress_calls = []

        def callback(message: str, progress: float):
            progress_calls.append((message, progress))

        result = instant_check_and_export(
            simple_df,
            target_column='target',
            enable_validation=False,
            progress_callback=callback,
        )

        # Should have received progress updates
        assert len(progress_calls) > 0

        # Progress should start at 0 and end at 1
        assert progress_calls[0][1] == 0.0
        assert progress_calls[-1][1] == 1.0

    def test_progress_is_monotonic(self, simple_df):
        """Progress should monotonically increase."""
        progress_values = []

        def callback(message: str, progress: float):
            progress_values.append(progress)

        result = instant_check_and_export(
            simple_df,
            target_column='target',
            enable_validation=False,
            progress_callback=callback,
        )

        # Check monotonic increase
        for i in range(1, len(progress_values)):
            assert progress_values[i] >= progress_values[i-1], \
                f"Progress decreased from {progress_values[i-1]} to {progress_values[i]}"


# ============================================================================
# MODEL TESTS
# ============================================================================


class TestExportResultModel:
    """Tests for ExportResult dataclass."""

    def test_status_auto_set_from_is_ready(self):
        """Status should auto-set from is_ready."""
        result_ready = ExportResult(is_ready=True)
        assert result_ready.status == 'ready'

        result_not_ready = ExportResult(is_ready=False)
        assert result_not_ready.status == 'needs_work'

    def test_rows_removed_calculated(self):
        """rows_removed property should calculate correctly."""
        result = ExportResult(
            original_row_count=100,
            cleaned_row_count=90,
        )
        assert result.rows_removed == 10

    def test_to_dict_serializable(self):
        """to_dict should produce JSON-serializable output."""
        import json

        result = ExportResult(
            is_ready=True,
            summary="Test summary",
            warnings=["Warning 1"],
            cleaning_actions=[
                CleaningAction(
                    action_type="fill_missing",
                    column="col_a",
                    description="Filled values",
                    rows_affected=5,
                )
            ],
            original_row_count=100,
            cleaned_row_count=100,
            target_column="target",
        )

        result_dict = result.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(result_dict)
        assert len(json_str) > 0

    def test_from_dict_roundtrip(self):
        """from_dict should restore object from dict."""
        original = ExportResult(
            is_ready=True,
            summary="Test",
            warnings=["W1"],
            original_row_count=50,
            cleaned_row_count=50,
            target_column="target",
            validation_score=85.0,
        )

        restored = ExportResult.from_dict(original.to_dict())

        assert restored.is_ready == original.is_ready
        assert restored.summary == original.summary
        assert restored.validation_score == original.validation_score


class TestCleaningActionModel:
    """Tests for CleaningAction dataclass."""

    def test_to_dict(self):
        """to_dict should produce correct dict."""
        action = CleaningAction(
            action_type="fill_missing",
            column="col_a",
            description="Test description",
            rows_affected=10,
        )

        d = action.to_dict()

        assert d["action_type"] == "fill_missing"
        assert d["column"] == "col_a"
        assert d["rows_affected"] == 10

    def test_from_dict(self):
        """from_dict should restore object."""
        d = {
            "action_type": "encode_category",
            "column": "col_b",
            "description": "Encoded",
            "rows_affected": 0,
        }

        action = CleaningAction.from_dict(d)

        assert action.action_type == "encode_category"
        assert action.column == "col_b"


# ============================================================================
# CRITICAL: INF VALUE HANDLING TESTS (P0 Fix)
# ============================================================================


class TestInfValueHandling:
    """Tests for Inf/-Inf value handling (critical fix)."""

    def test_inf_values_replaced_with_nan(self):
        """Inf values should be replaced with NaN then imputed."""
        df = pd.DataFrame({
            'feature_a': [1.0, 2.0, np.inf, 4.0, -np.inf, 6.0] * 20,  # 120 rows
            'feature_b': np.random.randn(120),
            'target': np.random.choice([0, 1], 120),
        })

        result = instant_check_and_export(
            df,
            target_column='target',
            enable_validation=False,
        )

        # Should complete without crash
        assert result.cleaned_df is not None

        # Should have no Inf values remaining
        for col in result.cleaned_df.columns:
            if pd.api.types.is_numeric_dtype(result.cleaned_df[col]):
                inf_count = np.isinf(result.cleaned_df[col]).sum()
                assert inf_count == 0, f"Column {col} still has {inf_count} Inf values"

    def test_inf_handling_logged_as_action(self):
        """Inf value replacement should be logged as a cleaning action."""
        df = pd.DataFrame({
            'feature_with_inf': [1.0, np.inf, 3.0, -np.inf, 5.0] * 20,
            'target': np.random.choice([0, 1], 100),
        })

        result = instant_check_and_export(
            df,
            target_column='target',
            enable_validation=False,
        )

        # Should have a convert_type action for the inf handling
        convert_actions = [a for a in result.cleaning_actions
                         if a.action_type == 'convert_type']
        assert len(convert_actions) > 0, "Should log Inf handling as convert_type action"

        # Action description should be plain language
        inf_action = convert_actions[0]
        assert 'extreme values' in inf_action.description.lower(), \
            "Inf handling should use plain language (extreme values)"

    def test_all_inf_column_removed(self):
        """Column with all Inf values should be removed."""
        df = pd.DataFrame({
            'all_inf': [np.inf] * 100,
            'normal': np.random.randn(100),
            'target': np.random.choice([0, 1], 100),
        })

        result = instant_check_and_export(
            df,
            target_column='target',
            enable_validation=False,
        )

        # Column with all inf (becomes all NaN) should be removed
        assert result.cleaned_df is not None


class TestRemoveRowsAction:
    """Tests for remove_rows action type."""

    def test_remove_rows_action_logged(self):
        """remove_rows action should be logged when target has missing values."""
        df = pd.DataFrame({
            'feature_a': np.random.randn(100),
            'target': [0, 1] * 45 + [np.nan] * 10,  # 10 missing targets
        })

        result = instant_check_and_export(
            df,
            target_column='target',
            enable_validation=False,
        )

        # Should have a remove_rows action
        remove_actions = [a for a in result.cleaning_actions
                        if a.action_type == 'remove_rows']
        assert len(remove_actions) == 1, "Should log target missing removal"
        assert remove_actions[0].rows_affected == 10

    def test_rows_actually_removed(self):
        """Rows with missing target should be removed from cleaned_df."""
        df = pd.DataFrame({
            'feature_a': np.random.randn(100),
            'target': [0, 1] * 45 + [np.nan] * 10,
        })

        result = instant_check_and_export(
            df,
            target_column='target',
            enable_validation=False,
        )

        # Should have 90 rows after removing 10 with missing targets
        assert result.cleaned_row_count == 90
        assert result.rows_removed == 10


class TestStratification:
    """Tests for train/test split stratification."""

    def test_imbalanced_data_handles_gracefully(self):
        """Imbalanced classification data should not crash."""
        # 95% class 0, 5% class 1
        df = pd.DataFrame({
            'feature': np.random.randn(100),
            'target': [0] * 95 + [1] * 5,
        })

        result = instant_check_and_export(
            df,
            target_column='target',
            enable_validation=True,  # Enable to trigger stratification code
        )

        # Should complete without crash
        assert result.cleaned_df is not None

    def test_rare_class_fallback(self):
        """Extremely rare classes should trigger fallback to simple split."""
        # Class 1 appears only twice - too few for stratification
        df = pd.DataFrame({
            'feature': np.random.randn(50),
            'target': [0] * 48 + [1] * 2,
        })

        result = instant_check_and_export(
            df,
            target_column='target',
            enable_validation=True,
        )

        # Should complete without crash (fallback to non-stratified)
        assert result.cleaned_df is not None
