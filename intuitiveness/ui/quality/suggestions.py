"""
Quality Dashboard - Feature Suggestions Components

Phase 1.3 - Code Simplification (011-code-simplification)
Extracted from quality_dashboard.py

Spec Traceability:
------------------
- 010-quality-ds-workflow: US-1 Step 3 (Apply Suggestions)
- 010-quality-ds-workflow: FR-002 (One-Click Apply All)

Contains:
- Feature engineering suggestions display
- Individual suggestion apply buttons
- One-click apply all functionality
"""

import streamlit as st
import pandas as pd
from typing import Any

from intuitiveness.ui.layout import spacer
from intuitiveness.ui.header import render_section_header
from intuitiveness.ui.alert import info, success, error
from intuitiveness.ui.quality.utils import (
    SESSION_KEY_QUALITY_DF,
    SESSION_KEY_APPLIED_SUGGESTIONS,
    SESSION_KEY_TRANSFORMED_DF,
    SESSION_KEY_TRANSFORMATION_LOG,
    SESSION_KEY_QUALITY_FILE_NAME,
    SESSION_KEY_QUALITY_REPORT,
)


def render_feature_suggestions(report: Any) -> None:
    """
    Render feature engineering suggestions section.

    Spec: 010-quality-ds-workflow US-1 Step 3

    Args:
        report: QualityReport instance
    """
    from intuitiveness.quality.feature_engineer import suggest_features, apply_suggestion

    render_section_header(
        "Feature Engineering Suggestions",
        "Recommendations to improve your dataset's quality"
    )

    # Get the current DataFrame
    df = st.session_state.get(SESSION_KEY_QUALITY_DF)
    if df is None:
        info("Upload a dataset to get feature engineering suggestions.")
        return

    # Generate suggestions
    suggestions = suggest_features(report, df=df, max_suggestions=5)

    if not suggestions:
        success("No suggestions - your dataset looks well-prepared!")
        return

    # Track applied suggestions
    applied = st.session_state.get(SESSION_KEY_APPLIED_SUGGESTIONS, set())

    for i, suggestion in enumerate(suggestions):
        suggestion_key = f"{suggestion.suggestion_type}_{'-'.join(suggestion.target_features)}"
        is_applied = suggestion_key in applied

        # Suggestion card
        with st.container():
            col1, col2, col3 = st.columns([1, 6, 2])

            with col1:
                # Type badge
                type_colors = {
                    "remove": "#ef4444",
                    "transform": "#3b82f6",
                    "combine": "#8b5cf6",
                }
                color = type_colors.get(suggestion.suggestion_type, "#64748b")
                st.markdown(
                    f"""
                    <div style="
                        background: {color}20;
                        color: {color};
                        padding: 4px 8px;
                        border-radius: 4px;
                        font-size: 12px;
                        font-weight: 600;
                        text-transform: uppercase;
                        text-align: center;
                    ">
                        {suggestion.suggestion_type}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col2:
                st.markdown(
                    f"""
                    <div style="margin-bottom: 4px;">
                        <strong>{', '.join(suggestion.target_features)}</strong>
                    </div>
                    <div style="color: #64748b; font-size: 14px;">
                        {suggestion.description}
                    </div>
                    <div style="color: #94a3b8; font-size: 12px; margin-top: 4px;">
                        Expected impact: <strong>+{suggestion.expected_impact:.1f}</strong> pts &middot;
                        Confidence: <strong>{suggestion.confidence:.0%}</strong>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col3:
                if is_applied:
                    st.markdown(
                        '<div style="color: #22c55e; font-weight: 600;">Applied</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    if st.button(
                        "Apply",
                        key=f"apply_suggestion_{i}",
                        use_container_width=True,
                    ):
                        # Apply the suggestion
                        try:
                            new_df = apply_suggestion(df, suggestion)
                            st.session_state[SESSION_KEY_QUALITY_DF] = new_df

                            # Mark as applied
                            if SESSION_KEY_APPLIED_SUGGESTIONS not in st.session_state:
                                st.session_state[SESSION_KEY_APPLIED_SUGGESTIONS] = set()
                            st.session_state[SESSION_KEY_APPLIED_SUGGESTIONS].add(suggestion_key)

                            success(f"Applied suggestion: {suggestion.suggestion_type} on {', '.join(suggestion.target_features)}")
                            st.rerun()
                        except Exception as e:
                            error(f"Failed to apply suggestion: {e}")

            st.markdown("<hr style='margin: 12px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

    # Re-assess button
    if applied:
        spacer(8)
        if st.button("Re-assess with Changes", use_container_width=True):
            # Save original report for comparison
            original_report = st.session_state.get(SESSION_KEY_QUALITY_REPORT)
            if original_report:
                # Save to history for before/after comparison
                from intuitiveness.ui.quality.state import save_report_to_history
                save_report_to_history(original_report)

            # Get current DF (which already has applied suggestions) and target column
            current_df = st.session_state.get(SESSION_KEY_QUALITY_DF)
            target_column = original_report.target_column if original_report else None

            if current_df is not None and target_column:
                # Clear report to trigger reassessment
                st.session_state.pop(SESSION_KEY_QUALITY_REPORT, None)

                # Set a flag to auto-trigger assessment on next render
                st.session_state['auto_reassess_target'] = target_column

            st.rerun()


def render_apply_all_button(report: Any) -> None:
    """
    Render one-click apply all suggestions button.

    Spec: 010-quality-ds-workflow FR-002

    Args:
        report: QualityReport instance
    """
    from intuitiveness.quality.assessor import apply_all_suggestions
    from intuitiveness.quality.feature_engineer import suggest_features

    df = st.session_state.get(SESSION_KEY_QUALITY_DF)
    if df is None:
        return

    # Get suggestions
    suggestions = suggest_features(report, df=df, max_suggestions=10)

    if not suggestions:
        return

    render_section_header(
        "One-Click Fix",
        f"Apply all {len(suggestions)} suggested transformations"
    )

    # Show preview of what will be applied
    st.markdown("**Transformations to apply:**")
    for i, s in enumerate(suggestions[:5], 1):
        impact_color = "#22c55e" if s.expected_impact > 0 else "#ef4444"
        st.markdown(
            f"- **{s.suggestion_type.title()}** on `{', '.join(s.target_features)}` "
            f"(<span style='color: {impact_color}'>+{s.expected_impact:.1f} pts</span>)",
            unsafe_allow_html=True,
        )
    if len(suggestions) > 5:
        st.markdown(f"- *...and {len(suggestions) - 5} more*")

    spacer(12)

    col1, col2 = st.columns([1, 3])
    with col1:
        apply_button = st.button(
            "Apply All Suggestions",
            type="primary",
            use_container_width=True,
            key="apply_all_suggestions_button",
        )

    if apply_button:
        with st.spinner("Applying transformations..."):
            try:
                transformed_df, log = apply_all_suggestions(
                    df=df,
                    suggestions=suggestions,
                    target_column=report.target_column,
                )

                log.dataset_name = st.session_state.get(SESSION_KEY_QUALITY_FILE_NAME, "dataset")

                # Save to session state
                st.session_state[SESSION_KEY_TRANSFORMED_DF] = transformed_df
                st.session_state[SESSION_KEY_TRANSFORMATION_LOG] = log
                st.session_state[SESSION_KEY_QUALITY_DF] = transformed_df

                success(
                    f"Applied {log.total_applied} transformations! "
                    f"Accuracy improved by {log.total_accuracy_improvement:.1%}" if log.total_accuracy_improvement else
                    f"Applied {log.total_applied} transformations!"
                )
                st.rerun()

            except Exception as e:
                error(f"Failed to apply suggestions: {e}")
