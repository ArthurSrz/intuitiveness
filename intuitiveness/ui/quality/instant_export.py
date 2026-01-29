"""
Instant Export UI Component

Spec: 012-tabpfn-instant-export

Simple UI for non-technical domain experts:
- Single "Check & Export" button
- Progress bar (not spinner) for visibility
- Binary readiness indicator (Ready / Needs Work)
- Plain-language summary (no ML jargon)
- Download button for clean CSV

Target: Complete workflow in <30 seconds (SC-001)

Author: Intuitiveness Framework
"""

import streamlit as st
from typing import Optional, Any
import pandas as pd

from intuitiveness.ui.layout import card, spacer
from intuitiveness.ui.header import render_section_header
from intuitiveness.ui.alert import info, success, warning
from intuitiveness.ui.quality.utils import SESSION_KEY_QUALITY_DF

# Session state keys for instant export
SESSION_KEY_INSTANT_RESULT = "instant_export_result"
SESSION_KEY_INSTANT_PROGRESS = "instant_export_progress"


def render_instant_export_ui(df: Optional[pd.DataFrame] = None) -> None:
    """
    Render the instant export workflow UI.

    Simple, jargon-free interface for domain experts.

    Args:
        df: Optional DataFrame to process. If None, reads from session state.
    """
    # Get DataFrame from session state if not provided
    if df is None:
        df = st.session_state.get(SESSION_KEY_QUALITY_DF)

    if df is None:
        _render_upload_prompt()
        return

    # Header
    render_section_header(
        "Quick Export",
        "Check your data and export it ready for analysis"
    )

    spacer(8)

    # Show data summary
    with card():
        _render_data_preview(df)

    spacer(16)

    # Target column selector
    target_column = _render_target_selector(df)

    if target_column is None:
        return

    spacer(16)

    # Main action button and results
    _render_check_and_export_section(df, target_column)


def _render_upload_prompt() -> None:
    """Show prompt when no data is loaded."""
    with card():
        st.markdown(
            """
            <div style="text-align: center; padding: 40px 20px;">
                <div style="font-size: 48px; margin-bottom: 16px;">📤</div>
                <h3 style="margin-bottom: 8px;">Upload Your Data</h3>
                <p style="color: #64748b;">
                    Upload a CSV file to check if it's ready for analysis
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        uploaded = st.file_uploader(
            "Choose a CSV file",
            type=["csv"],
            key="instant_export_uploader",
            label_visibility="collapsed",
        )

        if uploaded:
            try:
                df = pd.read_csv(uploaded)
                st.session_state[SESSION_KEY_QUALITY_DF] = df
                st.rerun()
            except Exception as e:
                st.error(f"Could not read file: {e}")


def _render_data_preview(df: pd.DataFrame) -> None:
    """Show compact data preview."""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Rows", f"{len(df):,}")

    with col2:
        st.metric("Columns", f"{len(df.columns):,}")

    with col3:
        missing_pct = (df.isna().sum().sum() / (df.shape[0] * df.shape[1])) * 100
        st.metric("Missing Data", f"{missing_pct:.1f}%")

    # Column list
    with st.expander("View columns"):
        cols_per_row = 4
        for i in range(0, len(df.columns), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col_name in enumerate(df.columns[i:i+cols_per_row]):
                with cols[j]:
                    dtype = "number" if pd.api.types.is_numeric_dtype(df[col_name]) else "text"
                    st.markdown(f"**{col_name}** ({dtype})")


def _render_target_selector(df: pd.DataFrame) -> Optional[str]:
    """Render target column selector with plain language."""
    st.markdown("### What do you want to focus on?")
    st.markdown(
        "<p style='color: #64748b; margin-top: -8px;'>"
        "Select the column you want to analyze"
        "</p>",
        unsafe_allow_html=True,
    )

    # Filter to reasonable target columns
    target_options = [col for col in df.columns if df[col].nunique() >= 2]

    if not target_options:
        warning("No suitable columns found. Your data needs columns with at least 2 different values.")
        return None

    selected = st.selectbox(
        "Target column",
        options=target_options,
        index=0,
        key="instant_export_target",
        label_visibility="collapsed",
    )

    # Show target stats
    n_unique = df[selected].nunique()
    n_missing = df[selected].isna().sum()

    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"📊 {n_unique} different values")
    with col2:
        if n_missing > 0:
            st.caption(f"⚠️ {n_missing} missing values")
        else:
            st.caption("✅ No missing values")

    return selected


def _render_check_and_export_section(df: pd.DataFrame, target_column: str) -> None:
    """Render the main check & export UI."""
    from intuitiveness.quality.instant_export import InstantExporter, export_clean_csv

    # Check if we have a previous result
    result = st.session_state.get(SESSION_KEY_INSTANT_RESULT)

    # Explain what the check does (before they click)
    if result is None:
        with card():
            st.markdown("### What happens when you check?")
            st.markdown(
                """
                When you click **Check & Export**, two things happen:

                **1. Clean** — We prepare your data automatically
                - Fill empty cells with typical values
                - Convert text to numbers
                - Remove columns that can't be used

                **2. Check** — An AI tests if your data is useful
                - It tries to find patterns related to your focus column
                - Reports a Quality Score (0-100) based on how well it can make predictions
                - Higher score = more reliable analysis results

                This takes about 10-20 seconds.
                """
            )

        spacer(16)

    # Main action button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "🔍 Check & Export",
            type="primary",
            use_container_width=True,
            key="instant_export_btn",
        ):
            # Clear previous result
            st.session_state[SESSION_KEY_INSTANT_RESULT] = None

            # Create progress placeholder
            progress_container = st.empty()
            status_container = st.empty()

            def progress_callback(message: str, progress: float):
                with progress_container:
                    st.progress(progress, text=message)

            # Run instant export
            exporter = InstantExporter(enable_tabpfn_validation=True)
            result = exporter.check_and_export(
                df=df,
                target_column=target_column,
                progress_callback=progress_callback,
            )

            # Store result
            st.session_state[SESSION_KEY_INSTANT_RESULT] = result

            # Clear progress
            progress_container.empty()
            status_container.empty()

            st.rerun()

    spacer(16)

    # Show result if available
    if result is not None:
        _render_result(result)


def _render_result(result: Any) -> None:
    """Render the export result."""
    # Binary readiness indicator
    _render_readiness_indicator(result)

    spacer(16)

    # Summary
    with card():
        st.markdown(f"### {result.summary}")

        # Cleaning summary
        if result.cleaning_actions:
            st.markdown(f"**{result.get_cleaning_summary()}**")

        # Stats (quality score is shown above in the readiness indicator)
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Rows",
                f"{result.cleaned_row_count:,}",
                delta=f"-{result.rows_removed}" if result.rows_removed > 0 else None,
                delta_color="inverse" if result.rows_removed > 0 else "off",
            )
        with col2:
            st.metric(
                "Columns",
                f"{result.cleaned_col_count:,}",
                delta=f"-{result.cols_removed}" if result.cols_removed > 0 else None,
                delta_color="inverse" if result.cols_removed > 0 else "off",
            )

    spacer(16)

    # Surface top 3 cleaning actions prominently (builds trust)
    if result.cleaning_actions:
        top_actions = result.cleaning_actions[:3]
        st.markdown("**What we fixed:**")
        for action in top_actions:
            st.markdown(f"- {action.description}")
        if len(result.cleaning_actions) > 3:
            st.caption(f"...and {len(result.cleaning_actions) - 3} more changes")

    spacer(8)

    # Additional details in expander (warnings + full cleaning log)
    if result.warnings or len(result.cleaning_actions) > 3:
        with st.expander("More details", expanded=False):
            if result.warnings:
                st.markdown("**Notes:**")
                for w in result.warnings:
                    st.markdown(f"- {w}")

            # Full cleaning actions log
            if len(result.cleaning_actions) > 3:
                st.markdown("---")
                st.markdown("**All changes:**")
                for action in result.cleaning_actions:
                    st.markdown(f"- {action.description}")

    spacer(16)

    # Export button
    if result.is_ready and result.cleaned_df is not None:
        _render_export_button(result)
    else:
        _render_not_ready_guidance(result)

    spacer(16)

    # Explain how the quality check works
    _render_how_it_works(result)


def _render_readiness_indicator(result: Any) -> None:
    """Render binary readiness indicator with quality score."""
    if result.is_ready:
        color = "#22c55e"  # Green
        bg_color = "#dcfce7"
        status = "READY"
        icon = "✓"
        message = "Your data is ready to export"
    else:
        color = "#ef4444"  # Red
        bg_color = "#fee2e2"
        status = "NEEDS WORK"
        icon = "!"
        message = "Your data needs some attention"

    # Build quality score section
    if result.validation_score is not None:
        score = result.validation_score
        if score >= 80:
            score_label = "Excellent"
            score_color = "#22c55e"
        elif score >= 60:
            score_label = "Good"
            score_color = "#22c55e"
        elif score >= 50:
            score_label = "Fair"
            score_color = "#eab308"
        else:
            score_label = "Low"
            score_color = "#ef4444"

        score_explanation = _get_score_explanation(score)
        score_section = f'''<div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid {color}40;">
            <div style="font-size: 14px; color: #64748b; margin-bottom: 4px;">Quality Score</div>
            <div style="font-size: 36px; font-weight: bold; color: {score_color};">{score:.0f}/100</div>
            <div style="font-size: 14px; color: #64748b;">{score_label} — {score_explanation}</div>
        </div>'''
    else:
        time_str = f"{result.processing_time_seconds:.1f}"
        # Show validation error if available, otherwise generic message
        error_msg = getattr(result, 'validation_error', None)
        if error_msg:
            error_display = f'<div style="font-size: 12px; color: #ef4444; margin-top: 4px;">⚠️ {error_msg}</div>'
        else:
            error_display = '<div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Quality score unavailable (AI validation skipped)</div>'
        score_section = f'''<div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid {color}40;">
            <div style="font-size: 14px; color: #64748b;">⚡ Quick check completed in {time_str}s</div>
            {error_display}
        </div>'''

    html = f'''<div style="background: {bg_color}; border: 3px solid {color}; border-radius: 16px; padding: 24px; text-align: center; margin: 16px 0;">
        <div style="width: 64px; height: 64px; background: {color}; border-radius: 50%; margin: 0 auto 16px; display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: bold; color: white;">{icon}</div>
        <div style="font-size: 24px; font-weight: bold; color: {color}; margin-bottom: 8px;">{status}</div>
        <div style="font-size: 16px; color: #475569;">{message}</div>
        {score_section}
    </div>'''

    st.markdown(html, unsafe_allow_html=True)


def _get_score_explanation(score: float) -> str:
    """Get plain-language explanation for a quality score."""
    if score >= 80:
        return "patterns are clear and reliable"
    elif score >= 60:
        return "good patterns with some noise"
    elif score >= 50:
        return "patterns found but borderline"
    else:
        return "weak patterns, may need more data"


def _render_export_button(result: Any) -> None:
    """Render export download button."""
    from intuitiveness.quality.instant_export import export_clean_csv

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        csv_bytes = export_clean_csv(result)

        st.download_button(
            label="📥 Download Clean Data",
            data=csv_bytes,
            file_name=f"clean_data_{result.target_column}.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True,
            key="instant_export_download",
        )

        st.caption(
            f"Ready for analysis • {result.cleaned_row_count:,} rows × "
            f"{result.cleaned_col_count:,} columns"
        )


def _render_not_ready_guidance(result: Any) -> None:
    """Render guidance when data is not ready."""
    with card():
        st.markdown("### What to do next")

        if result.warnings:
            st.markdown("Based on the issues found, you might want to:")

            guidance = []
            for warning in result.warnings:
                if "empty" in warning.lower() or "missing" in warning.lower():
                    guidance.append("- Review and fill in missing data in your source file")
                elif "removed" in warning.lower():
                    guidance.append("- Check if important columns were excluded")
                elif "few rows" in warning.lower() or "small" in warning.lower():
                    guidance.append("- Try to collect more data samples")

            if guidance:
                for g in set(guidance):  # Remove duplicates
                    st.markdown(g)
            else:
                st.markdown("- Review your data source and try again")

        st.markdown("")
        st.markdown(
            "💡 **Tip:** Check the 'How does this work?' section below "
            "to understand what the quality check found."
        )


def _render_how_it_works(result: Any) -> None:
    """Explain how the quality check works in plain language."""
    with st.expander("ℹ️ How does this work?", expanded=False):
        st.markdown(
            """
            ### Two Steps: Clean, Then Check

            **Step 1: We clean your data** (standard data preparation)

            Before any analysis, we automatically fix common issues:
            - **Empty cells** → filled with typical values from that column (median for numbers, most common for text)
            - **Text columns** → converted to numbers so analysis tools can read them
            - **Unusable columns** → removed (columns with only one value, or mostly empty)
            - **Extreme values** (like infinity) → replaced with reasonable estimates

            This is standard data preparation — the same steps a data analyst would do manually.

            ---

            **Step 2: We check quality with TabPFN** (AI-powered validation)

            After cleaning, we use **TabPFN** — an AI system published in the scientific journal *Nature* —
            to test if your data is useful:

            1. We split your data: 80% for learning, 20% for testing
            2. TabPFN learns patterns from the 80%
            3. It tries to predict the focus column on the 20% it hasn't seen
            4. The **Quality Score** is how accurate those predictions were

            **Why TabPFN?** It was trained on 100 million synthetic datasets, so it can instantly
            recognize patterns without needing hours of setup. It's like having an expert data scientist
            glance at your data and say "yes, this looks usable" or "no, there's a problem here."

            ---

            ### What the Quality Score means

            | Score | Meaning |
            |-------|---------|
            | **80+** | Excellent — clear patterns, reliable for analysis |
            | **60-79** | Good — usable with some noise |
            | **50-59** | Borderline — might work, consider more data |
            | **Below 50** | Low — couldn't find reliable patterns |

            ---

            **Your data stays private** — only a small sample is used for the quality check,
            and nothing is stored after the check completes.
            """
        )


def render_instant_export_tab() -> None:
    """
    Render instant export as a standalone tab/page.

    Use this when integrating into the main app.
    """
    st.markdown(
        """
        <style>
        .instant-export-header {
            text-align: center;
            padding: 24px 0;
        }
        .instant-export-header h1 {
            font-size: 32px;
            margin-bottom: 8px;
        }
        .instant-export-header p {
            color: #64748b;
            font-size: 18px;
        }
        </style>
        <div class="instant-export-header">
            <h1>Quick Data Export</h1>
            <p>Check your data and export it ready for analysis in seconds</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_instant_export_ui()
