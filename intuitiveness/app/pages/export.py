"""
Export Page - Session Export and Visualization

Implements Spec 011: Code Simplification
Extracted from streamlit_app.py (lines 4604-4640)

Handles:
- Session graph export (JSON)
- GraphML export
- CSV export for all levels
- Session replay functionality

Usage:
    from intuitiveness.app.pages import render_export_page
    render_export_page()
"""

import streamlit as st
import json
from datetime import datetime
from typing import Dict, Any

from intuitiveness.ui import (
    render_page_header,
    render_section_header,
    render_navigation_export,
    t,
)
from intuitiveness.persistence import SessionStore
from intuitiveness.utils import SessionStateKeys


def render_export_page():
    """
    Render session export page with multiple export formats.

    Implements Spec 011: Export Page Extraction

    Features:
    - JSON session export
    - GraphML export
    - CSV export per level
    - Session replay preparation

    Export formats:
    - session.json: Complete session state for replay
    - graph.graphml: L3 graph for network analysis
    - l4_manifest.json: L4 file metadata
    - l3_nodes.csv, l3_edges.csv: Graph data
    - l2_table.csv: Categorized table
    - l1_vector.csv: Feature vector
    - l0_datum.json: Atomic metric
    """
    render_page_header(
        title=t('export_title'),
        subtitle=t('export_subtitle')
    )

    datasets = st.session_state.get('datasets', {})
    if not datasets:
        st.error(t('no_data_to_export'))
        return

    # Export summary
    render_section_header(t('export_summary'))

    st.write(t('export_summary_text'))

    # Show what will be exported
    export_items = []
    if 'l4' in datasets:
        export_items.append("✓ L4: " + t('l4_files'))
    if 'l3' in datasets:
        export_items.append("✓ L3: " + t('l3_graph'))
    if 'l2' in datasets:
        export_items.append("✓ L2: " + t('l2_table'))
    if 'l1' in datasets:
        export_items.append("✓ L1: " + t('l1_vector'))
    if 'l0' in datasets:
        export_items.append("✓ L0: " + t('l0_datum'))

    for item in export_items:
        st.write(item)

    st.divider()

    # Export options
    render_section_header(t('export_options'))

    # Option 1: Complete session export
    with st.expander(t('complete_session_export'), expanded=True):
        st.write(t('session_export_description'))

        if st.button(t('export_session_json'), type="primary"):
            export_complete_session()

    # Option 2: Level-specific exports
    with st.expander(t('level_specific_exports')):
        st.write(t('level_export_description'))

        col1, col2 = st.columns(2)

        with col1:
            if 'l3' in datasets and st.button(t('export_l3_graph')):
                export_l3_graph(datasets['l3'])

            if 'l2' in datasets and st.button(t('export_l2_table')):
                export_l2_table(datasets['l2'])

        with col2:
            if 'l1' in datasets and st.button(t('export_l1_vector')):
                export_l1_vector(datasets['l1'])

            if 'l0' in datasets and st.button(t('export_l0_datum')):
                export_l0_datum(datasets['l0'])

    # Option 3: Session replay file
    with st.expander(t('session_replay_export')):
        st.write(t('replay_export_description'))

        if st.button(t('export_for_replay'), type="primary"):
            export_session_for_replay()


def export_complete_session():
    """Export complete session to JSON."""
    try:
        session_store = SessionStore()
        export_data = session_store.export_session()

        # Create download button
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"intuitiveness_session_{timestamp}.json"

        st.download_button(
            label=t('download_session'),
            data=json.dumps(export_data, indent=2),
            file_name=filename,
            mime="application/json"
        )

        st.success(t('session_exported_successfully'))

    except Exception as e:
        st.error(f"{t('export_error')}: {str(e)}")


def export_l3_graph(l3_dataset):
    """Export L3 graph to GraphML."""
    import networkx as nx

    G = l3_dataset.get_data()

    # Export to GraphML string
    import io
    buffer = io.BytesIO()
    nx.write_graphml(G, buffer)
    buffer.seek(0)

    st.download_button(
        label=t('download_graphml'),
        data=buffer.getvalue(),
        file_name="l3_graph.graphml",
        mime="application/xml"
    )

    st.success(t('graph_exported'))


def export_l2_table(l2_dataset):
    """Export L2 table to CSV."""
    df = l2_dataset.get_data()

    csv = df.to_csv(index=False)

    st.download_button(
        label=t('download_csv'),
        data=csv,
        file_name="l2_table.csv",
        mime="text/csv"
    )

    st.success(t('table_exported'))


def export_l1_vector(l1_dataset):
    """Export L1 vector to CSV."""
    series = l1_dataset.get_data()

    csv = series.to_csv()

    st.download_button(
        label=t('download_csv'),
        data=csv,
        file_name="l1_vector.csv",
        mime="text/csv"
    )

    st.success(t('vector_exported'))


def export_l0_datum(l0_dataset):
    """Export L0 datum to JSON."""
    datum_data = {
        'value': l0_dataset.get_data(),
        'description': l0_dataset.description,
        'aggregation_method': l0_dataset.aggregation_method,
        'has_parent': l0_dataset.has_parent
    }

    st.download_button(
        label=t('download_json'),
        data=json.dumps(datum_data, indent=2),
        file_name="l0_datum.json",
        mime="application/json"
    )

    st.success(t('datum_exported'))


def export_session_for_replay():
    """Export session optimized for replay in testing."""
    # Create replay-optimized export
    replay_data = {
        'version': '1.0',
        'exported_at': datetime.now().isoformat(),
        'datasets': {},
        'navigation_history': st.session_state.get('navigation_history', []),
        'decisions': st.session_state.get('decisions', [])
    }

    # Add dataset summaries (not full data)
    datasets = st.session_state.get('datasets', {})
    for level, dataset in datasets.items():
        replay_data['datasets'][level] = {
            'level': level,
            'type': type(dataset).__name__
        }

    st.download_button(
        label=t('download_replay_file'),
        data=json.dumps(replay_data, indent=2),
        file_name="session_replay.json",
        mime="application/json"
    )

    st.success(t('replay_file_exported'))
