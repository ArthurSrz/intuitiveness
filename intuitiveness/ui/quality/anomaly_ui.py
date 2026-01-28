"""
Anomaly Detection UI Component.

Implements Spec 009: FR-007 (Interactive Anomaly Exploration)

Provides UI for:
- Viewing anomalous records ranked by score
- Exploring feature attributions
- Filtering by severity
- Interactive anomaly investigation
"""

import streamlit as st
import pandas as pd
from typing import List, Optional, Dict, Any

from intuitiveness.quality.anomaly_detector import (
    detect_anomalies,
    get_anomaly_summary,
)
from intuitiveness.quality.models import AnomalyRecord
from intuitiveness.ui.i18n import t


def render_anomaly_detection(
    df: pd.DataFrame,
    key_prefix: str = "anomaly"
) -> Optional[List[AnomalyRecord]]:
    """
    Render anomaly detection UI with interactive exploration.

    Implements Spec 009: FR-003, FR-007

    Args:
        df: DataFrame to analyze for anomalies
        key_prefix: Unique prefix for session state keys

    Returns:
        List of detected anomalies if analysis run, None otherwise
    """
    st.markdown("### 🔍 Anomaly Detection")
    st.markdown(
        "Identify unusual records that may indicate data quality issues, "
        "fraud, or interesting outliers worth investigating."
    )

    # Configuration
    col1, col2 = st.columns(2)

    with col1:
        percentile_threshold = st.slider(
            "Severity Threshold (lower = stricter)",
            min_value=0.1,
            max_value=5.0,
            value=2.0,
            step=0.1,
            key=f"{key_prefix}_threshold",
            help="Flag rows below this percentile as anomalies. Lower = more selective."
        )

    with col2:
        max_anomalies = st.number_input(
            "Max Anomalies to Show",
            min_value=10,
            max_value=500,
            value=100,
            step=10,
            key=f"{key_prefix}_max",
            help="Maximum number of anomalous records to display"
        )

    # Run detection
    if st.button("🔎 Detect Anomalies", key=f"{key_prefix}_detect", use_container_width=True):
        with st.spinner("Analyzing data for anomalies..."):
            try:
                anomalies = detect_anomalies(
                    df,
                    percentile_threshold=percentile_threshold,
                    max_anomalies=max_anomalies
                )

                # Store in session state
                st.session_state[f"{key_prefix}_anomalies"] = anomalies
                st.session_state[f"{key_prefix}_df"] = df

                if anomalies:
                    st.success(f"✅ Detected {len(anomalies)} anomalous records")
                else:
                    st.info("ℹ️ No anomalies detected with current threshold")

            except Exception as e:
                st.error(f"❌ Anomaly detection failed: {e}")
                return None

    # Display results if available
    anomalies = st.session_state.get(f"{key_prefix}_anomalies")
    stored_df = st.session_state.get(f"{key_prefix}_df")

    if anomalies is not None and stored_df is not None:
        render_anomaly_results(anomalies, stored_df, key_prefix)

    return anomalies


def render_anomaly_results(
    anomalies: List[AnomalyRecord],
    df: pd.DataFrame,
    key_prefix: str = "anomaly"
) -> None:
    """
    Render anomaly detection results with interactive exploration.

    Args:
        anomalies: List of detected anomalies
        df: Original DataFrame
        key_prefix: Unique prefix for session state keys
    """
    if not anomalies:
        st.info("No anomalies detected")
        return

    # Summary statistics
    st.markdown("---")
    st.markdown("### 📊 Anomaly Summary")

    summary = get_anomaly_summary(anomalies, df)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Total Anomalies",
            f"{summary['total_anomalies']}",
            delta=f"{summary['percentage']:.2f}% of data"
        )

    with col2:
        severe_count = summary['severity_distribution'].get('severe', 0)
        st.metric(
            "Severe Anomalies",
            f"{severe_count}",
            delta=f"<0.5th percentile"
        )

    with col3:
        moderate_count = summary['severity_distribution'].get('moderate', 0)
        st.metric(
            "Moderate Anomalies",
            f"{moderate_count}",
            delta=f"0.5-1.0th percentile"
        )

    # Top contributing features
    if summary['top_contributing_features']:
        st.markdown("**Top Contributing Features:**")
        feature_text = ", ".join([
            f"**{item['feature']}** ({item['count']})"
            for item in summary['top_contributing_features'][:5]
        ])
        st.markdown(feature_text)

    # Anomaly table with details
    st.markdown("---")
    st.markdown("### 📋 Anomalous Records")

    # Severity filter
    severity_filter = st.multiselect(
        "Filter by Severity",
        options=["severe", "moderate", "mild"],
        default=["severe", "moderate", "mild"],
        key=f"{key_prefix}_severity_filter"
    )

    # Filter anomalies by severity
    filtered_anomalies = []
    for a in anomalies:
        if a.percentile < 0.5 and "severe" in severity_filter:
            filtered_anomalies.append(a)
        elif 0.5 <= a.percentile < 1.0 and "moderate" in severity_filter:
            filtered_anomalies.append(a)
        elif a.percentile >= 1.0 and "mild" in severity_filter:
            filtered_anomalies.append(a)

    if not filtered_anomalies:
        st.info("No anomalies match the selected severity levels")
        return

    # Display anomalies
    for i, anomaly in enumerate(filtered_anomalies[:20]):  # Show top 20
        with st.expander(
            f"🚨 Row {anomaly.row_index} "
            f"(Anomaly Score: {anomaly.anomaly_score:.2f}, "
            f"Percentile: {anomaly.percentile:.2f})",
            expanded=(i == 0)  # Expand first anomaly
        ):
            # Show row data
            row_data = df.iloc[anomaly.row_index]

            st.markdown("**Record Data:**")
            # Display as two-column table
            data_cols = st.columns(2)
            for idx, (col_name, value) in enumerate(row_data.items()):
                with data_cols[idx % 2]:
                    st.markdown(f"- **{col_name}**: `{value}`")

            # Show feature attributions
            if anomaly.top_contributors:
                st.markdown("**Why is this anomalous?**")

                for contrib in anomaly.top_contributors:
                    feature = contrib['feature']
                    contribution = contrib['contribution']
                    reason = contrib['reason']

                    # Color code by contribution strength
                    if contribution > 3:
                        color = "🔴"  # Severe
                    elif contribution > 2:
                        color = "🟡"  # Moderate
                    else:
                        color = "🟢"  # Mild

                    st.markdown(f"{color} **{feature}**: {reason}")

    # Show message if more anomalies exist
    if len(filtered_anomalies) > 20:
        st.info(f"Showing top 20 of {len(filtered_anomalies)} anomalies matching filter")


def render_anomaly_export(
    anomalies: List[AnomalyRecord],
    df: pd.DataFrame,
    key_prefix: str = "anomaly"
) -> None:
    """
    Render anomaly export options.

    Args:
        anomalies: List of detected anomalies
        df: Original DataFrame
        key_prefix: Unique prefix for session state keys
    """
    if not anomalies:
        return

    st.markdown("---")
    st.markdown("### 💾 Export Anomalies")

    # Create export DataFrame
    export_data = []
    for a in anomalies:
        row = df.iloc[a.row_index].to_dict()
        row['_anomaly_score'] = a.anomaly_score
        row['_percentile'] = a.percentile
        row['_row_index'] = a.row_index

        # Add top contributor info
        if a.top_contributors:
            row['_top_contributor'] = a.top_contributors[0]['feature']
            row['_contribution_score'] = a.top_contributors[0]['contribution']

        export_data.append(row)

    export_df = pd.DataFrame(export_data)

    # Download button
    csv = export_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Anomalies as CSV",
        data=csv,
        file_name="anomalies.csv",
        mime="text/csv",
        key=f"{key_prefix}_download",
        use_container_width=True
    )

    st.caption(
        f"Export includes {len(anomalies)} anomalous records with "
        "anomaly scores and feature attributions"
    )
