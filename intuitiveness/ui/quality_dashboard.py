"""
Quality Dashboard - Quick Export Only

Simplified to a single workflow: Upload → Check → Export

For domain experts with NO familiarity with data structures.
No ML jargon. No technical tabs. Just check your data and export it.

Spec: 012-tabpfn-instant-export
"""

import streamlit as st

from intuitiveness.ui.layout import spacer
from intuitiveness.ui.header import render_page_header
from intuitiveness.ui.quality.instant_export import render_instant_export_ui
from intuitiveness.ui.quality.utils import SESSION_KEY_QUALITY_DF


def render_quality_dashboard() -> None:
    """
    Render the quality dashboard.

    Single workflow: Upload → Select target → Check & Export
    """
    render_page_header(
        "Data Quality Check",
        "Check your data and export it ready for analysis",
    )

    spacer(16)

    # That's it. The instant export UI handles everything:
    # - File upload (if no data loaded)
    # - Data preview
    # - Target selection
    # - Check & Export button
    # - Results display
    # - Download button
    render_instant_export_ui()


# Backward compatibility
def render_quality_report(*args, **kwargs):
    """Deprecated: Use render_quality_dashboard() instead."""
    render_quality_dashboard()
