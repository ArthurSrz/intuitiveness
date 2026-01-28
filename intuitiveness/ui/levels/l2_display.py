"""
L2 Display - Domain-Categorized Table Visualization

Implements Spec 003: FR-008-009 (L2 Domain Table Display)
Extracted from ui/level_displays.py (lines 133-170)

Displays a table grouped by domain categories showing which domain
each item was classified into.

Usage:
    from intuitiveness.ui.levels import render_l2_domain_table
    render_l2_domain_table(domain_data_dict)
"""

from typing import Dict, Optional
import streamlit as st
import pandas as pd


def render_l2_domain_table(
    domain_data: Dict[str, pd.DataFrame],
    max_preview_rows: int = 50
) -> None:
    """
    Render L2 (Domain Table) display - categorized data by domain.

    FR-008: Display the domain-categorized table showing which domain
            each item was classified into
    FR-009: Show domain labels clearly for each item in the table

    Args:
        domain_data: Dict mapping domain names to DataFrames of items
        max_preview_rows: Maximum rows to show per domain (default: 50)

    Examples:
        >>> data = {
        ...     "high_score": pd.DataFrame({"school": ["A", "B"], "score": [90, 92]}),
        ...     "low_score": pd.DataFrame({"school": ["C", "D"], "score": [75, 78]})
        ... }
        >>> render_l2_domain_table(data)
        # Shows two expandable sections for high_score and low_score domains
    """
    # Domain-friendly header
    st.markdown("### 📊 Items by Category")

    if not domain_data:
        st.info("No categorized data available.")
        return

    total_items = sum(len(df) for df in domain_data.values())
    st.markdown(f"**{total_items:,} items across {len(domain_data)} categories**")

    # Render each domain as an expandable section
    for domain_name, df in domain_data.items():
        with st.expander(f"📁 {domain_name} ({len(df):,} items)", expanded=True):
            if df.empty:
                # Handle empty category state
                st.info(f"No items matched the '{domain_name}' category.")
            else:
                display_df = df.head(max_preview_rows) if len(df) > max_preview_rows else df
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                if len(df) > max_preview_rows:
                    st.caption(f"Showing first {max_preview_rows} of {len(df):,} items")


def render_l2_ascent_preview(
    categorized_table: pd.DataFrame,
    selected_column: str,
    num_unique_values: int
) -> None:
    """
    Render L2→L1 ascent preview showing table being reduced to vector.

    Implements Spec 003: FR-013 (Ascent displays show lower level data)

    Args:
        categorized_table: The L2 table being reduced
        selected_column: Column being extracted as L1 vector
        num_unique_values: Number of unique values in selected column

    Examples:
        >>> df = pd.DataFrame({"school": ["A", "B", "C"], "score": [90, 85, 92]})
        >>> render_l2_ascent_preview(df, "score", 3)
        # Shows table with "Extracting column: score (3 unique values)"
    """
    st.markdown("### L2 Table → L1 Vector")
    st.info(f"Extracting column **{selected_column}** ({num_unique_values} unique values)")

    # Show table preview
    st.dataframe(categorized_table.head(10), use_container_width=True)

    if len(categorized_table) > 10:
        st.caption(f"Showing first 10 of {len(categorized_table):,} rows")
