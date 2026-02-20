"""
L2→L3 Graph Building Form - Entity Extraction

Implements Spec 004: FR-011-015 (L2→L3 Graph Building)
Extracted from ui/ascent_forms.py (lines 405-520)

Features:
- Allow users to select a column to extract as a new entity type
- Allow users to define the relationship type
- Create nodes for each unique value in the selected entity column
- Create edges connecting original table rows to the new entity nodes
- Ensure the resulting graph has no orphan nodes

Usage:
    from intuitiveness.ui.ascent import render_l2_to_l3_entity_form

    result = render_l2_to_l3_entity_form(l2_dataset)
    if result:
        # User submitted graph building parameters
        entity_column = result['entity_column']
        entity_type_name = result['entity_type_name']
        relationship_type = result['relationship_type']
"""

from typing import Any, Dict, Optional
import streamlit as st
import pandas as pd

from intuitiveness.ui.i18n import t


def render_l2_to_l3_entity_form(
    dataset: Any,
    key_prefix: str = "l2_to_l3"
) -> Optional[Dict[str, Any]]:
    """
    Render L2→L3 graph building form.

    FR-011: Allow users to select a column to extract as a new entity type
    FR-012: Allow users to define the relationship type
    FR-013: Create nodes for each unique value in the selected entity column
    FR-014: Create edges connecting original table rows to the new entity nodes
    FR-015: Ensure the resulting graph has no orphan nodes

    Args:
        dataset: Level2Dataset with table data
        key_prefix: Unique prefix for session state keys

    Returns:
        Dict with graph building parameters if submitted, None if not ready
    """
    st.markdown(f"### {t('create_connections_title')}")

    # Info tooltip explaining connection building operation
    st.info(
        f"**{t('create_connections_title')}**: {t('create_connections_info')}"
    )

    st.markdown(t("create_connections_desc"))

    # Get available columns
    data = dataset.get_data() if hasattr(dataset, 'get_data') else dataset
    if not isinstance(data, pd.DataFrame):
        st.error(t("no_table_data"))
        return None

    available_columns = list(data.columns)
    if not available_columns:
        st.error(t("no_columns_available"))
        return None

    # Column selector (FR-011)
    selected_column = st.selectbox(
        t("select_column_extract"),
        options=available_columns,
        key=f"{key_prefix}_column_select",
        help=t("select_column_help")
    )

    # Column analysis
    if selected_column:
        unique_count = data[selected_column].nunique()
        total_rows = len(data)

        # Warning for low cardinality
        if unique_count == 1:
            st.warning(t("single_value_warning", rows=total_rows))
        else:
            st.info(t("unique_values_info", count=unique_count))

    st.divider()

    # Item type name (FR-012)
    entity_type_name = st.text_input(
        t("item_type_name_label"),
        value=st.session_state.get(f'{key_prefix}_entity_name', ''),
        key=f"{key_prefix}_entity_name_input",
        placeholder=t("item_type_placeholder"),
        help=t("item_type_help")
    )
    st.session_state[f'{key_prefix}_entity_name'] = entity_type_name

    # Connection type (FR-012)
    relationship_type = st.text_input(
        t("connection_type_label"),
        value=st.session_state.get(f'{key_prefix}_rel_type', ''),
        key=f"{key_prefix}_rel_type_input",
        placeholder=t("connection_type_placeholder"),
        help=t("connection_type_help")
    )
    st.session_state[f'{key_prefix}_rel_type'] = relationship_type

    # Validation
    is_valid = (
        selected_column is not None
        and entity_type_name.strip() != ""
        and relationship_type.strip() != ""
    )

    if not is_valid:
        if not entity_type_name.strip():
            st.caption(t("enter_item_type_name"))
        if not relationship_type.strip():
            st.caption(t("enter_connection_type"))

    st.divider()

    # Submit button
    if st.button(
        t("create_connections_btn"),
        key=f"{key_prefix}_submit_btn",
        type="primary",
        disabled=not is_valid
    ):
        return {
            'entity_column': selected_column,
            'entity_type_name': entity_type_name.strip(),
            'relationship_type': relationship_type.strip(),
            'unique_values': data[selected_column].unique().tolist()
        }

    return None
