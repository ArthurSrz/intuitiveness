"""
L3 Display - Knowledge Graph with Entity/Relationship Tabs

Implements Spec 003: FR-003-007 (L3 Graph Display with Tabs)
Uses logic from ui/entity_tabs.py

Displays a knowledge graph with tabbed views:
- Entity tabs: One tab per entity type showing properties
- Relationship tabs: One tab per relationship type showing connections
- Combined view: All entities/relationships for overview

Usage:
    from intuitiveness.ui.levels import render_l3_graph_with_tabs
    render_l3_graph_with_tabs(graph_data)
"""

from typing import Any, Union
import streamlit as st
import pandas as pd
import networkx as nx


def render_l3_graph_with_tabs(
    graph_data: Union[nx.DiGraph, pd.DataFrame],
    max_preview_rows: int = 50
) -> None:
    """
    Render L3 (Knowledge Graph) display with entity/relationship tabs.

    FR-003: Display a tabbed interface for the L3 graph
    FR-004: Display tabbed views with one tab per entity type
    FR-005: Display one tab per relationship type
    FR-006: Include a "Combined" view showing all entities and relationships
    FR-007: Each entity tab shows id, name, type, and properties

    Args:
        graph_data: NetworkX graph OR DataFrame (from OOM fix)
        max_preview_rows: Maximum rows per tab (default: 50)

    Examples:
        >>> import networkx as nx
        >>> G = nx.DiGraph()
        >>> G.add_node("school_1", type="School", name="Lincoln Elementary", score=90)
        >>> G.add_node("teacher_1", type="Teacher", name="Smith")
        >>> G.add_edge("teacher_1", "school_1", relationship="teaches_at")
        >>> render_l3_graph_with_tabs(G)
        # Shows tabs: School, Teacher, teaches_at, All Items, All Connections
    """
    # Import entity tab extraction logic
    from intuitiveness.ui.entity_tabs import (
        extract_entity_tabs,
        extract_relationship_tabs,
        extract_combined_tabs
    )

    st.markdown("### 🔗 Your Connected Information")

    # Extract tab data
    try:
        entity_tabs = extract_entity_tabs(graph_data)
        relationship_tabs = extract_relationship_tabs(graph_data)
        combined_tabs = extract_combined_tabs(graph_data)
    except Exception as e:
        st.error(f"Error extracting graph data: {e}")
        return

    # Create tab layout: Entities | Relationships | Combined
    tab_labels = (
        [f"📦 {tab.entity_type} ({tab.entity_count})" for tab in entity_tabs] +
        [f"🔗 {tab.relationship_key} ({tab.relationship_count})" for tab in relationship_tabs] +
        [f"📊 {tab.label} ({tab.count})" for tab in combined_tabs]
    )

    if not tab_labels:
        st.info("No graph data available to display.")
        return

    # Render tabs
    tabs = st.tabs(tab_labels)

    # Entity tabs
    for idx, entity_tab in enumerate(entity_tabs):
        with tabs[idx]:
            _render_entity_tab(entity_tab, max_preview_rows)

    # Relationship tabs
    offset = len(entity_tabs)
    for idx, rel_tab in enumerate(relationship_tabs):
        with tabs[offset + idx]:
            _render_relationship_tab(rel_tab, max_preview_rows)

    # Combined tabs
    offset += len(relationship_tabs)
    for idx, combined_tab in enumerate(combined_tabs):
        with tabs[offset + idx]:
            _render_combined_tab(combined_tab, max_preview_rows)


def _render_entity_tab(entity_tab, max_rows: int) -> None:
    """Render a single entity type tab."""
    df = entity_tab.to_dataframe()

    st.markdown(f"**{entity_tab.entity_count} {entity_tab.entity_type} entities**")

    display_df = df.head(max_rows) if len(df) > max_rows else df
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    if len(df) > max_rows:
        st.caption(f"Showing first {max_rows} of {len(df):,} entities")


def _render_relationship_tab(rel_tab, max_rows: int) -> None:
    """Render a single relationship type tab."""
    df = rel_tab.to_dataframe()

    st.markdown(f"**{rel_tab.relationship_count} {rel_tab.relationship_type} connections**")

    display_df = df.head(max_rows) if len(df) > max_rows else df
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    if len(df) > max_rows:
        st.caption(f"Showing first {max_rows} of {len(df):,} connections")


def _render_combined_tab(combined_tab, max_rows: int) -> None:
    """Render a combined view tab (All Items or All Connections)."""
    df = combined_tab.to_dataframe()

    st.markdown(f"**{combined_tab.count} total items**")

    display_df = df.head(max_rows) if len(df) > max_rows else df
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    if len(df) > max_rows:
        st.caption(f"Showing first {max_rows} of {len(df):,} items")


def render_l3_ascent_preview(
    categorized_table: pd.DataFrame,
    entity_column: str,
    num_unique_entities: int
) -> None:
    """
    Render L3→L2 ascent preview showing graph being categorized to table.

    Implements Spec 003: FR-014 (Ascent displays show lower level data)

    Args:
        categorized_table: The resulting L2 table
        entity_column: Column used for entity extraction
        num_unique_entities: Number of unique entities created

    Examples:
        >>> df = pd.DataFrame({"category": ["A", "B"], "value": [10, 20]})
        >>> render_l3_ascent_preview(df, "category", 2)
        # Shows "Created 2 unique entities from column: category"
    """
    st.markdown("### L3 Graph → L2 Table")
    st.info(f"Created **{num_unique_entities}** unique entities from column: **{entity_column}**")

    # Show resulting table preview
    st.dataframe(categorized_table.head(10), use_container_width=True)

    if len(categorized_table) > 10:
        st.caption(f"Showing first 10 of {len(categorized_table):,} rows")
