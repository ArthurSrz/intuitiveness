"""
Quality Data Platform - Quality Dashboard UI (REFACTORED)

Implements Spec 011: Code Simplification (1,433 → ~300 lines)

Thin orchestration layer that delegates to ui/quality/ package modules.

Architecture:
- ui/quality/upload.py: File upload & target selection
- ui/quality/assessment.py: Assessment button & progress
- ui/quality/readiness.py: Traffic light indicator & methodology
- ui/quality/suggestions.py: Feature suggestions & apply all
- ui/quality/ml_diagnostics.py: ML visualizations
- ui/quality/state.py: Report history management
- ui/quality/workflow_ui.py: 60-second workflow
- ui/quality/anomaly_ui.py: Anomaly detection
- This file: Main dashboard orchestrator only

Spec Traceability:
- 009-quality-data-platform: Quality assessment core
- 010-quality-ds-workflow: DS Co-Pilot features (US-1 through US-4)
- 011-code-simplification: Module extraction & simplification
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Optional

# Layout components
from intuitiveness.ui.layout import card, spacer
from intuitiveness.ui.header import render_page_header, render_section_header
from intuitiveness.ui.alert import info, warning

# Quality UI modules (Phase 1.3: 011-code-simplification)
from intuitiveness.ui.quality.utils import (
    SESSION_KEY_QUALITY_REPORT,
    SESSION_KEY_QUALITY_DF,
    SESSION_KEY_QUALITY_FILE_NAME,
    SESSION_KEY_TRANSFORMED_DF,
    SESSION_KEY_TRANSFORMATION_LOG,
    SESSION_KEY_BENCHMARK_REPORT,
    SESSION_KEY_APPLIED_SUGGESTIONS,
    get_score_color,
    get_score_label,
)

from intuitiveness.ui.quality.state import (
    clear_report_history,
    render_quality_score_evolution,
)

from intuitiveness.ui.quality.upload import (
    render_file_upload,
    render_target_selection,
)

from intuitiveness.ui.quality.assessment import (
    render_assessment_button,
)

from intuitiveness.ui.quality.readiness import (
    render_readiness_indicator,
    render_tabpfn_methodology,
)

from intuitiveness.ui.quality.suggestions import (
    render_feature_suggestions,
)

from intuitiveness.ui.quality.ml_diagnostics import (
    render_ml_diagnostics,
)

from intuitiveness.ui.quality.workflow_ui import (
    render_60_second_workflow,
)

from intuitiveness.ui.quality.anomaly_ui import (
    render_anomaly_detection,
    render_anomaly_results,
)

# Backward compatibility aliases
_clear_report_history = clear_report_history
_score_color = get_score_color
_score_label = get_score_label


def render_quality_dashboard() -> None:
    """
    Render the complete quality assessment dashboard.
    
    This is the main entry point that orchestrates all quality UI components.
    """
    render_page_header(
        "Dataset Quality Assessment",
        "Analyze your dataset's ML-readiness with TabPFN-powered quality scoring",
    )
    
    spacer(16)
    
    # Check for existing report in session
    report = st.session_state.get(SESSION_KEY_QUALITY_REPORT)
    
    if report is not None:
        _render_report_view(report)
        return
    
    # No report yet - show upload and assessment flow
    _render_upload_and_assessment()


def _render_report_view(report) -> None:
    """Render the quality report view with all tabs."""
    
    # New Assessment button
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 New Assessment", use_container_width=True):
            _clear_all_quality_state()
            st.rerun()
    
    # Main quality report with tabs
    _render_quality_report_tabs(report)


def _clear_all_quality_state():
    """Clear all quality-related session state."""
    clear_report_history()
    st.session_state.pop(SESSION_KEY_QUALITY_DF, None)
    st.session_state.pop(SESSION_KEY_QUALITY_FILE_NAME, None)
    st.session_state.pop(SESSION_KEY_TRANSFORMED_DF, None)
    st.session_state.pop(SESSION_KEY_TRANSFORMATION_LOG, None)
    st.session_state.pop(SESSION_KEY_BENCHMARK_REPORT, None)
    st.session_state.pop(SESSION_KEY_APPLIED_SUGGESTIONS, None)


def _render_upload_and_assessment():
    """Render file upload and assessment configuration."""
    
    # File upload
    with card():
        render_section_header("Upload Dataset", "Upload a CSV file to begin assessment")
        df = render_file_upload()
    
    if df is None:
        info(
            "Upload a CSV file to get started. "
            "The assessment works best with datasets of 50-10,000 rows."
        )
        return
    
    spacer(16)
    
    # Show data preview
    with card():
        render_section_header(
            "Data Preview",
            f"{len(df):,} rows × {len(df.columns)} columns"
        )
        st.dataframe(df.head(10), use_container_width=True)
    
    spacer(16)
    
    # Target selection and assessment
    with card():
        render_section_header("Configure Assessment", "Select the target column for prediction")
        
        target_column = render_target_selection(df)
        
        if target_column:
            _render_target_stats(df, target_column)
            spacer(16)
            render_assessment_button(df, target_column)


def _render_target_stats(df: pd.DataFrame, target_column: str):
    """Render target column statistics."""
    target_series = df[target_column]
    n_unique = target_series.nunique()
    n_missing = target_series.isna().sum()
    
    st.markdown(
        f"""
        <div style="color: #64748b; font-size: 14px; margin: 12px 0;">
            Target: <strong>{target_column}</strong> &middot;
            {n_unique} unique values &middot;
            {n_missing} missing ({n_missing/len(df):.1%})
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_quality_report_tabs(report):
    """Render the quality report with all tabs."""
    
    # Traffic light indicator (Spec 010: FR-001)
    with card():
        render_readiness_indicator(report)
    
    spacer(16)
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Overview",
        "✨ Suggestions",
        "🔬 ML Diagnostics",
        "🚀 60-Second Workflow",
        "🔍 Anomaly Detection",
        "📖 Methodology"
    ])
    
    with tab1:
        _render_overview_tab(report)
    
    with tab2:
        _render_suggestions_tab(report)
    
    with tab3:
        render_ml_diagnostics(report)
    
    with tab4:
        df = st.session_state.get(SESSION_KEY_QUALITY_DF)
        if df is not None:
            render_60_second_workflow(df, report, report.target_column)
        else:
            info("Dataset not available for workflow.")
    
    with tab5:
        _render_anomaly_tab(report)
    
    with tab6:
        render_tabpfn_methodology()


def _render_overview_tab(report):
    """Render overview tab with score and metadata."""
    from intuitiveness.ui.metric_card import render_metric_card_row
    
    # Score metrics
    render_metric_card_row([
        {
            "label": "Usability Score",
            "value": f"{report.usability_score:.1f}/100",
            "delta": get_score_label(report.usability_score),
            "color": get_score_color(report.usability_score),
        },
        {
            "label": "Prediction Quality",
            "value": f"{report.prediction_quality:.1f}%",
            "delta": "TabPFN 5-fold CV",
        },
        {
            "label": "Data Completeness",
            "value": f"{report.data_completeness:.1f}%",
            "delta": f"{sum(fp.missing_count for fp in report.feature_profiles):,} missing values",
        },
    ])
    
    spacer(16)
    
    # Dataset metadata
    with card():
        render_section_header("Dataset Metadata", "Summary of your dataset")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Rows:** {report.row_count:,}")
            st.markdown(f"**Columns:** {report.feature_count}")
            st.markdown(f"**Target:** {report.target_column}")
        with col2:
            st.markdown(f"**Task Type:** {report.task_type.title()}")
            st.markdown(f"**Assessment Time:** {report.assessment_time_seconds:.1f}s")
            st.markdown(f"**TabPFN Accuracy:** {report.prediction_quality:.1f}%")
    
    spacer(16)
    
    # Score evolution (if multiple reports)
    render_quality_score_evolution()


def _render_suggestions_tab(report):
    """Render feature suggestions tab."""
    df = st.session_state.get(SESSION_KEY_QUALITY_DF)
    if df is None:
        warning("Dataset not found in session state.")
        return
    
    render_feature_suggestions(report)


def _render_anomaly_tab(report):
    """Render anomaly detection tab."""
    df = st.session_state.get(SESSION_KEY_QUALITY_DF)
    if df is None:
        warning("Dataset not found in session state.")
        return
    
    anomalies = render_anomaly_detection(df, key_prefix="quality_dash")
    if anomalies:
        spacer(16)
        render_anomaly_results(anomalies, df)


# Export old function names for backward compatibility
render_quality_report = _render_quality_report_tabs
