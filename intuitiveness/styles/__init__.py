"""
Centralized style module for Streamlit design makeup.

This module provides:
- COLORS: Dictionary of color tokens for programmatic access
- inject_all_styles(): Function to inject all CSS into the app

Usage in streamlit_app.py:
    from intuitiveness.styles import inject_all_styles

    def main():
        st.set_page_config(...)
        inject_all_styles()  # Call early in main()
"""

from .chrome import HIDE_CHROME_CSS
from .typography import TYPOGRAPHY_CSS, TYPOGRAPHY
from .palette import PALETTE_CSS, COLORS
from .components import COMPONENT_CSS
from .progress import PROGRESS_CSS
from .alerts import ALERTS_CSS
from .sidebar import SIDEBAR_CSS
from .layout import LAYOUT_CSS

# Combined CSS for single injection
ALL_STYLES = f"""<style>
{PALETTE_CSS}
{TYPOGRAPHY_CSS}
{HIDE_CHROME_CSS}
{COMPONENT_CSS}
{PROGRESS_CSS}
{ALERTS_CSS}
{SIDEBAR_CSS}
{LAYOUT_CSS}
</style>"""


def inject_all_styles():
    """Inject all custom styles into the Streamlit app.

    Call this function once, early in your main() function,
    immediately after st.set_page_config().
    """
    import streamlit as st
    st.markdown(ALL_STYLES, unsafe_allow_html=True)


# Metric card components (Spec 007: FR-004)
from .metric_card import render_metric_card, render_metric_row

# Re-export for convenience
__all__ = [
    "COLORS",
    "TYPOGRAPHY",
    "inject_all_styles",
    "ALL_STYLES",
    "render_metric_card",
    "render_metric_row",
]
