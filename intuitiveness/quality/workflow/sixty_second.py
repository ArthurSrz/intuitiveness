"""
60-Second Data Prep Workflow Orchestration.

Implements Spec 010: FR-002, FR-003, FR-004, FR-005

Orchestrates the complete workflow:
1. Upload messy CSV
2. Assess quality (< 30s)
3. Apply all suggestions (< 5s)
4. Export clean data + Python code (instant)

Total time: < 60 seconds for datasets up to 5,000 rows.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional, Callable
import pandas as pd

from intuitiveness.quality.assessor import assess_dataset, apply_all_suggestions
from intuitiveness.quality.exporter import generate_python_snippet
from intuitiveness.quality.models import QualityReport, TransformationLog
from intuitiveness.quality.workflow.traffic_light import (
    get_readiness_status,
    estimate_score_improvement,
    ReadinessStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class WorkflowResult:
    """Result of the 60-second workflow."""

    # Quality assessment
    quality_report: QualityReport
    readiness_status: ReadinessStatus

    # Transformations
    transformed_df: Optional[pd.DataFrame] = None
    transformation_log: Optional[TransformationLog] = None

    # Export
    export_csv: Optional[bytes] = None
    python_snippet: Optional[str] = None

    # Timing
    assessment_time: float = 0.0
    transformation_time: float = 0.0
    total_time: float = 0.0

    def meets_60s_target(self) -> bool:
        """Check if workflow completed in under 60 seconds."""
        return self.total_time < 60.0


def run_60_second_workflow(
    df: pd.DataFrame,
    target_column: str,
    auto_apply_suggestions: bool = True,
    progress_callback: Optional[Callable[[str, float], None]] = None,
) -> WorkflowResult:
    """
    Run the complete 60-second data prep workflow.

    Implements Spec 010: FR-001 through FR-005

    Args:
        df: Input DataFrame (messy CSV).
        target_column: Target column for prediction.
        auto_apply_suggestions: Whether to auto-apply all suggestions.
        progress_callback: Optional callback for progress updates (message, progress 0-1).

    Returns:
        WorkflowResult with transformed data and export materials.
    """
    start_time = time.time()

    def report_progress(message: str, progress: float):
        if progress_callback:
            progress_callback(message, progress)
        logger.info(f"[{progress*100:.0f}%] {message}")

    # Step 1: Assess quality (FR-001, target: <30s)
    report_progress("Assessing data quality...", 0.1)
    assessment_start = time.time()

    quality_report = assess_dataset(
        df,
        target_column=target_column,
        progress_callback=progress_callback
    )

    assessment_time = time.time() - assessment_start
    logger.info(f"Assessment completed in {assessment_time:.1f}s")
    report_progress(f"Quality score: {quality_report.usability_score:.1f}/100", 0.4)

    # Determine readiness status
    estimated_improvement = estimate_score_improvement(
        quality_report.suggestions,
        quality_report.usability_score
    )

    readiness_status = get_readiness_status(
        quality_report.usability_score,
        n_suggestions=len(quality_report.suggestions),
        estimated_improvement=estimated_improvement
    )

    # Step 2: Apply suggestions if requested (FR-002, target: <5s)
    transformed_df = None
    transformation_log = None
    transformation_time = 0.0

    if auto_apply_suggestions and quality_report.suggestions:
        report_progress(
            f"Applying {len(quality_report.suggestions)} suggestions...",
            0.5
        )
        transformation_start = time.time()

        try:
            transformed_df, transformation_log = apply_all_suggestions(
                df,
                quality_report.suggestions,
                target_column=target_column
            )

            transformation_time = time.time() - transformation_start
            logger.info(f"Transformations applied in {transformation_time:.1f}s")
            report_progress(f"Applied {len(transformation_log.transformations)} fixes", 0.8)

        except Exception as e:
            logger.error(f"Transformation failed: {e}")
            report_progress(f"Some transformations failed: {e}", 0.8)

    # Step 3: Prepare export materials (FR-003, FR-004)
    report_progress("Preparing export...", 0.9)

    # Export CSV (use transformed if available, otherwise original)
    export_df = transformed_df if transformed_df is not None else df
    export_csv = export_df.to_csv(index=False).encode('utf-8')

    # Generate Python snippet
    python_snippet = generate_python_snippet(
        dataset_name="clean_data.csv",
        target_column=target_column,
        transformations=transformation_log.transformations if transformation_log else []
    )

    total_time = time.time() - start_time
    logger.info(f"Workflow completed in {total_time:.1f}s")
    report_progress(f"✅ Ready! ({total_time:.1f}s)", 1.0)

    return WorkflowResult(
        quality_report=quality_report,
        readiness_status=readiness_status,
        transformed_df=transformed_df,
        transformation_log=transformation_log,
        export_csv=export_csv,
        python_snippet=python_snippet,
        assessment_time=assessment_time,
        transformation_time=transformation_time,
        total_time=total_time
    )


def quick_export(
    df: pd.DataFrame,
    target_column: str,
    filename: str = "clean_data.csv"
) -> tuple[bytes, str]:
    """
    Quick export without full workflow (when user just wants to export).

    Implements Spec 010: FR-003, FR-004

    Args:
        df: DataFrame to export.
        target_column: Target column name.
        filename: Output filename.

    Returns:
        Tuple of (CSV bytes, Python snippet string).
    """
    # Export CSV
    csv_bytes = df.to_csv(index=False).encode('utf-8')

    # Generate minimal Python snippet
    python_snippet = generate_python_snippet(
        dataset_name=filename,
        target_column=target_column,
        transformations=[]
    )

    return csv_bytes, python_snippet
