"""
Streamlit App for Interactive Data Redesign - REFACTORED

Version: b0aa53d+1 (deploy trigger)
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
from intuitiveness.app.pages.descent import render_descent_page

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
    """Reset the workflow to start over — clears all state comprehensively."""
    st.session_state.current_step = 0
    st.session_state.answers = {}
    st.session_state.datasets = {}
    st.session_state.data_model = None
    st.session_state.raw_data = None
    # Reset free navigation state
    st.session_state.nav_mode = 'guided'
    st.session_state.nav_session = None
    st.session_state.nav_action = None
    st.session_state.nav_target = None
    st.session_state.nav_export = None
    st.session_state.relationship_builder = None
    # Reset ascent state
    st.session_state.pop('ascent_level', None)
    st.session_state.pop('loaded_session_graph', None)
    st.session_state.pop('loaded_graph_decisions', None)
    # Reset cart state
    st.session_state.pop('dataset_cart', None)
    st.session_state.cart_mode = 'selection'
    st.session_state.analysis_started = False
    # Reset quality/synthetic tools
    st.session_state.pop('active_quality_tool', None)
    st.session_state.pop('quality_df', None)
    st.session_state.pop('quality_report', None)
    st.session_state.pop('synthetic_result', None)
    st.session_state.pop('synthetic_metrics', None)
    # Reset wizard state
    st.session_state.pop('wizard_step', None)
    st.session_state.pop('discovery_results', None)


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

# Combine descent + ascent into a single STEPS array for unified dispatch
ALL_STEPS = STEPS + ASCENT_STEPS


def render_step_header(step: dict):
    """Render step header with title and description, split by language."""
    title = step['title']
    # Split bilingual titles (e.g., "English // Français") by active language
    if ' // ' in title:
        en_title, fr_title = title.split(' // ', 1)
        lang = st.session_state.get('ui_language', 'en')
        title = fr_title if lang == 'fr' else en_title
    st.markdown(f"## {title}")
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
    /* Right sidebar container - fixed position, small and compact */
    .right-progress-sidebar {
        position: fixed;
        right: 5px;
        top: 50%;
        transform: translateY(-50%);
        height: auto;
        width: 50px;
        background: linear-gradient(180deg, #fafaf9, #f5f5f4);
        border: 1px solid #e7e5e4;
        border-radius: 0.5rem;
        z-index: 999;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        padding: 15px 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    /* Progress track container */
    .progress-track {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0;
    }

    /* Level container with emoji */
    .level-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
    }

    .level-emoji {
        font-size: 18px;
        line-height: 1;
    }

    .level-label {
        font-size: 0.55rem;
        font-weight: 500;
        color: #78716c;
        text-transform: uppercase;
        letter-spacing: 0.02em;
        white-space: nowrap;
    }

    /* Transition bars (horizontal thick lines) */
    .transition-bar {
        width: 30px;
        height: 8px;
        border-radius: 4px;
        transition: all 0.3s ease;
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .transition-bar.completed {
        background: #22c55e;
    }

    .transition-bar.current-descent {
        background: #2563eb;
    }

    .transition-bar.current-ascent {
        background: #f59e0b;
    }

    .transition-bar.pending {
        background: #a8a29e;
    }

    /* Vertical connectors between bars */
    .connector {
        width: 3px;
        height: 80px;
        background: #e7e5e4;
    }

    .connector.completed {
        background: #22c55e;
    }

    /* Pulsing glow animation for current bar */
    @keyframes glow-descent {
        0%, 100% {
            box-shadow: 0 0 4px #2563eb;
        }
        50% {
            box-shadow: 0 0 12px #2563eb, 0 0 20px #2563eb;
        }
    }

    @keyframes glow-ascent {
        0%, 100% {
            box-shadow: 0 0 4px #f59e0b;
        }
        50% {
            box-shadow: 0 0 12px #f59e0b, 0 0 20px #f59e0b;
        }
    }

    .transition-bar.current-descent {
        animation: glow-descent 1.5s ease-in-out infinite;
    }

    .transition-bar.current-ascent {
        animation: glow-ascent 1.5s ease-in-out infinite;
    }

    /* Mode label at top */
    .progress-mode-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 20px;
        writing-mode: vertical-rl;
        text-orientation: mixed;
        transform: rotate(180deg);
    }

    .progress-mode-label.descent {
        color: #2563eb;
    }

    .progress-mode-label.ascent {
        color: #f59e0b;
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
    """Handle switch from descent to ascent mode.

    Stays in guided mode and advances to the first ascent step (index 6
    in ALL_STEPS = STEPS + ASCENT_STEPS). The ascent steps are dispatched
    by _render_guided_mode() → _render_ascent_step().
    """
    if st.session_state.get(SessionStateKeys.SWITCH_TO_ASCENT):
        del st.session_state[SessionStateKeys.SWITCH_TO_ASCENT]
        # Stay in guided mode — ascent steps are ALL_STEPS[6..8]
        st.session_state[SessionStateKeys.CURRENT_STEP] = len(STEPS)  # First ascent step
        st.session_state.ascent_level = 0  # Initialize ascent tracking for sidebar


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
    """Check if we're on the pure landing page (no data, no search, empty cart)."""
    from intuitiveness.app.models.cart import CartManager
    cart = CartManager()
    return (
        st.session_state.get(SessionStateKeys.NAV_MODE) == 'guided' and
        st.session_state.get(SessionStateKeys.CURRENT_STEP) == 0 and
        st.session_state.get(SessionStateKeys.RAW_DATA) is None and
        not st.session_state.get('datagouv_loaded_datasets') and
        not st.session_state.get('datagouv_results') and
        cart.is_empty()
    )


def _bridge_raw_data_to_quality_df():
    """Bridge cart/upload/datasets data to quality_df if not already set.

    The quality tool reads from session_state['quality_df'] but data may live
    in raw_data, datasets dict, or the cart. This bridge auto-populates
    quality_df from whichever source is available.
    """
    quality_df_key = SessionStateKeys.QUALITY_DF
    if st.session_state.get(quality_df_key) is not None:
        return  # Already set, don't override

    # Source 1: raw_data (from uploads or cart.to_raw_data())
    raw_data = st.session_state.get(SessionStateKeys.RAW_DATA)
    if raw_data is not None:
        if isinstance(raw_data, dict):
            dataframes = [v for v in raw_data.values() if isinstance(v, pd.DataFrame)]
            if len(dataframes) == 1:
                st.session_state[quality_df_key] = dataframes[0]
                return
            elif len(dataframes) > 1:
                st.session_state[quality_df_key] = pd.concat(dataframes, ignore_index=True)
                return
        elif isinstance(raw_data, pd.DataFrame):
            st.session_state[quality_df_key] = raw_data
            return

    # Source 2: datasets dict (L3 DataFrame from descent)
    datasets = st.session_state.get('datasets', {})
    for level_key in ('l3', 'l2', 'l4'):
        ds = datasets.get(level_key)
        if ds is not None:
            df = ds.get_data() if hasattr(ds, 'get_data') else ds
            if isinstance(df, pd.DataFrame) and not df.empty:
                st.session_state[quality_df_key] = df
                return

    # Source 3: cart datasets (not yet started analysis)
    from intuitiveness.app.models.cart import CartManager
    cart = CartManager()
    if not cart.is_empty():
        cart_raw = cart.to_raw_data()
        if isinstance(cart_raw, dict):
            dataframes = [v for v in cart_raw.values() if isinstance(v, pd.DataFrame)]
            if dataframes:
                st.session_state[quality_df_key] = (
                    dataframes[0] if len(dataframes) == 1
                    else pd.concat(dataframes, ignore_index=True)
                )
                return


def _route_to_active_page():
    """Route to the active page based on mode and state."""
    
    # Check for data tools first
    active_quality_tool = st.session_state.get('active_quality_tool', 'none')
    if active_quality_tool == 'synthetic':
        from intuitiveness.app.pages.synthetic import render_synthetic_page
        _bridge_raw_data_to_quality_df()
        render_synthetic_page()
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
    
    # Validate current_step is within ALL_STEPS bounds (descent + ascent)
    current_step = st.session_state.current_step
    if current_step < 0 or current_step >= len(ALL_STEPS):
        # Handle export step (was set to 99) or other out-of-bounds values
        from intuitiveness.app.pages.export import render_export_page
        render_export_page()
        return

    # Dispatch to appropriate step
    step_id = ALL_STEPS[current_step]['id']
    step = ALL_STEPS[current_step]

    if step_id == "upload":
        render_upload_page(step, skip_header=is_search_landing)
    elif step_id in ("entities", "domains", "features", "aggregation", "results"):
        render_descent_page()
    elif step_id in ("l0_to_l1", "l1_to_l2", "l2_to_l3"):
        _render_ascent_step(step_id, step)


def _render_ascent_step(step_id: str, step: dict):
    """
    Render an ascent step (L0->L1, L1->L2, L2->L3).

    Uses the dedicated ascent form renderers from ui.ascent and
    the AscentController for execution logic.
    """
    from intuitiveness.app.ascent_controller import get_ascent_controller, AscentResult
    from intuitiveness.ui import (
        render_l0_to_l1_unfold_form,
        render_l1_to_l2_domain_form,
        render_l2_to_l3_entity_form,
        render_page_header,
    )

    render_step_header(step)

    datasets = st.session_state.get('datasets', {})
    controller = get_ascent_controller()

    if step_id == "l0_to_l1":
        l0_data = datasets.get('l0')
        if l0_data is None:
            st.warning("No L0 datum available. Complete the descent first.")
            return

        params = render_l0_to_l1_unfold_form(l0_data, key_prefix="guided_l0_l1")
        if params is not None:
            with st.spinner("Recovering source values..."):
                outcome = controller.execute_l0_to_l1(params)
            if outcome.result == AscentResult.SUCCESS:
                datasets['l1_ascent'] = outcome.data
                st.session_state['datasets'] = datasets
                st.session_state.ascent_level = 1
                st.success(outcome.message)
                st.session_state.current_step += 1
                st.rerun()
            else:
                st.error(outcome.message)

    elif step_id == "l1_to_l2":
        # Use ascent L1 if available, otherwise descent L1
        l1_data = datasets.get('l1_ascent', datasets.get('l1'))
        if l1_data is None:
            st.warning("No L1 data available. Complete the previous step first.")
            return

        params = render_l1_to_l2_domain_form(l1_data, key_prefix="guided_l1_l2")
        if params is not None:
            # Extract raw DataFrame for the controller
            l1_df = l1_data.get_data() if hasattr(l1_data, 'get_data') else l1_data
            if isinstance(l1_df, pd.Series):
                l1_df = l1_df.to_frame(name=params.get('column_name', 'value'))
            with st.spinner("Categorizing into domains..."):
                outcome = controller.execute_l1_to_l2(
                    categories=params.get('dimensions', []),
                    column=params.get('column_name'),
                    use_semantic=params.get('use_semantic', True),
                    threshold=params.get('threshold', 0.5),
                    l1_data=l1_df,
                )
            if outcome.result == AscentResult.SUCCESS:
                datasets['l2_ascent'] = outcome.data
                st.session_state['datasets'] = datasets
                st.session_state.ascent_level = 2
                st.success(outcome.message)
                st.session_state.current_step += 1
                st.rerun()
            else:
                st.error(outcome.message)

    elif step_id == "l2_to_l3":
        # Use ascent L2 if available, otherwise descent L2
        l2_data = datasets.get('l2_ascent', datasets.get('l2'))
        if l2_data is None:
            st.warning("No L2 data available. Complete the previous step first.")
            return

        params = render_l2_to_l3_entity_form(l2_data, key_prefix="guided_l2_l3")
        if params is not None:
            # Extract raw DataFrame for the controller
            l2_df = l2_data.get_data() if hasattr(l2_data, 'get_data') else l2_data
            with st.spinner("Building knowledge graph..."):
                outcome = controller.execute_l2_to_l3(
                    entity_column=params['entity_column'],
                    entity_type_name=params.get('entity_type_name'),
                    relationship_type=params.get('relationship_type'),
                    l2_data=l2_df,
                )
            if outcome.result == AscentResult.SUCCESS:
                datasets['l3_ascent'] = outcome.data
                st.session_state['datasets'] = datasets
                st.session_state.ascent_level = 3
                st.success(outcome.message)
                # After L3 ascent, go to export
                st.session_state.current_step = len(ALL_STEPS)
                st.rerun()
            else:
                st.error(outcome.message)


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


def get_descent_transition(current_step: int) -> int:
    """Map 6 descent steps (0-5) to 5 transitions (0-4)."""
    if current_step <= 1:
        return 0  # L4 phase (Upload + Entities)
    elif current_step == 2:
        return 1  # L3 phase (Domains)
    elif current_step == 3:
        return 2  # L2 phase (Features)
    elif current_step == 4:
        return 3  # L1 phase (Aggregation)
    else:
        return 4  # L0 phase (Results/complete)


def get_ascent_transition(ascent_level: int) -> int:
    """Map ascent level (0-3) directly to transition index."""
    return ascent_level


def render_vertical_progress_sidebar():
    """
    Render the vertical progress indicator on the right side.

    Shows current level (L0-L4) and phase (descent/ascent).
    """
    # Determine mode and current position
    nav_mode = st.session_state.get('nav_mode', 'guided')
    current_step = st.session_state.get('current_step', 0)

    # Ascent mode: guided ascent (step >= 6), or free mode with ascent in progress.
    # Note: loaded_session_graph is also set during descent (for tracking), so
    # it must NOT be used alone to signal ascent — that caused L4→L0 jump bug.
    is_ascent = (current_step >= len(STEPS)) or (
        nav_mode == 'free' and 'ascent_level' in st.session_state
    )

    if is_ascent:
        # Ascent: L0 → L3 (progress goes UP, so we render bottom-to-top visually)
        ascent_level = st.session_state.get('ascent_level', 0)
        current_transition = get_ascent_transition(ascent_level)
        mode_class = "ascent"
        mode_label = t("ascent_mode_label")
        # In ascent, transitions are ordered from L0 (bottom) to L3 (top)
        # Visually: index 0 = bottom, index 3 = top
        # So we need to render in reverse order (3, 2, 1, 0) for top-to-bottom HTML
        transitions = [(3, "🔗", "L3"), (2, "📋", "L2"), (1, "📐", "L1"), (0, "🎯", "L0")]
    else:
        # Descent: L4 → L0 (progress goes DOWN)
        current_step = st.session_state.get('current_step', 0)
        current_transition = get_descent_transition(current_step)
        mode_class = "descent"
        mode_label = t("descent_mode_label")
        # In descent, transitions are ordered from L4 (top) to L0/Datum (bottom)
        # 🧶 L4, 🔗 L3, 📋 L2, 📐 L1, 🎯 L0
        transitions = [(0, "🧶", "L4"), (1, "🔗", "L3"), (2, "📋", "L2"), (3, "📐", "L1"), (4, "🎯", "L0")]

    # Build HTML
    html_parts = [
        f'<div class="right-progress-sidebar">',
        f'<div class="progress-mode-label {mode_class}">{mode_label}</div>',
        f'<div class="progress-track">'
    ]

    for i, (trans_idx, label, level_name) in enumerate(transitions):
        # Determine state of this transition
        if is_ascent:
            # Ascent: completed if ascent_level > trans_idx
            if ascent_level > trans_idx:
                bar_class = "completed"
                is_current = False
            elif ascent_level == trans_idx:
                bar_class = f"current-{mode_class}"
                is_current = True
            else:
                bar_class = "pending"
                is_current = False
        else:
            # Descent: completed if current_transition > trans_idx
            if current_transition > trans_idx:
                bar_class = "completed"
                is_current = False
            elif current_transition == trans_idx:
                bar_class = f"current-{mode_class}"
                is_current = True
            else:
                bar_class = "pending"
                is_current = False

        # Add level with emoji, label, and transition bar
        html_parts.append(f'<div class="level-container">')
        html_parts.append(f'<div class="level-emoji">{label}</div>')
        html_parts.append(f'<div class="level-label">{level_name}</div>')
        html_parts.append(f'<div class="transition-bar {bar_class}"></div>')
        html_parts.append(f'</div>')

        # Add connector (except after the last bar)
        if i < len(transitions) - 1:
            connector_class = "completed" if bar_class == "completed" else ""
            html_parts.append(f'<div class="connector {connector_class}"></div>')

    html_parts.append('</div>')  # Close progress-track
    html_parts.append('</div>')  # Close right-progress-sidebar

    st.markdown(''.join(html_parts), unsafe_allow_html=True)


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
    """Render export page in free exploration mode."""
    from intuitiveness.app.pages.export import render_export_page
    render_export_page()


def render_session_graph_loader():
    """Render the session graph file uploader for Free Exploration mode."""
    st.subheader(t("load_session"))
    st.info(
        "Upload a session graph file to continue from a previous descent. "
        "This restores your L0 results for the ascent phase."
    )

    uploaded_file = st.file_uploader(
        t("upload_session_graph"),
        type=['json'],
        key='session_graph_upload'
    )

    if uploaded_file is not None:
        import tempfile
        import os

        try:
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False) as f:
                f.write(uploaded_file.getvalue())
                temp_path = f.name

            session_data = NavigationSession.load_graph(temp_path)
            os.unlink(temp_path)

            st.session_state['loaded_session_graph'] = session_data
            st.session_state['loaded_graph_decisions'] = session_data.get('decisions', [])

            st.success(t("session_loaded_success"))

            st.markdown(f"**{t('loaded_session_summary')}**")
            accumulated = session_data.get('accumulated_outputs', {})
            for level in sorted(accumulated.keys(), reverse=True):
                level_data = accumulated[level]
                st.markdown(
                    f"- **L{level}**: {level_data.get('row_count', '?')} items - "
                    f"{level_data.get('decision_description', '')[:50]}"
                )

            st.markdown(f"**{t('navigation_path')}**")
            for decision in session_data.get('decisions', []):
                action = decision.get('action', 'entry')
                desc = decision.get('decision_description', '')
                st.markdown(
                    f"  {decision['step']}. L{decision['level']} ({action}): {desc[:40]}..."
                )

            st.divider()
            if st.button(t("continue_free_exploration"), type="primary"):
                st.rerun()

            return True

        except Exception as e:
            st.error(t("session_load_failed", error=str(e)))
            return False

    return False


def render_free_navigation_main():
    """Render the main content area for free navigation mode."""
    # Check for loaded session graph first (ascent)
    if st.session_state.get('loaded_session_graph'):
        _render_loaded_graph_view()
        return

    nav_session = st.session_state.nav_session
    if nav_session is None:
        # Try to initialize from raw_data
        if st.session_state.raw_data is None:
            st.error(t("upload_data_first"))
            return
        l4_dataset = Level4Dataset(st.session_state.raw_data)
        st.session_state.nav_session = NavigationSession(l4_dataset)
        st.session_state.relationship_builder = DragDropRelationshipBuilder()
        nav_session = st.session_state.nav_session

    current_level = nav_session.current_level
    level_names = {
        0: "Your Computed Result",
        1: "Your Selected Values",
        2: "Items by Category",
        3: "Connected Information",
        4: "Your Uploaded Files"
    }

    st.subheader(f"Current View: {level_names.get(current_level.value, current_level.name)}")

    # Display available options
    st.divider()
    st.subheader(t("what_would_you_like"))
    options = nav_session.get_available_options()

    if options:
        cols = st.columns(min(len(options), 3))
        for i, option in enumerate(options):
            with cols[i % 3]:
                action = option["action"]
                description = option["description"]
                target = option.get("target_level", "")

                if action == "descend":
                    if st.button(
                        f"{t('explore_deeper', level=target)}",
                        key=f"nav_descend_{i}"
                    ):
                        st.session_state.nav_action = 'descend'
                        st.session_state.nav_target = target
                        st.rerun()
                elif action == "ascend":
                    if st.button(
                        f"{t('build_up_to', level=target)}",
                        key=f"nav_ascend_{i}",
                        type="primary"
                    ):
                        st.session_state.nav_action = 'ascend'
                        st.session_state.nav_target = target
                        st.rerun()
                elif action == "exit":
                    if st.button(
                        f"Exit: {description}",
                        key=f"nav_exit_{i}",
                        type="secondary"
                    ):
                        st.session_state.nav_export = True
                        st.rerun()
    else:
        st.info(t("start_exploring"))


def _render_loaded_graph_view():
    """Render the view for a loaded session graph (ascent phase ready)."""
    session_data = st.session_state.get('loaded_session_graph')
    if not session_data:
        return

    accumulated = session_data.get('accumulated_outputs', {})
    decisions = session_data.get('decisions', [])
    graph = session_data.get('graph')

    if 'ascent_level' not in st.session_state:
        st.session_state.ascent_level = 0

    level_names = {
        0: "Computed Result",
        1: "Selected Values",
        2: "Items by Category",
        3: "Connected Information"
    }

    st.subheader(
        f"Ascent Phase - {level_names.get(st.session_state.ascent_level, f'Level {st.session_state.ascent_level}')}"
    )

    # Show L0 result
    if 0 in accumulated:
        l0_data = accumulated[0]
        l0_formatted = format_l0_value_for_display(l0_data.get('output_value'))
        st.success(f"**{t('ground_truth_l0')}** {l0_formatted}")
        st.caption(f"{t('calculation_method')}: {l0_data.get('decision_description', '')}")

    st.divider()

    # Navigation history
    with st.expander(t("navigation_path"), expanded=False):
        for decision in decisions:
            action = decision.get('action', 'entry')
            level = decision.get('level', '?')
            desc = decision.get('decision_description', '')
            st.markdown(f"- **L{level}** ({action}): {desc[:60]}...")

    st.divider()

    # Ascent steps using the same guided ascent forms
    datasets = st.session_state.get('datasets', {})
    from intuitiveness.app.ascent_controller import get_ascent_controller, AscentResult

    controller = get_ascent_controller()

    if st.session_state.ascent_level == 0:
        st.subheader(t("step_7_recover"))
        if graph:
            l1_df = graph.get_level_data(1)
            if l1_df is not None and not l1_df.empty:
                st.metric(t("source_values_available"), f"{len(l1_df)} {t('rows_label')}")
                with st.expander(t("preview_l1_data"), expanded=False):
                    st.dataframe(l1_df.head(10))
                if st.button(t("recover_source_values_btn"), type="primary", key="free_ascent_l0_l1"):
                    datasets['l1_ascent'] = l1_df
                    st.session_state['datasets'] = datasets
                    st.session_state.ascent_level = 1
                    st.rerun()
            else:
                st.warning(t("l1_not_found_warning"))
        else:
            # Fallback: use datasets from guided descent
            l1_data = datasets.get('l1')
            if l1_data is not None:
                params = render_l0_to_l1_unfold_form(
                    datasets.get('l0'), key_prefix="free_l0_l1"
                )
                if params is not None:
                    outcome = controller.execute_l0_to_l1(params)
                    if outcome.result == AscentResult.SUCCESS:
                        datasets['l1_ascent'] = outcome.data
                        st.session_state['datasets'] = datasets
                        st.session_state.ascent_level = 1
                        st.rerun()
            else:
                st.warning(t("l1_not_found_warning"))

    elif st.session_state.ascent_level == 1:
        if st.button(t("back_to_step_9"), key="free_back_9"):
            st.session_state.ascent_level = 0
            st.rerun()

        st.subheader(t("step_8_add_dimension"))
        l1_data = datasets.get('l1_ascent', datasets.get('l1'))
        if l1_data is not None:
            params = render_l1_to_l2_domain_form(l1_data, key_prefix="free_l1_l2")
            if params is not None:
                l1_df = l1_data.get_data() if hasattr(l1_data, 'get_data') else l1_data
                if isinstance(l1_df, pd.Series):
                    l1_df = l1_df.to_frame(name=params.get('column_name', 'value'))
                outcome = controller.execute_l1_to_l2(
                    categories=params.get('dimensions', []),
                    column=params.get('column_name'),
                    use_semantic=params.get('use_semantic', True),
                    threshold=params.get('threshold', 0.5),
                    l1_data=l1_df,
                )
                if outcome.result == AscentResult.SUCCESS:
                    datasets['l2_ascent'] = outcome.data
                    st.session_state['datasets'] = datasets
                    st.session_state.ascent_level = 2
                    st.rerun()
                else:
                    st.error(outcome.message)

    elif st.session_state.ascent_level == 2:
        if st.button(t("back_to_step_10"), key="free_back_10"):
            st.session_state.ascent_level = 1
            st.rerun()

        st.subheader(t("step_9_linkage"))
        l2_data = datasets.get('l2_ascent', datasets.get('l2'))
        if l2_data is not None:
            params = render_l2_to_l3_entity_form(l2_data, key_prefix="free_l2_l3")
            if params is not None:
                l2_df = l2_data.get_data() if hasattr(l2_data, 'get_data') else l2_data
                outcome = controller.execute_l2_to_l3(
                    entity_column=params['entity_column'],
                    entity_type_name=params.get('entity_type_name'),
                    relationship_type=params.get('relationship_type'),
                    l2_data=l2_df,
                )
                if outcome.result == AscentResult.SUCCESS:
                    datasets['l3_ascent'] = outcome.data
                    st.session_state['datasets'] = datasets
                    st.session_state.ascent_level = 3
                    st.rerun()
                else:
                    st.error(outcome.message)

    elif st.session_state.ascent_level >= 3:
        st.success(t("ascent_completed"))
        st.divider()

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(t("try_different_dimension"), key="free_try_dim"):
                st.session_state.ascent_level = 1
                datasets.pop('l2_ascent', None)
                datasets.pop('l3_ascent', None)
                st.session_state['datasets'] = datasets
                st.rerun()
        with col2:
            if st.button(t("try_different_linkage"), key="free_try_link"):
                st.session_state.ascent_level = 2
                datasets.pop('l3_ascent', None)
                st.session_state['datasets'] = datasets
                st.rerun()
        with col3:
            if st.button(t("export_session"), key="free_export"):
                st.session_state.nav_export = True
                st.rerun()


def render_free_navigation_sidebar():
    """Render the decision-tree sidebar for free navigation mode."""
    nav_session = st.session_state.nav_session
    if nav_session is None:
        return

    st.markdown(f"### {t('navigation_tree')}")

    tree_viz = nav_session.get_tree_visualization()
    decision_tree = DecisionTreeComponent()

    def on_node_click(node_id: str):
        try:
            nav_session.restore(node_id)
            st.session_state.nav_action = 'restored'
        except NavigationError as e:
            st.error(str(e))

    decision_tree.render(
        tree_viz,
        on_node_click=on_node_click,
        available_options=nav_session.get_available_options()
    )

    render_branch_management(nav_session)


def render_branch_management(nav_session):
    """Explicit branch controls (spec 015 T025/T027): time-travel, prune, archive.

    Time-travel + branch-from are already available by clicking a node in the
    tree above and then taking a new decision; this panel adds the explicit
    prune/archive actions (no automatic eviction).
    """
    tree = nav_session.navigation_tree

    # Candidate nodes to manage: everything except the root and the node we're
    # currently standing on (pruning either would orphan the active position).
    candidates = {}
    for node_id, node in tree.nodes.items():
        if node.parent_id is None:           # root
            continue
        if node_id == tree.current_id:       # current position
            continue
        archived = " 📦" if node.metadata.get("_archived") else ""
        desc = node.decision_description or node.action
        label = f"{node.level.name.replace('LEVEL_', 'L')} · {desc}{archived}"
        candidates[label] = node_id

    with st.sidebar.expander(t("manage_branches"), expanded=False):
        st.caption(t("branch_from_hint"))

        if not candidates:
            st.info(t("no_branches_to_manage"))
            return

        chosen_label = st.selectbox(
            t("select_branch_to_manage"),
            options=list(candidates.keys()),
            key="branch_mgmt_select",
        )
        chosen_id = candidates[chosen_label]

        col_prune, col_archive = st.columns(2)
        with col_prune:
            if st.button(t("prune_branch"), key="branch_mgmt_prune", use_container_width=True):
                try:
                    removed = nav_session.prune(chosen_id)
                    st.success(t("branch_pruned", count=removed))
                    st.rerun()
                except NavigationError as e:
                    st.error(str(e))
        with col_archive:
            if st.button(t("archive_branch"), key="branch_mgmt_archive", use_container_width=True):
                try:
                    marked = nav_session.archive(chosen_id)
                    st.success(t("branch_archived", count=marked))
                    st.rerun()
                except NavigationError as e:
                    st.error(str(e))


if __name__ == "__main__":
    main()
