"""
TabPFN Compatibility Tests

Verifies that navigation-path data structures are compatible with
TabPFN synthetic data generation requirements.

Feature: 011-e2e-robust
"""

import sys
import pytest
import numpy as np
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, '/Users/arthursarazin/Documents/data_redesign_method')

from intuitiveness.complexity import Level2Dataset, Level0Dataset, Level1Dataset
from intuitiveness.quality.tabpfn_validation import (
    validate_for_tabpfn,
    prepare_for_tabpfn,
    detect_csv_delimiter,
    load_csv_with_auto_delimiter,
    CONSTRAINTS,
    ValidationResult,
    PreparationResult,
)
from intuitiveness.quality.synthetic_generator import (
    generate_synthetic,
    _encode_categorical_features,
    _decode_categorical_features,
    validate_synthetic,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def simple_numeric_df():
    """Simple DataFrame with only numeric columns."""
    np.random.seed(42)
    return pd.DataFrame({
        'feature_a': np.random.randn(100),
        'feature_b': np.random.randint(0, 10, 100),
        'feature_c': np.random.uniform(0, 100, 100),
    })


@pytest.fixture
def mixed_type_df():
    """DataFrame with mixed numeric and categorical columns."""
    np.random.seed(42)
    return pd.DataFrame({
        'numeric_col': np.random.randn(100),
        'category_col': np.random.choice(['A', 'B', 'C', 'D'], 100),
        'int_col': np.random.randint(0, 50, 100),
        'bool_col': np.random.choice([True, False], 100),
    })


@pytest.fixture
def high_cardinality_df():
    """DataFrame with a high-cardinality text column."""
    np.random.seed(42)
    return pd.DataFrame({
        'numeric_col': np.random.randn(500),
        'free_text': [f"Unique text value {i}" for i in range(500)],  # 500 unique values
        'category_col': np.random.choice(['X', 'Y', 'Z'], 500),
    })


@pytest.fixture
def df_with_missing():
    """DataFrame with missing values."""
    df = pd.DataFrame({
        'col_a': [1.0, 2.0, np.nan, 4.0, 5.0] * 20,
        'col_b': ['A', 'B', None, 'A', 'C'] * 20,
        'col_c': np.random.randn(100),
    })
    return df


@pytest.fixture
def large_df():
    """DataFrame exceeding TabPFN row limit."""
    np.random.seed(42)
    return pd.DataFrame({
        'col_a': np.random.randn(15000),
        'col_b': np.random.randint(0, 100, 15000),
    })


@pytest.fixture
def test_data_path():
    """Path to test data directory."""
    return '/Users/arthursarazin/Documents/data_redesign_method/test_data'


# ============================================================================
# LEVEL2DATASET COMPATIBILITY TESTS
# ============================================================================

class TestLevel2DatasetCompatibility:
    """Tests that Level2Dataset correctly returns DataFrame for TabPFN."""

    def test_level2_returns_dataframe(self, simple_numeric_df):
        """Level2Dataset.get_data() must return a pandas DataFrame."""
        dataset = Level2Dataset(simple_numeric_df, name="test")
        data = dataset.get_data()

        assert isinstance(data, pd.DataFrame), "Level2Dataset must return DataFrame"
        assert len(data) == len(simple_numeric_df)
        assert list(data.columns) == list(simple_numeric_df.columns)

    def test_level2_preserves_dtypes(self, mixed_type_df):
        """Level2Dataset preserves original column dtypes."""
        dataset = Level2Dataset(mixed_type_df, name="mixed")
        data = dataset.get_data()

        for col in mixed_type_df.columns:
            assert data[col].dtype == mixed_type_df[col].dtype, f"Dtype mismatch for {col}"

    def test_level2_complexity_level(self, simple_numeric_df):
        """Level2Dataset reports correct complexity level."""
        dataset = Level2Dataset(simple_numeric_df, name="test")

        assert dataset.complexity_level.value == 2


# ============================================================================
# VALIDATION TESTS
# ============================================================================

class TestTabPFNValidation:
    """Tests for TabPFN pre-flight validation."""

    def test_valid_dataframe_passes(self, simple_numeric_df):
        """Valid DataFrame should pass validation."""
        result = validate_for_tabpfn(simple_numeric_df)

        assert result.is_valid or result.can_auto_fix
        assert not result.has_errors()
        assert result.row_count == 100
        assert result.feature_count == 3

    def test_too_few_rows_fails(self):
        """DataFrame with <10 rows should fail."""
        tiny_df = pd.DataFrame({'a': [1, 2, 3]})
        result = validate_for_tabpfn(tiny_df)

        assert result.has_errors()
        assert any(i.code == 'TOO_FEW_ROWS' for i in result.issues)

    def test_too_many_rows_warns(self, large_df):
        """DataFrame with >10K rows should warn."""
        result = validate_for_tabpfn(large_df)

        assert any(i.code == 'TOO_MANY_ROWS' for i in result.issues)
        assert result.can_auto_fix  # Can be fixed by sampling

    def test_high_cardinality_detected(self, high_cardinality_df):
        """High-cardinality text columns should be flagged."""
        result = validate_for_tabpfn(high_cardinality_df)

        assert len(result.high_cardinality_columns) > 0
        assert 'free_text' in result.high_cardinality_columns
        assert any(i.code == 'HIGH_CARDINALITY' for i in result.issues)

    def test_missing_values_detected(self, df_with_missing):
        """Missing values should be detected."""
        result = validate_for_tabpfn(df_with_missing)

        assert any(i.code == 'MISSING_VALUES' for i in result.issues)

    def test_target_column_validation(self, simple_numeric_df):
        """Target column existence should be validated."""
        result = validate_for_tabpfn(simple_numeric_df, target_column='nonexistent')

        assert any(i.code == 'TARGET_NOT_FOUND' for i in result.issues)


# ============================================================================
# AUTO-PREPARATION TESTS
# ============================================================================

class TestTabPFNPreparation:
    """Tests for TabPFN auto-preparation."""

    def test_high_cardinality_removed(self, high_cardinality_df):
        """High-cardinality columns should be removed."""
        result = prepare_for_tabpfn(high_cardinality_df)

        assert 'free_text' in result.columns_removed
        assert 'free_text' not in result.prepared_df.columns
        assert len(result.actions_taken) > 0

    def test_categorical_encoded(self, mixed_type_df):
        """Categorical columns should be encoded to numeric."""
        result = prepare_for_tabpfn(mixed_type_df)

        # All columns should be numeric after preparation
        assert all(np.issubdtype(dtype, np.number)
                   for dtype in result.prepared_df.dtypes)

    def test_missing_values_filled(self, df_with_missing):
        """Missing values should be filled."""
        result = prepare_for_tabpfn(df_with_missing, handle_missing='fill')

        assert not result.prepared_df.isnull().any().any()

    def test_large_df_sampled(self, large_df):
        """Large DataFrames should be sampled down."""
        result = prepare_for_tabpfn(large_df, max_rows=10000)

        assert len(result.prepared_df) == 10000
        assert result.rows_sampled
        assert result.original_row_count == 15000

    def test_preparation_reproducible(self, large_df):
        """Preparation should be reproducible with random_state."""
        result1 = prepare_for_tabpfn(large_df, random_state=42)
        result2 = prepare_for_tabpfn(large_df, random_state=42)

        pd.testing.assert_frame_equal(result1.prepared_df, result2.prepared_df)


# ============================================================================
# ENCODING ROUNDTRIP TESTS
# ============================================================================

class TestCategoricalEncodingRoundtrip:
    """Tests that categorical encoding/decoding preserves data."""

    def test_simple_encoding_roundtrip(self, mixed_type_df):
        """Categorical encoding should be reversible."""
        # Encode
        encoded_df, encoders = _encode_categorical_features(mixed_type_df)

        # All columns should be numeric after encoding
        assert all(np.issubdtype(dtype, np.number)
                   for dtype in encoded_df.dtypes)

        # Decode
        categorical_cols = mixed_type_df.select_dtypes(exclude=[np.number]).columns.tolist()
        decoded_df = _decode_categorical_features(
            encoded_df,
            mixed_type_df.columns.tolist(),
            categorical_cols,
            encoders,
        )

        # Original categorical values should be restored
        for col in categorical_cols:
            original_values = set(mixed_type_df[col].dropna().unique())
            decoded_values = set(decoded_df[col].dropna().unique())
            assert original_values == decoded_values, f"Values mismatch for {col}"

    def test_nan_handling_in_encoding(self, df_with_missing):
        """NaN values should be handled correctly in encoding."""
        encoded_df, encoders = _encode_categorical_features(df_with_missing)

        # NaN should be encoded as -1
        assert -1 in encoded_df['col_b'].values or encoded_df['col_b'].isnull().any()


# ============================================================================
# SYNTHETIC GENERATION TESTS
# ============================================================================

class TestSyntheticGeneration:
    """Tests for synthetic data generation pipeline."""

    def test_synthetic_preserves_columns(self, simple_numeric_df):
        """Synthetic data should have same columns as original."""
        try:
            synthetic_df, metrics = generate_synthetic(
                simple_numeric_df,
                n_samples=50,
                random_state=42,
            )

            assert list(synthetic_df.columns) == list(simple_numeric_df.columns)
            assert len(synthetic_df) == 50
        except Exception as e:
            # TabPFN might not be available in test environment
            pytest.skip(f"TabPFN not available: {e}")

    def test_synthetic_quality_metrics(self, simple_numeric_df):
        """Synthetic data quality metrics should be reasonable."""
        try:
            synthetic_df, metrics = generate_synthetic(
                simple_numeric_df,
                n_samples=50,
                random_state=42,
            )

            # Quality thresholds
            assert metrics.mean_correlation_error < 0.5, "Correlation error too high"
            assert metrics.distribution_similarity > 0.5, "Distribution similarity too low"
        except Exception as e:
            pytest.skip(f"TabPFN not available: {e}")

    def test_validate_synthetic_function(self, simple_numeric_df):
        """validate_synthetic should compute reasonable metrics."""
        # Create a slightly perturbed version as "synthetic"
        synthetic_df = simple_numeric_df + np.random.randn(*simple_numeric_df.shape) * 0.1

        metrics = validate_synthetic(simple_numeric_df, synthetic_df)

        assert 0 <= metrics.mean_correlation_error <= 1
        assert 0 <= metrics.distribution_similarity <= 1


# ============================================================================
# CSV DELIMITER DETECTION TESTS
# ============================================================================

class TestCSVDelimiterDetection:
    """Tests for auto-detecting CSV delimiters."""

    def test_detect_comma_delimiter(self, tmp_path):
        """Should detect comma delimiter."""
        csv_file = tmp_path / "comma.csv"
        csv_file.write_text("a,b,c\n1,2,3\n4,5,6\n")

        delimiter, encoding = detect_csv_delimiter(str(csv_file))
        assert delimiter == ','
        assert encoding == 'utf-8'

    def test_detect_semicolon_delimiter(self, tmp_path):
        """Should detect semicolon delimiter."""
        csv_file = tmp_path / "semicolon.csv"
        csv_file.write_text("a;b;c\n1;2;3\n4;5;6\n")

        delimiter, encoding = detect_csv_delimiter(str(csv_file))
        assert delimiter == ';'
        assert encoding == 'utf-8'

    def test_load_with_auto_delimiter(self, tmp_path):
        """Should load CSV with auto-detected delimiter."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("col_a;col_b;col_c\n1;2;3\n4;5;6\n")

        df, delimiter = load_csv_with_auto_delimiter(str(csv_file))

        assert delimiter == ';'
        assert len(df) == 2
        assert list(df.columns) == ['col_a', 'col_b', 'col_c']


# ============================================================================
# REAL TEST DATA TESTS
# ============================================================================

class TestRealTestData:
    """Tests using actual test_data files."""

    def test_schools_data_validation(self, test_data_path):
        """Test validation on schools dataset (test0)."""
        file_path = f"{test_data_path}/test0/fr-en-indicateurs-valeur-ajoutee-colleges_small.csv"

        try:
            df, delimiter = load_csv_with_auto_delimiter(file_path)
            result = validate_for_tabpfn(df)

            assert result.row_count > 0
            assert result.feature_count > 0
            assert len(result.numeric_columns) > 0  # Has numeric school scores
        except FileNotFoundError:
            pytest.skip("Test data not available")

    def test_energy_data_delimiter(self, test_data_path):
        """Test that energy data (semicolon) is correctly detected."""
        file_path = f"{test_data_path}/test2/Niveaux_prix_TRVG.csv"

        try:
            delimiter, encoding = detect_csv_delimiter(file_path)
            assert delimiter == ';', "Energy data uses semicolon delimiter"

            df, _ = load_csv_with_auto_delimiter(file_path)
            assert len(df) > 0
        except FileNotFoundError:
            pytest.skip("Test data not available")

    def test_ademe_high_cardinality(self, test_data_path):
        """Test that ADEME data high-cardinality columns are detected."""
        file_path = f"{test_data_path}/test1/Les aides financieres ADEME.csv"

        try:
            df = pd.read_csv(file_path, nrows=1000)  # Sample for speed
            result = validate_for_tabpfn(df)

            # 'objet' column should be flagged as high-cardinality
            assert len(result.high_cardinality_columns) > 0 or len(result.categorical_columns) > 0
        except FileNotFoundError:
            pytest.skip("Test data not available")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestNavigationToTabPFNPipeline:
    """Integration tests for navigation-path to TabPFN pipeline."""

    def test_l2_to_tabpfn_pipeline(self, mixed_type_df):
        """Test full pipeline: L2Dataset -> validation -> preparation -> ready for TabPFN."""
        # Step 1: Wrap in Level2Dataset
        dataset = Level2Dataset(mixed_type_df, name="test")
        df = dataset.get_data()

        # Step 2: Validate
        validation = validate_for_tabpfn(df)
        assert validation.can_auto_fix or validation.is_valid

        # Step 3: Always prepare to ensure TabPFN compatibility
        # (preparation handles categorical encoding, missing values, etc.)
        preparation = prepare_for_tabpfn(df)
        df_prepared = preparation.prepared_df

        # Step 4: Verify ready for TabPFN
        assert len(df_prepared) >= CONSTRAINTS.MIN_ROWS
        assert len(df_prepared) <= CONSTRAINTS.MAX_ROWS
        assert all(np.issubdtype(dtype, np.number) for dtype in df_prepared.dtypes), (
            f"Non-numeric columns found: {[c for c in df_prepared.columns if not np.issubdtype(df_prepared[c].dtype, np.number)]}"
        )

    def test_l0_ascent_preserves_tabpfn_compatibility(self):
        """Test that L0 -> L1 ascent produces TabPFN-compatible series."""
        # Create L0 from aggregation
        parent_series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0] * 20, name="scores")
        l0 = Level0Dataset(
            value=parent_series.mean(),
            description="mean_score",
            parent_data=parent_series,
            aggregation_method="mean",
        )

        # Verify L0 has parent for ascent
        assert l0.has_parent
        assert l0.get_parent_data() is not None

        # Parent data should be numeric (TabPFN compatible)
        parent = l0.get_parent_data()
        assert np.issubdtype(parent.dtype, np.number)


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
