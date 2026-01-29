"""
Quality Data Platform - Quality Assessment Module

This module provides TabPFN-based dataset quality assessment, feature engineering
suggestions, anomaly detection, and synthetic data generation.

Primary Components:
- assessor: Dataset quality assessment with usability scores
- feature_engineer: Feature engineering suggestions
- anomaly_detector: Density-based anomaly detection
- synthetic_generator: Synthetic data generation
- report: Quality report generation and export
"""

from intuitiveness.quality.models import (
    QualityReport,
    FeatureProfile,
    FeatureSuggestion,
    AnomalyRecord,
    SyntheticDataMetrics,
    # New models for 010-quality-ds-workflow
    SyntheticBenchmarkReport,
    ModelBenchmarkResult,
    TransformationResult,
    TransformationLog,
    ReadinessIndicator,
    ExportPackage,
)

from intuitiveness.quality.assessor import (
    assess_dataset,
    apply_all_suggestions,
    get_readiness_indicator,
    quick_benchmark,
)

# Feature profiling utilities (Spec 009: FR-002, extracted from assessor.py)
from intuitiveness.quality.feature_profiler import (
    compute_feature_profile,
    compute_data_completeness,
    compute_feature_diversity,
    compute_size_appropriateness,
    compute_usability_score,
    build_feature_profiles,
)

# Data preparation utilities (Spec 009: FR-009, extracted from assessor.py)
from intuitiveness.quality.data_preparer import (
    DatasetWarning,
    handle_high_cardinality_categorical,
    select_top_features,
    check_dataset_edge_cases,
    prepare_data_for_tabpfn,
)

from intuitiveness.quality.feature_engineer import (
    suggest_features,
    apply_suggestion,
)

from intuitiveness.quality.anomaly_detector import (
    detect_anomalies,
    explain_anomaly,
    get_anomaly_summary,
)

from intuitiveness.quality.synthetic_generator import (
    generate_synthetic,
    validate_synthetic,
    check_tabpfn_auth,
    get_synthetic_summary,
)

from intuitiveness.quality.benchmark import (
    benchmark_synthetic,
    generate_balanced_synthetic,
    generate_targeted_synthetic,
)

from intuitiveness.quality.exporter import (
    export_dataset,
    export_to_bytes,
    export_with_metadata,
    generate_python_snippet,
    get_mime_type,
)

# 60-second workflow (Spec 010: FR-001 through FR-005)
from intuitiveness.quality.workflow import (
    ReadinessStatus,
    get_readiness_status,
    estimate_score_improvement,
    GREEN_THRESHOLD,
    YELLOW_THRESHOLD,
    WorkflowResult,
    run_60_second_workflow,
    quick_export,
)

# Instant Export (Spec 012: tabpfn-instant-export)
from intuitiveness.quality.instant_export import (
    InstantExporter,
    instant_check_and_export,
    export_clean_csv,
)

from intuitiveness.quality.models import (
    ExportResult,
    CleaningAction,
)

__all__ = [
    # Models
    "QualityReport",
    "FeatureProfile",
    "FeatureSuggestion",
    "AnomalyRecord",
    "SyntheticDataMetrics",
    # New models for 010-quality-ds-workflow
    "SyntheticBenchmarkReport",
    "ModelBenchmarkResult",
    "TransformationResult",
    "TransformationLog",
    "ReadinessIndicator",
    "ExportPackage",
    # Assessment functions
    "assess_dataset",
    "apply_all_suggestions",
    "get_readiness_indicator",
    "quick_benchmark",
    # Feature profiling functions (extracted from assessor.py)
    "compute_feature_profile",
    "compute_data_completeness",
    "compute_feature_diversity",
    "compute_size_appropriateness",
    "compute_usability_score",
    "build_feature_profiles",
    # Data preparation functions (extracted from assessor.py)
    "DatasetWarning",
    "handle_high_cardinality_categorical",
    "select_top_features",
    "check_dataset_edge_cases",
    "prepare_data_for_tabpfn",
    # Feature engineering functions
    "suggest_features",
    "apply_suggestion",
    # Anomaly detection functions
    "detect_anomalies",
    "explain_anomaly",
    "get_anomaly_summary",
    # Synthetic data functions
    "generate_synthetic",
    "validate_synthetic",
    "check_tabpfn_auth",
    "get_synthetic_summary",
    # Benchmark functions (new)
    "benchmark_synthetic",
    "generate_balanced_synthetic",
    "generate_targeted_synthetic",
    # Export functions (new)
    "export_dataset",
    "export_to_bytes",
    "export_with_metadata",
    "generate_python_snippet",
    "get_mime_type",
    # 60-second workflow (Spec 010)
    "ReadinessStatus",
    "get_readiness_status",
    "estimate_score_improvement",
    "GREEN_THRESHOLD",
    "YELLOW_THRESHOLD",
    "WorkflowResult",
    "run_60_second_workflow",
    "quick_export",
    # Instant Export (Spec 012)
    "InstantExporter",
    "instant_check_and_export",
    "export_clean_csv",
    "ExportResult",
    "CleaningAction",
]
