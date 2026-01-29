"""
Quality Data Platform - Data Models

Core data models for quality assessment, feature engineering,
anomaly detection, and synthetic data generation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Literal, Tuple
from uuid import UUID, uuid4


# ============================================================================
# TabPFN DIAGNOSTICS - Full Transparency Layer (P0 Fix)
# Captures all TabPFN internals for user transparency
# ============================================================================


@dataclass
class TabPFNDiagnostics:
    """
    Full transparency into TabPFN assessment process.

    Captures per-fold CV results, prediction confidence, estimator agreement,
    and all methodology details for user trust and interpretability.

    This addresses the ML engineer feedback: "I don't trust the interface
    on what TabPFN did - it should be transparent."
    """

    # Cross-validation details (not just mean!)
    fold_scores: List[float] = field(default_factory=list)
    mean_accuracy: float = 0.0
    std_accuracy: float = 0.0

    # Prediction confidence metrics
    prediction_confidence_mean: float = 0.0  # Mean of max class probabilities
    prediction_confidence_min: float = 0.0   # Lowest confidence prediction
    prediction_confidence_max: float = 0.0   # Highest confidence prediction

    # Estimator agreement (TabPFN uses 8 estimators internally)
    estimator_agreement: float = 0.0  # 1.0 = perfect agreement, 0.0 = no agreement

    # Feature handling transparency
    categorical_features_detected: List[str] = field(default_factory=list)
    numeric_features_used: List[str] = field(default_factory=list)

    # TabPFN internal parameters
    temperature_used: float = 1.0
    n_estimators: int = 8

    # Embeddings shape (for reference - embeddings can be extracted)
    embeddings_shape: Tuple[int, ...] = field(default_factory=tuple)

    # SHAP computation status
    shap_status: str = "not_computed"  # 'success' | 'failed' | 'not_computed'
    shap_error_message: Optional[str] = None
    shap_fallback_used: bool = False  # True if permutation importance was used

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "fold_scores": self.fold_scores,
            "mean_accuracy": self.mean_accuracy,
            "std_accuracy": self.std_accuracy,
            "prediction_confidence_mean": self.prediction_confidence_mean,
            "prediction_confidence_min": self.prediction_confidence_min,
            "prediction_confidence_max": self.prediction_confidence_max,
            "estimator_agreement": self.estimator_agreement,
            "categorical_features_detected": self.categorical_features_detected,
            "numeric_features_used": self.numeric_features_used,
            "temperature_used": self.temperature_used,
            "n_estimators": self.n_estimators,
            "embeddings_shape": list(self.embeddings_shape),
            "shap_status": self.shap_status,
            "shap_error_message": self.shap_error_message,
            "shap_fallback_used": self.shap_fallback_used,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TabPFNDiagnostics":
        """Create from dictionary."""
        return cls(
            fold_scores=data.get("fold_scores", []),
            mean_accuracy=data.get("mean_accuracy", 0.0),
            std_accuracy=data.get("std_accuracy", 0.0),
            prediction_confidence_mean=data.get("prediction_confidence_mean", 0.0),
            prediction_confidence_min=data.get("prediction_confidence_min", 0.0),
            prediction_confidence_max=data.get("prediction_confidence_max", 0.0),
            estimator_agreement=data.get("estimator_agreement", 0.0),
            categorical_features_detected=data.get("categorical_features_detected", []),
            numeric_features_used=data.get("numeric_features_used", []),
            temperature_used=data.get("temperature_used", 1.0),
            n_estimators=data.get("n_estimators", 8),
            embeddings_shape=tuple(data.get("embeddings_shape", [])),
            shap_status=data.get("shap_status", "not_computed"),
            shap_error_message=data.get("shap_error_message"),
            shap_fallback_used=data.get("shap_fallback_used", False),
        )


@dataclass
class FeatureProfile:
    """
    Per-feature statistics and importance scores.

    Attributes:
        feature_name: Column name in the dataset.
        feature_type: Detected data type (numeric, categorical, boolean, datetime).
        missing_count: Number of missing/null values.
        missing_ratio: Fraction of missing values (0-1).
        unique_count: Number of unique values.
        importance_score: TabPFN ablation importance (0-1, normalized).
        shap_mean: Mean absolute SHAP value for interpretability.
        distribution_skew: Skewness for numeric features.
        suggested_transform: Recommended transformation (log, normalize, etc.).
    """

    feature_name: str
    feature_type: Literal["numeric", "categorical", "boolean", "datetime"]
    missing_count: int = 0
    missing_ratio: float = 0.0
    unique_count: int = 0
    importance_score: float = 0.0
    shap_mean: float = 0.0
    distribution_skew: float = 0.0
    suggested_transform: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "feature_name": self.feature_name,
            "feature_type": self.feature_type,
            "missing_count": self.missing_count,
            "missing_ratio": self.missing_ratio,
            "unique_count": self.unique_count,
            "importance_score": self.importance_score,
            "shap_mean": self.shap_mean,
            "distribution_skew": self.distribution_skew,
            "suggested_transform": self.suggested_transform,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeatureProfile":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class FeatureSuggestion:
    """
    Recommended feature engineering action.

    Attributes:
        suggestion_type: Type of recommendation (remove, transform, combine).
        target_features: Feature(s) involved (1-2 elements).
        description: Plain-language explanation.
        expected_impact: Expected change in usability score (-100 to +100).
        confidence: Model confidence in suggestion (0-1).
    """

    suggestion_type: Literal["remove", "transform", "combine"]
    target_features: List[str]
    description: str
    expected_impact: float = 0.0
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "suggestion_type": self.suggestion_type,
            "target_features": self.target_features,
            "description": self.description,
            "expected_impact": self.expected_impact,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeatureSuggestion":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class AnomalyRecord:
    """
    Flagged row with unusual density score.

    Attributes:
        row_index: Original row number in dataset.
        anomaly_score: Log-density score (lower = more anomalous).
        percentile: Density percentile (lower = more anomalous).
        top_contributors: Top 3 features contributing to anomaly.
    """

    row_index: int
    anomaly_score: float
    percentile: float
    top_contributors: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "row_index": self.row_index,
            "anomaly_score": self.anomaly_score,
            "percentile": self.percentile,
            "top_contributors": self.top_contributors,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnomalyRecord":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class SyntheticDataMetrics:
    """
    Quality metrics for generated synthetic data.

    Attributes:
        n_samples: Number of generated rows.
        mean_correlation_error: Quality metric: correlation preservation (0-1).
        distribution_similarity: Quality metric: KS-test average (0-1).
        generation_time_seconds: Time taken to generate.
    """

    n_samples: int
    mean_correlation_error: float = 0.0
    distribution_similarity: float = 0.0
    generation_time_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "n_samples": self.n_samples,
            "mean_correlation_error": self.mean_correlation_error,
            "distribution_similarity": self.distribution_similarity,
            "generation_time_seconds": self.generation_time_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyntheticDataMetrics":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class QualityReport:
    """
    Results of a TabPFN-based quality assessment.

    Attributes:
        id: Unique identifier.
        usability_score: Composite quality score (0-100).
        prediction_quality: TabPFN cross-validation accuracy (0-100).
        data_completeness: (1 - missing_ratio) * 100.
        feature_diversity: Entropy of feature types (0-100).
        size_appropriateness: Penalty for extreme sizes (0-100).
        target_column: Column used for assessment.
        task_type: Detected or specified task (classification/regression).
        feature_profiles: List of per-feature profiles.
        anomalies: List of flagged anomalous rows.
        suggestions: List of feature engineering recommendations.
        assessment_time_seconds: Time taken for assessment.
        created_at: When assessment was run.
        row_count: Number of rows in assessed dataset.
        feature_count: Number of features assessed.
        sampled: Whether the dataset was sampled for assessment.
        sample_size: Size of sample if sampled.
    """

    id: UUID = field(default_factory=uuid4)
    usability_score: float = 0.0
    prediction_quality: float = 0.0
    data_completeness: float = 0.0
    feature_diversity: float = 0.0
    size_appropriateness: float = 0.0
    target_column: str = ""
    task_type: Literal["classification", "regression"] = "classification"
    feature_profiles: List[FeatureProfile] = field(default_factory=list)
    anomalies: List[AnomalyRecord] = field(default_factory=list)
    suggestions: List[FeatureSuggestion] = field(default_factory=list)
    assessment_time_seconds: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    row_count: int = 0
    feature_count: int = 0
    sampled: bool = False
    sample_size: Optional[int] = None

    # P0 FIX: Full TabPFN transparency - captures all methodology details
    tabpfn_diagnostics: Optional[TabPFNDiagnostics] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "usability_score": self.usability_score,
            "prediction_quality": self.prediction_quality,
            "data_completeness": self.data_completeness,
            "feature_diversity": self.feature_diversity,
            "size_appropriateness": self.size_appropriateness,
            "target_column": self.target_column,
            "task_type": self.task_type,
            "feature_profiles": [fp.to_dict() for fp in self.feature_profiles],
            "anomalies": [a.to_dict() for a in self.anomalies],
            "suggestions": [s.to_dict() for s in self.suggestions],
            "assessment_time_seconds": self.assessment_time_seconds,
            "created_at": self.created_at.isoformat(),
            "row_count": self.row_count,
            "feature_count": self.feature_count,
            "sampled": self.sampled,
            "sample_size": self.sample_size,
            "tabpfn_diagnostics": self.tabpfn_diagnostics.to_dict() if self.tabpfn_diagnostics else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QualityReport":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]) if isinstance(data.get("id"), str) else data.get("id", uuid4()),
            usability_score=data.get("usability_score", 0.0),
            prediction_quality=data.get("prediction_quality", 0.0),
            data_completeness=data.get("data_completeness", 0.0),
            feature_diversity=data.get("feature_diversity", 0.0),
            size_appropriateness=data.get("size_appropriateness", 0.0),
            target_column=data.get("target_column", ""),
            task_type=data.get("task_type", "classification"),
            feature_profiles=[
                FeatureProfile.from_dict(fp) for fp in data.get("feature_profiles", [])
            ],
            anomalies=[
                AnomalyRecord.from_dict(a) for a in data.get("anomalies", [])
            ],
            suggestions=[
                FeatureSuggestion.from_dict(s) for s in data.get("suggestions", [])
            ],
            assessment_time_seconds=data.get("assessment_time_seconds", 0.0),
            created_at=datetime.fromisoformat(data["created_at"])
            if isinstance(data.get("created_at"), str)
            else data.get("created_at", datetime.now()),
            row_count=data.get("row_count", 0),
            feature_count=data.get("feature_count", 0),
            sampled=data.get("sampled", False),
            sample_size=data.get("sample_size"),
            tabpfn_diagnostics=TabPFNDiagnostics.from_dict(data["tabpfn_diagnostics"]) if data.get("tabpfn_diagnostics") else None,
        )

    def get_top_features(self, n: int = 5) -> List[FeatureProfile]:
        """Get top N features by importance score."""
        return sorted(
            self.feature_profiles,
            key=lambda x: x.importance_score,
            reverse=True
        )[:n]

    def get_low_importance_features(self, threshold: float = 0.05) -> List[FeatureProfile]:
        """Get features with importance below threshold."""
        return [
            fp for fp in self.feature_profiles
            if fp.importance_score < threshold
        ]


# ============================================================================
# NEW DATA MODELS FOR 010-quality-ds-workflow
# Data Scientist Co-Pilot Feature
# ============================================================================


@dataclass
class ModelBenchmarkResult:
    """
    Benchmark results for a single model.

    Compares real→real training vs synthetic→real training performance.
    """

    model_name: str  # 'LogisticRegression' | 'RandomForest' | 'XGBoost'

    # Real → Real (baseline)
    real_accuracy: float = 0.0
    real_f1: float = 0.0
    real_precision: float = 0.0
    real_recall: float = 0.0

    # Synthetic → Real (transfer)
    synthetic_accuracy: float = 0.0
    synthetic_f1: float = 0.0
    synthetic_precision: float = 0.0
    synthetic_recall: float = 0.0

    @property
    def transfer_gap(self) -> float:
        """Percentage drop from real to synthetic training."""
        if self.real_accuracy == 0:
            return 1.0
        return (self.real_accuracy - self.synthetic_accuracy) / self.real_accuracy

    @property
    def transfer_gap_percent(self) -> str:
        """Human-readable transfer gap."""
        return f"{self.transfer_gap * 100:.1f}%"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "model_name": self.model_name,
            "real_accuracy": self.real_accuracy,
            "real_f1": self.real_f1,
            "real_precision": self.real_precision,
            "real_recall": self.real_recall,
            "synthetic_accuracy": self.synthetic_accuracy,
            "synthetic_f1": self.synthetic_f1,
            "synthetic_precision": self.synthetic_precision,
            "synthetic_recall": self.synthetic_recall,
            "transfer_gap": self.transfer_gap,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelBenchmarkResult":
        """Create from dictionary."""
        return cls(
            model_name=data["model_name"],
            real_accuracy=data.get("real_accuracy", 0.0),
            real_f1=data.get("real_f1", 0.0),
            real_precision=data.get("real_precision", 0.0),
            real_recall=data.get("real_recall", 0.0),
            synthetic_accuracy=data.get("synthetic_accuracy", 0.0),
            synthetic_f1=data.get("synthetic_f1", 0.0),
            synthetic_precision=data.get("synthetic_precision", 0.0),
            synthetic_recall=data.get("synthetic_recall", 0.0),
        )


@dataclass
class SyntheticBenchmarkReport:
    """
    Results of synthetic data validation pipeline.

    Train-on-synthetic/test-on-real methodology to prove synthetic data quality.
    """

    # Identification
    dataset_name: str = ""
    target_column: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # Generation parameters
    n_synthetic_samples: int = 0
    generation_method: str = "gaussian_copula"  # 'tabpfn' | 'gaussian_copula'
    class_balanced: bool = False

    # Benchmark results per model
    model_results: List[ModelBenchmarkResult] = field(default_factory=list)

    # Aggregate metrics
    mean_transfer_gap: float = 0.0
    max_transfer_gap: float = 0.0
    min_transfer_gap: float = 0.0
    # P1 FIX (Dr. Metric Mind): Add CI field for visualization
    transfer_gap_ci_95: float = 0.0  # 95% confidence interval on transfer gap

    # Recommendation
    recommendation: str = "not_recommended"  # 'safe_to_use' | 'use_with_caution' | 'not_recommended'
    recommendation_reason: str = ""

    @property
    def is_safe(self) -> bool:
        """Transfer gap < 10% is considered safe."""
        return self.mean_transfer_gap < 0.10

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "dataset_name": self.dataset_name,
            "target_column": self.target_column,
            "timestamp": self.timestamp.isoformat(),
            "n_synthetic_samples": self.n_synthetic_samples,
            "generation_method": self.generation_method,
            "class_balanced": self.class_balanced,
            "model_results": [r.to_dict() for r in self.model_results],
            "mean_transfer_gap": self.mean_transfer_gap,
            "max_transfer_gap": self.max_transfer_gap,
            "min_transfer_gap": self.min_transfer_gap,
            "transfer_gap_ci_95": self.transfer_gap_ci_95,
            "recommendation": self.recommendation,
            "recommendation_reason": self.recommendation_reason,
            "is_safe": self.is_safe,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyntheticBenchmarkReport":
        """Create from dictionary."""
        return cls(
            dataset_name=data.get("dataset_name", ""),
            target_column=data.get("target_column", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if isinstance(data.get("timestamp"), str) else datetime.now(),
            n_synthetic_samples=data.get("n_synthetic_samples", 0),
            generation_method=data.get("generation_method", "gaussian_copula"),
            class_balanced=data.get("class_balanced", False),
            model_results=[ModelBenchmarkResult.from_dict(r) for r in data.get("model_results", [])],
            mean_transfer_gap=data.get("mean_transfer_gap", 0.0),
            max_transfer_gap=data.get("max_transfer_gap", 0.0),
            min_transfer_gap=data.get("min_transfer_gap", 0.0),
            transfer_gap_ci_95=data.get("transfer_gap_ci_95", 0.0),
            recommendation=data.get("recommendation", "not_recommended"),
            recommendation_reason=data.get("recommendation_reason", ""),
        )


@dataclass
class TransformationResult:
    """
    Result of applying a single transformation.

    Tracks accuracy before/after to show ROI of each change.
    """

    suggestion_type: str  # 'remove' | 'transform' | 'combine'
    target_features: List[str] = field(default_factory=list)
    description: str = ""
    applied_at: datetime = field(default_factory=datetime.now)

    # Success/failure
    success: bool = True
    error: Optional[str] = None

    # Accuracy tracking (if target column specified)
    accuracy_before: Optional[float] = None
    accuracy_after: Optional[float] = None

    @property
    def accuracy_delta(self) -> Optional[float]:
        """Change in accuracy from this transformation."""
        if self.accuracy_before is None or self.accuracy_after is None:
            return None
        return self.accuracy_after - self.accuracy_before

    @property
    def accuracy_delta_percent(self) -> Optional[str]:
        """Human-readable accuracy change."""
        delta = self.accuracy_delta
        if delta is None:
            return None
        sign = "+" if delta >= 0 else ""
        return f"{sign}{delta * 100:.1f}%"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "suggestion_type": self.suggestion_type,
            "target_features": self.target_features,
            "description": self.description,
            "applied_at": self.applied_at.isoformat(),
            "success": self.success,
            "error": self.error,
            "accuracy_before": self.accuracy_before,
            "accuracy_after": self.accuracy_after,
            "accuracy_delta": self.accuracy_delta,
            "accuracy_delta_percent": self.accuracy_delta_percent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransformationResult":
        """Create from dictionary."""
        return cls(
            suggestion_type=data.get("suggestion_type", "transform"),
            target_features=data.get("target_features", []),
            description=data.get("description", ""),
            applied_at=datetime.fromisoformat(data["applied_at"]) if isinstance(data.get("applied_at"), str) else datetime.now(),
            success=data.get("success", True),
            error=data.get("error"),
            accuracy_before=data.get("accuracy_before"),
            accuracy_after=data.get("accuracy_after"),
        )


@dataclass
class TransformationLog:
    """
    Complete log of all transformations applied to a dataset.

    Provides audit trail and before/after metrics.
    """

    dataset_name: str = ""
    original_shape: tuple = (0, 0)  # (rows, cols)
    final_shape: tuple = (0, 0)

    # Individual results
    results: List[TransformationResult] = field(default_factory=list)

    # Aggregate metrics
    total_applied: int = 0
    total_failed: int = 0

    # Accuracy tracking
    initial_accuracy: Optional[float] = None
    final_accuracy: Optional[float] = None

    @property
    def total_accuracy_improvement(self) -> Optional[float]:
        """Total accuracy improvement from all transformations."""
        if self.initial_accuracy is None or self.final_accuracy is None:
            return None
        return self.final_accuracy - self.initial_accuracy

    def to_metadata(self) -> Dict[str, Any]:
        """Export as metadata for inclusion in exported files."""
        return {
            "original_shape": list(self.original_shape),
            "final_shape": list(self.final_shape),
            "transformations_applied": self.total_applied,
            "accuracy_improvement": self.total_accuracy_improvement,
            "transformations": [
                {
                    "type": r.suggestion_type,
                    "columns": r.target_features,
                    "delta": r.accuracy_delta_percent,
                }
                for r in self.results if r.success
            ],
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "dataset_name": self.dataset_name,
            "original_shape": list(self.original_shape),
            "final_shape": list(self.final_shape),
            "results": [r.to_dict() for r in self.results],
            "total_applied": self.total_applied,
            "total_failed": self.total_failed,
            "initial_accuracy": self.initial_accuracy,
            "final_accuracy": self.final_accuracy,
            "total_accuracy_improvement": self.total_accuracy_improvement,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransformationLog":
        """Create from dictionary."""
        return cls(
            dataset_name=data.get("dataset_name", ""),
            original_shape=tuple(data.get("original_shape", [0, 0])),
            final_shape=tuple(data.get("final_shape", [0, 0])),
            results=[TransformationResult.from_dict(r) for r in data.get("results", [])],
            total_applied=data.get("total_applied", 0),
            total_failed=data.get("total_failed", 0),
            initial_accuracy=data.get("initial_accuracy"),
            final_accuracy=data.get("final_accuracy"),
        )


@dataclass
class ReadinessIndicator:
    """
    Traffic light readiness indicator for dataset quality.

    Provides instant go/no-go visual for data scientists.
    """

    status: str = "needs_work"  # 'ready' | 'fixable' | 'needs_work'
    color: str = "red"  # 'green' | 'yellow' | 'red'
    score: float = 0.0  # 0-100 usability score

    # Messaging
    title: str = ""
    message: str = ""

    # Fixable details (if status == 'fixable')
    n_fixes_available: int = 0
    estimated_score_after_fixes: float = 0.0

    @classmethod
    def from_score(
        cls,
        score: float,
        n_suggestions: int = 0,
        estimated_improvement: float = 0.0,
    ) -> "ReadinessIndicator":
        """Create indicator from usability score."""
        if score >= 80:
            return cls(
                status="ready",
                color="green",
                score=score,
                title="READY FOR MODELING",
                message="Export and start training!",
            )
        elif score >= 60:
            projected_score = min(100, score + estimated_improvement)
            return cls(
                status="fixable",
                color="yellow",
                score=score,
                title="FIXABLE",
                message=f"{n_suggestions} automated fixes will improve score to {projected_score:.0f}",
                n_fixes_available=n_suggestions,
                estimated_score_after_fixes=projected_score,
            )
        else:
            return cls(
                status="needs_work",
                color="red",
                score=score,
                title="NEEDS WORK",
                message="Significant data issues. Review recommendations below.",
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status,
            "color": self.color,
            "score": self.score,
            "title": self.title,
            "message": self.message,
            "n_fixes_available": self.n_fixes_available,
            "estimated_score_after_fixes": self.estimated_score_after_fixes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReadinessIndicator":
        """Create from dictionary."""
        return cls(
            status=data.get("status", "needs_work"),
            color=data.get("color", "red"),
            score=data.get("score", 0.0),
            title=data.get("title", ""),
            message=data.get("message", ""),
            n_fixes_available=data.get("n_fixes_available", 0),
            estimated_score_after_fixes=data.get("estimated_score_after_fixes", 0.0),
        )


@dataclass
class ExportPackage:
    """
    Package containing exported dataset and supporting files.

    Includes Python code snippet for immediate use in Jupyter.

    P0 FIX: Added dataset field to hold actual DataFrame (Prof. Schema Whisperer).
    Note: dataset is excluded from serialization due to size.
    """

    # Core data
    dataset_name: str = "dataset"
    format: str = "csv"  # 'csv' | 'pickle' | 'parquet'

    # P0 FIX: The actual dataset - excluded from to_dict() serialization
    # Use field(default=None, repr=False) to avoid issues with mutable defaults
    dataset: Any = field(default=None, repr=False)

    # Metadata
    target_column: Optional[str] = None
    transformation_log: Optional[TransformationLog] = None
    row_count: int = 0
    column_count: int = 0

    # P0 FIX: Add task_type for correct model code generation
    task_type: Literal["classification", "regression"] = "classification"

    def __post_init__(self):
        """Auto-fill row/column count from dataset if provided."""
        if self.dataset is not None:
            import pandas as pd
            if isinstance(self.dataset, pd.DataFrame):
                if self.row_count == 0:
                    self.row_count = len(self.dataset)
                if self.column_count == 0:
                    self.column_count = len(self.dataset.columns)

    @property
    def filename(self) -> str:
        """Generated filename for export."""
        return f"{self.dataset_name}_clean.{self.format}"

    @property
    def python_snippet(self) -> str:
        """
        Generate robust Python code snippet for loading data and modeling.

        Features:
        - Auto-detects best task type (classification vs regression) at runtime
        - Handles TabPFN's 10-class limit for classification
        - Falls back to sklearn if TabPFN unavailable or fails
        - Provides clear feedback about model selection
        """
        from intuitiveness.quality.exporter import generate_python_snippet
        return generate_python_snippet(
            filename=self.filename,
            target_column=self.target_column or "target",
            format=self.format,
            task_type=self.task_type,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "dataset_name": self.dataset_name,
            "format": self.format,
            "target_column": self.target_column,
            "transformation_log": self.transformation_log.to_dict() if self.transformation_log else None,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "task_type": self.task_type,
            "filename": self.filename,
            "python_snippet": self.python_snippet,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExportPackage":
        """Create from dictionary."""
        return cls(
            dataset_name=data.get("dataset_name", "dataset"),
            format=data.get("format", "csv"),
            target_column=data.get("target_column"),
            transformation_log=TransformationLog.from_dict(data["transformation_log"]) if data.get("transformation_log") else None,
            row_count=data.get("row_count", 0),
            column_count=data.get("column_count", 0),
            task_type=data.get("task_type", "classification"),
        )


# ============================================================================
# INSTANT EXPORT DATA MODELS (012-tabpfn-instant-export)
# Simplified data export for non-technical domain experts
# ============================================================================


@dataclass
class CleaningAction:
    """
    Single data cleaning action applied during instant export.

    Used to build plain-language change log for user transparency.
    """

    action_type: str  # 'fill_missing' | 'encode_category' | 'remove_column' | 'convert_type'
    column: str
    description: str  # Plain language, no ML jargon
    rows_affected: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "action_type": self.action_type,
            "column": self.column,
            "description": self.description,
            "rows_affected": self.rows_affected,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CleaningAction":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ExportResult:
    """
    Result of instant export workflow.

    Spec: 012-tabpfn-instant-export

    Designed for non-technical users:
    - Binary readiness indicator (ready/needs_work)
    - Plain language summary (no ML jargon)
    - Cleaning log showing what was auto-fixed

    Attributes:
        is_ready: Binary readiness indicator (True = export immediately)
        status: 'ready' or 'needs_work'
        summary: Plain-language summary for domain expert
        warnings: List of human-readable warnings (no technical terms)
        cleaning_actions: Log of auto-applied cleaning operations
        cleaned_df: The cleaned DataFrame (ready for export)
        original_row_count: Rows before cleaning
        cleaned_row_count: Rows after cleaning
        original_col_count: Columns before cleaning
        cleaned_col_count: Columns after cleaning
        target_column: Column used for validation
        task_type: Detected task type
        validation_score: Optional quick validation score (0-100)
        processing_time_seconds: Time taken for check & clean
    """

    # Core readiness
    is_ready: bool = False
    status: Literal["ready", "needs_work"] = "needs_work"
    summary: str = ""

    # User-facing info (no ML jargon)
    warnings: List[str] = field(default_factory=list)
    cleaning_actions: List[CleaningAction] = field(default_factory=list)

    # Cleaned data reference (excluded from serialization due to size)
    cleaned_df: Any = field(default=None, repr=False)

    # Metadata
    original_row_count: int = 0
    cleaned_row_count: int = 0
    original_col_count: int = 0
    cleaned_col_count: int = 0
    target_column: str = ""
    task_type: Literal["classification", "regression"] = "classification"

    # Optional validation
    validation_score: Optional[float] = None  # 0-100 if TabPFN validation ran
    validation_error: Optional[str] = None  # Why validation failed (if it did)

    # Performance
    processing_time_seconds: float = 0.0
    api_calls_used: int = 0  # Should be ≤5 per spec

    def __post_init__(self):
        """Auto-calculate status from is_ready."""
        self.status = "ready" if self.is_ready else "needs_work"

    @property
    def rows_removed(self) -> int:
        """Number of rows removed during cleaning."""
        return self.original_row_count - self.cleaned_row_count

    @property
    def cols_removed(self) -> int:
        """Number of columns removed during cleaning."""
        return self.original_col_count - self.cleaned_col_count

    def get_cleaning_summary(self) -> str:
        """Get plain-language summary of cleaning actions."""
        if not self.cleaning_actions:
            return "No changes needed - your data was already clean!"

        action_counts = {}
        for action in self.cleaning_actions:
            action_counts[action.action_type] = action_counts.get(action.action_type, 0) + 1

        parts = []
        if action_counts.get("fill_missing", 0):
            parts.append(f"filled {action_counts['fill_missing']} columns with missing values")
        if action_counts.get("encode_category", 0):
            parts.append(f"converted {action_counts['encode_category']} text columns to numbers")
        if action_counts.get("remove_column", 0):
            parts.append(f"removed {action_counts['remove_column']} unusable columns")
        if action_counts.get("convert_type", 0):
            parts.append(f"fixed {action_counts['convert_type']} column types")

        return "Auto-cleaned: " + ", ".join(parts) + "."

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_ready": self.is_ready,
            "status": self.status,
            "summary": self.summary,
            "warnings": self.warnings,
            "cleaning_actions": [a.to_dict() for a in self.cleaning_actions],
            "original_row_count": self.original_row_count,
            "cleaned_row_count": self.cleaned_row_count,
            "original_col_count": self.original_col_count,
            "cleaned_col_count": self.cleaned_col_count,
            "target_column": self.target_column,
            "task_type": self.task_type,
            "validation_score": self.validation_score,
            "processing_time_seconds": self.processing_time_seconds,
            "api_calls_used": self.api_calls_used,
            "cleaning_summary": self.get_cleaning_summary(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExportResult":
        """Create from dictionary."""
        return cls(
            is_ready=data.get("is_ready", False),
            status=data.get("status", "needs_work"),
            summary=data.get("summary", ""),
            warnings=data.get("warnings", []),
            cleaning_actions=[
                CleaningAction.from_dict(a) for a in data.get("cleaning_actions", [])
            ],
            original_row_count=data.get("original_row_count", 0),
            cleaned_row_count=data.get("cleaned_row_count", 0),
            original_col_count=data.get("original_col_count", 0),
            cleaned_col_count=data.get("cleaned_col_count", 0),
            target_column=data.get("target_column", ""),
            task_type=data.get("task_type", "classification"),
            validation_score=data.get("validation_score"),
            processing_time_seconds=data.get("processing_time_seconds", 0.0),
            api_calls_used=data.get("api_calls_used", 0),
        )
