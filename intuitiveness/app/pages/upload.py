"""
Upload Page Module

Implements Spec 011: Code Simplification
Extracted from streamlit_app.py (lines 1035-1181)

Responsibilities:
- File upload interface
- Data.gouv.fr search integration (Spec 008)
- AI-powered connection wizard initialization
- L4 file list display (Spec 003)

Target: <200 lines (self-contained upload workflow)
"""

import streamlit as st
from typing import Dict, Optional
import pandas as pd

from intuitiveness.complexity import Level4Dataset
from intuitiveness.ui import (
    render_l4_file_list,
    render_search_interface,
    render_wizard_step_1_columns,
    render_wizard_step_2_connections,
    render_wizard_step_3_confirm,
    _get_wizard_step,
    _set_wizard_step,
    SESSION_KEY_DISCOVERY_RESULTS,
    t,
)
from intuitiveness.discovery import run_discovery, DiscoveryResult
from intuitiveness.interactive import Neo4jDataModel, DataModelNode


def render_upload_page(step: Dict, skip_header: bool = False) -> None:
    """
    Render Step 0: Search and load data from data.gouv.fr.
    
    This page handles:
    1. Display uploaded files with L4 file list (Spec 003: FR-001, FR-002)
    2. Run AI-powered connection wizard
    3. Show data.gouv.fr search interface (Spec 008)
    
    Args:
        step: Step configuration dictionary
        skip_header: Whether to skip step header rendering
    """
    from intuitiveness.streamlit_app import render_step_header
    
    if not skip_header:
        render_step_header(step)
    
    # Check if data is already loaded (from search)
    raw_data = st.session_state.raw_data
    if raw_data:
        _render_uploaded_files(raw_data)
        _render_connection_wizard(raw_data)
    else:
        _render_search_interface()


def _render_uploaded_files(raw_data: Dict[str, pd.DataFrame]) -> None:
    """Display uploaded files using L4 file list component."""
    files_data = [
        {
            "name": name,
            "dataframe": df,
            "rows": df.shape[0],
            "columns": df.shape[1]
        }
        for name, df in raw_data.items()
    ]
    render_l4_file_list(files_data, show_preview=True, max_preview_rows=5)


def _render_connection_wizard(raw_data: Dict[str, pd.DataFrame]) -> None:
    """
    Render AI-powered connection wizard.
    
    Three-step wizard:
    1. Select columns to include
    2. Define connections between tables
    3. Confirm and preview joined data
    """
    st.markdown("---")
    st.subheader("🔮 Connect Your Data")
    st.markdown("I'll analyze your files and suggest how to connect them.")
    
    # Initialize discovery results if not exists
    if SESSION_KEY_DISCOVERY_RESULTS not in st.session_state:
        st.session_state[SESSION_KEY_DISCOVERY_RESULTS] = None
    
    # Run discovery if not done yet
    if st.session_state[SESSION_KEY_DISCOVERY_RESULTS] is None:
        _run_discovery_analysis(raw_data)
    
    # Get discovery results
    discovery_result = st.session_state[SESSION_KEY_DISCOVERY_RESULTS]
    
    if discovery_result and discovery_result.entity_suggestions:
        _render_wizard_steps(raw_data, discovery_result)
        _render_wizard_reset()
    else:
        _render_fallback_continue()


def _run_discovery_analysis(raw_data: Dict[str, pd.DataFrame]) -> None:
    """Run discovery analysis on uploaded files."""
    with st.spinner("Analyzing your files to find connections..."):
        try:
            discovery_result = run_discovery(raw_data)
            st.session_state[SESSION_KEY_DISCOVERY_RESULTS] = discovery_result
            st.success(
                f"Found {len(discovery_result.entity_suggestions)} data types "
                f"and {len(discovery_result.relationship_suggestions)} potential connections "
                f"in {discovery_result.analysis_time_ms:.0f}ms"
            )
        except Exception as e:
            st.error(f"Error analyzing files: {e}")
            st.session_state[SESSION_KEY_DISCOVERY_RESULTS] = DiscoveryResult()


def _render_wizard_steps(
    raw_data: Dict[str, pd.DataFrame],
    discovery_result: DiscoveryResult
) -> None:
    """Render appropriate wizard step based on current progress."""
    wizard_step = _get_wizard_step()
    
    if wizard_step == 1:
        # Step 1: Column selection
        if render_wizard_step_1_columns(raw_data, key_prefix="upload_wizard_s1"):
            _set_wizard_step(2)
            st.rerun()
    
    elif wizard_step == 2:
        # Step 2: Connection definition
        if render_wizard_step_2_connections(
            raw_data,
            selected_columns_key="upload_wizard_s1_selected_columns",
            key_prefix="upload_wizard_s2"
        ):
            _set_wizard_step(3)
            st.rerun()
    
    elif wizard_step == 3:
        # Step 3: Confirm and join
        joined_df = render_wizard_step_3_confirm(
            raw_data,
            key_prefix="upload_wizard_s3"
        )
        if joined_df is not None:
            _finalize_wizard(joined_df)


def _finalize_wizard(joined_df: pd.DataFrame) -> None:
    """Finalize wizard by storing joined dataset and advancing to next step."""
    # Store the joined L3 dataset
    st.session_state.joined_l3_dataset = joined_df
    
    # Create L3 dataset for Step 3 (Define Categories)
    # L3 accepts DataFrame directly - no need to convert to graph
    st.session_state.datasets['l3'] = Level4Dataset.L3(joined_df)
    
    # Create entity/relationship mappings from the joined table
    entity_mapping = {}
    relationship_mapping = {}
    
    # Create a single entity from the joined table
    nodes = []
    relationships = []
    
    # The joined table becomes a single unified entity
    nodes.append(DataModelNode(
        label="JoinedData",
        key_property=joined_df.columns[0],
        properties=list(joined_df.columns)
    ))
    
    st.session_state.entity_mapping = entity_mapping
    st.session_state.relationship_mapping = relationship_mapping
    
    # Store the data model
    st.session_state.data_model = Neo4jDataModel(
        nodes=nodes,
        relationships=relationships
    )
    
    st.success(t("configuration_complete"))
    st.session_state.current_step = 2  # Skip to step 2 (graph building)
    st.rerun()


def _render_wizard_reset() -> None:
    """Render wizard reset button in expander."""
    with st.expander(f"🔄 {t('reset_analyze')}"):
        if st.button(t("reset_analyze"), key="upload_reset_wizard"):
            st.session_state[SESSION_KEY_DISCOVERY_RESULTS] = None
            _set_wizard_step(1)
            keys_to_clear = [
                k for k in st.session_state.keys()
                if k.startswith('upload_wizard_s')
            ]
            for k in keys_to_clear:
                del st.session_state[k]
            st.rerun()


def _render_fallback_continue() -> None:
    """Render fallback when discovery fails - manual mode."""
    st.warning(t("could_not_analyze"))
    if st.button(t("continue_arrow"), type="primary"):
        st.session_state.current_step = 1
        st.rerun()


def _render_search_interface() -> None:
    """
    Render data.gouv.fr search interface when no files are uploaded.

    Implements Spec 008: DataGouv Search Integration
    """
    # Initialize loaded datasets tracking
    if 'datagouv_loaded_datasets' not in st.session_state:
        st.session_state.datagouv_loaded_datasets = {}

    # Clean search interface only - basket is in sidebar
    loaded_df = render_search_interface()

    if loaded_df is not None:
        # Get the dataset name from session state or generate one
        dataset_name = st.session_state.get(
            'datagouv_last_dataset_name',
            f"dataset_{len(st.session_state.datagouv_loaded_datasets) + 1}.csv"
        )
        st.session_state.datagouv_loaded_datasets[dataset_name] = loaded_df
        st.session_state.pop('datagouv_last_dataset_name', None)
        st.rerun()

    # Small, discrete CSV upload option (below search)
    st.markdown("---")
    with st.expander("📁 Or upload your own CSV file", expanded=False):
        from intuitiveness.streamlit_app import smart_load_csv

        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=["csv"],
            key="discrete_csv_upload",
            label_visibility="collapsed"
        )

        if uploaded_file is not None:
            with st.spinner("Loading..."):
                try:
                    df, info_msg = smart_load_csv(uploaded_file)
                    if df is not None:
                        filename = uploaded_file.name
                        if "raw_data" not in st.session_state:
                            st.session_state.raw_data = {}
                        st.session_state.raw_data[filename] = df
                        st.success(f"✅ {filename} loaded")
                        st.rerun()
                    else:
                        st.error("Could not load file")
                except Exception as e:
                    st.error(f"Error: {e}")
