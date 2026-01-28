"""
L4 Display - Raw Data File List

Implements Spec 003: FR-001-002 (L4 File List Display)
Extracted from ui/level_displays.py (lines 85-131)

Displays uploaded raw dataset files as a list showing file name,
row count, and column count with optional preview.

Usage:
    from intuitiveness.ui.levels import render_l4_file_list
    render_l4_file_list(files_data)
"""

from typing import Any, Dict, List
import streamlit as st
import pandas as pd


def render_l4_file_list(
    files_data: List[Dict[str, Any]],
    show_preview: bool = True,
    max_preview_rows: int = 5
) -> None:
    """
    Render L4 (Raw Data) file list display.

    FR-001: Display uploaded raw dataset files as a list showing
            file name, row count, and column count
    FR-002: Allow users to preview each raw file's first few rows

    Args:
        files_data: List of dicts with 'name', 'dataframe', 'rows', 'columns' keys
        show_preview: Whether to show file preview (default: True)
        max_preview_rows: Number of rows to show in preview (default: 5)

    Examples:
        >>> files = [
        ...     {
        ...         "name": "schools.csv",
        ...         "dataframe": pd.DataFrame({"id": [1, 2], "name": ["A", "B"]}),
        ...         "rows": 2,
        ...         "columns": 2
        ...     }
        ... ]
        >>> render_l4_file_list(files)
        # Shows file list with preview expandable section
    """
    st.markdown("### 📁 Your Uploaded Files")

    if not files_data:
        st.info("No files uploaded yet.")
        return

    # Summary table - using domain-friendly labels
    summary_df = pd.DataFrame([
        {
            "File Name": f["name"],
            "Items": f"{f['rows']:,}",
            "Categories": f["columns"]
        }
        for f in files_data
    ])
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    # Preview section
    if show_preview:
        st.markdown("#### Preview")
        for file_info in files_data:
            with st.expander(f"📄 {file_info['name']} - First {max_preview_rows} items"):
                if 'dataframe' in file_info and file_info['dataframe'] is not None:
                    st.dataframe(
                        file_info['dataframe'].head(max_preview_rows),
                        use_container_width=True
                    )
                else:
                    st.info("No preview available")


def render_l4_stats(files_data: List[Dict[str, Any]]) -> None:
    """
    Render L4 statistics summary.

    Shows aggregate stats across all uploaded files:
    - Total number of files
    - Total rows across all files
    - Total columns (unique)

    Args:
        files_data: List of file info dictionaries

    Examples:
        >>> files = [
        ...     {"name": "file1.csv", "rows": 100, "columns": 5},
        ...     {"name": "file2.csv", "rows": 200, "columns": 3}
        ... ]
        >>> render_l4_stats(files)
        # Shows: "2 files | 300 total rows | 8 total columns"
    """
    if not files_data:
        return

    total_files = len(files_data)
    total_rows = sum(f["rows"] for f in files_data)
    total_cols = sum(f["columns"] for f in files_data)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Files", f"{total_files}")
    with col2:
        st.metric("Total Items", f"{total_rows:,}")
    with col3:
        st.metric("Total Categories", f"{total_cols}")
