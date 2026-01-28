"""
ML Diagnostics UI Module

Implements Spec 011: Code Simplification (extracted from quality_dashboard.py)
Extracted from quality_dashboard.py lines 87-196

Provides standard ML diagnostic visualizations:
- Feature importance via ablation
- SHAP summary plots
- Class distribution analysis

Target: <200 lines
"""

import streamlit as st
from typing import Optional

from intuitiveness.ui.layout import card, spacer
from intuitiveness.ui.header import render_section_header
from intuitiveness.ui.alert import info, warning
from intuitiveness.ui.quality.utils import SESSION_KEY_QUALITY_DF


def render_ml_diagnostics(report) -> None:
    """
    Render standard ML diagnostic visualizations.
    
    Addresses ML engineer feedback: "The common machine learning graphics
    are not there, so how do I know that my dataset is ready for ML?"
    
    Shows:
    - Feature Importance Bar Chart
    - SHAP Summary Plot
    - Class Distribution (for classification)
    
    Args:
        report: QualityReport instance.
    """
    from intuitiveness.quality.visualizations import (
        create_feature_importance_chart,
        create_shap_summary_plot,
        create_class_distribution,
    )
    
    render_section_header(
        "ML Diagnostic Visualizations",
        "Standard charts to validate your dataset is ready for modeling"
    )
    
    df = st.session_state.get(SESSION_KEY_QUALITY_DF)
    
    with card():
        # Tabs for different visualizations
        tab1, tab2, tab3 = st.tabs([
            "📊 Feature Importance",
            "🎯 SHAP Impact",
            "📈 Class Distribution"
        ])
        
        with tab1:
            _render_feature_importance_tab(report)
        
        with tab2:
            _render_shap_tab(report)
        
        with tab3:
            _render_class_distribution_tab(report, df)


def _render_feature_importance_tab(report) -> None:
    """Render feature importance visualization tab."""
    from intuitiveness.quality.visualizations import create_feature_importance_chart
    
    st.markdown("""
    ### 📊 Feature Importance via Ablation
    
    **How it works**: TabPFN importance is computed using **ablation study** - we measure how much
    prediction accuracy drops when each feature is removed. This is repeated across 3 cross-validation folds
    for stability.
    
    - **High importance** (0.7+): Feature is critical for predictions
    - **Medium importance** (0.3-0.7): Feature contributes but isn't essential
    - **Low importance** (<0.3): Consider removing to reduce noise and speed up modeling
    
    *This differs from tree-based importance (which measures split frequency) - ablation directly measures
    predictive contribution.*
    """)
    spacer(8)
    try:
        fig = create_feature_importance_chart(report)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        warning(f"Could not generate feature importance chart: {e}")


def _render_shap_tab(report) -> None:
    """Render SHAP values visualization tab."""
    from intuitiveness.quality.visualizations import create_shap_summary_plot
    
    st.markdown("""
    ### 🎯 SHAP Values (Model Interpretability)
    
    **SHAP** (SHapley Additive exPlanations) comes from game theory. It answers:
    *"How much did each feature contribute to each prediction?"*
    
    **How it works with TabPFN**:
    - We use KernelSHAP to compute feature attributions
    - Each bar shows the **mean |SHAP value|** - higher means more influence on predictions
    - Unlike feature importance (global), SHAP can show per-sample contributions
    
    **Interpreting the chart**:
    - Features at the top have the most consistent impact
    - Small SHAP values mean the feature's impact varies or is minimal
    
    *If SHAP fails (e.g., timeout), we fall back to permutation importance.*
    """)
    spacer(8)
    try:
        fig = create_shap_summary_plot(report.feature_profiles)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        warning(f"Could not generate SHAP chart: {e}")


def _render_class_distribution_tab(report, df: Optional) -> None:
    """Render class distribution visualization tab."""
    from intuitiveness.quality.visualizations import create_class_distribution
    
    if report.task_type == "classification" and df is not None:
        st.markdown("""
        ### 📈 Class Distribution
        
        **Why it matters**: TabPFN, like most classifiers, can struggle with severe class imbalance.
        If one class is much rarer than others, the model may under-predict it.
        
        **What to look for**:
        - **Balanced** (green): Classes are roughly equal - ideal for learning
        - **Moderate imbalance** (yellow): Some classes have 2-5× more samples
        - **Severe imbalance** (red): 10× or more difference - consider oversampling or class weights
        
        *TabPFN handles moderate imbalance well, but severe cases may need synthetic data augmentation.*
        """)
        spacer(8)
        if report.target_column in df.columns:
            try:
                fig = create_class_distribution(df[report.target_column])
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                warning(f"Could not generate class distribution: {e}")
        else:
            info("Target column not found in dataset.")
    else:
        info("Class distribution is only available for classification tasks.")
