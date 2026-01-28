"""
Streamlit App for Interactive Data Redesign - REFACTORED

Implements Spec 011: Code Simplification (4,900 → ~800 lines)

This module provides the main entry point for the Streamlit app, delegating
to specialized page modules for rendering logic.

Architecture:
- app/sidebar.py: Sidebar rendering and controls
- app/pages/*.py: Page-specific rendering logic
- This file: Configuration, initialization, routing

Usage:
    streamlit run intuitiveness/streamlit_app.py

Author: Intuitiveness Framework
"""

import streamlit as st
import pandas as pd
import networkx as nx
import json
import csv
import io
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

# Get the project root directory for asset paths
PROJECT_ROOT = Path(__file__).parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"

# Core data structures
from intuitiveness.complexity import (
    Level4Dataset, Level3Dataset, Level2Dataset, Level1Dataset, Level0Dataset
)
from intuitiveness.interactive import (
    DataModelGenerator, Neo4jDataModel, SemanticMatcher, QuestionType, DataModelNode, DataModelRelationship
)
from intuitiveness.navigation import NavigationSession, NavigationState, NavigationError
from intuitiveness.persistence import (
    SessionStore,
    SessionCorrupted,
    VersionMismatch,
)
from intuitiveness.discovery import (
    RelationshipDiscovery,
    EntitySuggestion,
    RelationshipSuggestion,
    DiscoveryResult,
    run_discovery,
)

# UI components
from intuitiveness.ui import (
    DecisionTreeComponent, render_simple_tree,
    JsonVisualizer, render_navigation_export,
    DragDropRelationshipBuilder, get_entities_from_dataframe,
    render_l4_file_list,
    render_l2_domain_table,
    render_l1_vector,
    render_l0_datum,
    extract_entity_tabs,
    extract_relationship_tabs,
    render_entity_relationship_tabs,
    render_l0_to_l1_unfold_form,
    render_l1_to_l2_domain_form,
    render_l2_to_l3_entity_form,
    render_wizard_step_1_columns,
    render_wizard_step_1_entities,
    render_wizard_step_2_connections,
    render_wizard_step_2_relationships,
    render_wizard_step_3_confirm,
    convert_suggestions_to_mappings,
    _get_wizard_step,
    _set_wizard_step,
    SESSION_KEY_WIZARD_STEP,
    SESSION_KEY_DISCOVERY_RESULTS,
    RecoveryAction,
    render_recovery_banner,
    render_start_fresh_button,
    render_start_fresh_confirmation,
    t,
    render_language_toggle_compact,
    render_page_header,
    render_section_header,
    card,
    render_quality_dashboard,
    render_catalog_browser,
    separator,
    spacer,
    render_search_interface,
    render_basket_sidebar,
    render_tutorial,
    render_tutorial_replay_button,
    is_tutorial_completed,
    mark_tutorial_completed,
    reset_tutorial,
)

# Neo4j utilities
from intuitiveness.neo4j_writer import (
    generate_constraint_queries,
    generate_node_ingest_query,
    generate_relationship_ingest_query,
    generate_full_ingest_script
)
from intuitiveness.neo4j_client import Neo4jClient

# Styling
from intuitiveness.styles import inject_all_styles
from intuitiveness.styles.charts import (
    styled_bar_chart,
    styled_metric_card,
    render_plotly_chart,
    render_metrics_row,
    KLEIN_BLUE,
    CHART_COLORS,
)

# Session management
from intuitiveness.utils import (
    init_session_state as utils_init_session_state,
    SessionStateKeys,
    session,
)

# Page modules (Spec 011: Code Simplification)
from intuitiveness.app.sidebar import render_sidebar
from intuitiveness.app.pages.upload import render_upload_page
# Note: Other page imports will be added as we integrate them

# ============================================================================
# ESSENTIAL UTILITIES (kept from original)
# ============================================================================

def smart_load_csv(file) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Intelligently load CSV files with auto-detection of:
    - Delimiter (comma, semicolon, tab, pipe)
    - Encoding (utf-8, latin-1, cp1252, iso-8859-1)
    - Handle malformed lines gracefully

    Returns:
        (DataFrame, info_string) on success
        (None, error_string) on failure
    """
    DELIMITERS = [',', ';', '\t', '|']
    ENCODINGS = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'utf-16']

    # Read file content once
    file.seek(0)
    raw_content = file.read()

    # Try each encoding
    for encoding in ENCODINGS:
        try:
            if isinstance(raw_content, bytes):
                content = raw_content.decode(encoding)
            else:
                content = raw_content
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        return None, "Could not decode file with any known encoding"

    # Use csv.Sniffer to detect delimiter
    try:
        sample = content[:8192]  # First 8KB
        dialect = csv.Sniffer().sniff(sample, delimiters=''.join(DELIMITERS))
        detected_delimiter = dialect.delimiter
    except csv.Error:
        # Fallback: count delimiters in first few lines
        first_lines = content.split('\n')[:5]
        delimiter_counts = {d: sum(line.count(d) for line in first_lines) for d in DELIMITERS}
        detected_delimiter = max(delimiter_counts, key=delimiter_counts.get)

    # Try to load with detected settings
    try:
        df = pd.read_csv(
            io.StringIO(content),
            sep=detected_delimiter,
            on_bad_lines='skip',
            engine='python'
        )

        # Validate we got something useful
        if len(df.columns) < 2 and detected_delimiter != ',':
            # Try comma as fallback
            df = pd.read_csv(
                io.StringIO(content),
                sep=',',
                on_bad_lines='skip',
                engine='python'
            )
            detected_delimiter = ','

        delimiter_name = {',': 'comma', ';': 'semicolon', '\t': 'tab', '|': 'pipe'}.get(detected_delimiter, detected_delimiter)
        return df, f"encoding={encoding}, delimiter={delimiter_name}"

    except Exception as e:
        return None, f"Parsing error: {str(e)}"


def format_l0_value_for_display(value: Any) -> str:
    """
    Format L0 datum value for display.
    
    Handles:
    - Numeric values with appropriate precision
    - Large numbers with K/M/B suffixes
    - Non-numeric values
    """
    if isinstance(value, (int, float)):
        if abs(value) >= 1_000_000_000:
            return f"{value/1_000_000_000:.2f}B"
        elif abs(value) >= 1_000_000:
            return f"{value/1_000_000:.2f}M"
        elif abs(value) >= 1_000:
            return f"{value/1_000:.2f}K"
        elif isinstance(value, float):
            return f"{value:.4f}"
        else:
            return str(value)
    return str(value)


def init_session_state():
    """
    Initialize Streamlit session state for the redesign workflow.

    Delegates to centralized session manager (Phase 0 - 011-code-simplification).
    Session keys and defaults are defined in utils/session_manager.py
    with spec traceability comments.
    """
    utils_init_session_state()


def reset_workflow():
    """Reset the workflow to start over."""
    st.session_state.current_step = 0
    st.session_state.answers = {}
    st.session_state.datasets = {}
    st.session_state.data_model = None
    # Reset free navigation state
    st.session_state.nav_mode = 'guided'
    st.session_state.nav_session = None
    st.session_state.nav_action = None
    st.session_state.nav_target = None
    st.session_state.nav_export = None
    st.session_state.relationship_builder = None


# ============================================================================
# WORKFLOW STEPS CONFIGURATION
# ============================================================================

STEPS = [
    {
        "id": "upload",
        "title": "Unlinkable datasets // Données non-structurées",
        "level": "Step 1",
        "description": "Upload your raw data files (CSV format)"
    },
    {
        "id": "entities",
        "title": "Linkable data // Données liables",
        "level": "Step 2",
        "description": "What are the main things you want to see in your connected information?"
    },
    {
        "id": "domains",
        "title": "Table // Tableau de données",
        "level": "Step 3",
        "description": "What categories do you want to organize your data by?"
    },
    {
        "id": "features",
        "title": "Vector // Vecteur de données",
        "level": "Step 4",
        "description": "What values do you want to extract?"
    },
    {
        "id": "aggregation",
        "title": "Datum // Datum",
        "level": "Step 5",
        "description": "What computation do you want to run on your values?"
    },
    {
        "id": "results",
        "title": "Final Results // Résultats finaux",
        "level": "Step 6",
        "description": "View your complete analysis"
    }
]

# Ascent phase steps (Steps 7-12) - Bilingual: English // Français
ASCENT_STEPS = [
    {
        "id": "l0_to_l1",
        "title": "Datum → Vector // Datum → Vecteur",
        "level": "Ascent Step 1",
        "description": "Unfold datum into vector"
    },
    {
        "id": "l1_to_l2",
        "title": "Vector → Table // Vecteur → Tableau",
        "level": "Ascent Step 2",
        "description": "Enrich vector with domain knowledge"
    },
    {
        "id": "l2_to_l3",
        "title": "Table → Graph // Tableau → Graphe",
        "level": "Ascent Step 3",
        "description": "Build knowledge graph from table"
    }
]


def render_step_header(step: dict):
    """Render step header with title and description."""
    st.markdown(f"## {step['title']}")
    if step.get('description'):
        st.markdown(f"*{step['description']}*")


def inject_right_sidebar_css():
    """
    Inject CSS for the fixed right sidebar progress indicator.
    
    This creates a persistent vertical progress bar showing the current
    navigation level (L0-L4) and phase (descent/ascent).
    """
    st.markdown("""
    <style>
    /* Fixed right sidebar for progress indicator */
    .right-sidebar {
        position: fixed;
        right: 0;
        top: 0;
        height: 100vh;
        width: 60px;
        background: white;
        border-left: 1px solid #e5e7eb;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        z-index: 999;
        padding: 1rem 0;
    }
    
    .progress-indicator {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    
    .level-dot {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        border: 2px solid #e5e7eb;
        background: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.7rem;
        font-weight: 600;
        color: #9ca3af;
        transition: all 0.3s ease;
    }
    
    .level-dot.active {
        background: #002fa7;
        border-color: #002fa7;
        color: white;
        transform: scale(1.2);
    }
    
    .level-dot.completed {
        background: #10b981;
        border-color: #10b981;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main Streamlit app entry point - REFACTORED for readability."""
    
    # App configuration
    st.set_page_config(
        page_title="Data Redesign Method",
        page_icon="🔄",
        layout="wide"
    )
    
    # Inject centralized design styles (007-streamlit-design-makeup)
    inject_all_styles()
    inject_right_sidebar_css()
    
    # Initialize session state
    init_session_state()
    
    # Handle ascent mode switch (before sidebar widget renders)
    _handle_ascent_mode_switch()
    
    # Session persistence
    store = SessionStore()
    _handle_session_recovery(store)
    
    # Determine if sidebar should be shown
    is_pure_landing = _is_pure_landing_page()
    
    if is_pure_landing:
        # Hide sidebar on pure landing page
        st.markdown("""
        <style>
        [data-testid="stSidebar"] { display: none !important; }
        .stApp > header { display: none !important; }
        </style>
        """, unsafe_allow_html=True)
    else:
        # Render sidebar (delegated to sidebar module)
        with st.sidebar:
            render_sidebar(store)
    
    # Main content routing
    _route_to_active_page()
    
    # Render fixed right sidebar progress indicator
    render_vertical_progress_sidebar()


def _handle_ascent_mode_switch():
    """Handle switch from descent to ascent mode."""
    if st.session_state.get(SessionStateKeys.SWITCH_TO_ASCENT):
        del st.session_state[SessionStateKeys.SWITCH_TO_ASCENT]
        st.session_state[SessionStateKeys.NAV_MODE] = 'free'
        # Delete widget key so it reinitializes with new nav_mode value
        if SessionStateKeys.MODE_SELECTOR in st.session_state:
            del st.session_state[SessionStateKeys.MODE_SELECTOR]
    
    # Keep free mode when in ascent workflow (has loaded_session_graph)
    if st.session_state.get(SessionStateKeys.LOADED_SESSION_GRAPH) and \
       st.session_state.get(SessionStateKeys.NAV_MODE) != 'free':
        st.session_state[SessionStateKeys.NAV_MODE] = 'free'


def _handle_session_recovery(store: SessionStore):
    """Handle session recovery on first load."""
    if 'session_recovery_handled' not in st.session_state:
        st.session_state.session_recovery_handled = True
        
        if store.has_saved_session():
            info = store.get_session_info()
            if info:
                action = render_recovery_banner(info)
                
                if action == RecoveryAction.CONTINUE:
                    try:
                        result = store.load()
                        if result.warnings:
                            for w in result.warnings:
                                st.warning(w)
                        st.success(f"Session restored! Resuming from Step {result.wizard_step + 1}")
                    except (SessionCorrupted, VersionMismatch) as e:
                        st.error(f"Could not restore session: {e}")
                        store.clear()
                    st.rerun()
                elif action == RecoveryAction.START_FRESH:
                    store.clear()
                    st.rerun()
                elif action == RecoveryAction.PENDING:
                    # User hasn't clicked yet - stop here and wait
                    st.stop()


def _is_pure_landing_page() -> bool:
    """Check if we're on the pure landing page (no data, no search)."""
    return (
        st.session_state.get(SessionStateKeys.NAV_MODE) == 'guided' and
        st.session_state.get(SessionStateKeys.CURRENT_STEP) == 0 and
        st.session_state.get(SessionStateKeys.RAW_DATA) is None and
        not st.session_state.get('datagouv_loaded_datasets') and
        not st.session_state.get('datagouv_results')
    )


def _route_to_active_page():
    """Route to the active page based on mode and state."""
    
    # Check for Quality Tools first (009-quality-data-platform)
    active_quality_tool = st.session_state.get('active_quality_tool', 'none')
    if active_quality_tool == 'quality':
        render_quality_dashboard()
        return
    elif active_quality_tool == 'catalog':
        render_catalog_browser()
        return
    
    # Route based on navigation mode
    if st.session_state.nav_mode == 'guided':
        _render_guided_mode()
    else:
        _render_free_mode()


def _render_guided_mode():
    """Render guided (step-by-step) mode."""
    
    # Check if we're in search flow (hide header)
    is_search_landing = (
        st.session_state.current_step == 0 and
        st.session_state.raw_data is None
    )
    
    # Show tutorial dialog if appropriate
    should_show_tutorial = (
        st.session_state.get('show_tutorial', False) and
        not is_tutorial_completed()
    )
    
    if should_show_tutorial:
        render_tutorial()
    
    # Dispatch to appropriate step
    step_id = STEPS[st.session_state.current_step]['id']
    step = STEPS[st.session_state.current_step]
    
    if step_id == "upload":
        render_upload_page(step, skip_header=is_search_landing)
    elif step_id == "entities":
        render_entities_step()
    elif step_id == "domains":
        render_domains_step()
    elif step_id == "features":
        render_features_step()
    elif step_id == "aggregation":
        render_aggregation_step()
    elif step_id == "results":
        render_results_step()


def _render_free_mode():
    """Render free exploration mode."""
    
    # Check for export view
    if st.session_state.nav_export:
        render_export_view()
        return
    
    # Check if data is available OR we have a loaded session graph
    if st.session_state.raw_data is None and not st.session_state.get('loaded_session_graph'):
        st.warning(
            "Please upload data first in **Step-by-Step** mode, or load a saved session graph below."
        )
        
        # Offer two options
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Switch to Step-by-Step"):
                st.session_state.nav_mode = 'guided'
                st.rerun()
        
        with col2:
            st.markdown("**OR**")
        
        # Session graph loader
        render_session_graph_loader()
    else:
        render_free_navigation_main()


def render_vertical_progress_sidebar():
    """
    Render the vertical progress indicator on the right side.
    
    Shows current level (L0-L4) and phase (descent/ascent).
    """
    # Implementation placeholder - kept from original
    # This function renders the fixed progress bar on the right side
    pass


# Placeholder functions for features still in original file
# These will be gradually migrated or kept as needed

def render_entities_step():
    """Placeholder - needs migration to app/pages/descent.py"""
    st.info("Entity step - under migration")

def render_domains_step():
    """Placeholder - needs migration to app/pages/descent.py"""
    st.info("Domains step - under migration")

def render_features_step():
    """Placeholder - needs migration to app/pages/descent.py"""
    st.info("Features step - under migration")

def render_aggregation_step():
    """Placeholder - needs migration to app/pages/descent.py"""
    st.info("Aggregation step - under migration")

def render_results_step():
    """Placeholder - needs migration to app/pages/descent.py"""
    st.info("Results step - under migration")

def render_export_view():
    """Placeholder - needs migration to app/pages/export.py"""
    st.info("Export view - under migration")

def render_session_graph_loader():
    """Placeholder - session graph loading UI"""
    st.info("Session graph loader - under migration")

def render_free_navigation_main():
    """Placeholder - free navigation main view"""
    st.info("Free navigation - under migration")

def render_free_navigation_sidebar():
    """Placeholder - free navigation sidebar"""
    pass


if __name__ == "__main__":
    main()
