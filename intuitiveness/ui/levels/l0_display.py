"""
L0 Display - Atomic Metric Visualization

Implements Spec 003: FR-001-002 (L0 Datum Display)
Extracted from ui/level_displays.py (lines 211-271)

Displays a single atomic metric value prominently using the metric card component.
Integrated with Spec 007 (Streamlit Design) for centralized design tokens.

Usage:
    from intuitiveness.ui.levels import render_l0_datum
    render_l0_datum(88.25, "mean", "Average school score")
"""

from typing import Any, Optional
import streamlit as st


def render_l0_datum(
    value: Any,
    aggregation_method: str = "computed",
    source_info: Optional[str] = None
) -> None:
    """
    Render L0 (Datum) display - atomic metric visualization.

    Displays a single scalar value prominently using design system colors.
    Updated for 007-streamlit-design-makeup with centralized design tokens.

    Args:
        value: The scalar value to display
        aggregation_method: How the value was computed (e.g., "average", "sum", "count")
        source_info: Optional info about source (e.g., "Average from school scores")

    Examples:
        >>> render_l0_datum(88.25, "mean", "Average school performance")
        # Shows large "88.25" with "Calculated using: mean | Average school performance"

        >>> render_l0_datum(1250, "sum", "Total ADEME funding")
        # Shows large "1250" with calculation details
    """
    # Import metric card component
    from intuitiveness.styles.metric_card import render_metric_card

    # Domain-friendly header
    st.markdown("### Your Computed Result")

    # Build description from aggregation method and source
    description = f"Calculated using: {aggregation_method}"
    if source_info:
        description += f" | {source_info}"

    # Display the value using metric card component
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        render_metric_card(
            value=value,
            label="Result",
            description=description,
            centered=True
        )
