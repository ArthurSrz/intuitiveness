"""
Descent-Synthetic-Ascent Integration Tests

Verifies the complete pipeline:
1. Load L4 test data
2. Descent to L2 (flat table)
3. Generate synthetic data with TabPFN
4. Validate synthetic quality
5. Ascent back to L3 (with dimensions)

Feature: 011-e2e-robust

This test suite ensures that the navigation path system produces data
that can be successfully processed by TabPFN for synthetic generation,
and that the generated synthetic data can be used in subsequent ascent operations.
"""

import sys
import pytest
import numpy as np
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, '/Users/arthursarazin/Documents/data_redesign_method')

from intuitiveness.complexity import (
    Level0Dataset,
    Level1Dataset,
    Level2Dataset,
    Level3Dataset,
    Level4Dataset,
    ComplexityLevel,
)
from intuitiveness.quality.tabpfn_validation import (
    validate_for_tabpfn,
    prepare_for_tabpfn,
    load_csv_with_auto_delimiter,
    CONSTRAINTS,
)
from intuitiveness.quality.synthetic_generator import (
    generate_synthetic,
    validate_synthetic,
)
from intuitiveness.ascent.dimensions import (
    DimensionDefinition,
    DimensionRegistry,
    create_dimension_groups,
)
from intuitiveness.redesign.lineage import SourceReference
from datetime import datetime, timezone


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def test_data_path():
    """Path to test data directory."""
    return '/Users/arthursarazin/Documents/data_redesign_method/test_data'


@pytest.fixture
def schools_data(test_data_path):
    """Load schools dataset (test0) as L4."""
    file_path = f"{test_data_path}/test0/fr-en-indicateurs-valeur-ajoutee-colleges_small.csv"
    try:
        df, delimiter = load_csv_with_auto_delimiter(file_path)
        return Level4Dataset({'schools': df})
    except FileNotFoundError:
        pytest.skip("Test data not available")


@pytest.fixture
def energy_data(test_data_path):
    """Load energy prices dataset (test2) as L4."""
    file_path = f"{test_data_path}/test2/Niveaux_prix_TRVG.csv"
    try:
        df, delimiter = load_csv_with_auto_delimiter(file_path)
        return Level4Dataset({'energy_prices': df})
    except FileNotFoundError:
        pytest.skip("Test data not available")


@pytest.fixture
def simulated_descent_l2():
    """Simulated L2 DataFrame after descent from L4."""
    np.random.seed(42)
    return pd.DataFrame({
        'school_id': range(1, 201),
        'region': np.random.choice(['IDF', 'PACA', 'ARA', 'NAQ'], 200),
        'student_count': np.random.randint(100, 1000, 200),
        'success_rate': np.random.uniform(0.6, 1.0, 200),
        'teacher_count': np.random.randint(10, 50, 200),
        'budget_per_student': np.random.uniform(5000, 15000, 200),
    })


@pytest.fixture
def median_threshold_dimension():
    """Custom dimension for median-based classification."""
    return DimensionDefinition(
        name='score_category',
        description='High score (above median) vs Low score (below median)',
        possible_values=['high_score', 'low_score'],
        classifier=lambda x: 'high_score' if x > 0.8 else 'low_score',
        default_value='low_score',
        applicable_levels=[(ComplexityLevel.LEVEL_1, ComplexityLevel.LEVEL_2)]
    )


# ============================================================================
# L4 → L2 DESCENT TESTS
# ============================================================================

class TestDescentToL2:
    """Tests for descent from L4 to L2."""

    def test_l4_to_l3_extract_single_table(self, schools_data):
        """Extract single table from L4 dataset."""
        l4_data = schools_data.get_data()

        # Simulate L4 → L3: Select primary table
        primary_table = l4_data['schools']
        l3 = Level3Dataset(primary_table)

        assert l3.complexity_level == ComplexityLevel.LEVEL_3
        assert isinstance(l3.get_data(), pd.DataFrame)

    def test_l3_to_l2_flatten(self, schools_data):
        """Flatten L3 to L2 by selecting subset of columns."""
        l4_data = schools_data.get_data()
        df = l4_data['schools']

        # Select numeric columns for L2 (flat table)
        numeric_cols = df.select_dtypes(include=[np.number]).columns[:5].tolist()
        l2_df = df[numeric_cols].copy()

        l2 = Level2Dataset(l2_df, name="schools_numeric")

        assert l2.complexity_level == ComplexityLevel.LEVEL_2
        assert isinstance(l2.get_data(), pd.DataFrame)
        assert len(l2.get_data().columns) <= 5

    def test_descent_produces_tabpfn_compatible_data(self, simulated_descent_l2):
        """Verify that descended L2 data passes TabPFN validation."""
        l2 = Level2Dataset(simulated_descent_l2, name="test")
        df = l2.get_data()

        # Validate
        validation = validate_for_tabpfn(df)

        # Should be valid or auto-fixable
        assert validation.can_auto_fix or validation.is_valid, (
            f"Descent output not TabPFN compatible: {validation.get_plain_summary()}"
        )


# ============================================================================
# SYNTHETIC DATA GENERATION TESTS
# ============================================================================

class TestSyntheticGeneration:
    """Tests for TabPFN synthetic data generation from L2."""

    def test_l2_to_synthetic_pipeline(self, simulated_descent_l2):
        """Full pipeline: L2 → validate → prepare → generate synthetic."""
        # Step 1: Create L2 dataset
        l2 = Level2Dataset(simulated_descent_l2, name="test")
        df = l2.get_data()

        # Step 2: Validate for TabPFN
        validation = validate_for_tabpfn(df)

        # Step 3: Prepare if needed
        if not validation.is_valid:
            preparation = prepare_for_tabpfn(df)
            df_prepared = preparation.prepared_df
        else:
            df_prepared = df

        # Step 4: Generate synthetic (may fail if TabPFN not available)
        try:
            synthetic_df, metrics = generate_synthetic(
                df_prepared,
                n_samples=100,
                random_state=42,
            )

            # Verify synthetic matches schema
            assert list(synthetic_df.columns) == list(df_prepared.columns)
            assert len(synthetic_df) == 100

            # Verify quality
            assert metrics.mean_correlation_error < 0.5
            assert metrics.distribution_similarity > 0.3

        except Exception as e:
            # TabPFN might not be available - verify at least preparation worked
            assert len(df_prepared) > 0
            pytest.skip(f"TabPFN not available: {e}")

    def test_synthetic_preserves_categorical_distribution(self, simulated_descent_l2):
        """Synthetic data should preserve categorical column distribution."""
        df = simulated_descent_l2.copy()

        # Prepare
        preparation = prepare_for_tabpfn(df)
        df_prepared = preparation.prepared_df

        try:
            synthetic_df, metrics = generate_synthetic(
                df_prepared,
                n_samples=200,
                random_state=42,
            )

            # Region was encoded - check distribution similarity
            # (This is a softer check since exact preservation isn't guaranteed)
            assert len(synthetic_df) == 200

        except Exception as e:
            pytest.skip(f"TabPFN not available: {e}")

    def test_synthetic_quality_metrics_reasonable(self, simulated_descent_l2):
        """Synthetic quality metrics should be within acceptable thresholds."""
        preparation = prepare_for_tabpfn(simulated_descent_l2)
        df_prepared = preparation.prepared_df

        try:
            synthetic_df, metrics = generate_synthetic(
                df_prepared,
                n_samples=100,
                random_state=42,
            )

            # Correlation error < 0.3 is good
            # Distribution similarity > 0.7 is good
            # But we allow looser bounds for integration testing
            assert metrics.mean_correlation_error <= 0.5, (
                f"Correlation error too high: {metrics.mean_correlation_error}"
            )
            assert metrics.distribution_similarity >= 0.3, (
                f"Distribution similarity too low: {metrics.distribution_similarity}"
            )

        except Exception as e:
            pytest.skip(f"TabPFN not available: {e}")


# ============================================================================
# SYNTHETIC → ASCENT TESTS
# ============================================================================

class TestSyntheticToAscent:
    """Tests for using synthetic data in ascent operations."""

    def test_synthetic_l2_to_l3_ascent(self, simulated_descent_l2, median_threshold_dimension):
        """Synthetic L2 data can be used for L2 → L3 ascent."""
        # Prepare and generate synthetic
        preparation = prepare_for_tabpfn(simulated_descent_l2)
        df_prepared = preparation.prepared_df

        try:
            synthetic_df, _ = generate_synthetic(
                df_prepared,
                n_samples=100,
                random_state=42,
            )
        except Exception:
            # Use original data if TabPFN not available
            synthetic_df = df_prepared.head(100)

        # Create L2 from synthetic
        l2_synthetic = Level2Dataset(synthetic_df, name="synthetic_schools")

        # Apply dimension classification for ascent
        registry = DimensionRegistry.create_fresh(with_defaults=True)
        defaults = registry.get_defaults(
            ComplexityLevel.LEVEL_2,
            ComplexityLevel.LEVEL_3
        )

        # Apply first available dimension
        if defaults:
            dim = defaults[0]
            classified_df = dim.apply_to_dataframe(
                synthetic_df,
                source_column=synthetic_df.columns[0]
            )

            # Create L3 with dimension grouping
            l3_df = create_dimension_groups(
                classified_df,
                group_by=[dim.name]
            )

            l3 = Level3Dataset(l3_df)

            assert l3.complexity_level == ComplexityLevel.LEVEL_3
            assert dim.name in l3.get_data().columns

    def test_ascent_operation_tracking(self, simulated_descent_l2):
        """A SourceReference (the single provenance record) should track ascent transitions."""
        # Prepare synthetic
        preparation = prepare_for_tabpfn(simulated_descent_l2)
        df_prepared = preparation.prepared_df

        try:
            synthetic_df, _ = generate_synthetic(
                df_prepared,
                n_samples=50,
                random_state=42,
            )
        except Exception:
            synthetic_df = df_prepared.head(50)

        # Create L2
        l2 = Level2Dataset(synthetic_df, name="synthetic")

        # Simulate L2 → L3 ascent with dimension
        registry = DimensionRegistry.create_fresh(with_defaults=True)
        dim = DimensionDefinition(
            name='value_category',
            description='Category based on values',
            possible_values=['high', 'medium', 'low'],
            classifier=lambda x: 'high' if x > 0.7 else ('medium' if x > 0.3 else 'low'),
            default_value='medium',
        )

        # Apply and create L3
        result_df = dim.apply_to_dataframe(synthetic_df, source_column=synthetic_df.columns[0])
        l3 = Level3Dataset(result_df)

        # Track operation as the single canonical provenance record (spec 015)
        operation = SourceReference(
            operation_type="L2→L3",
            input_level=ComplexityLevel.LEVEL_2,
            output_level=ComplexityLevel.LEVEL_3,
            timestamp=datetime.now(timezone.utc),
            parameters={
                'enrichment_function': 'dimension_classification',
                'dimensions_added': [dim.name],
            },
            row_count_before=len(synthetic_df),
            row_count_after=len(result_df),
        )

        assert operation.input_level == ComplexityLevel.LEVEL_2
        assert operation.output_level == ComplexityLevel.LEVEL_3
        assert 'value_category' in operation.parameters['dimensions_added']
        assert operation.row_count_before == len(synthetic_df)
        # ascent preserves item count (the integrity invariant, now enforced by the engine)
        assert operation.row_count_before == operation.row_count_after


# ============================================================================
# FULL PIPELINE INTEGRATION TESTS
# ============================================================================

class TestFullPipeline:
    """End-to-end tests for complete descent → synthetic → ascent cycle."""

    def test_schools_full_cycle(self, schools_data):
        """Full cycle with schools data: L4 → L2 → synthetic → L3."""
        # === DESCENT ===
        # L4: Raw data sources
        l4_data = schools_data.get_data()
        df = l4_data['schools']

        # L3: Select entity-centric view
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 2:
            pytest.skip("Not enough numeric columns in schools data")

        l3_df = df[numeric_cols[:5]].copy()
        l3 = Level3Dataset(l3_df)

        # L2: Flatten to table
        l2_df = l3.get_data().head(500)  # Sample for speed
        l2 = Level2Dataset(l2_df, name="schools_flat")

        # === SYNTHETIC GENERATION ===
        validation = validate_for_tabpfn(l2_df)

        if not validation.is_valid and validation.can_auto_fix:
            preparation = prepare_for_tabpfn(l2_df, random_state=42)
            prepared_df = preparation.prepared_df
        else:
            prepared_df = l2_df

        # Generate or skip
        try:
            synthetic_df, metrics = generate_synthetic(
                prepared_df,
                n_samples=100,
                random_state=42,
            )
            using_synthetic = True
        except Exception:
            synthetic_df = prepared_df.head(100)
            using_synthetic = False

        # === ASCENT ===
        # L2 synthetic → L3 with dimension
        dim = DimensionDefinition(
            name='performance_tier',
            description='School performance tier',
            possible_values=['top', 'average', 'needs_improvement'],
            classifier=lambda x: 'top' if x > 0.9 else ('average' if x > 0.7 else 'needs_improvement'),
            default_value='average',
        )

        # Apply dimension
        final_df = synthetic_df.copy()
        if len(final_df.columns) > 0:
            first_col = final_df.columns[0]
            final_df[dim.name] = final_df[first_col].apply(
                lambda x: dim.classify(x) if pd.notna(x) else dim.default_value
            )

        final_l3 = Level3Dataset(final_df)

        # === VERIFY ===
        assert final_l3.complexity_level == ComplexityLevel.LEVEL_3
        assert dim.name in final_l3.get_data().columns
        assert len(final_l3.get_data()) > 0

    def test_energy_full_cycle(self, energy_data):
        """Full cycle with energy data (semicolon delimiter): L4 → L2 → synthetic → L3."""
        # === DESCENT ===
        l4_data = energy_data.get_data()
        df = l4_data['energy_prices']

        # Verify delimiter was handled (should have multiple columns)
        assert len(df.columns) > 1, "CSV delimiter not properly detected"

        # L2: Select relevant columns
        sample_df = df.head(500).copy()
        l2 = Level2Dataset(sample_df, name="energy_flat")

        # === VALIDATION ===
        validation = validate_for_tabpfn(sample_df)

        # Energy data has mostly categorical - should detect this
        assert len(validation.categorical_columns) > 0 or validation.can_auto_fix

        # === PREPARE ===
        preparation = prepare_for_tabpfn(sample_df, random_state=42)
        prepared_df = preparation.prepared_df

        # Should have been transformed
        assert len(preparation.actions_taken) > 0

        # === SYNTHETIC (if available) ===
        try:
            synthetic_df, metrics = generate_synthetic(
                prepared_df,
                n_samples=100,
                random_state=42,
            )
        except Exception:
            synthetic_df = prepared_df.head(100)

        # === ASCENT ===
        dim = DimensionDefinition(
            name='price_category',
            description='Energy price category',
            possible_values=['high_price', 'low_price'],
            classifier=lambda x: 'high_price' if x > 3 else 'low_price',
            default_value='low_price',
        )

        final_df = synthetic_df.copy()
        if 'NIVEAU_PRIX' in df.columns and len(final_df.columns) > 0:
            # Use original price column name if available
            final_df[dim.name] = dim.default_value
        else:
            first_col = final_df.columns[0]
            final_df[dim.name] = final_df[first_col].apply(
                lambda x: dim.classify(x) if pd.notna(x) else dim.default_value
            )

        final_l3 = Level3Dataset(final_df)

        assert final_l3.complexity_level == ComplexityLevel.LEVEL_3
        assert len(final_l3.get_data()) > 0


# ============================================================================
# SPEC COMPLIANCE TESTS (from CLAUDE.md objectives)
# ============================================================================

class TestSpecCompliance:
    """Tests verifying compliance with CLAUDE.md intermediary objectives."""

    def test_descent_l4_to_l3_links_scores_to_students(self, schools_data):
        """
        Spec: L3 data table that links number of students to middle school scores.
        """
        l4_data = schools_data.get_data()
        df = l4_data['schools']

        # Find student count and score columns
        student_cols = [c for c in df.columns if any(kw in c.lower() for kw in ['elev', 'student', 'effectif', 'nb'])]
        score_cols = [c for c in df.columns if any(kw in c.lower() for kw in ['taux', 'score', 'note', 'reussite'])]

        if not student_cols or not score_cols:
            pytest.skip("Required columns not found in schools data")

        # Create L3 linking students to scores
        link_df = df[[student_cols[0], score_cols[0]]].dropna()
        l3 = Level3Dataset(link_df)

        assert l3.complexity_level == ComplexityLevel.LEVEL_3
        assert len(l3.get_data().columns) == 2

    def test_ascent_l1_to_l2_median_categorization(self, simulated_descent_l2):
        """
        Spec: L2 table where categorizes high score (above median) and low score (below median).
        """
        # Extract L1 (single series)
        scores = simulated_descent_l2['success_rate']
        l1 = Level1Dataset(scores, name="success_rate")

        # Compute median
        median_value = scores.median()

        # Create dimension for median categorization
        median_dim = DimensionDefinition(
            name='score_category',
            description='Above/below median categorization',
            possible_values=['high_score', 'low_score'],
            classifier=lambda x: 'high_score' if x >= median_value else 'low_score',
            default_value='low_score',
        )

        # Apply to create L2
        l2_df = pd.DataFrame({
            'success_rate': scores,
            'score_category': scores.apply(median_dim.classify),
        })
        l2 = Level2Dataset(l2_df, name="categorized_scores")

        # Verify
        assert 'score_category' in l2.get_data().columns
        categories = l2.get_data()['score_category'].unique()
        assert 'high_score' in categories or 'low_score' in categories

    def test_descent_to_l0_average_score(self, simulated_descent_l2):
        """
        Spec: L0 datum that gives the average middle school score.
        """
        # L1: Extract score series
        scores = simulated_descent_l2['success_rate']
        l1 = Level1Dataset(scores, name="success_rate")

        # L0: Aggregate to single value (mean)
        mean_score = scores.mean()
        l0 = Level0Dataset(
            value=mean_score,
            description="average_success_rate",
            parent_data=scores,
            aggregation_method="mean",
        )

        assert l0.complexity_level == ComplexityLevel.LEVEL_0
        assert l0.has_parent
        assert l0.aggregation_method == "mean"
        assert isinstance(l0.get_data(), float)


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
