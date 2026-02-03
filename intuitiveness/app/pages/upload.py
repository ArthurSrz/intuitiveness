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
    Render Step 0: Cart-based dataset selection workflow.

    This page handles two modes:
    1. Selection Mode: Search/upload/demo data + cart building
    2. Processing Mode: Connection wizard and analysis preparation

    Args:
        step: Step configuration dictionary
        skip_header: Whether to skip step header rendering
    """
    from intuitiveness.streamlit_app import render_step_header

    if not skip_header:
        render_step_header(step)

    # Determine mode: selection (cart building) or processing (wizard)
    cart_mode = st.session_state.get('cart_mode', 'selection')

    if cart_mode == 'selection':
        _render_selection_mode()
    else:
        _render_processing_mode()


def _render_selection_mode() -> None:
    """
    Render selection mode: upload/search/demo interfaces + cart preview.

    Users can add multiple datasets to cart before starting analysis.
    """
    from intuitiveness.ui.cart import render_cart_preview_grid, render_cart_state_indicator

    # State indicator
    render_cart_state_indicator()

    # Cart preview (if not empty)
    from intuitiveness.app.models.cart import CartManager
    cart = CartManager()

    if not cart.is_empty():
        render_cart_preview_grid()
        st.markdown("---")

    # Data source options
    _render_search_interface()


def _render_processing_mode() -> None:
    """
    Render processing mode: wizard and connection configuration.

    Shows uploaded files and runs the connection wizard.
    """
    # Get raw data from session state (populated by cart)
    raw_data = st.session_state.get('raw_data') or {}

    if not raw_data:
        st.error("No data loaded. Please restart the workflow.")
        return

    _render_uploaded_files(raw_data)
    _render_connection_wizard(raw_data)


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

    # Show option to upload more files
    st.markdown("---")
    from intuitiveness.streamlit_app import smart_load_csv

    # Add styling for additional upload button
    st.markdown("""
    <style>
    /* Style for additional file upload button */
    [data-testid="stFileUploader"][key="additional_csv_upload"] section > div,
    [data-testid="stFileUploader"][key="additional_csv_upload"] section > ul,
    [data-testid="stFileUploader"][key="additional_csv_upload"] section > small,
    [data-testid="stFileUploader"][key="additional_csv_upload"] section span {
        display: none !important;
    }
    [data-testid="stFileUploader"][key="additional_csv_upload"] section > button:first-of-type {
        display: block !important;
    }
    [data-testid="stFileUploader"][key="additional_csv_upload"] section > button:not(:first-of-type) {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("""
            <div style="text-align: center; margin-bottom: 8px;">
                <span style="font-size: 0.9rem; color: #64748b;">
                    Want to connect multiple datasets?
                </span>
            </div>
        """, unsafe_allow_html=True)

        additional_file = st.file_uploader(
            "Upload another CSV",
            type=["csv"],
            key="additional_csv_upload",
            label_visibility="collapsed"
        )

        if additional_file is not None:
            # Check if file already uploaded
            if additional_file.name not in raw_data:
                with st.spinner("Loading..."):
                    try:
                        df, info_msg = smart_load_csv(additional_file)
                        if df is not None and not df.empty:
                            # Defensive: ensure raw_data is still a dict before assignment
                            if not isinstance(st.session_state.get('raw_data'), dict):
                                st.session_state.raw_data = {}
                            st.session_state.raw_data[additional_file.name] = df
                            st.success(f"✅ Added {additional_file.name}")
                            st.rerun()
                        else:
                            st.error("Failed to load CSV file")
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning("This file is already uploaded")


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

    # Show explicit "Continue to Descent" button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            f"✅ {t('continue_to_descent')}",
            type="primary",
            use_container_width=True,
            key="wizard_complete_continue"
        ):
            st.session_state.current_step = 2
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
    Render data source selection: search, upload, or demo data.

    Implements Spec 008: DataGouv Search Integration + Cart workflow
    """
    from intuitiveness.app.models.cart import CartManager
    from intuitiveness.ui.cart import add_to_cart_button

    # Tabs for different sources
    tab1, tab2, tab3 = st.tabs([
        "🌐 Data.gouv.fr Search",
        "📁 Upload Files",
        "🎯 Demo Data"
    ])

    with tab1:
        _render_datagouv_tab()

    with tab2:
        _render_upload_tab()

    with tab3:
        _render_demo_tab()


def _render_datagouv_tab() -> None:
    """Render data.gouv.fr search tab with cart integration."""
    # Initialize loaded datasets tracking (backward compatibility)
    if 'datagouv_loaded_datasets' not in st.session_state:
        st.session_state.datagouv_loaded_datasets = {}

    # Clean search interface - cart integration handled in datagouv_search.py
    loaded_df = render_search_interface()

    if loaded_df is not None:
        # This path is for backward compatibility with old search interface
        # New integration happens in datagouv_search.py via add_to_cart_button
        from intuitiveness.app.models.cart import CartManager

        dataset_name = st.session_state.get(
            'datagouv_last_dataset_name',
            f"dataset_{len(st.session_state.datagouv_loaded_datasets) + 1}.csv"
        )

        cart = CartManager()
        cart.add_item(
            name=dataset_name,
            source="datagouv",
            df=loaded_df
        )

        st.session_state.pop('datagouv_last_dataset_name', None)
        st.success(f"✅ {t('added_to_cart')}")
        st.rerun()


def _render_upload_tab() -> None:
    """Render file upload tab with cart integration."""
    from intuitiveness.streamlit_app import smart_load_csv
    from intuitiveness.app.models.cart import CartManager

    st.markdown("### Upload CSV Files")
    st.markdown("Upload one or more CSV files to your cart")

    uploaded_files = st.file_uploader(
        "Choose CSV files",
        type=["csv"],
        accept_multiple_files=True,
        key="cart_csv_upload"
    )

    if uploaded_files:
        cart = CartManager()

        for file in uploaded_files:
            # Check if already in cart
            if cart.get_item(file.name):
                st.info(f"✓ {file.name} already in cart")
                continue

            with st.spinner(f"Loading {file.name}..."):
                try:
                    df, info_msg = smart_load_csv(file)
                    if df is not None and not df.empty:
                        cart.add_item(
                            name=file.name,
                            source="upload",
                            df=df,
                            metadata={"original_name": file.name}
                        )
                        st.success(f"✅ Added {file.name} ({df.shape[0]} rows × {df.shape[1]} cols)")
                    else:
                        st.error(f"Failed to load {file.name}")
                except Exception as e:
                    st.error(f"Error loading {file.name}: {e}")

        # Rerun to update cart display
        if uploaded_files:
            st.rerun()


def _render_demo_tab() -> None:
    """Render demo data selector with cart integration."""
    from intuitiveness.app.models.cart import CartManager

    st.markdown(f"### {t('demo_data')}")
    st.markdown(t('choose_demo'))

    # Demo datasets (would load from actual files in production)
    demo_datasets = {
        "School Scores": {
            "description": "Middle school performance scores",
            "file": "demo_school_scores.csv"
        },
        "ADEME Funding": {
            "description": "Energy transition funding records",
            "file": "demo_ademe_funding.csv"
        },
        "Energy Prices": {
            "description": "Energy consumption and pricing data",
            "file": "demo_energy_prices.csv"
        }
    }

    cart = CartManager()

    for demo_name, demo_info in demo_datasets.items():
        with st.container():
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**{demo_name}**")
                st.caption(demo_info["description"])

            with col2:
                # Check if already in cart
                if cart.get_item(demo_name):
                    st.success("✓ In cart")
                else:
                    if st.button(
                        "Add",
                        key=f"demo_add_{demo_name}",
                        type="secondary",
                        use_container_width=True
                    ):
                        # In production, load actual demo CSV files
                        # For now, create placeholder DataFrame
                        demo_df = pd.DataFrame({
                            "id": range(1, 11),
                            "value": [i * 10 for i in range(1, 11)]
                        })

                        cart.add_item(
                            name=demo_name,
                            source="demo",
                            df=demo_df,
                            metadata={"file": demo_info["file"]}
                        )
                        st.rerun()

            st.markdown("---")
