"""
60-Second Workflow UI Component.

Implements Spec 010: UI for 60-second data prep workflow

Provides UI for:
- One-click "Apply All Suggestions"
- Traffic light readiness indicator
- Export clean CSV + Python code snippet
- Before/after comparison
"""

import streamlit as st
import pandas as pd
from typing import Optional

from intuitiveness.quality.workflow import (
    run_60_second_workflow,
    quick_export,
    ReadinessStatus,
    GREEN_THRESHOLD,
    YELLOW_THRESHOLD,
)
from intuitiveness.quality.models import QualityReport, TransformationLog
from intuitiveness.ui.i18n import t


def render_traffic_light_indicator(
    readiness_status: ReadinessStatus,
    show_details: bool = True
) -> None:
    """
    Render traffic light readiness indicator.

    Implements Spec 010: FR-001

    Args:
        readiness_status: ReadinessStatus object
        show_details: Whether to show detailed messages
    """
    # Color mapping
    colors = {
        "green": ("#10b981", "#ecfdf5"),  # green-500, green-50
        "yellow": ("#f59e0b", "#fffbeb"),  # amber-500, amber-50
        "red": ("#ef4444", "#fef2f2"),  # red-500, red-50
    }

    bg_color, text_color = colors[readiness_status.status]

    # Large status banner
    st.markdown(
        f"""
        <div style="
            background-color: {text_color};
            border-left: 6px solid {bg_color};
            padding: 1.5rem;
            margin: 1rem 0;
            border-radius: 0.5rem;
        ">
            <h2 style="margin: 0; color: {bg_color}; font-size: 1.75rem;">
                {readiness_status.message}
            </h2>
            <p style="margin: 0.5rem 0 0 0; font-size: 1.125rem; color: #374151;">
                Score: <strong>{readiness_status.usability_score:.1f}/100</strong>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if show_details:
        st.info(f"💡 {readiness_status.action_message}")


def render_apply_all_button(
    df: pd.DataFrame,
    quality_report: QualityReport,
    target_column: str,
    key_prefix: str = "workflow"
) -> Optional[tuple[pd.DataFrame, TransformationLog]]:
    """
    Render "Apply All Suggestions" button with progress.

    Implements Spec 010: FR-002

    Args:
        df: Original DataFrame
        quality_report: Quality assessment report
        target_column: Target column name
        key_prefix: Unique prefix for session state keys

    Returns:
        Tuple of (transformed_df, transformation_log) if applied, None otherwise
    """
    if not quality_report.suggestions:
        st.info("✅ No suggestions available - data is already in good shape!")
        return None

    n_suggestions = len(quality_report.suggestions)

    st.markdown(f"### 🔧 Available Improvements ({n_suggestions})")

    # Show preview of suggestions
    with st.expander("Preview Suggestions", expanded=False):
        for i, suggestion in enumerate(quality_report.suggestions[:5], 1):
            st.markdown(f"{i}. **{suggestion.suggestion_type}**: {suggestion.rationale}")

        if n_suggestions > 5:
            st.caption(f"... and {n_suggestions - 5} more")

    # Apply All button
    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button(
            f"✨ Apply All {n_suggestions} Suggestions",
            key=f"{key_prefix}_apply_all",
            use_container_width=True,
            type="primary"
        ):
            with st.spinner("Applying transformations..."):
                try:
                    from intuitiveness.quality.assessor import apply_all_suggestions

                    transformed_df, transformation_log = apply_all_suggestions(
                        df,
                        quality_report.suggestions,
                        target_column=target_column
                    )

                    # Store in session state
                    st.session_state[f"{key_prefix}_transformed_df"] = transformed_df
                    st.session_state[f"{key_prefix}_transformation_log"] = transformation_log

                    st.success(
                        f"✅ Applied {len(transformation_log.transformations)} transformations! "
                        f"New score: {transformation_log.new_score:.1f}/100"
                    )

                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Transformation failed: {e}")
                    return None

    with col2:
        if st.button("Clear Transformations", key=f"{key_prefix}_clear"):
            if f"{key_prefix}_transformed_df" in st.session_state:
                del st.session_state[f"{key_prefix}_transformed_df"]
            if f"{key_prefix}_transformation_log" in st.session_state:
                del st.session_state[f"{key_prefix}_transformation_log"]
            st.rerun()

    # Show transformation results if available
    transformed_df = st.session_state.get(f"{key_prefix}_transformed_df")
    transformation_log = st.session_state.get(f"{key_prefix}_transformation_log")

    if transformed_df is not None and transformation_log is not None:
        render_transformation_summary(transformation_log)
        return transformed_df, transformation_log

    return None


def render_transformation_summary(
    transformation_log: TransformationLog
) -> None:
    """
    Render before/after transformation summary.

    Implements Spec 010: FR-010 (Before/After Comparison)

    Args:
        transformation_log: Log of applied transformations
    """
    st.markdown("---")
    st.markdown("### 📊 Transformation Results")

    # Before/After scores
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Original Score",
            f"{transformation_log.original_score:.1f}",
            delta=None
        )

    with col2:
        improvement = transformation_log.new_score - transformation_log.original_score
        st.metric(
            "New Score",
            f"{transformation_log.new_score:.1f}",
            delta=f"+{improvement:.1f}",
            delta_color="normal"
        )

    with col3:
        st.metric(
            "Transformations",
            len(transformation_log.transformations),
            delta=None
        )

    # Transformation details
    with st.expander("Transformation Details", expanded=True):
        for t in transformation_log.transformations:
            impact = f"+{t.accuracy_impact:.1f}%" if t.accuracy_impact else "N/A"
            st.markdown(
                f"- **{t.feature_name}**: {t.transformation_type} "
                f"({impact} impact)"
            )


def render_export_section(
    df: pd.DataFrame,
    target_column: str,
    filename: str = "clean_data.csv",
    key_prefix: str = "workflow"
) -> None:
    """
    Render export section with CSV download and Python snippet.

    Implements Spec 010: FR-003, FR-004

    Args:
        df: DataFrame to export (original or transformed)
        target_column: Target column name
        filename: Output filename
        key_prefix: Unique prefix for session state keys
    """
    st.markdown("---")
    st.markdown("### 💾 Export Clean Data")

    col1, col2 = st.columns(2)

    with col1:
        # Export CSV
        csv_bytes = df.to_csv(index=False).encode('utf-8')

        st.download_button(
            label="📥 Download Clean CSV",
            data=csv_bytes,
            file_name=filename,
            mime="text/csv",
            key=f"{key_prefix}_download_csv",
            use_container_width=True
        )

        st.caption(f"{len(df)} rows × {len(df.columns)} columns")

    with col2:
        # Python snippet
        if st.button(
            "📋 Copy Python Code",
            key=f"{key_prefix}_show_code",
            use_container_width=True
        ):
            st.session_state[f"{key_prefix}_show_code_snippet"] = True

    # Show Python snippet if requested
    if st.session_state.get(f"{key_prefix}_show_code_snippet", False):
        from intuitiveness.quality.exporter import generate_python_snippet

        python_snippet = generate_python_snippet(
            dataset_name=filename,
            target_column=target_column,
            transformations=[]
        )

        st.code(python_snippet, language="python")

        st.caption(
            "💡 Paste this code into your Jupyter notebook to load the clean data "
            "and start modeling!"
        )


def render_60_second_workflow(
    df: pd.DataFrame,
    quality_report: QualityReport,
    target_column: str,
    key_prefix: str = "workflow"
) -> None:
    """
    Render complete 60-second workflow UI.

    Implements Spec 010: Complete workflow UI

    Args:
        df: Original DataFrame
        quality_report: Quality assessment report
        target_column: Target column name
        key_prefix: Unique prefix for session state keys
    """
    st.markdown("## 🚀 60-Second Data Prep Workflow")

    # Step 1: Traffic light indicator
    from intuitiveness.quality.workflow import (
        get_readiness_status,
        estimate_score_improvement
    )

    estimated_improvement = estimate_score_improvement(
        quality_report.suggestions,
        quality_report.usability_score
    )

    readiness_status = get_readiness_status(
        quality_report.usability_score,
        n_suggestions=len(quality_report.suggestions),
        estimated_improvement=estimated_improvement
    )

    render_traffic_light_indicator(readiness_status)

    # Step 2: Apply suggestions
    result = render_apply_all_button(
        df,
        quality_report,
        target_column,
        key_prefix
    )

    # Determine which DataFrame to export
    export_df = result[0] if result else df

    # Step 3: Export
    render_export_section(
        export_df,
        target_column,
        filename="clean_data.csv",
        key_prefix=key_prefix
    )
