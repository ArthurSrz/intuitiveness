"""
L1 Display - Vector Visualization

Implements Spec 003: FR-010-011 (L1 Vector Display)
Extracted from ui/level_displays.py (lines 172-209)

Displays a series or list of values extracted from a table column.
Shows column name and value preview with count.

Usage:
    from intuitiveness.ui.levels import render_l1_vector
    render_l1_vector(scores_series, "school_score")
"""

from typing import Any, List, Optional, Union
import streamlit as st
import pandas as pd


def render_l1_vector(
    vector_data: Union[pd.Series, List[Any]],
    column_name: str,
    max_preview_rows: int = 50
) -> None:
    """
    Render L1 (Vector) display - series of values.

    FR-010: Display the vector as a list or series of values
    FR-011: Show the column name from which the vector was extracted

    Args:
        vector_data: Series or list of values
        column_name: Name of the source column
        max_preview_rows: Maximum number of rows to display (default: 50)

    Examples:
        >>> import pandas as pd
        >>> scores = pd.Series([85, 90, 78, 92, 88])
        >>> render_l1_vector(scores, "school_score")
        # Shows "From: school_score" with 5 values in table format

        >>> funding_amounts = [10000, 15000, 8000, 12000]
        >>> render_l1_vector(funding_amounts, "funding_amount")
        # Shows list of funding amounts
    """
    # Domain-friendly header
    st.markdown("### 📊 Your Selected Values")
    st.markdown(f"**From:** `{column_name}`")

    # Convert to list for display
    if isinstance(vector_data, pd.Series):
        total_count = len(vector_data)
        values_to_show = vector_data.head(max_preview_rows).tolist()
    else:
        total_count = len(vector_data)
        values_to_show = vector_data[:max_preview_rows]

    st.markdown(f"**Values** (showing first {min(max_preview_rows, total_count)} of {total_count:,}):")

    # Display as a simple dataframe for better formatting
    display_df = pd.DataFrame({
        "#": range(1, len(values_to_show) + 1),
        "Value": values_to_show
    })
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=300)


def render_l1_ascent_preview(
    source_vector: Union[pd.Series, List[Any]],
    aggregation_method: str,
    computed_value: Any
) -> None:
    """
    Render L1→L0 ascent preview showing source vector being aggregated.

    Implements Spec 003: FR-012 (Ascent displays show lower level data)

    Args:
        source_vector: The L1 vector being aggregated
        aggregation_method: Method used (mean, sum, count, etc.)
        computed_value: The resulting L0 datum

    Examples:
        >>> scores = pd.Series([85, 90, 78, 92, 88])
        >>> render_l1_ascent_preview(scores, "mean", 88.6)
        # Shows vector with "Aggregating to: 88.6 using mean"
    """
    st.markdown("### L1 Vector → L0 Datum")
    st.info(f"Aggregating {len(source_vector)} values using **{aggregation_method}** → Result: **{computed_value}**")

    # Show vector preview
    if isinstance(source_vector, pd.Series):
        values_preview = source_vector.head(10).tolist()
    else:
        values_preview = source_vector[:10]

    st.markdown("**Source values:**")
    st.write(values_preview)

    if len(source_vector) > 10:
        st.caption(f"... and {len(source_vector) - 10} more values")
