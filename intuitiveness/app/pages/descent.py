"""
Descent Page - L3→L2→L1→L0 Workflow

Implements Spec 011: Code Simplification
Extracted from streamlit_app.py (lines 1599-1798)

Handles:
- L3→L2 domain categorization
- L2→L1 feature extraction
- L1→L0 aggregation
- Atomic metric computation

Usage:
    from intuitiveness.app.pages import render_descent_page
    render_descent_page()
"""

import streamlit as st
import pandas as pd
from typing import Any, Dict, Optional

from intuitiveness.complexity import (
    Level3Dataset, Level2Dataset, Level1Dataset, Level0Dataset
)
from intuitiveness.redesign import Redesigner
from intuitiveness.ui import (
    render_page_header,
    render_section_header,
    render_l2_domain_table,
    render_l1_vector,
    render_l0_datum,
    t,
)
from intuitiveness.utils import SessionStateKeys
from intuitiveness.persistence.session_graph import SessionGraph


def _ensure_datasets_dict():
    """Ensure datasets dict exists in session state before writing to it."""
    if 'datasets' not in st.session_state:
        st.session_state['datasets'] = {}


def _track_descent_step(level: int, data_artifact, output_value=None,
                         description: str = "", params: dict = None):
    """
    Record a descent step in the SessionGraph for ascent recovery.

    Creates or updates the session graph stored in session state,
    adding the level state node and transition edge from the previous level.
    """
    graph_key = SessionStateKeys.LOADED_SESSION_GRAPH
    sg = st.session_state.get(graph_key)
    if sg is None:
        sg = SessionGraph()
        st.session_state[graph_key] = sg

    prev_id = sg.current_id
    node_id = sg.add_level_state(
        level=level,
        output_value=output_value,
        data_artifact=data_artifact,
        metadata={"decision_description": description},
    )
    if prev_id is not None:
        sg.add_transition(prev_id, node_id, action="descend", params=params)


def render_descent_page():
    """
    Render L3→L2→L1→L0 descent workflow page.

    Implements Spec 011: Descent Page Extraction

    Features:
    - Domain categorization (L3→L2)
    - Feature extraction (L2→L1)
    - Aggregation (L1→L0)
    - Atomic metric display

    Workflow:
    1. User selects domains for categorization
    2. System categorizes L3 graph into L2 table
    3. User selects column for L1 vector
    4. User selects aggregation method
    5. L0 datum computed and displayed
    """
    render_page_header(
        title=t('descent_title'),
        subtitle=t('descent_subtitle')
    )

    # Determine current descent step
    datasets = st.session_state.get('datasets', {})

    if 'l3' not in datasets:
        st.error(t('no_l3_dataset'))
        return

    # Check what we have
    if 'l0' in datasets:
        render_results_view(datasets['l0'])
    elif 'l1' in datasets:
        render_aggregation_step(datasets['l1'])
    elif 'l2' in datasets:
        render_feature_extraction_step(datasets['l2'])
    else:
        render_domain_categorization_step(datasets['l3'])


def render_domain_categorization_step(l3_dataset: Level3Dataset):
    """
    Step 1: L3→L2 domain categorization.

    User specifies domains and system categorizes graph nodes.
    """
    render_section_header(t('step_domains'))

    st.write(t('domain_categorization_prompt'))

    # Domain input
    domains_input = st.text_input(
        t('enter_domains'),
        placeholder=t('domain_placeholder'),
        help=t('domain_help')
    )

    # Matching strategy
    col1, col2 = st.columns(2)
    with col1:
        use_semantic = st.checkbox(t('use_semantic_matching'), value=True)
    with col2:
        threshold = st.slider(
            t('similarity_threshold'),
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.05
        )

    if st.button(t('categorize'), type="primary") and domains_input:
        domains = [d.strip() for d in domains_input.split(',') if d.strip()]

        with st.spinner(t('categorizing')):
            # Perform categorization
            l2_dataset = categorize_l3_to_l2(
                l3_dataset,
                domains=domains,
                use_semantic=use_semantic,
                threshold=threshold
            )

            _ensure_datasets_dict()
            st.session_state['datasets']['l2'] = l2_dataset
            _track_descent_step(
                level=2, data_artifact=l2_dataset.get_data(),
                description=f"Categorized into domains: {domains}",
                params={"domains": domains, "threshold": threshold},
            )
            st.success(t('categorization_complete'))
            st.rerun()


def render_feature_extraction_step(l2_dataset: Level2Dataset):
    """
    Step 2: L2→L1 feature extraction.

    User selects column to extract as L1 vector.
    """
    render_section_header(t('step_features'))

    st.write(t('feature_extraction_prompt'))

    # Display L2 table
    df = l2_dataset.get_data()
    st.dataframe(df.head(10), use_container_width=True)

    # Column selection
    column = st.selectbox(
        t('select_column'),
        options=df.columns.tolist(),
        help=t('column_help')
    )

    if st.button(t('extract_features'), type="primary"):
        with st.spinner(t('extracting')):
            # Extract column as L1 vector
            redesigner = Redesigner()
            l1_dataset = redesigner.reduce_complexity(
                l2_dataset,
                target_level=1,
                column=column
            )

            _ensure_datasets_dict()
            st.session_state['datasets']['l1'] = l1_dataset
            _track_descent_step(
                level=1, data_artifact=l1_dataset.get_data(),
                description=f"Extracted column: {column}",
                params={"column": column},
            )
            st.success(t('extraction_complete'))
            st.rerun()


def render_aggregation_step(l1_dataset: Level1Dataset):
    """
    Step 3: L1→L0 aggregation.

    User selects aggregation method to compute atomic metric.
    """
    render_section_header(t('step_aggregation'))

    st.write(t('aggregation_prompt'))

    # Display L1 vector
    render_l1_vector(l1_dataset)

    # Aggregation method selection
    aggregation = st.selectbox(
        t('select_aggregation'),
        options=['mean', 'sum', 'count', 'min', 'max'],
        index=0,
        help=t('aggregation_help')
    )

    if st.button(t('compute_metric'), type="primary"):
        with st.spinner(t('computing')):
            # Aggregate to L0
            redesigner = Redesigner()
            l0_dataset = redesigner.reduce_complexity(
                l1_dataset,
                target_level=0,
                aggregation=aggregation
            )

            _ensure_datasets_dict()
            st.session_state['datasets']['l0'] = l0_dataset
            _track_descent_step(
                level=0,
                data_artifact=l0_dataset.value if hasattr(l0_dataset, 'value') else l0_dataset,
                output_value=l0_dataset.value if hasattr(l0_dataset, 'value') else l0_dataset,
                description=f"Aggregated with: {aggregation}",
                params={"aggregation": aggregation},
            )
            st.success(t('metric_computed'))
            st.rerun()


def render_results_view(l0_dataset: Level0Dataset):
    """
    Step 4: Results display.

    Shows atomic metric (L0 datum) with metadata.
    """
    render_section_header(t('results_title'))

    st.write(t('results_prompt'))

    # Display L0 datum
    render_l0_datum(l0_dataset)

    # Show metadata
    with st.expander(t('show_metadata')):
        st.json({
            'value': l0_dataset.value,
            'aggregation_method': l0_dataset.aggregation_method,
            'has_parent': l0_dataset.has_parent,
            'description': l0_dataset.description
        })

    # Navigation buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button(t('start_ascent'), type="primary"):
            # Use SWITCH_TO_ASCENT flag so _handle_ascent_mode_switch() processes
            # the transition before sidebar widgets render (avoids widget conflicts)
            st.session_state[SessionStateKeys.SWITCH_TO_ASCENT] = True
            st.rerun()
    with col2:
        if st.button(t('export_session')):
            # Set out-of-bounds step to trigger export page rendering
            st.session_state[SessionStateKeys.CURRENT_STEP] = 99
            st.rerun()


def categorize_l3_to_l2(
    l3_dataset: Level3Dataset,
    domains: list,
    use_semantic: bool,
    threshold: float
) -> Level2Dataset:
    """
    Categorize L3 graph into L2 table by domains.

    Parameters:
    -----------
    l3_dataset : Level3Dataset
        Input graph
    domains : list
        Domain categories
    use_semantic : bool
        Use semantic matching
    threshold : float
        Similarity threshold

    Returns:
    --------
    Level2Dataset
        Categorized table
    """
    G = l3_dataset.get_data()

    # Extract nodes as rows
    rows = []
    for node in G.nodes():
        node_data = G.nodes[node]
        row = {
            'node_id': node,
            'node_type': node_data.get('node_type', 'unknown'),
            'category': 'uncategorized'  # Placeholder for domain
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Apply domain categorization (simplified for now)
    # In full implementation, use semantic matching
    if domains:
        df['category'] = domains[0]  # Assign first domain as default

    return Level2Dataset(df)
