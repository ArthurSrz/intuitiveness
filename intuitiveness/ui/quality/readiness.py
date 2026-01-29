"""
Quality Dashboard - Readiness Indicator Components

Phase 1.3 - Code Simplification (011-code-simplification)
Extracted from quality_dashboard.py

Spec Traceability:
------------------
- 010-quality-ds-workflow: US-4 (Traffic Light Indicator)
- 010-quality-ds-workflow: FR-001 (Readiness Indicator)

Contains:
- Traffic light readiness indicator
- TabPFN methodology transparency section
"""

import streamlit as st
from typing import Any

from intuitiveness.ui.layout import card, spacer
from intuitiveness.ui.header import render_section_header
from intuitiveness.ui.metric_card import render_metric_card
from intuitiveness.ui.alert import info
from intuitiveness.ui.quality.utils import SESSION_KEY_QUALITY_DF


def render_readiness_indicator(report: Any) -> None:
    """
    Display traffic light readiness indicator.

    Provides instant go/no-go visual for data scientists.

    Spec: 010-quality-ds-workflow US-4, FR-001

    Args:
        report: QualityReport instance
    """
    from intuitiveness.quality.assessor import get_readiness_indicator
    from intuitiveness.quality.feature_engineer import suggest_features

    df = st.session_state.get(SESSION_KEY_QUALITY_DF)
    suggestions = suggest_features(report, df=df, max_suggestions=10) if df is not None else []

    # Estimate improvement from suggestions
    estimated_improvement = sum(s.expected_impact for s in suggestions)

    indicator = get_readiness_indicator(
        score=report.usability_score,
        n_suggestions=len(suggestions),
        estimated_improvement=estimated_improvement,
    )

    # Color mapping
    colors = {
        "green": "#22c55e",
        "yellow": "#eab308",
        "red": "#ef4444",
    }
    bg_colors = {
        "green": "#dcfce7",
        "yellow": "#fef3c7",
        "red": "#fee2e2",
    }

    color = colors.get(indicator.color, "#64748b")
    bg_color = bg_colors.get(indicator.color, "#f1f5f9")

    # Visual indicator using colored circles
    status_visual = {
        "green": "●",  # Green filled circle
        "yellow": "●",  # Yellow filled circle
        "red": "●",  # Red filled circle
    }.get(indicator.color, "○")

    st.markdown(
        f"""
        <div style="
            background: {bg_color};
            border: 3px solid {color};
            border-radius: 16px;
            padding: 24px;
            text-align: center;
            margin: 16px 0;
        ">
            <div style="font-size: 64px; color: {color}; margin-bottom: 8px;">{status_visual}</div>
            <div style="
                font-size: 24px;
                font-weight: bold;
                color: {color};
                margin-bottom: 8px;
            ">
                {indicator.title}
            </div>
            <div style="
                font-size: 16px;
                color: #475569;
            ">
                {indicator.message}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Threshold rationale tooltip
    with st.expander("How are these thresholds determined?"):
        st.markdown(
            """
            The traffic light thresholds are based on **industry ML benchmarks** and empirical research:

            | Score | Status | Rationale |
            |-------|--------|-----------|
            | **80+** | Ready | Datasets scoring 80+ typically yield reliable models without significant preprocessing. This aligns with the industry standard for "production-ready" data quality. |
            | **60-79** | Fixable | Scores in this range indicate workable datasets that will benefit from automated fixes. Most issues are addressable with our suggested transformations. |
            | **<60** | Needs Work | Below 60, datasets have significant quality issues (high missing rates, severe class imbalance, or low predictive signal) that may require manual investigation. |

            *These thresholds are calibrated against TabPFN's cross-validation performance and match common ML pipeline quality gates.*
            """,
            unsafe_allow_html=True,
        )


def render_tabpfn_methodology(report: Any) -> None:
    """
    Explain TabPFN methodology for user transparency.

    Shows:
    - What TabPFN is and how it works
    - Per-fold CV scores (not just mean)
    - Estimator agreement
    - Feature handling details
    - SHAP computation status

    Args:
        report: QualityReport instance with tabpfn_diagnostics
    """
    render_section_header(
        "How TabPFN Assessed Your Data",
        "Full transparency into the assessment methodology"
    )

    with card():
        # TabPFN Overview - Educational content from Nature paper
        st.markdown("""
        **TabPFN** (Tabular Prior-data Fitted Network) is a **foundation model for tabular data** from the
        [Nature paper](https://www.nature.com/articles/s41586-024-07544-w) by Hollmann et al. (2024).

        ### How TabPFN Works

        | Traditional ML | TabPFN (In-Context Learning) |
        |---------------|------------------------------|
        | Trains model parameters on your data | Already trained - uses your data as "context" |
        | Each dataset needs fresh training | Single forward pass through pre-trained model |
        | Minutes to hours per dataset | Seconds per dataset |
        | Requires hyperparameter tuning | No tuning needed |

        ### Key Innovations

        - **Pre-trained on 100 million synthetic datasets** using structural causal models (SCMs)
          - These SCMs simulate real-world causal relationships
          - The model learned general patterns that transfer to real data

        - **In-Context Learning (ICL)**: Your entire dataset is passed as "context" to a transformer
          - Similar to how GPT processes text, TabPFN processes tabular data
          - The model predicts based on patterns it learned during pre-training

        - **Zero-shot capability**: No training on your specific data
          - Your data stays private - only used for inference
          - Faster iteration: change data, get instant new predictions

        - **Ensemble of 8 estimators** averaged for robustness
          - Reduces variance and improves reliability
          - Each estimator learned slightly different patterns

        - **5,140x faster** than AutoML baselines while matching accuracy on datasets up to 10K rows

        **Important limits**: TabPFN is optimized for 10,000 rows, 500 features, and 10 classes.
        """)

        spacer(16)

        # Show diagnostics if available
        diag = report.tabpfn_diagnostics if hasattr(report, 'tabpfn_diagnostics') else None

        if diag and diag.fold_scores:
            st.markdown("### Your Assessment Details")

            # Cross-validation results
            col1, col2, col3 = st.columns(3)

            with col1:
                render_metric_card(
                    label="Mean Accuracy",
                    value=f"{diag.mean_accuracy:.1%}",
                    description="5-fold cross-validation",
                )

            with col2:
                render_metric_card(
                    label="Std Deviation",
                    value=f"+/-{diag.std_accuracy:.1%}",
                    description="Variance across folds",
                )

            with col3:
                # Determine confidence level
                if diag.std_accuracy < 0.05:
                    confidence = "High"
                    conf_color = "#22c55e"
                elif diag.std_accuracy < 0.10:
                    confidence = "Medium"
                    conf_color = "#f59e0b"
                else:
                    confidence = "Lower"
                    conf_color = "#ef4444"

                st.markdown(
                    f"""
                    <div style="background: #f8fafc; border-radius: 8px; padding: 16px; text-align: center;">
                        <div style="font-size: 12px; color: #64748b; text-transform: uppercase;">Confidence</div>
                        <div style="font-size: 28px; font-weight: bold; color: {conf_color};">{confidence}</div>
                        <div style="font-size: 12px; color: #94a3b8;">Based on fold variance</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            spacer(12)

            # Per-fold breakdown
            st.markdown("**Per-Fold Scores** (5-fold stratified cross-validation):")
            fold_cols = st.columns(5)
            for i, (col, score) in enumerate(zip(fold_cols, diag.fold_scores)):
                with col:
                    color = "#22c55e" if score >= 0.7 else "#f59e0b" if score >= 0.5 else "#ef4444"
                    st.markdown(
                        f"""
                        <div style="text-align: center; padding: 8px; background: #f1f5f9; border-radius: 8px;">
                            <div style="font-size: 11px; color: #64748b;">Fold {i+1}</div>
                            <div style="font-size: 20px; font-weight: bold; color: {color};">{score:.1%}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            spacer(16)

            # Feature handling transparency
            if diag.categorical_features_detected or diag.numeric_features_used:
                st.markdown("**Feature Handling:**")

                feature_info = []
                if diag.numeric_features_used:
                    feature_info.append(f"**{len(diag.numeric_features_used)}** numeric features")
                if diag.categorical_features_detected:
                    feature_info.append(f"**{len(diag.categorical_features_detected)}** categorical features (auto-encoded)")

                st.markdown(" - ".join(feature_info))

            spacer(12)

            # SHAP computation status
            st.markdown("**SHAP Value Computation:**")

            if diag.shap_status == "success":
                st.markdown("SHAP values computed successfully using KernelExplainer")
            elif diag.shap_status == "fallback":
                st.markdown(
                    f"SHAP unavailable - using **permutation importance** as fallback\n\n"
                    f"*Reason: {diag.shap_error_message}*"
                )
            else:
                st.markdown("SHAP computation was skipped")

        else:
            # Fallback when diagnostics aren't available
            info(
                "TabPFN diagnostics not available for this assessment. "
                "Re-run assessment to see full methodology details."
            )
