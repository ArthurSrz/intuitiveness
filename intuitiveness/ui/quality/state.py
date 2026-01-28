"""
Quality Dashboard - State Management

Phase 1.3 - Code Simplification (011-code-simplification)
Extracted from quality_dashboard.py

Spec Traceability:
------------------
- 010-quality-ds-workflow: Report history for before/after comparison (US-3)

Contains:
- Report history management functions
- Quality score evolution display
"""

import streamlit as st
import pandas as pd
from typing import Optional, Any

from intuitiveness.ui.layout import spacer
from intuitiveness.ui.quality.utils import (
    SESSION_KEY_QUALITY_REPORT,
    SESSION_KEY_QUALITY_REPORTS_HISTORY,
    SESSION_KEY_CURRENT_REPORT_INDEX,
    get_score_color,
)


def save_report_to_history(report: Any) -> None:
    """
    Save report to history instead of overwriting.

    This preserves the original assessment so users can compare
    before/after quality scores across transformation iterations.

    Args:
        report: QualityReport instance
    """
    if SESSION_KEY_QUALITY_REPORTS_HISTORY not in st.session_state:
        st.session_state[SESSION_KEY_QUALITY_REPORTS_HISTORY] = []

    # Append to history
    st.session_state[SESSION_KEY_QUALITY_REPORTS_HISTORY].append(report)
    # Update current index
    st.session_state[SESSION_KEY_CURRENT_REPORT_INDEX] = (
        len(st.session_state[SESSION_KEY_QUALITY_REPORTS_HISTORY]) - 1
    )
    # Also set current report (for backward compatibility)
    st.session_state[SESSION_KEY_QUALITY_REPORT] = report


def get_initial_report() -> Optional[Any]:
    """
    Get the initial (first) quality report from history.

    Returns:
        First QualityReport or None if no history
    """
    history = st.session_state.get(SESSION_KEY_QUALITY_REPORTS_HISTORY, [])
    return history[0] if history else None


def get_current_report() -> Optional[Any]:
    """
    Get the current (latest) quality report.

    Returns:
        Current QualityReport or None
    """
    return st.session_state.get(SESSION_KEY_QUALITY_REPORT)


def clear_report_history() -> None:
    """Clear all report history (for starting fresh)."""
    st.session_state.pop(SESSION_KEY_QUALITY_REPORTS_HISTORY, None)
    st.session_state.pop(SESSION_KEY_CURRENT_REPORT_INDEX, None)
    st.session_state.pop(SESSION_KEY_QUALITY_REPORT, None)


def render_quality_score_evolution() -> None:
    """
    Display before/after quality scores when re-assessment occurs.

    Shows quality score evolution across transformations, allowing users to see
    the impact of their data cleaning decisions.

    Spec: 010-quality-ds-workflow US-3 (Before/After Benchmarks)
    """
    initial = get_initial_report()
    current = get_current_report()

    # Only show if we have both reports and they differ
    if not initial or not current:
        return
    if initial.id == current.id:
        return

    # Calculate deltas
    score_delta = current.usability_score - initial.usability_score

    # Determine improvement direction
    improved = score_delta >= 0
    delta_color = "#22c55e" if improved else "#ef4444"
    delta_icon = "↑" if improved else "↓"

    # Build evolution display
    st.markdown(
        f"""<div style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin: 16px 0;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
        <div style="font-weight: 600; color: #475569; font-size: 14px;">Quality Score Evolution</div>
        <div style="background: {delta_color}20; color: {delta_color}; padding: 4px 12px; border-radius: 16px; font-weight: 600; font-size: 14px;">{delta_icon} {abs(score_delta):+.1f} pts</div>
    </div>
    <div style="display: flex; align-items: center; gap: 24px;">
        <div style="text-align: center; flex: 1;">
            <div style="color: #94a3b8; font-size: 12px; margin-bottom: 4px;">INITIAL</div>
            <div style="font-size: 32px; font-weight: bold; color: {get_score_color(initial.usability_score)};">{initial.usability_score:.0f}</div>
        </div>
        <div style="font-size: 24px; color: #cbd5e1;">→</div>
        <div style="text-align: center; flex: 1;">
            <div style="color: #94a3b8; font-size: 12px; margin-bottom: 4px;">CURRENT</div>
            <div style="font-size: 32px; font-weight: bold; color: {get_score_color(current.usability_score)};">{current.usability_score:.0f}</div>
        </div>
    </div>
</div>""",
        unsafe_allow_html=True,
    )

    # Show sub-metric changes in expandable section
    with st.expander("View Sub-Metric Changes"):
        metrics = [
            ("Prediction Quality", initial.prediction_quality, current.prediction_quality),
            ("Data Completeness", initial.data_completeness, current.data_completeness),
            ("Feature Diversity", initial.feature_diversity, current.feature_diversity),
            ("Size Appropriateness", initial.size_appropriateness, current.size_appropriateness),
        ]

        metric_data = []
        for name, init_val, curr_val in metrics:
            delta = curr_val - init_val
            delta_str = f"{delta:+.1f}" if delta != 0 else "—"
            metric_data.append({
                "Metric": name,
                "Initial": f"{init_val:.0f}",
                "Current": f"{curr_val:.0f}",
                "Change": delta_str,
            })

        metric_df = pd.DataFrame(metric_data)
        st.dataframe(
            metric_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Metric": st.column_config.TextColumn("Metric", width="medium"),
                "Initial": st.column_config.TextColumn("Initial", width="small"),
                "Current": st.column_config.TextColumn("Current", width="small"),
                "Change": st.column_config.TextColumn("Change", width="small"),
            },
        )

        # Visual score evolution chart when multiple assessments
        history = st.session_state.get(SESSION_KEY_QUALITY_REPORTS_HISTORY, [])
        if len(history) >= 2:
            st.markdown(
                f'<div style="color: #94a3b8; font-size: 13px; margin-bottom: 12px;">{len(history)} assessments in history</div>',
                unsafe_allow_html=True,
            )

            # Import visualization function
            try:
                from intuitiveness.quality.visualizations import create_score_evolution_chart

                scores = [r.usability_score for r in history]
                labels = [f"Assessment {i+1}" for i in range(len(history))]

                fig = create_score_evolution_chart(scores, labels)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                # Fallback to text if visualization fails
                st.markdown(
                    f'<div style="color: #94a3b8; font-size: 12px;">Could not render evolution chart: {e}</div>',
                    unsafe_allow_html=True,
                )


# Legacy aliases for backward compatibility
_save_report_to_history = save_report_to_history
_get_initial_report = get_initial_report
_get_current_report = get_current_report
_clear_report_history = clear_report_history
