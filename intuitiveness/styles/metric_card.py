"""
Metric Card Component

Implements Spec 007: FR-004 (Reusable Metric Display)

Provides a reusable metric card component for displaying prominent values
with consistent styling across the application. Used primarily for L0 datum
display but can be used anywhere a key metric needs emphasis.

Usage:
    from intuitiveness.styles.metric_card import render_metric_card

    render_metric_card(
        value=88.25,
        label="Average Score",
        description="Calculated using mean aggregation"
    )
"""

from typing import Any, Optional
import streamlit as st

from intuitiveness.styles.palette import COLORS


def render_metric_card(
    value: Any,
    label: str,
    description: Optional[str] = None,
    icon: Optional[str] = None,
    centered: bool = True
) -> None:
    """
    Render a prominent metric card with design system styling.

    Args:
        value: The metric value to display (number, string, etc.)
        label: Primary label for the metric
        description: Optional detailed description below the value
        icon: Optional emoji icon to show before the label
        centered: Whether to center the card (default: True)

    Examples:
        >>> render_metric_card(88.25, "Average Score", "Mean of 410 schools")
        # Large prominent 88.25 with label and description

        >>> render_metric_card("1,250€", "Total Funding", icon="💰")
        # Shows 💰 Total Funding with 1,250€

        >>> render_metric_card(42, "Active Users", centered=False)
        # Left-aligned metric card
    """
    # Format value if it's numeric
    if isinstance(value, (int, float)):
        if isinstance(value, float):
            # Show 2 decimal places for floats
            formatted_value = f"{value:.2f}"
        else:
            # Show comma separators for ints
            formatted_value = f"{value:,}"
    else:
        formatted_value = str(value)

    # Build label with optional icon
    full_label = f"{icon} {label}" if icon else label

    # Determine container styling
    if centered:
        container_style = "text-align: center;"
    else:
        container_style = ""

    # Render the metric card
    st.markdown(
        f"""
        <div style="
            {container_style}
            padding: 2rem;
            background: {COLORS["bg_elevated"]};
            border-radius: 0.5rem;
            border: 1px solid {COLORS["border"]};
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            margin: 1.5rem 0;
        ">
            <div style="
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: {COLORS["text_secondary"]};
                margin-bottom: 0.5rem;
            ">
                {full_label}
            </div>
            <div style="
                font-size: 3rem;
                font-weight: 600;
                color: {COLORS["accent"]};
                line-height: 1.2;
            ">
                {formatted_value}
            </div>
            {f'''
            <div style="
                font-size: 0.875rem;
                color: {COLORS["text_secondary"]};
                margin-top: 0.75rem;
                line-height: 1.5;
            ">
                {description}
            </div>
            ''' if description else ''}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_metric_row(metrics: list) -> None:
    """
    Render a row of metric cards side by side.

    Args:
        metrics: List of dicts with keys: value, label, description (optional), icon (optional)

    Examples:
        >>> metrics = [
        ...     {"value": 410, "label": "Schools", "icon": "🏫"},
        ...     {"value": 88.25, "label": "Avg Score", "icon": "📊"},
        ...     {"value": "95%", "label": "Success Rate", "icon": "✅"}
        ... ]
        >>> render_metric_row(metrics)
        # Shows 3 metric cards in a row
    """
    cols = st.columns(len(metrics))

    for idx, metric in enumerate(metrics):
        with cols[idx]:
            render_metric_card(
                value=metric["value"],
                label=metric["label"],
                description=metric.get("description"),
                icon=metric.get("icon"),
                centered=True
            )
