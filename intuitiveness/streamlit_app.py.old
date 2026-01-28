"""
Streamlit App for Interactive Data Redesign

This module provides a Streamlit-based Q&A workflow for the descent-ascent cycle.
Each level transition is guided by questions presented as Streamlit widgets.

Includes Free Navigation Mode with decision-tree sidebar for visual navigation
through abstraction levels with time-travel support (002-ascent-functionality).

Usage:
    streamlit run intuitiveness/streamlit_app.py

Author: Intuitiveness Framework
"""

import streamlit as st
import pandas as pd
import networkx as nx
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Get the project root directory for asset paths
PROJECT_ROOT = Path(__file__).parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"

# Import from the package
from intuitiveness.complexity import (
    Level4Dataset, Level3Dataset, Level2Dataset, Level1Dataset, Level0Dataset
)
from intuitiveness.interactive import (
    DataModelGenerator, Neo4jDataModel, SemanticMatcher, QuestionType
)
from intuitiveness.navigation import NavigationSession, NavigationState, NavigationError
from intuitiveness.ui import (
    DecisionTreeComponent, render_simple_tree,
    JsonVisualizer, render_navigation_export,
    DragDropRelationshipBuilder, get_entities_from_dataframe,
    # Level-specific display components (003-level-dataviz-display)
    render_l4_file_list,
    render_l2_domain_table,
    render_l1_vector,
    render_l0_datum,
    render_navigation_direction_indicator,
    extract_entity_tabs,
    extract_relationship_tabs,
    render_entity_relationship_tabs,
    NavigationDirection,
    # Ascent UI forms (004-ascent-precision)
    render_l0_to_l1_unfold_form,
    render_l1_to_l2_domain_form,
    render_l2_to_l3_entity_form,
    _render_domain_categorization_inputs,
    _parse_domains,
    _apply_domain_categorization,
    # Discovery wizard components (Step 2 simplification)
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
    # Recovery banner (005-session-persistence)
    RecoveryAction,
    render_recovery_banner,
    render_start_fresh_button,
    render_start_fresh_confirmation,
    # Internationalization (006-playwright-mcp-e2e)
    t,
    render_language_toggle_compact,
    # SaaS-style header and layout (007-streamlit-design-makeup)
    render_page_header,
    render_section_header,
    card,
    # Quality Data Platform (009-quality-data-platform)
    render_quality_dashboard,
    render_catalog_browser,
    separator,
    spacer,
    # Data.gouv.fr search interface (008-datagouv-search)
    render_search_interface,
    render_basket_sidebar,
    # Sarazin & Mourey tutorial (007-streamlit-design-makeup, Phase 9)
    render_tutorial,
    render_tutorial_replay_button,
    is_tutorial_completed,
    mark_tutorial_completed,
    reset_tutorial,
)
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
from intuitiveness.neo4j_writer import (
    generate_constraint_queries,
    generate_node_ingest_query,
    generate_relationship_ingest_query,
    generate_full_ingest_script
)
from intuitiveness.neo4j_client import Neo4jClient
from intuitiveness.styles import inject_all_styles
from intuitiveness.styles.charts import (
    styled_bar_chart,
    styled_metric_card,
    render_plotly_chart,
    render_metrics_row,
    KLEIN_BLUE,
    CHART_COLORS,
)
# Phase 0 utilities (011-code-simplification)
from intuitiveness.utils import (
    init_session_state as utils_init_session_state,
    SessionStateKeys,
    session,
)
import csv
import io


# ============================================================================
# SMART CSV LOADER - Handles all CSV formats
# ============================================================================

def smart_load_csv(file) -> tuple:
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
        return None, str(e)


# ============================================================================
# DISPLAY HELPERS
# ============================================================================

def format_l0_value_for_display(value: Any) -> str:
    """
    Format L0 ground truth value for user-friendly display.

    Converts raw Python dicts with numpy types into readable format:
    - Dict: shows as bullet list with formatted numbers
    - Single value: shows formatted number/text

    Args:
        value: The L0 output value (could be dict, number, string, etc.)

    Returns:
        User-friendly string representation
    """
    if value is None:
        return "N/A"

    if isinstance(value, dict):
        # Format as a readable list
        lines = []
        for key, val in value.items():
            # Convert numpy types to Python native for display
            if hasattr(val, 'item'):  # numpy type
                val = val.item()
            # Format numbers with thousand separators
            if isinstance(val, (int, float)):
                val_str = f"{val:,}".replace(",", " ")
            else:
                val_str = str(val)
            lines.append(f"• **{key}**: {val_str}")
        return "\n".join(lines)

    # Single value
    if hasattr(value, 'item'):  # numpy type
        value = value.item()
    if isinstance(value, (int, float)):
        return f"{value:,}".replace(",", " ")

    return str(value)


# ============================================================================
# SESSION STATE MANAGEMENT
# ============================================================================

def init_session_state():
    """
    Initialize Streamlit session state for the redesign workflow.

    Delegates to centralized session manager (Phase 0 - 011-code-simplification).
    Session keys and defaults are defined in utils/session_manager.py
    with spec traceability comments.
    """
    utils_init_session_state()


def _get_sidebar_branding_html() -> str:
    """
    Generate sidebar branding with animated mini gear cube.

    Returns HTML with:
    - Animated gear cube (compact version)
    - "Intuitiveness" brand name
    - "The next stage of open data" tagline
    """
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 0;
    }

    .mini-cube-container {
        perspective: 200px;
        width: 40px;
        height: 40px;
    }

    .mini-cube {
        width: 40px;
        height: 40px;
        transform-style: preserve-3d;
        animation: mini-shuffle 12s ease-in-out infinite;
    }

    @keyframes mini-shuffle {
        0%   { transform: rotateX(-15deg) rotateY(0deg); }
        15%  { transform: rotateX(20deg) rotateY(90deg) rotateZ(-5deg); }
        30%  { transform: rotateX(-20deg) rotateY(180deg) rotateZ(5deg); }
        45%  { transform: rotateX(15deg) rotateY(270deg); }
        60%  { transform: rotateX(-15deg) rotateY(360deg); }
        100% { transform: rotateX(-15deg) rotateY(360deg); }
    }

    .mini-face {
        position: absolute;
        width: 40px;
        height: 40px;
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1px;
        padding: 2px;
        background: rgba(0, 47, 167, 0.03);
        border-radius: 4px;
    }

    .mini-face.front  { transform: translateZ(20px); }
    .mini-face.back   { transform: rotateY(180deg) translateZ(20px); }
    .mini-face.right  { transform: rotateY(90deg) translateZ(20px); }
    .mini-face.left   { transform: rotateY(-90deg) translateZ(20px); }
    .mini-face.top    { transform: rotateX(90deg) translateZ(20px); }
    .mini-face.bottom { transform: rotateX(-90deg) translateZ(20px); }

    .mini-gear {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        position: relative;
    }

    .mini-gear::after {
        content: '';
        position: absolute;
        width: 100%;
        height: 100%;
        background: inherit;
        border-radius: 50%;
        clip-path: polygon(
            50% 0%, 65% 15%, 85% 15%, 85% 35%, 100% 50%,
            85% 65%, 85% 85%, 65% 85%, 50% 100%,
            35% 85%, 15% 85%, 15% 65%, 0% 50%,
            15% 35%, 15% 15%, 35% 15%
        );
    }

    .mini-gear.l0 { background: #002fa7; }
    .mini-gear.l1 { background: #0041d1; }
    .mini-gear.l2 { background: #3b82f6; }
    .mini-gear.l3 { background: #60a5fa; }
    .mini-gear.l4 { background: #93c5fd; }

    .mini-gear.spin-cw { animation: mini-spin-cw 8s linear infinite; }
    .mini-gear.spin-ccw { animation: mini-spin-ccw 8s linear infinite; }

    @keyframes mini-spin-cw { to { transform: rotate(360deg); } }
    @keyframes mini-spin-ccw { to { transform: rotate(-360deg); } }

    .brand-text {
        display: flex;
        flex-direction: column;
    }

    .brand-name {
        font-family: 'Outfit', sans-serif;
        font-size: 1.3rem;
        font-weight: 700;
        color: #002fa7;
        letter-spacing: -0.02em;
        line-height: 1.1;
    }

    .brand-tagline {
        font-family: 'Outfit', sans-serif;
        font-size: 0.7rem;
        font-weight: 400;
        color: #64748b;
        letter-spacing: 0.01em;
    }
    </style>

    <div class="sidebar-brand">
        <div class="mini-cube-container">
            <div class="mini-cube">
                <div class="mini-face front">
                    <div class="mini-gear l4 spin-cw"></div>
                    <div class="mini-gear l3 spin-ccw"></div>
                    <div class="mini-gear l4 spin-cw"></div>
                    <div class="mini-gear l2 spin-ccw"></div>
                    <div class="mini-gear l0 spin-cw"></div>
                    <div class="mini-gear l2 spin-ccw"></div>
                    <div class="mini-gear l4 spin-cw"></div>
                    <div class="mini-gear l3 spin-ccw"></div>
                    <div class="mini-gear l4 spin-cw"></div>
                </div>
                <div class="mini-face back">
                    <div class="mini-gear l3 spin-cw"></div>
                    <div class="mini-gear l2 spin-ccw"></div>
                    <div class="mini-gear l3 spin-cw"></div>
                    <div class="mini-gear l1 spin-ccw"></div>
                    <div class="mini-gear l0 spin-cw"></div>
                    <div class="mini-gear l1 spin-ccw"></div>
                    <div class="mini-gear l3 spin-cw"></div>
                    <div class="mini-gear l2 spin-ccw"></div>
                    <div class="mini-gear l3 spin-cw"></div>
                </div>
                <div class="mini-face right">
                    <div class="mini-gear l4 spin-cw"></div>
                    <div class="mini-gear l2 spin-ccw"></div>
                    <div class="mini-gear l3 spin-cw"></div>
                    <div class="mini-gear l3 spin-ccw"></div>
                    <div class="mini-gear l1 spin-cw"></div>
                    <div class="mini-gear l2 spin-ccw"></div>
                    <div class="mini-gear l4 spin-cw"></div>
                    <div class="mini-gear l2 spin-ccw"></div>
                    <div class="mini-gear l3 spin-cw"></div>
                </div>
                <div class="mini-face left">
                    <div class="mini-gear l3 spin-cw"></div>
                    <div class="mini-gear l2 spin-ccw"></div>
                    <div class="mini-gear l4 spin-cw"></div>
                    <div class="mini-gear l2 spin-ccw"></div>
                    <div class="mini-gear l1 spin-cw"></div>
                    <div class="mini-gear l3 spin-ccw"></div>
                    <div class="mini-gear l3 spin-cw"></div>
                    <div class="mini-gear l2 spin-ccw"></div>
                    <div class="mini-gear l4 spin-cw"></div>
                </div>
                <div class="mini-face top">
                    <div class="mini-gear l4 spin-cw"></div>
                    <div class="mini-gear l4 spin-ccw"></div>
                    <div class="mini-gear l4 spin-cw"></div>
                    <div class="mini-gear l3 spin-ccw"></div>
                    <div class="mini-gear l2 spin-cw"></div>
                    <div class="mini-gear l3 spin-ccw"></div>
                    <div class="mini-gear l2 spin-cw"></div>
                    <div class="mini-gear l1 spin-ccw"></div>
                    <div class="mini-gear l2 spin-cw"></div>
                </div>
                <div class="mini-face bottom">
                    <div class="mini-gear l2 spin-cw"></div>
                    <div class="mini-gear l1 spin-ccw"></div>
                    <div class="mini-gear l2 spin-cw"></div>
                    <div class="mini-gear l3 spin-ccw"></div>
                    <div class="mini-gear l2 spin-cw"></div>
                    <div class="mini-gear l3 spin-ccw"></div>
                    <div class="mini-gear l4 spin-cw"></div>
                    <div class="mini-gear l4 spin-ccw"></div>
                    <div class="mini-gear l4 spin-cw"></div>
                </div>
            </div>
        </div>
        <div class="brand-text">
            <span class="brand-name">Intuitiveness</span>
            <span class="brand-tagline">""" + t("brand_tagline") + """</span>
        </div>
    </div>
    """


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
# WORKFLOW STEPS
# ============================================================================

# Descent phase steps (Steps 1-6) - Bilingual: English // Français
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
        "title": "Analytic core // Cœur analytique",
        "level": "Step 6",
        "description": "View your computed results"
    }
]

# Ascent phase steps (Steps 7-12) - Bilingual: English // Français
ASCENT_STEPS = [
    {
        "id": "recover_sources",
        "title": "Datum // Datum",
        "level": "Step 7",
        "description": "L0 → L1: Recover source values // Récupérer les valeurs sources"
    },
    {
        "id": "new_dimension",
        "title": "Vector // Vecteur de données",
        "level": "Step 8",
        "description": "L1 → L2: Define new categories // Définir de nouvelles catégories"
    },
    {
        "id": "linkage",
        "title": "Table // Tableau de données",
        "level": "Step 9",
        "description": "L2 → L3: Enrich with linkage keys // Enrichir avec des clés de liaison"
    },
    {
        "id": "final",
        "title": "Linkable data // Données liables",
        "level": "Step 10",
        "description": "Final verification // Vérification finale"
    }
]


# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_progress_bar():
    """Render progress header for descent (L4→L0) using native Streamlit."""
    current = st.session_state.current_step

    # Simple container with background
    with st.container():
        st.markdown(f"""
        <div style="background:linear-gradient(180deg,#f0f9ff,#e0f2fe);padding:12px 16px;border-radius:8px;margin-bottom:16px;border:1px solid #bae6fd;">
        <div style="font-size:11px;color:#0369a1;font-weight:600;margin-bottom:8px;">{t("descent_progress")}</div>
        </div>
        """, unsafe_allow_html=True)

        levels = [("L4", [0, 1]), ("L3", [2]), ("L2", [3]), ("L1", [4]), ("L0", [5])]

        for name, steps in levels:
            max_step, min_step = max(steps), min(steps)
            col1, col2 = st.columns([1, 12])
            with col1:
                if current > max_step:
                    st.markdown(f"**:green[● {name}]**")
                elif current >= min_step:
                    st.markdown(f"**:blue[● {name}]**")
                else:
                    st.markdown(f":gray[○ {name}]")
            with col2:
                if current > max_step:
                    st.progress(1.0)
                elif current >= min_step:
                    st.progress(0.5)
                else:
                    st.progress(0.0)

        st.divider()


def render_ascent_progress_bar():
    """Render progress header for ascent (L0→L3) using native Streamlit."""
    ascent_level = st.session_state.get('ascent_level', 0)

    # Simple container with amber background
    with st.container():
        st.markdown(f"""
        <div style="background:linear-gradient(180deg,#fffbeb,#fef3c7);padding:12px 16px;border-radius:8px;margin-bottom:16px;border:1px solid #fde68a;">
        <div style="font-size:11px;color:#b45309;font-weight:600;margin-bottom:8px;">{t("ascent_progress")}</div>
        </div>
        """, unsafe_allow_html=True)

        # L3 at top (destination), L0 at bottom (start) - climbing UP
        levels = [("L3", 3), ("L2", 2), ("L1", 1), ("L0", 0)]

        for name, step in levels:
            col1, col2 = st.columns([1, 12])
            with col1:
                if ascent_level > step:
                    st.markdown(f"**:green[● {name}]**")
                elif ascent_level == step:
                    st.markdown(f"**:orange[◉ {name}]**")
                else:
                    st.markdown(f":gray[○ {name}]")
            with col2:
                if ascent_level > step:
                    st.progress(1.0)
                elif ascent_level == step:
                    st.progress(0.5)
                else:
                    st.progress(0.0)

        st.divider()


# =============================================================================
# RIGHT SIDEBAR VERTICAL PROGRESS INDICATOR
# =============================================================================

def inject_right_sidebar_css():
    """Inject CSS for fixed right sidebar progress indicator with pulsing animation.

    Uses design tokens from styles/palette.py for consistency (007-streamlit-design-makeup).
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
        background: linear-gradient(180deg, var(--color-bg-primary, #fafaf9), var(--color-bg-secondary, #f5f5f4));
        border: 1px solid var(--color-border, #e7e5e4);
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
        background: var(--color-success, #22c55e);
    }

    .transition-bar.current-descent {
        background: var(--color-accent, #2563eb);
    }

    .transition-bar.current-ascent {
        background: var(--color-warning, #f59e0b);
    }

    .transition-bar.pending {
        background: var(--color-text-muted, #a8a29e);
    }

    /* Vertical connectors between bars */
    .connector {
        width: 3px;
        height: 80px;
        background: var(--color-border, #e7e5e4);
    }

    .connector.completed {
        background: var(--color-success, #22c55e);
    }

    /* Pulsing glow animation for current bar - using accent color */
    @keyframes glow-descent {
        0%, 100% {
            box-shadow: 0 0 4px var(--color-accent, #2563eb);
        }
        50% {
            box-shadow: 0 0 12px var(--color-accent, #2563eb), 0 0 20px var(--color-accent, #2563eb);
        }
    }

    @keyframes glow-ascent {
        0%, 100% {
            box-shadow: 0 0 4px var(--color-warning, #f59e0b);
        }
        50% {
            box-shadow: 0 0 12px var(--color-warning, #f59e0b), 0 0 20px var(--color-warning, #f59e0b);
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
        color: var(--color-accent, #2563eb);
    }

    .progress-mode-label.ascent {
        color: var(--color-warning, #f59e0b);
    }
    </style>
    """, unsafe_allow_html=True)


def get_descent_transition(current_step: int) -> int:
    """Map 6 descent steps (0-5) to 4 transitions (0-3), or 4 if complete."""
    if current_step <= 1:
        return 0  # L4 phase (Upload + Entities)
    elif current_step == 2:
        return 1  # L3 phase (Domains)
    elif current_step == 3:
        return 2  # L2 phase (Features)
    elif current_step == 4:
        return 3  # L1 phase (Aggregation)
    else:
        return 4  # L0 complete (Results)


def get_ascent_transition(ascent_level: int) -> int:
    """Map ascent level (0-3) directly to transition index."""
    return ascent_level


def render_vertical_progress_sidebar():
    """Render the fixed right sidebar with vertical progress indicator."""
    # Determine mode and current position
    nav_mode = st.session_state.get('nav_mode', 'guided')
    loaded_session = st.session_state.get('loaded_session_graph', False)

    # Ascent mode: free exploration OR loaded session graph
    is_ascent = (nav_mode == 'free') or loaded_session

    if is_ascent:
        # Ascent: L0 → L3 (progress goes UP, so we render bottom-to-top visually)
        ascent_level = st.session_state.get('ascent_level', 0)
        current_transition = get_ascent_transition(ascent_level)
        mode_class = "ascent"
        mode_label = t("ascent_mode_label")
        # In ascent, transitions are ordered from L0 (bottom) to L3 (top)
        # Visually: index 0 = bottom, index 3 = top
        # So we need to render in reverse order (3, 2, 1, 0) for top-to-bottom HTML
        transitions = [(3, "🔗"), (2, "📋"), (1, "📐"), (0, "🎯")]  # L3, L2, L1, L0
    else:
        # Descent: L4 → L0 (progress goes DOWN)
        current_step = st.session_state.get('current_step', 0)
        current_transition = get_descent_transition(current_step)
        mode_class = "descent"
        mode_label = t("descent_mode_label")
        # In descent, transitions are ordered from L4 (top) to L0/Datum (bottom)
        # 🧶 L4, 🔗 L3, 📋 L2, 📐 L1, 🎯 L0
        transitions = [(0, "🧶"), (1, "🔗"), (2, "📋"), (3, "📐"), (4, "🎯")]

    # Build HTML
    html_parts = [
        f'<div class="right-progress-sidebar">',
        f'<div class="progress-mode-label {mode_class}">{mode_label}</div>',
        f'<div class="progress-track">'
    ]

    for i, (trans_idx, label) in enumerate(transitions):
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

        # Add level with emoji and transition bar
        html_parts.append(f'<div class="level-container">')
        html_parts.append(f'<div class="level-emoji">{label}</div>')
        html_parts.append(f'<div class="transition-bar {bar_class}"></div>')
        html_parts.append(f'</div>')

        # Add connector (except after the last bar)
        if i < len(transitions) - 1:
            connector_class = "completed" if bar_class == "completed" else ""
            html_parts.append(f'<div class="connector {connector_class}"></div>')

    html_parts.append('</div>')  # Close progress-track
    html_parts.append('</div>')  # Close right-progress-sidebar

    st.markdown(''.join(html_parts), unsafe_allow_html=True)


def render_step_header(step: dict):
    """Render the header for a step - disabled for clean SaaS design."""
    # Headers removed for minimal design (007-streamlit-design-makeup)
    pass


def render_methodology_intro():
    """
    Render a compelling introduction to the Data Redesign Method.

    Shows the 5 levels of abstraction, explains descent/ascent cycle,
    and references the scientific research. This creates an inviting
    experience before the user uploads data.
    """
    # Key visual: The 5 Levels of Abstraction
    st.markdown("""
    <style>
    .methodology-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 4px 24px rgba(0, 47, 167, 0.08);
        border-left: 4px solid #002fa7;
    }
    .level-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 8px;
    }
    .level-l4 { background: #fee2e2; color: #991b1b; }
    .level-l3 { background: #fef3c7; color: #92400e; }
    .level-l2 { background: #dbeafe; color: #1e40af; }
    .level-l1 { background: #d1fae5; color: #065f46; }
    .level-l0 { background: #ede9fe; color: #5b21b6; }
    .cycle-arrow {
        font-size: 1.5rem;
        color: #002fa7;
        margin: 0 8px;
    }
    .research-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #f1f5f9;
        padding: 6px 12px;
        border-radius: 8px;
        font-size: 0.8rem;
        color: #475569;
    }
    </style>
    """, unsafe_allow_html=True)

    # Introduction card
    st.markdown("""
    <div class="methodology-card">
        <h3 style="margin-top:0; color: #002fa7;">Transform Data Chaos into Clarity</h3>
        <p style="font-size: 1.05rem; line-height: 1.7; color: #334155;">
            The Data Redesign Method helps you navigate complex datasets by controlling
            <strong>abstraction levels</strong>. Like zooming in and out on a map, you can
            descend from overwhelming complexity to a single atomic insight, then ascend
            back with purpose-built structure.
        </p>
        <div class="research-badge">
            <span>📚</span> Based on peer-reviewed research by Sarazin, Mourey & Debru (Dataflow Project)
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Two columns: The Cycle + The Levels
    col_left, col_right = st.columns([1.2, 1])

    with col_left:
        st.markdown("#### The Descent-Ascent Cycle")
        st.markdown("""
        <div style="background: #f8fafc; border-radius: 12px; padding: 20px; margin-bottom: 16px;">
            <div style="text-align: center; font-size: 1.1rem; margin-bottom: 16px;">
                <span class="level-badge level-l4">L4</span>
                <span class="cycle-arrow">→</span>
                <span class="level-badge level-l3">L3</span>
                <span class="cycle-arrow">→</span>
                <span class="level-badge level-l2">L2</span>
                <span class="cycle-arrow">→</span>
                <span class="level-badge level-l1">L1</span>
                <span class="cycle-arrow">→</span>
                <span class="level-badge level-l0">L0</span>
            </div>
            <p style="color: #64748b; font-size: 0.9rem; text-align: center; margin-bottom: 8px;">
                <strong>DESCENT</strong>: Reduce complexity by 75-100% per level
            </p>
            <hr style="border: none; height: 1px; background: linear-gradient(to right, transparent, #cbd5e1, transparent); margin: 16px 0;">
            <div style="text-align: center; font-size: 1.1rem; margin-bottom: 16px;">
                <span class="level-badge level-l0">L0</span>
                <span class="cycle-arrow">→</span>
                <span class="level-badge level-l1">L1</span>
                <span class="cycle-arrow">→</span>
                <span class="level-badge level-l2">L2</span>
                <span class="cycle-arrow">→</span>
                <span class="level-badge level-l3">L3</span>
            </div>
            <p style="color: #64748b; font-size: 0.9rem; text-align: center; margin: 0;">
                <strong>ASCENT</strong>: Rebuild with intentional structure
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        st.markdown("#### 5 Levels of Abstraction")
        levels_data = [
            ("L0", "Datum", "Single fact: entity-attribute-value", "level-l0"),
            ("L1", "Vector", "One entity, multiple attributes", "level-l1"),
            ("L2", "Table", "Multiple entities and attributes", "level-l2"),
            ("L3", "Graph", "Linkable multi-level datasets", "level-l3"),
            ("L4", "Chaos", "Unlinkable datasets (your data!)", "level-l4"),
        ]
        for level, name, desc, css_class in reversed(levels_data):
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px; padding: 8px 12px; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0;">
                <span class="level-badge {css_class}">{level}</span>
                <div>
                    <strong style="color: #1e293b;">{name}</strong>
                    <span style="color: #64748b; font-size: 0.85rem;"> — {desc}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # What you'll experience section
    st.markdown("#### What You'll Experience")

    exp_col1, exp_col2, exp_col3 = st.columns(3)

    with exp_col1:
        st.markdown("""
        <div style="background: #eff6ff; border-radius: 12px; padding: 16px; height: 140px;">
            <div style="font-size: 1.5rem; margin-bottom: 8px;">📊</div>
            <strong style="color: #1e40af;">Upload & Connect</strong>
            <p style="font-size: 0.85rem; color: #475569; margin-top: 6px;">
                AI discovers relationships between your CSV files automatically
            </p>
        </div>
        """, unsafe_allow_html=True)

    with exp_col2:
        st.markdown("""
        <div style="background: #fef3c7; border-radius: 12px; padding: 16px; height: 140px;">
            <div style="font-size: 1.5rem; margin-bottom: 8px;">🔍</div>
            <strong style="color: #92400e;">Descend to Insight</strong>
            <p style="font-size: 0.85rem; color: #475569; margin-top: 6px;">
                Reduce complexity step-by-step until you reach atomic truth
            </p>
        </div>
        """, unsafe_allow_html=True)

    with exp_col3:
        st.markdown("""
        <div style="background: #d1fae5; border-radius: 12px; padding: 16px; height: 140px;">
            <div style="font-size: 1.5rem; margin-bottom: 8px;">🚀</div>
            <strong style="color: #065f46;">Ascend with Purpose</strong>
            <p style="font-size: 0.85rem; color: #475569; margin-top: 6px;">
                Rebuild tailored datasets that answer your specific questions
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Call to action
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("**Ready to begin?** Upload your CSV files above to start the descent-ascent cycle.")


def render_upload_step(skip_header: bool = False):
    """Step 0: Search and load data from data.gouv.fr."""
    step = STEPS[0]
    if not skip_header:
        render_step_header(step)

    # Check if data is already loaded (from search)
    raw_data = st.session_state.raw_data
    if raw_data:
        # Use standardized L4 file list display (003-level-dataviz-display FR-001, FR-002)
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

        # ========== AI-POWERED CONNECTION WIZARD (shown immediately after upload) ==========
        st.markdown("---")
        st.subheader("🔮 Connect Your Data")
        st.markdown("I'll analyze your files and suggest how to connect them.")

        # Initialize discovery results if not exists
        if SESSION_KEY_DISCOVERY_RESULTS not in st.session_state:
            st.session_state[SESSION_KEY_DISCOVERY_RESULTS] = None

        # Run discovery if not done yet
        if st.session_state[SESSION_KEY_DISCOVERY_RESULTS] is None:
            with st.spinner("Analyzing your files to find connections..."):
                try:
                    discovery_result = run_discovery(raw_data)
                    st.session_state[SESSION_KEY_DISCOVERY_RESULTS] = discovery_result
                    st.success(f"Found {len(discovery_result.entity_suggestions)} data types "
                              f"and {len(discovery_result.relationship_suggestions)} potential connections "
                              f"in {discovery_result.analysis_time_ms:.0f}ms")
                except Exception as e:
                    st.error(f"Error analyzing files: {e}")
                    st.session_state[SESSION_KEY_DISCOVERY_RESULTS] = DiscoveryResult()

        # Get discovery results
        discovery_result = st.session_state[SESSION_KEY_DISCOVERY_RESULTS]

        if discovery_result and discovery_result.entity_suggestions:
            # Get current wizard step
            wizard_step = _get_wizard_step()

            # Render appropriate wizard step
            if wizard_step == 1:
                if render_wizard_step_1_columns(
                    raw_data,
                    key_prefix="upload_wizard_s1"
                ):
                    _set_wizard_step(2)
                    st.rerun()

            elif wizard_step == 2:
                if render_wizard_step_2_connections(
                    raw_data,
                    selected_columns_key="upload_wizard_s1_selected_columns",
                    key_prefix="upload_wizard_s2"
                ):
                    _set_wizard_step(3)
                    st.rerun()

            elif wizard_step == 3:
                joined_df = render_wizard_step_3_confirm(
                    raw_data,
                    key_prefix="upload_wizard_s3"
                )
                if joined_df is not None:
                    # Store the joined L3 dataset
                    st.session_state.joined_l3_dataset = joined_df

                    # Create L3 dataset for Step 3 (Define Categories)
                    # L3 accepts DataFrame directly - no need to convert to graph
                    # (Converting rows to graph nodes caused OOM on large datasets)
                    st.session_state.datasets['l3'] = Level3Dataset(joined_df)

                    # Create entity/relationship mappings from the joined table
                    entity_mapping = {}
                    relationship_mapping = {}

                    # Create a single entity from the joined table
                    from intuitiveness.interactive import DataModelNode, DataModelRelationship
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

            # Option to reset wizard
            with st.expander(f"🔄 {t('reset_analyze')}"):
                if st.button(t("reset_analyze"), key="upload_reset_wizard"):
                    st.session_state[SESSION_KEY_DISCOVERY_RESULTS] = None
                    _set_wizard_step(1)
                    keys_to_clear = [k for k in st.session_state.keys()
                                    if k.startswith('upload_wizard_s')]
                    for k in keys_to_clear:
                        del st.session_state[k]
                    st.rerun()

        else:
            # Fallback: No entities found, continue with manual mode
            st.warning(t("could_not_analyze"))
            if st.button(t("continue_arrow"), type="primary"):
                st.session_state.current_step = 1
                st.rerun()
    else:
        # Welcome section when no files are uploaded
        # Feature 008-datagouv-search: Show search-first interface

        # Initialize loaded datasets tracking
        if 'datagouv_loaded_datasets' not in st.session_state:
            st.session_state.datagouv_loaded_datasets = {}

        # Clean search interface only - basket is in sidebar
        loaded_df = render_search_interface()

        if loaded_df is not None:
            # Get the dataset name from session state or generate one
            dataset_name = st.session_state.get('datagouv_last_dataset_name', f"dataset_{len(st.session_state.datagouv_loaded_datasets) + 1}.csv")
            st.session_state.datagouv_loaded_datasets[dataset_name] = loaded_df
            st.session_state.pop('datagouv_last_dataset_name', None)
            st.rerun()


def render_entities_step():
    """Step 1: L4 → L3 - Define items for the connected information."""
    step = STEPS[1]
    render_step_header(step)

    # Constitution v1.2.0: Use domain-friendly labels
    st.markdown("""
    Define the core **items** that will appear in your connected information.

    Think about:
    - What are the main "things" in your data?
    - How are they connected to each other?
    """)

    # Choose generation method
    generation_method = st.radio(
        "How would you like to define your items?",
        options=["Manual (specify items)", "AI-Assisted (describe in natural language)"],
        horizontal=True,
        key="data_model_method"
    )

    if generation_method == "AI-Assisted (describe in natural language)":
        # LLM-assisted data model generation
        st.markdown("### 🤖 AI-Assisted Item Definition")

        col_llm1, col_llm2 = st.columns([2, 1])
        with col_llm1:
            llm_provider = st.selectbox(
                "LLM Provider:",
                options=["ollama", "openai"],
                key="llm_provider"
            )
        with col_llm2:
            if llm_provider == "ollama":
                llm_model = st.text_input(
                    "Model:",
                    value="qwen2.5-coder:7b",
                    key="ollama_model",
                    help="Available models: qwen2.5-coder:7b, llama3.2:3b, etc."
                )
            else:
                llm_model = st.selectbox(
                    "Model:",
                    options=["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
                    key="openai_model"
                )

        if llm_provider == "openai":
            openai_key = st.text_input(
                "OpenAI API Key:",
                type="password",
                key="openai_api_key",
                help="Your OpenAI API key"
            )
        else:
            openai_key = None

        user_query = st.text_area(
            "Describe your data structure:",
            value="Create a structure for business indicators with their sources and business domains. Indicators belong to domains and come from sources.",
            height=100,
            key="llm_data_model_query",
            help="Describe the main things in your data and how they connect"
        )

        if st.button("🤖 Generate Structure with AI", type="primary"):
            if llm_provider == "openai" and not openai_key:
                st.error("Please enter your OpenAI API key")
            else:
                with st.spinner(f"Generating structure with {llm_provider}..."):
                    try:
                        data_model = DataModelGenerator.generate_from_llm(
                            user_query=user_query,
                            source_data=st.session_state.raw_data,
                            llm_provider=llm_provider,
                            model=llm_model,
                            api_key=openai_key,
                            verbose=True
                        )
                        st.session_state.data_model = data_model
                        st.session_state.answers['llm_query'] = user_query
                        st.success("✅ Structure generated successfully!")
                        st.rerun()
                    except ConnectionError as e:
                        st.error(f"Connection error: {e}")
                        if llm_provider == "ollama":
                            st.info("💡 Make sure Ollama is running: `ollama serve`")
                    except Exception as e:
                        st.error(f"Error: {e}")

    else:
        # Manual item input (original method)
        # Examples
        with st.expander("💡 Examples"):
            st.markdown("""
            - **Logistics:** `Indicator, Source, BusinessDomain, ClientSegment`
            - **E-commerce:** `Product, Customer, Order, Location`
            - **HR:** `Employee, Department, Project, Skill`
            """)

        # Input
        default_entities = "Indicator, Source, BusinessDomain"
        entities_input = st.text_input(
            "Enter main items (comma-separated):",
            value=st.session_state.answers.get('entities', default_entities),
            help="E.g., Product, Customer, Order"
        )

        # Core item selection
        entities_list = [e.strip() for e in entities_input.split(",") if e.strip()]

        if entities_list:
            core_entity = st.selectbox(
                "Select the main item:",
                options=entities_list,
                help="This will be the main thing everything else connects to"
            )

            # Generate and preview structure
            if st.button("Generate Structure"):
                with st.spinner("Generating structure..."):
                    data_model = DataModelGenerator.generate_from_entities(
                        entities=entities_list,
                        core_entity=core_entity,
                        source_data=st.session_state.raw_data
                    )
                    st.session_state.data_model = data_model
                    st.session_state.answers['entities'] = entities_input
                    st.session_state.answers['core_entity'] = core_entity

    # Show data model preview (for BOTH AI and Manual methods)
    if st.session_state.data_model:
        render_data_model_preview(st.session_state.data_model)

        # Build Knowledge Graph (NetworkX only - no Neo4j execution)
        st.divider()
        st.subheader("📊 Build Connected Information")
        st.info("Your connected information will be built instantly. No setup needed.")

        # Connection mode selection
        st.markdown("**How to connect your files:**")
        col_mode1, col_mode2 = st.columns(2)
        with col_mode1:
            rel_mode = st.radio(
                "How should items be connected?",
                options=["key_matching", "semantic"],
                format_func=lambda x: "🔑 Exact Match" if x == "key_matching" else "🧠 Smart Match (AI)",
                index=0,
                key="relationship_mode",
                help="Exact match: Connects items with identical values. Smart match: Uses AI to find similar items."
            )
        with col_mode2:
            if rel_mode == "semantic":
                sim_threshold = st.slider(
                    "Matching strictness",
                    min_value=0.5,
                    max_value=0.95,
                    value=0.7,
                    step=0.05,
                    key="similarity_threshold",
                    help="Higher = more strict (fewer but more confident matches)"
                )
            else:
                sim_threshold = 0.7
                st.info("Exact matching connects items that have the same identifier values.")

        if st.button("🔨 Build Connected Information", type="primary"):
            with st.spinner("Building your connected information..."):
                build_knowledge_graph_from_model(
                    relationship_mode=rel_mode,
                    similarity_threshold=sim_threshold
                )
                st.success("✅ Connected information built successfully!")
                st.rerun()

        # Show graph if built
        if 'l3' in st.session_state.datasets:
            st.divider()
            st.subheader("🔗 How Your Data Connects")
            render_knowledge_graph_view()

            # Graph export options
            st.divider()
            col_exp1, col_exp2, col_exp3 = st.columns(3)
            with col_exp1:
                G = st.session_state.datasets['l3'].get_data()
                # Export as GraphML
                import io
                graphml_buffer = io.BytesIO()
                nx.write_graphml(G, graphml_buffer)
                graphml_buffer.seek(0)
                st.download_button(
                    "📥 Download GraphML",
                    data=graphml_buffer.getvalue(),
                    file_name="knowledge_graph.graphml",
                    mime="application/xml"
                )
            with col_exp2:
                # Export as JSON (node-link format)
                graph_json = nx.node_link_data(G)
                st.download_button(
                    "📥 Download JSON",
                    data=json.dumps(graph_json, indent=2),
                    file_name="knowledge_graph.json",
                    mime="application/json"
                )
            with col_exp3:
                # Export as edge list
                edges = list(G.edges(data=True))
                edges_data = [{"source": s, "target": t, **d} for s, t, d in edges]
                st.download_button(
                    "📥 Download Edge List",
                    data=json.dumps(edges_data, indent=2),
                    file_name="edges.json",
                    mime="application/json"
                )

            col1, col2 = st.columns(2)
            with col1:
                if st.button(t("back_arrow")):
                    st.session_state.current_step = 0
                    st.rerun()
            with col2:
                if st.button(t("continue_arrow"), type="primary"):
                    st.session_state.current_step = 2
                    st.rerun()


def render_domains_step():
    """Step 2: L3 → L2 - Define domains for categorization."""
    step = STEPS[2]
    render_step_header(step)

    # Check if L3 dataset exists
    if 'l3' not in st.session_state.datasets:
        st.warning(t("no_connected_view"))
        if st.button(t("back_arrow")):
            st.session_state.current_step = 1
            st.rerun()
        return

    # Extract data from L3 graph
    graph = st.session_state.datasets['l3'].get_data()

    # ========== Use shared entity_tabs functions (003-level-dataviz-display FR-004, FR-005, FR-007) ==========
    entity_tabs_data = extract_entity_tabs(graph)
    relationship_tabs_data = extract_relationship_tabs(graph)

    if not entity_tabs_data:
        st.warning("No items found. Please check the previous step.")
        return

    # ========== Show Graph Data with Tabs ==========
    st.subheader("📊 Browse Your Connected Information")

    # Constitution v1.2.0: Use domain-friendly labels - simplified (007-streamlit-design-makeup)
    st.markdown("""
    Votre jeu de données lié est prêt. Parcourez les données ci-dessous pour vérifier la qualité du matching.
    """)

    # Use shared render function - no selection button needed (007-streamlit-design-makeup)
    render_entity_relationship_tabs(
        entity_tabs_data,
        relationship_tabs_data,
        graph=graph,
        max_rows=50,
        show_summary=True,
        enable_selection=False,
        selection_key_prefix="domains_step"
    )

    # Build entities_by_type dict for backward compatibility with domain categorization
    entities_by_type = {
        tab.entity_type: tab.data
        for tab in entity_tabs_data
    }

    # Use the first entity type's data directly (simplified - 007-streamlit-design-makeup)
    entity_type_names = [tab.entity_type for tab in entity_tabs_data]
    first_entity_type = entity_type_names[0] if entity_type_names else None

    # Get DataFrame from graph or entity tabs
    if isinstance(graph, pd.DataFrame):
        graph_df = graph
    else:
        graph_df = pd.DataFrame(entities_by_type.get(first_entity_type, []))
    selected_table_name = first_entity_type

    st.divider()

    # Column selection for domain categorization
    st.subheader("🎯 Define Categories")

    if graph_df.empty:
        st.warning(f"No data available for '{selected_table_name}'")
        return

    # Get available text columns (exclude 'id' and numeric-only columns)
    # Preserve original dataframe column order for user familiarity (T041 fix)
    all_columns_ordered = list(graph_df.columns)
    text_columns = [col for col in all_columns_ordered if col != 'id' and graph_df[col].dtype == 'object']
    if not text_columns:
        # Fallback: use all columns in original order
        text_columns = [col for col in all_columns_ordered if col != 'id']

    # Column selector
    default_col = 'name' if 'name' in text_columns else text_columns[0] if text_columns else None

    if default_col:
        selected_column = st.selectbox(
            "Select column to categorize by:",
            options=text_columns,
            index=text_columns.index(default_col) if default_col in text_columns else 0,
            help="The values in this column will be matched against your domains",
            key="domains_column_select"
        )

        # Show unique values and "Use as categories" quick option (same as ascent phase)
        unique_values = graph_df[selected_column].dropna().unique()
        unique_count = len(unique_values)

        # Quick action: Use unique values as categories - DETERMINISTIC (007-streamlit-design-makeup)
        if unique_count <= 20:
            st.markdown(f"**🎯 Quick option: Use `{selected_column}` unique values as categories ({unique_count} categories):**")
            st.caption(f"Unique values: {', '.join(str(v) for v in unique_values[:10])}{'...' if unique_count > 10 else ''}")
            if st.button(f"✨ Use '{selected_column}' values as categories", key="domains_use_unique_values"):
                # Apply deterministic categorization directly (exact match, no semantic)
                categories_list = [str(v) for v in unique_values]
                categorize_by_domains(
                    categories_list,
                    use_semantic=False,  # Deterministic - exact match
                    threshold=0.0,
                    column=selected_column,
                    entity_type=selected_table_name
                )
                st.session_state.answers['domains'] = ", ".join(categories_list)
                st.session_state.answers['domain_column'] = selected_column
                st.session_state.answers['entity_type'] = selected_table_name
                st.success(f"Categorized by {unique_count} unique values from '{selected_column}' (exact match)")
                st.rerun()
        else:
            st.warning(f"Column '{selected_column}' has {unique_count} unique values (too many for automatic categories). Enter custom categories below.")

        with st.expander(f"Sample values in '{selected_column}' column ({unique_count} unique)"):
            st.write(list(unique_values[:20]))
    else:
        st.error("No suitable columns found for categorization")
        return

    st.divider()

    # Category input
    st.markdown("**Enter the categories you want to group by:**")

    with st.expander("💡 Examples"):
        st.markdown("""
        - **Business metrics:** `Revenue, Volume, ETP`
        - **Priority levels:** `High, Medium, Low`
        - **Departments:** `Sales, Marketing, Operations`
        """)

    # Use stored categories if set via quick option, otherwise default
    default_domains = st.session_state.answers.get('domains', "Revenue, Volume, ETP")
    domains_input = st.text_input(
        "Categories (comma-separated):",
        value=default_domains,
        help="E.g., Revenue, Volume, ETP"
    )

    col1, col2 = st.columns(2)
    with col1:
        # Smart matching toggle
        use_semantic = st.checkbox(
            "Use smart matching (AI)",
            value=True,
            help="Use AI to find similar items (smarter but slower)"
        )
    with col2:
        # Matching strictness
        threshold = st.slider(
            "Matching strictness:",
            min_value=0.1,
            max_value=0.9,
            value=0.3,
            step=0.05,
            help="How strict should matching be? (higher = fewer matches)"
        )

    domains_list = [d.strip() for d in domains_input.split(",") if d.strip()]

    if domains_list and st.button(f"🔄 {t('categorize_data')}", type="primary"):
        # Progress bar is shown inside categorize_by_domains via get_batch_similarities
        st.info(t("categorizing_data"))
        # Use selected_table_name (defined from selected table or first entity type)
        categorize_by_domains(domains_list, use_semantic, threshold, column=selected_column, entity_type=selected_table_name)
        st.session_state.answers['domains'] = domains_input
        st.session_state.answers['domain_column'] = selected_column
        st.session_state.answers['entity_type'] = selected_table_name
        st.rerun()

    # Show categorization results
    if 'l2' in st.session_state.datasets:
        st.divider()
        render_domain_results()

        col1, col2 = st.columns(2)
        with col1:
            if st.button(t("back_arrow")):
                st.session_state.current_step = 1
                st.rerun()
        with col2:
            if st.button(t("continue_arrow"), type="primary"):
                st.session_state.current_step = 3
                st.rerun()


def render_features_step():
    """Step 3: L2 → L1 - Select feature/column to extract."""
    step = STEPS[3]
    render_step_header(step)

    st.markdown(t("select_column_extract"))

    if 'l2' not in st.session_state.datasets:
        st.warning(t("no_categorized_data"))
        return

    # Show L2 domain tables using shared display (003-level-dataviz-display FR-008, FR-009)
    domain_data = {
        domain: l2_ds.get_data()
        for domain, l2_ds in st.session_state.datasets['l2'].items()
    }
    render_l2_domain_table(domain_data)

    st.divider()

    # Get available columns from first non-empty domain
    available_columns = []
    for domain, l2_ds in st.session_state.datasets['l2'].items():
        df = l2_ds.get_data()
        if not df.empty:
            available_columns = list(df.columns)
            break

    if not available_columns:
        st.warning(t("no_columns_available"))
        return

    st.subheader(f"🎯 {t('select_column')}")
    selected_column = st.selectbox(
        t("select_column"),
        options=available_columns,
        index=available_columns.index('name') if 'name' in available_columns else 0
    )

    if st.button(t("extract_values")):
        extract_features(selected_column)
        st.session_state.answers['feature'] = selected_column

    # Show extracted vectors using shared display (003-level-dataviz-display FR-010, FR-011)
    if 'l1' in st.session_state.datasets:
        st.divider()
        for domain, l1_ds in st.session_state.datasets['l1'].items():
            vector_data = l1_ds.get_data()
            column_name = st.session_state.answers.get('feature', 'extracted')
            render_l1_vector(vector_data, f"{column_name} ({domain})")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(t("back_arrow")):
                st.session_state.current_step = 2
                st.rerun()
        with col2:
            if st.button(t("continue_arrow"), type="primary"):
                st.session_state.current_step = 4
                st.rerun()


def render_aggregation_step():
    """Step 4: L1 → L0 - Choose aggregation metric."""
    step = STEPS[4]
    render_step_header(step)

    st.markdown(t("choose_calculation"))

    # Show L1 vectors first (what we're aggregating from)
    if 'l1' in st.session_state.datasets:
        st.subheader("📊 Available Value Lists")
        for domain, l1_ds in st.session_state.datasets['l1'].items():
            vector_data = l1_ds.get_data()
            column_name = st.session_state.answers.get('feature', 'extracted')
            with st.expander(f"{domain} - {len(vector_data)} values"):
                st.write(vector_data.head(20).tolist())

    st.divider()

    aggregation = st.selectbox(
        t("select_aggregation"),
        options=["count", "sum", "mean", "min", "max"],
        index=0,
        help=t("choose_calculation")
    )

    if st.button(t("compute_metrics")):
        compute_atomic_metrics(aggregation)
        st.session_state.answers['aggregation'] = aggregation

    # Show atomic metrics using shared display (003-level-dataviz-display L0 datum)
    if 'l0' in st.session_state.datasets:
        st.divider()
        feature_name = st.session_state.answers.get('feature', 'value')

        for domain, l0_ds in st.session_state.datasets['l0'].items():
            value = l0_ds.get_data()
            source_info = f'"{feature_name}" from {domain} domain'
            render_l0_datum(value, aggregation, source_info)

        col1, col2 = st.columns(2)
        with col1:
            if st.button(t("back_arrow")):
                st.session_state.current_step = 3
                st.rerun()
        with col2:
            if st.button(f"{t('view_results')} →", type="primary"):
                st.session_state.current_step = 5
                st.rerun()


def render_results_step():
    """Step 5: Show final results and data model."""
    step = STEPS[5]
    render_step_header(step)

    st.success(f"🎉 {t('descent_complete')}")

    # Summary metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Data Sources (L4)",
            len(st.session_state.raw_data) if st.session_state.raw_data else 0
        )

    with col2:
        if 'l3' in st.session_state.datasets:
            G = st.session_state.datasets['l3'].get_data()
            # Handle both NetworkX graphs and DataFrames
            if hasattr(G, 'number_of_nodes'):
                st.metric("Connected Items", G.number_of_nodes())
            elif hasattr(G, 'shape'):  # DataFrame
                st.metric("Connected Items", len(G))
            else:
                st.metric("Connected Items", 0)
        else:
            st.metric("Connected Items", 0)

    with col3:
        if 'l0' in st.session_state.datasets:
            total = sum(l0.get_data() for l0 in st.session_state.datasets['l0'].values())
            st.metric("Total Items (L0)", total)

    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Final Results",
        "📦 Structure",
        "🔗 Connected View",
        "📥 Export"
    ])

    with tab1:
        render_atomic_metrics_view()

    with tab2:
        if st.session_state.data_model:
            render_data_model_preview(st.session_state.data_model)

    with tab3:
        render_knowledge_graph_view()

    with tab4:
        render_export_options()

    # Action buttons
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        if st.button(f"🔄 {t('start_new_analysis')}"):
            reset_workflow()
            st.rerun()

    with col2:
        if st.button(f"🚀 {t('start_redesign_ascent')}", type="primary"):
            # Build session graph from descent results and switch to ascent mode
            session_data = build_session_graph_from_descent()
            if session_data:
                st.session_state['loaded_session_graph'] = session_data
                # Initialize ascent state
                st.session_state.ascent_level = 0
                st.session_state.ascent_l1_data = None
                st.session_state.ascent_l2_data = None
                st.session_state.ascent_l3_data = None
                # Set flag to switch to Free Navigation on next rerun
                # (before sidebar widget renders)
                st.session_state._switch_to_ascent = True
                st.rerun()
            else:
                st.error(t("cannot_start_redesign"))


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def build_session_graph_from_descent() -> Optional[Dict[str, Any]]:
    """
    Build a session graph dictionary from step-by-step descent results.

    This enables transitioning from descent Results step to ascent mode.
    Reuses the same logic as the session export feature.

    Returns:
        Session data dict with 'accumulated_outputs', 'decisions', 'graph',
        or None if insufficient data.
    """
    from intuitiveness.persistence.session_graph import SessionGraph

    # Check we have descent results
    if 'l0' not in st.session_state.datasets:
        return None

    graph = SessionGraph()
    accumulated_outputs = {}
    decisions = []
    prev_id = None

    # Add L4 (raw data)
    if st.session_state.raw_data:
        l4_metadata = {
            "decision_description": "Uploaded data files",
            "files": list(st.session_state.raw_data.keys())
        }
        combined_info = {
            "file": list(st.session_state.raw_data.keys()),
            "rows": [len(df) for df in st.session_state.raw_data.values()],
            "columns": [len(df.columns) for df in st.session_state.raw_data.values()]
        }
        l4_id = graph.add_level_state(
            level=4,
            output_value=combined_info,
            data_artifact=pd.DataFrame(combined_info),
            metadata=l4_metadata
        )
        prev_id = l4_id
        accumulated_outputs[4] = {
            "output_value": combined_info,
            "decision_description": "Uploaded data files",
            "row_count": len(st.session_state.raw_data)
        }
        decisions.append({
            "step": 1,
            "level": 4,
            "action": "entry",
            "decision_description": "Uploaded data files"
        })

    # Add L3 (connected data)
    if 'l3' in st.session_state.datasets:
        l3_data = st.session_state.datasets['l3']
        l3_artifact = l3_data.get_data() if hasattr(l3_data, 'get_data') else l3_data
        l3_metadata = {
            "decision_description": "Semantic join created connected items",
            "answers": st.session_state.answers
        }
        l3_id = graph.add_level_state(
            level=3,
            output_value={"type": "connected_data"},
            data_artifact=l3_artifact if isinstance(l3_artifact, pd.DataFrame) else pd.DataFrame(),
            metadata=l3_metadata
        )
        if prev_id:
            graph.add_transition(prev_id, l3_id, "descend", {"operation": "semantic_join"})
        prev_id = l3_id
        row_count = len(l3_artifact) if hasattr(l3_artifact, '__len__') else 0
        accumulated_outputs[3] = {
            "output_value": {"type": "connected_data"},
            "decision_description": "Semantic join created connected items",
            "row_count": row_count
        }
        decisions.append({
            "step": 2,
            "level": 3,
            "action": "descend",
            "decision_description": "Semantic join"
        })

    # Add L2 (categorized data)
    if 'l2' in st.session_state.datasets:
        l2_data = st.session_state.datasets['l2']
        domain_column = st.session_state.answers.get('domain_column', 'unknown')
        l2_metadata = {
            "decision_description": f"Categorized by {domain_column}",
            "categories": st.session_state.answers.get('domains', [])
        }
        l2_frames = []
        for cat, ds in l2_data.items():
            df = ds.get_data() if hasattr(ds, 'get_data') else pd.DataFrame()
            if not df.empty:
                df = df.copy()
                df['category'] = cat
                l2_frames.append(df)
        l2_combined = pd.concat(l2_frames, ignore_index=True) if l2_frames else pd.DataFrame()
        l2_summary = {cat: {"count": len(ds.get_data()) if hasattr(ds, 'get_data') else 0}
                     for cat, ds in l2_data.items()}
        l2_id = graph.add_level_state(
            level=2,
            output_value=l2_summary,
            data_artifact=l2_combined,
            metadata=l2_metadata
        )
        if prev_id:
            graph.add_transition(prev_id, l2_id, "descend", {"operation": "categorize"})
        prev_id = l2_id
        accumulated_outputs[2] = {
            "output_value": l2_summary,
            "decision_description": f"Categorized by {domain_column}",
            "row_count": len(l2_combined)
        }
        decisions.append({
            "step": 3,
            "level": 2,
            "action": "descend",
            "decision_description": f"Categorized by {domain_column}"
        })

    # Add L1 (extracted values)
    if 'l1' in st.session_state.datasets:
        l1_data = st.session_state.datasets['l1']
        feature_name = st.session_state.answers.get('feature', 'value')
        l1_metadata = {
            "decision_description": f"Extracted {feature_name}",
            "feature": feature_name
        }
        l1_rows = []
        l1_summary = {}
        for cat, ds in l1_data.items():
            values = ds.get_data() if hasattr(ds, 'get_data') else ds
            if hasattr(values, '__iter__') and not isinstance(values, str):
                for val in values:
                    l1_rows.append({"category": cat, feature_name: val})
            else:
                l1_rows.append({"category": cat, feature_name: values})
            l1_summary[cat] = {"count": len(values) if hasattr(values, '__len__') else 1}
        l1_combined = pd.DataFrame(l1_rows) if l1_rows else pd.DataFrame()
        l1_id = graph.add_level_state(
            level=1,
            output_value=l1_summary,
            data_artifact=l1_combined,
            metadata=l1_metadata
        )
        if prev_id:
            graph.add_transition(prev_id, l1_id, "descend", {"operation": "extract"})
        prev_id = l1_id
        accumulated_outputs[1] = {
            "output_value": l1_summary,
            "decision_description": f"Extracted {feature_name}",
            "row_count": len(l1_combined)
        }
        decisions.append({
            "step": 4,
            "level": 1,
            "action": "descend",
            "decision_description": f"Extracted {feature_name}"
        })

    # Add L0 (computed results)
    if 'l0' in st.session_state.datasets:
        l0_data = st.session_state.datasets['l0']
        l0_metadata = {
            "decision_description": f"Computed {st.session_state.answers.get('aggregation', 'metric')}",
            "aggregation": st.session_state.answers.get('aggregation', 'unknown')
        }
        l0_values = {}
        for cat, ds in l0_data.items():
            val = ds.get_data() if hasattr(ds, 'get_data') else ds
            l0_values[cat] = val
        l0_id = graph.add_level_state(
            level=0,
            output_value=l0_values,
            data_artifact=l0_values,
            metadata=l0_metadata
        )
        if prev_id:
            graph.add_transition(prev_id, l0_id, "descend", {"operation": "aggregate"})
        accumulated_outputs[0] = {
            "output_value": l0_values,
            "decision_description": f"Computed {st.session_state.answers.get('aggregation', 'metric')}",
            "row_count": len(l0_values)
        }
        decisions.append({
            "step": 5,
            "level": 0,
            "action": "descend",
            "decision_description": f"Computed final result"
        })

    return {
        'accumulated_outputs': accumulated_outputs,
        'decisions': decisions,
        'graph': graph,
        'current_level': 0
    }


def create_demo_data() -> Dict[str, pd.DataFrame]:
    """Create sample demo data for testing."""
    import numpy as np
    np.random.seed(42)

    # Generate sample indicator names
    prefixes = ['CA', 'VOL', 'NB', 'TX', 'MT', 'QT']
    segments = ['B2B', 'B2C', 'PRO', 'PART']
    locations = ['FR', 'INT', 'EU', 'DOM']

    data = []
    for i in range(100):
        name = f"{np.random.choice(prefixes)}_{np.random.choice(segments)}_{np.random.choice(locations)}"
        data.append({
            'name': name,
            'description': f'Indicator {i}',
            'source': f'Source_{np.random.randint(1, 5)}'
        })

    return {'demo_indicators.csv': pd.DataFrame(data)}


def render_data_model_preview(data_model: Neo4jDataModel):
    """Render a preview of the Neo4j data model with column mapping and Cypher."""
    st.subheader("📦 Generated Structure")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Items:**")
        for node in data_model.nodes:
            # Handle both dict properties and string properties
            if node.properties:
                props = ", ".join([
                    p['name'] if isinstance(p, dict) else str(p)
                    for p in node.properties
                ])
            else:
                props = "(none)"
            st.code(f"({node.label})\n  Identifier: {node.key_property}\n  Fields: {props}")

    with col2:
        st.markdown("**Connections:**")
        for rel in data_model.relationships:
            st.code(f"({rel.start_node_label})—[{rel.type}]→({rel.end_node_label})")

    # Mermaid diagram
    with st.expander("📊 View as Diagram"):
        mermaid_code = generate_mermaid_diagram(data_model)
        st.code(mermaid_code, language="mermaid")

    # Initialize entity_mapping in session state if not exists
    if 'entity_mapping' not in st.session_state:
        st.session_state.entity_mapping = {}
    if 'relationship_mapping' not in st.session_state:
        st.session_state.relationship_mapping = {}

    # ========== AI-POWERED CONNECTION WIZARD ==========
    if st.session_state.raw_data:
        st.markdown("---")
        st.subheader("🔮 Connect Your Data")

        # Initialize discovery results if not exists
        if SESSION_KEY_DISCOVERY_RESULTS not in st.session_state:
            st.session_state[SESSION_KEY_DISCOVERY_RESULTS] = None

        # Run discovery if not done yet
        if st.session_state[SESSION_KEY_DISCOVERY_RESULTS] is None:
            with st.spinner("Analyzing your files to find connections..."):
                try:
                    discovery_result = run_discovery(st.session_state.raw_data)
                    st.session_state[SESSION_KEY_DISCOVERY_RESULTS] = discovery_result
                    st.success(f"Found {len(discovery_result.entity_suggestions)} data types "
                              f"and {len(discovery_result.relationship_suggestions)} potential connections "
                              f"in {discovery_result.analysis_time_ms:.0f}ms")
                except Exception as e:
                    st.error(f"Error analyzing files: {e}")
                    st.session_state[SESSION_KEY_DISCOVERY_RESULTS] = DiscoveryResult()

        # Get discovery results
        discovery_result = st.session_state[SESSION_KEY_DISCOVERY_RESULTS]

        if discovery_result:
            # Get current wizard step
            wizard_step = _get_wizard_step()

            # Render appropriate wizard step
            if wizard_step == 1:
                if render_wizard_step_1_entities(
                    discovery_result.entity_suggestions,
                    key_prefix="wizard_s1"
                ):
                    _set_wizard_step(2)
                    st.rerun()

            elif wizard_step == 2:
                if render_wizard_step_2_relationships(
                    discovery_result.relationship_suggestions,
                    key_prefix="wizard_s2"
                ):
                    _set_wizard_step(3)
                    st.rerun()

            elif wizard_step == 3:
                joined_df = render_wizard_step_3_confirm(
                    st.session_state.raw_data,
                    key_prefix="wizard_s3"
                )
                if joined_df is not None:
                    # Store the joined L3 dataset
                    st.session_state.joined_l3_dataset = joined_df

                    # Create basic entity/relationship mappings from joined table
                    st.session_state.entity_mapping = {}
                    st.session_state.relationship_mapping = {}

                    st.success("Configuration complete! Your joined L3 dataset is ready.")
                    st.rerun()

        # Option to reset wizard
        with st.expander("🔄 Start Over"):
            if st.button("Reset and Re-analyze", key="reset_wizard"):
                st.session_state[SESSION_KEY_DISCOVERY_RESULTS] = None
                _set_wizard_step(1)
                # Clear decision states
                keys_to_clear = [k for k in st.session_state.keys()
                                if k.startswith('wizard_s')]
                for k in keys_to_clear:
                    del st.session_state[k]
                st.rerun()


def generate_mermaid_diagram(data_model: Neo4jDataModel) -> str:
    """Generate a Mermaid diagram for the data model."""
    lines = ["graph TD"]

    for node in data_model.nodes:
        lines.append(f'    {node.label}["{node.label}"]')

    for rel in data_model.relationships:
        lines.append(f'    {rel.start_node_label} -->|{rel.type}| {rel.end_node_label}')

    return "\n".join(lines)


def build_knowledge_graph():
    """Build the L3 knowledge graph from raw data (legacy function)."""
    if not st.session_state.raw_data or not st.session_state.data_model:
        return

    G = nx.Graph()
    core_label = st.session_state.data_model.nodes[0].label

    for filename, df in st.session_state.raw_data.items():
        # Add source node
        source_id = f"source_{filename}"
        G.add_node(source_id, type="Source", name=filename)

        # Find name column
        name_col = None
        for col in df.columns:
            if df[col].dtype == 'object':
                name_col = col
                break

        if name_col:
            for idx, row in df.iterrows():
                entity_name = str(row.get(name_col, 'Unknown'))
                if entity_name == 'nan' or pd.isna(entity_name):
                    continue

                entity_id = f"{filename}_{idx}"
                node_attrs = {
                    "type": core_label,
                    "name": entity_name,
                    "source_file": filename
                }

                for col in df.columns[:5]:
                    if col != name_col:
                        node_attrs[col.lower().replace(" ", "_")] = str(row.get(col, ""))

                G.add_node(entity_id, **node_attrs)
                G.add_edge(entity_id, source_id, relation="FOUND_IN")

    st.session_state.datasets['l3'] = Level3Dataset(G)


def build_knowledge_graph_from_model(relationship_mode: str = "key_matching", similarity_threshold: float = 0.7):
    """
    Build the L3 knowledge graph from raw data using the generated data model.
    Uses the entity_mapping and relationship_mapping from session state.

    Args:
        relationship_mode: Default mode if not specified per-relationship
        similarity_threshold: Default threshold for semantic similarity
    """
    if not st.session_state.raw_data:
        return

    data_model = st.session_state.data_model
    entity_mapping = st.session_state.get('entity_mapping', {})
    relationship_mapping = st.session_state.get('relationship_mapping', {})

    G = nx.DiGraph()  # Directed graph to properly represent relationships

    # Track nodes by entity type and key value for relationship creation
    # entity_nodes[entity_type][key_value] = node_id
    entity_nodes = {}
    node_texts = {}  # For semantic matching

    print(f"[Graph Build] Entity mapping: {list(entity_mapping.keys())}")
    print(f"[Graph Build] Relationship mapping: {list(relationship_mapping.keys())}")

    # ========== CREATE NODES FROM ENTITY MAPPING ==========
    for entity_label, mapping in entity_mapping.items():
        source_file = mapping.get('source_file')
        key_column = mapping.get('key_column')
        prop_columns = mapping.get('property_columns', [])

        if not source_file or source_file not in st.session_state.raw_data:
            print(f"[Graph Build] Skipping {entity_label}: no source file")
            continue

        df = st.session_state.raw_data[source_file]

        if not key_column or key_column not in df.columns:
            print(f"[Graph Build] Skipping {entity_label}: key column '{key_column}' not found")
            continue

        print(f"[Graph Build] Creating {entity_label} nodes from {source_file} using key '{key_column}'")

        entity_nodes[entity_label] = {}

        for idx, row in df.iterrows():
            key_value = str(row.get(key_column, '')).strip()
            if not key_value or key_value == 'nan':
                continue

            # Use key_value as unique identifier for this entity
            entity_id = f"{entity_label}_{key_value}"

            # Build node attributes
            node_attrs = {
                "type": entity_label,
                "label": entity_label,
                "name": key_value,
                "key_value": key_value,
                "source_file": source_file
            }

            # Add property columns
            text_parts = [key_value]
            for col in prop_columns:
                if col in df.columns:
                    val = row.get(col)
                    if val is not None and pd.notna(val) and str(val).strip():
                        prop_name = col.lower().replace(" ", "_").replace("-", "_")
                        str_val = str(val).strip()
                        node_attrs[prop_name] = str_val
                        text_parts.append(f"{col}: {str_val}")

            # Only add if not already exists (avoid duplicates for same key)
            if entity_id not in G:
                G.add_node(entity_id, **node_attrs)
                node_texts[entity_id] = " | ".join(text_parts)

            # Track for relationship creation
            entity_nodes[entity_label][key_value] = entity_id

    print(f"[Graph Build] Created {G.number_of_nodes()} nodes")

    # ========== CREATE RELATIONSHIPS FROM RELATIONSHIP MAPPING ==========
    relationship_edges = 0

    if data_model and data_model.relationships:
        print(f"[Graph Build] Creating relationships from {len(data_model.relationships)} relationship definitions...")

        for rel in data_model.relationships:
            rel_key = f"{rel.start_node_label}_{rel.type}_{rel.end_node_label}"
            rel_config = relationship_mapping.get(rel_key, {})

            start_label = rel.start_node_label
            end_label = rel.end_node_label
            rel_type = rel.type
            mode = rel_config.get('mode', 'key_matching')

            print(f"[Graph Build] Processing: {start_label} -[{rel_type}]-> {end_label} (mode: {mode})")

            # Get entities for this relationship
            start_entities = entity_nodes.get(start_label, {})
            end_entities = entity_nodes.get(end_label, {})

            if not start_entities or not end_entities:
                print(f"  Skipping: no nodes for {start_label} ({len(start_entities)}) or {end_label} ({len(end_entities)})")
                continue

            if mode == 'key_matching':
                # Get the join columns from mapping
                start_key_col = rel_config.get('start_key_column')
                end_key_col = rel_config.get('end_key_column')

                # Get source files for each entity type
                start_file = entity_mapping.get(start_label, {}).get('source_file')
                end_file = entity_mapping.get(end_label, {}).get('source_file')

                if not start_file or not end_file:
                    print(f"  Skipping: no source files")
                    continue

                if not start_key_col or not end_key_col:
                    print(f"  Skipping: join columns not specified")
                    continue

                start_df = st.session_state.raw_data.get(start_file)
                end_df = st.session_state.raw_data.get(end_file)

                if start_df is None or end_df is None:
                    continue

                # Build lookup from end entity's join column values to node IDs
                end_key_to_nodes = {}
                end_entity_key_col = entity_mapping.get(end_label, {}).get('key_column')

                for idx, row in end_df.iterrows():
                    join_val = str(row.get(end_key_col, '')).strip()
                    entity_key = str(row.get(end_entity_key_col, '')).strip()
                    if join_val and entity_key:
                        node_id = f"{end_label}_{entity_key}"
                        if node_id in G:
                            if join_val not in end_key_to_nodes:
                                end_key_to_nodes[join_val] = []
                            end_key_to_nodes[join_val].append(node_id)

                # Create relationships by matching join column values
                start_entity_key_col = entity_mapping.get(start_label, {}).get('key_column')

                for idx, row in start_df.iterrows():
                    join_val = str(row.get(start_key_col, '')).strip()
                    entity_key = str(row.get(start_entity_key_col, '')).strip()

                    if join_val and entity_key:
                        start_node_id = f"{start_label}_{entity_key}"
                        if start_node_id in G and join_val in end_key_to_nodes:
                            for end_node_id in end_key_to_nodes[join_val]:
                                if not G.has_edge(start_node_id, end_node_id):
                                    G.add_edge(start_node_id, end_node_id,
                                               type=rel_type,
                                               label=rel_type,
                                               matched_value=join_val)
                                    relationship_edges += 1

                print(f"  Created {relationship_edges} edges via key matching")

            elif mode == 'semantic':
                # Semantic similarity mode via HF Inference API
                # Uses intfloat/multilingual-e5-base for consistency
                threshold = rel_config.get('threshold', 0.8)
                print(f"  Using semantic similarity with threshold {threshold}")

                try:
                    from intuitiveness.models import get_batch_similarities
                    import numpy as np

                    # Get text representations for start and end nodes
                    start_nodes = [(nid, node_texts.get(nid, '')) for nid in
                                   [f"{start_label}_{k}" for k in start_entities.keys()] if nid in G]
                    end_nodes = [(nid, node_texts.get(nid, '')) for nid in
                                 [f"{end_label}_{k}" for k in end_entities.keys()] if nid in G]

                    if start_nodes and end_nodes:
                        start_texts = [t for _, t in start_nodes]
                        end_texts = [t for _, t in end_nodes]

                        # Get similarities via HF API (shows progress bar)
                        sims = get_batch_similarities(start_texts, end_texts)

                        if sims is not None:
                            matches = np.where(sims >= threshold)

                            for idx1, idx2 in zip(matches[0], matches[1]):
                                start_node_id = start_nodes[idx1][0]
                                end_node_id = end_nodes[idx2][0]
                                sim_score = float(sims[idx1, idx2])

                                if not G.has_edge(start_node_id, end_node_id):
                                    G.add_edge(start_node_id, end_node_id,
                                               type=rel_type,
                                               label=rel_type,
                                               similarity=sim_score)
                                    relationship_edges += 1

                            print(f"  Created {relationship_edges} edges via semantic similarity")
                        else:
                            print(f"  Embedding API failed - skipping semantic edges")

                except Exception as e:
                    print(f"  Semantic mode error: {e}")

    print(f"[Graph Build] Total: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges ({relationship_edges} relationship edges)")

    # Store the graph
    st.session_state.datasets['l3'] = Level3Dataset(G)


def categorize_by_domains(domains: List[str], use_semantic: bool, threshold: float, column: str = "name", entity_type: str = None):
    """Categorize L3 data into L2 domain tables based on selected column and entity type."""
    if 'l3' not in st.session_state.datasets:
        st.error("No L3 dataset available")
        return

    graph_or_df = st.session_state.datasets['l3'].get_data()

    # Extract items, handling both DataFrame and NetworkX graph inputs
    items = []
    item_data = []

    # Handle DataFrame input (from OOM Fix #1 - Level3Dataset stores DataFrame)
    if isinstance(graph_or_df, pd.DataFrame):
        df = graph_or_df
        for idx, row in df.iterrows():
            # Use the selected column for categorization, fall back to first column
            if column in df.columns:
                value = row[column]
            elif 'name' in df.columns:
                value = row['name']
            else:
                value = row[df.columns[0]] if len(df.columns) > 0 else str(idx)
            items.append(str(value) if value is not None else "")
            item_data.append({"id": str(idx), "categorization_value": value, **row.to_dict()})
    else:
        # Original NetworkX graph handling
        graph = graph_or_df
        for node, attrs in graph.nodes(data=True):
            node_type = attrs.get("type", "Unknown")
            # Skip Source nodes
            if node_type == "Source":
                continue
            # Filter by entity type if specified
            if entity_type and node_type != entity_type:
                continue
            # Use the selected column for categorization
            value = attrs.get(column, attrs.get("name", str(node)))
            items.append(str(value) if value is not None else "")
            item_data.append({"id": node, "categorization_value": value, **attrs})

    # Categorize
    matcher = SemanticMatcher(use_embeddings=use_semantic)
    categorized = matcher.categorize_by_domains(items, domains, threshold)

    # Create L2 datasets
    results = {}
    for domain, matches in categorized.items():
        matched_values = {item for item, score in matches}
        domain_data = [d for d in item_data if str(d.get("categorization_value", "")) in matched_values]

        if domain_data:
            # Remove the temporary categorization_value column
            for d in domain_data:
                d.pop("categorization_value", None)
            df = pd.DataFrame(domain_data)
            results[domain] = Level2Dataset(df, name=f"{domain}_indicators")
        else:
            results[domain] = Level2Dataset(pd.DataFrame(), name=f"{domain}_indicators")

    st.session_state.datasets['l2'] = results


def render_domain_results():
    """Render the domain categorization results."""
    st.subheader("Items Organized by Category")

    for domain, l2_ds in st.session_state.datasets['l2'].items():
        df = l2_ds.get_data()
        with st.expander(f"{domain} ({len(df)} items)"):
            if not df.empty:
                st.dataframe(df.head(20))
            else:
                st.info("No items matched this domain")


def extract_features(column: str):
    """Extract L1 vectors from L2 domain tables."""
    if 'l2' not in st.session_state.datasets:
        return

    results = {}
    for domain, l2_ds in st.session_state.datasets['l2'].items():
        df = l2_ds.get_data()
        if not df.empty and column in df.columns:
            series = df[column]
            results[domain] = Level1Dataset(series, name=column)

    st.session_state.datasets['l1'] = results


def compute_atomic_metrics(aggregation: str):
    """Compute L0 atomic metrics from L1 vectors."""
    if 'l1' not in st.session_state.datasets:
        return

    results = {}
    for domain, l1_ds in st.session_state.datasets['l1'].items():
        series = l1_ds.get_data()

        if aggregation == "count":
            value = series.count()
        elif aggregation == "sum":
            value = series.sum() if series.dtype in ['int64', 'float64'] else len(series)
        elif aggregation == "mean":
            value = series.mean() if series.dtype in ['int64', 'float64'] else len(series)
        elif aggregation == "min":
            value = series.min()
        elif aggregation == "max":
            value = series.max()
        else:
            value = series.count()

        results[domain] = Level0Dataset(value, description=f"{aggregation} of {domain}")

    st.session_state.datasets['l0'] = results


def render_atomic_metrics_view():
    """Render the atomic metrics visualization with stylish Klein Blue design."""
    if 'l0' not in st.session_state.datasets:
        st.info("No atomic metrics computed yet")
        return

    domains = list(st.session_state.datasets['l0'].keys())
    values = [l0.get_data() for l0 in st.session_state.datasets['l0'].values()]

    # Create stylish bar chart with Klein Blue palette
    fig = styled_bar_chart(
        data=dict(zip(domains, values)),
        title="Atomic Metrics by Domain",
        show_values=True,
        height=350,
    )

    # Render with clean config (no toolbar)
    render_plotly_chart(fig, key="metrics_chart")


def render_knowledge_graph_view():
    """Render the knowledge graph visualization using NetworkX + matplotlib."""
    if 'l3' not in st.session_state.datasets:
        st.info("No knowledge graph built yet")
        return

    import matplotlib.pyplot as plt

    G = st.session_state.datasets['l3'].get_data()

    # Handle DataFrame input (from OOM Fix #1 - Level3Dataset may store DataFrame)
    if isinstance(G, pd.DataFrame):
        st.info("📊 Graph visualization is available when data is stored as a knowledge graph. "
                "Your data is currently in tabular format for better performance.")
        # Show basic stats for DataFrame
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Rows", len(G))
        with col2:
            st.metric("Columns", len(G.columns))
        return

    col1, col2 = st.columns([2, 1])

    with col2:
        st.markdown(f"**Graph Statistics:**")
        st.metric("Nodes", G.number_of_nodes())
        st.metric("Edges", G.number_of_edges())

        # Node type distribution
        node_types = {}
        for _, attrs in G.nodes(data=True):
            t = attrs.get('type', 'Unknown')
            node_types[t] = node_types.get(t, 0) + 1

        st.markdown("**Node Types:**")
        for t, count in node_types.items():
            st.markdown(f"- {t}: {count}")

    with col1:
        # NetworkX + matplotlib visualization
        type_colors = {
            'Source': '#E74C3C',      # Red
            'Indicator': '#3498DB',    # Blue
            'Entity': '#2ECC71',       # Green
            'BusinessDomain': '#F39C12', # Orange
            'Businessdomain': '#F39C12', # Orange (lowercase variant)
            'Unknown': '#95A5A6'       # Gray
        }

        # Limit nodes for performance - SELECT NODES WITH DATA MODEL RELATIONSHIPS
        max_nodes = 50

        # Get relationship types from data model
        data_model_rel_types = set()
        if st.session_state.data_model and st.session_state.data_model.relationships:
            for rel in st.session_state.data_model.relationships:
                data_model_rel_types.add(rel.type)

        # Calculate "data model degree" - count edges that are data model relationships
        # (excludes FROM_SOURCE which just links to source files)
        node_dm_degrees = {}  # Degree counting only data model relationships
        node_degrees = dict(G.degree())  # Total degree for sizing

        for node in G.nodes():
            dm_degree = 0
            for neighbor in G.neighbors(node):
                edge_data = G.get_edge_data(node, neighbor)
                if edge_data:
                    edge_type = edge_data.get('type', '')
                    # Count edges that are:
                    # 1. From the data model relationship definitions
                    # 2. Cross-file relationships (SAME_* or SEMANTICALLY_RELATED)
                    # Exclude only: FROM_SOURCE (links to source file nodes)
                    if edge_type != 'FROM_SOURCE':
                        dm_degree += 1
            node_dm_degrees[node] = dm_degree

        if G.number_of_nodes() > max_nodes:
            # Sort nodes by data model degree (highest first) to show richest entity connections
            sorted_nodes = sorted(node_dm_degrees.items(), key=lambda x: x[1], reverse=True)

            # Take top N/2 seed nodes and include their neighbors to show actual edges
            seed_count = max(10, max_nodes // 3)
            seed_nodes = set(node for node, degree in sorted_nodes[:seed_count])

            # Add neighbors of seed nodes (both predecessors and successors)
            nodes_to_include = set(seed_nodes)
            for seed in seed_nodes:
                # Add successors (outgoing edges)
                for neighbor in G.successors(seed):
                    edge_type = G.get_edge_data(seed, neighbor, {}).get('type', '')
                    if edge_type != 'FROM_SOURCE':
                        nodes_to_include.add(neighbor)
                # Add predecessors (incoming edges)
                for neighbor in G.predecessors(seed):
                    edge_type = G.get_edge_data(neighbor, seed, {}).get('type', '')
                    if edge_type != 'FROM_SOURCE':
                        nodes_to_include.add(neighbor)

            # Limit total nodes if too many
            if len(nodes_to_include) > max_nodes * 2:
                # Keep seeds + top neighbors by their own dm_degree
                neighbor_only = nodes_to_include - seed_nodes
                sorted_neighbors = sorted(neighbor_only, key=lambda n: node_dm_degrees.get(n, 0), reverse=True)
                nodes_to_include = seed_nodes | set(sorted_neighbors[:max_nodes - seed_count])

            # Create subgraph with seeds and their connected neighbors
            subgraph = G.subgraph(nodes_to_include).copy()

            # Remove FROM_SOURCE edges from the subgraph for cleaner visualization
            edges_to_remove = [(u, v) for u, v, d in subgraph.edges(data=True) if d.get('type') == 'FROM_SOURCE']
            subgraph.remove_edges_from(edges_to_remove)
        else:
            subgraph = G.copy()
            # Remove FROM_SOURCE edges for cleaner visualization
            edges_to_remove = [(u, v) for u, v, d in subgraph.edges(data=True) if d.get('type') == 'FROM_SOURCE']
            subgraph.remove_edges_from(edges_to_remove)

        # Create figure with better size for visibility
        fig, ax = plt.subplots(figsize=(12, 10))

        # Get node colors and sizes based on type and degree
        node_colors = []
        node_sizes = []
        labels = {}

        # Calculate min/max degrees for scaling
        degrees_in_subgraph = [node_degrees.get(n, 1) for n in subgraph.nodes()]
        min_deg = min(degrees_in_subgraph) if degrees_in_subgraph else 1
        max_deg = max(degrees_in_subgraph) if degrees_in_subgraph else 1
        deg_range = max_deg - min_deg if max_deg > min_deg else 1

        for node in subgraph.nodes():
            attrs = subgraph.nodes[node]
            node_type = attrs.get('type', 'Unknown')
            node_colors.append(type_colors.get(node_type, type_colors['Unknown']))

            # Scale node size by degree (more connections = larger node)
            degree = node_degrees.get(node, 1)
            if node_type == 'Source':
                node_sizes.append(1200)  # Source nodes always large
            else:
                # Scale between 200 and 1000 based on degree
                normalized = (degree - min_deg) / deg_range
                node_sizes.append(200 + normalized * 800)

            # Truncate labels
            name = attrs.get('name', str(node))
            labels[node] = name[:15] + '...' if len(name) > 15 else name

        # Layout - use spring layout with more spacing
        pos = nx.spring_layout(subgraph, k=2, iterations=50, seed=42)

        # Draw edges
        nx.draw_networkx_edges(
            subgraph, pos, ax=ax,
            edge_color='#CCCCCC',
            arrows=True,
            arrowsize=15,
            alpha=0.6
        )

        # Draw nodes
        nx.draw_networkx_nodes(
            subgraph, pos, ax=ax,
            node_color=node_colors,
            node_size=node_sizes,
            alpha=0.9
        )

        # Draw labels
        nx.draw_networkx_labels(
            subgraph, pos, labels, ax=ax,
            font_size=8,
            font_weight='bold'
        )

        # Add legend
        legend_elements = []
        for node_type, color in type_colors.items():
            if node_type in node_types:
                from matplotlib.patches import Patch
                legend_elements.append(Patch(facecolor=color, label=f"{node_type} ({node_types.get(node_type, 0)})"))

        if legend_elements:
            ax.legend(handles=legend_elements, loc='upper left', fontsize=8)

        ax.set_title(f"Knowledge Graph: {subgraph.number_of_nodes()} Nodes, {subgraph.number_of_edges()} Entity Relationships")
        ax.axis('off')
        plt.tight_layout()

        st.pyplot(fig)
        plt.close(fig)

        if G.number_of_nodes() > max_nodes:
            # Show data model relationship info
            dm_rel_count = sum(1 for n in subgraph.nodes() if node_dm_degrees.get(n, 0) > 0)
            max_dm_degree = max(node_dm_degrees.values()) if node_dm_degrees else 0
            st.caption(f"Showing top {max_nodes} nodes with data model relationships ({dm_rel_count} have DM edges, max DM degree: {max_dm_degree}) out of {G.number_of_nodes()} total nodes")


def render_export_options():
    """Render export options for the data model and results."""
    import pandas as pd  # Ensure pd is available in this scope
    st.subheader("Export Options")

    col1, col2 = st.columns(2)

    with col1:
        if st.session_state.data_model:
            model_json = st.session_state.data_model.to_json()
            st.download_button(
                "📥 Download Data Model (JSON)",
                data=json.dumps(model_json, indent=2),
                file_name="data_model.json",
                mime="application/json"
            )

    with col2:
        if st.session_state.data_model:
            arrows_json = st.session_state.data_model.to_arrows_format()
            st.download_button(
                "📥 Download Arrows.app Format",
                data=json.dumps(arrows_json, indent=2),
                file_name="arrows_model.json",
                mime="application/json"
            )

    # Export answers/workflow
    if st.session_state.answers:
        st.download_button(
            "📥 Download Workflow Configuration",
            data=json.dumps(st.session_state.answers, indent=2),
            file_name="workflow_config.json",
            mime="application/json"
        )

    # CSV Export Section (direct from session state - no decompression needed)
    st.divider()
    st.subheader("📊 Export Data as CSV")
    st.info("Download each level's data directly as CSV files.")

    csv_cols = st.columns(4)

    # L3 - Joined data
    with csv_cols[0]:
        if 'l3' in st.session_state.datasets and st.session_state.datasets['l3']:
            l3_data = st.session_state.datasets['l3']
            if hasattr(l3_data, 'get_data'):
                l3_df = l3_data.get_data()
            else:
                l3_df = l3_data
            st.download_button(
                "📥 L3 Joined",
                data=l3_df.to_csv(index=False),
                file_name="L3_joined_data.csv",
                mime="text/csv"
            )

    # L2 - Categorized data
    with csv_cols[1]:
        if 'l2' in st.session_state.datasets and st.session_state.datasets['l2']:
            l2_frames = []
            for cat, ds in st.session_state.datasets['l2'].items():
                df = ds.get_data() if hasattr(ds, 'get_data') else pd.DataFrame()
                if not df.empty:
                    df = df.copy()
                    df['category'] = cat
                    l2_frames.append(df)
            if l2_frames:
                l2_combined = pd.concat(l2_frames, ignore_index=True)
                st.download_button(
                    "📥 L2 Categorized",
                    data=l2_combined.to_csv(index=False),
                    file_name="L2_categorized_data.csv",
                    mime="text/csv"
                )

    # L1 - Extracted values
    with csv_cols[2]:
        if 'l1' in st.session_state.datasets and st.session_state.datasets['l1']:
            feature_name = st.session_state.answers.get('feature', 'value')
            l1_rows = []
            for cat, ds in st.session_state.datasets['l1'].items():
                values = ds.get_data() if hasattr(ds, 'get_data') else ds
                if hasattr(values, '__iter__') and not isinstance(values, str):
                    for val in values:
                        l1_rows.append({"category": cat, feature_name: val})
                else:
                    l1_rows.append({"category": cat, feature_name: values})
            if l1_rows:
                l1_df = pd.DataFrame(l1_rows)
                st.download_button(
                    "📥 L1 Values",
                    data=l1_df.to_csv(index=False),
                    file_name="L1_values.csv",
                    mime="text/csv"
                )

    # L0 - Final results
    with csv_cols[3]:
        if 'l0' in st.session_state.datasets and st.session_state.datasets['l0']:
            l0_rows = []
            for cat, ds in st.session_state.datasets['l0'].items():
                val = ds.get_data() if hasattr(ds, 'get_data') else ds
                l0_rows.append({"category": cat, "value": val})
            if l0_rows:
                l0_df = pd.DataFrame(l0_rows)
                st.download_button(
                    "📥 L0 Results",
                    data=l0_df.to_csv(index=False),
                    file_name="L0_results.csv",
                    mime="text/csv"
                )

    # Session Graph Export (Phase 2B - 006-playwright-mcp-e2e)
    st.divider()
    st.subheader("💾 Session Graph (for Free Exploration)")
    st.info(
        "Save your session as a graph to continue in Free Exploration mode. "
        "This preserves all level states and decisions for the ascent phase."
    )

    import os
    from datetime import datetime
    import uuid

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = str(uuid.uuid4())[:8]
    filename = f"session_graph_{session_id}_{timestamp}.json"
    filepath = os.path.join("sessions", filename)

    # Check if we have step-by-step data OR nav_session
    has_step_data = 'datasets' in st.session_state and st.session_state.datasets
    has_nav_session = st.session_state.nav_session is not None

    if has_step_data or has_nav_session:
        if st.button("💾 Save Session Graph", type="primary"):
            try:
                # Ensure sessions directory exists
                os.makedirs("sessions", exist_ok=True)

                if has_nav_session:
                    # Use existing nav_session (Free Exploration mode)
                    graph = st.session_state.nav_session.save_graph(filepath)
                else:
                    # Build SessionGraph from step-by-step state
                    from intuitiveness.persistence.session_graph import SessionGraph

                    graph = SessionGraph()

                    # Add L4 (raw data)
                    if st.session_state.raw_data:
                        l4_metadata = {
                            "decision_description": "Uploaded data files",
                            "files": list(st.session_state.raw_data.keys())
                        }
                        # Combine raw data into summary DataFrame
                        import pandas as pd
                        combined_info = {
                            "file": list(st.session_state.raw_data.keys()),
                            "rows": [len(df) for df in st.session_state.raw_data.values()],
                            "columns": [len(df.columns) for df in st.session_state.raw_data.values()]
                        }
                        l4_id = graph.add_level_state(
                            level=4,
                            output_value=combined_info,
                            data_artifact=pd.DataFrame(combined_info),
                            metadata=l4_metadata
                        )
                        prev_id = l4_id

                    # Add L3 (connected data) if exists
                    if 'l3' in st.session_state.datasets:
                        l3_data = st.session_state.datasets['l3']
                        if hasattr(l3_data, 'get_data'):
                            l3_artifact = l3_data.get_data()
                        else:
                            l3_artifact = l3_data
                        l3_metadata = {
                            "decision_description": "Semantic join created connected items",
                            "answers": st.session_state.answers
                        }
                        l3_id = graph.add_level_state(
                            level=3,
                            output_value={"type": "connected_data"},
                            data_artifact=l3_artifact if isinstance(l3_artifact, pd.DataFrame) else pd.DataFrame(),
                            metadata=l3_metadata
                        )
                        graph.add_transition(prev_id, l3_id, "descend", {"operation": "semantic_join"})
                        prev_id = l3_id

                    # Add L2 (categorized data) if exists
                    if 'l2' in st.session_state.datasets:
                        l2_data = st.session_state.datasets['l2']
                        domain_column = st.session_state.answers.get('domain_column', 'unknown')
                        l2_metadata = {
                            "decision_description": f"Categorized by {domain_column}",
                            "categories": st.session_state.answers.get('domains', [])
                        }
                        # Combine all L2 datasets into a single DataFrame with category column
                        l2_frames = []
                        for cat, ds in l2_data.items():
                            df = ds.get_data() if hasattr(ds, 'get_data') else pd.DataFrame()
                            if not df.empty:
                                df = df.copy()
                                df['category'] = cat
                                l2_frames.append(df)
                        l2_combined = pd.concat(l2_frames, ignore_index=True) if l2_frames else pd.DataFrame()
                        l2_summary = {cat: {"count": len(ds.get_data()) if hasattr(ds, 'get_data') else 0}
                                     for cat, ds in l2_data.items()}
                        l2_id = graph.add_level_state(
                            level=2,
                            output_value=l2_summary,
                            data_artifact=l2_combined,  # Store actual data, not just counts
                            metadata=l2_metadata
                        )
                        graph.add_transition(prev_id, l2_id, "descend", {"operation": "categorize"})
                        prev_id = l2_id

                    # Add L1 (extracted values) if exists
                    if 'l1' in st.session_state.datasets:
                        l1_data = st.session_state.datasets['l1']
                        feature_name = st.session_state.answers.get('feature', 'value')
                        l1_metadata = {
                            "decision_description": f"Extracted {feature_name}",
                            "feature": feature_name
                        }
                        # Combine all L1 datasets into a DataFrame with category and values
                        l1_rows = []
                        l1_summary = {}
                        for cat, ds in l1_data.items():
                            values = ds.get_data() if hasattr(ds, 'get_data') else ds
                            if hasattr(values, '__iter__') and not isinstance(values, str):
                                for val in values:
                                    l1_rows.append({"category": cat, feature_name: val})
                            else:
                                l1_rows.append({"category": cat, feature_name: values})
                            l1_summary[cat] = {"count": len(values) if hasattr(values, '__len__') else 1}
                        l1_combined = pd.DataFrame(l1_rows) if l1_rows else pd.DataFrame()
                        l1_id = graph.add_level_state(
                            level=1,
                            output_value=l1_summary,
                            data_artifact=l1_combined,  # Store actual values, not just counts
                            metadata=l1_metadata
                        )
                        graph.add_transition(prev_id, l1_id, "descend", {"operation": "extract"})
                        prev_id = l1_id

                    # Add L0 (computed results) if exists
                    if 'l0' in st.session_state.datasets:
                        l0_data = st.session_state.datasets['l0']
                        l0_metadata = {
                            "decision_description": f"Computed {st.session_state.answers.get('aggregation', 'metric')}",
                            "aggregation": st.session_state.answers.get('aggregation', 'unknown')
                        }
                        # Get L0 values
                        l0_values = {}
                        for cat, ds in l0_data.items():
                            val = ds.get_data() if hasattr(ds, 'get_data') else ds
                            l0_values[cat] = val
                        l0_id = graph.add_level_state(
                            level=0,
                            output_value=l0_values,
                            data_artifact=l0_values,
                            metadata=l0_metadata
                        )
                        graph.add_transition(prev_id, l0_id, "descend", {"operation": "aggregate"})

                    # Save the graph
                    graph.export_to_json(filepath)

                st.success(f"✅ Session saved to: `{filepath}`")
                st.session_state['last_saved_graph'] = filepath

                # Show graph summary
                st.markdown(f"""
                **Graph Summary:**
                - Nodes: {graph.G.number_of_nodes()}
                - Edges: {graph.G.number_of_edges()}
                - Current Level: L{graph.G.nodes[graph.current_id]['level'] if graph.current_id else '?'}
                """)
            except Exception as e:
                import traceback
                st.error(f"Failed to save session graph: {e}")
                st.code(traceback.format_exc())
    else:
        st.warning("No active session data to save. Complete the workflow first.")


# ============================================================================
# FREE NAVIGATION MODE (002-ascent-functionality)
# ============================================================================

def init_free_navigation():
    """Initialize a free navigation session with tree support."""
    # Check if we have a loaded session graph
    if st.session_state.get('loaded_session_graph'):
        return True

    if st.session_state.raw_data is None:
        st.error("Please upload data first in the guided workflow")
        return False

    if st.session_state.nav_session is None:
        l4_dataset = Level4Dataset(st.session_state.raw_data)
        st.session_state.nav_session = NavigationSession(l4_dataset, use_tree=True)
        st.session_state.relationship_builder = DragDropRelationshipBuilder()

    return True


def render_session_graph_loader():
    """Render the session graph file uploader for Free Exploration mode."""
    st.subheader("📂 Load Saved Session")
    st.info(
        "Upload a session graph file to continue from a previous descent. "
        "This restores your L0 results for the ascent phase."
    )

    uploaded_file = st.file_uploader(
        "Load Session Graph (.json)",
        type=['json'],
        key='session_graph_upload'
    )

    if uploaded_file is not None:
        import tempfile
        import os

        try:
            # Save to temp file
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False) as f:
                f.write(uploaded_file.getvalue())
                temp_path = f.name

            # Load the session graph
            session_data = NavigationSession.load_graph(temp_path)

            # Clean up temp file
            os.unlink(temp_path)

            # Store in session state
            st.session_state['loaded_session_graph'] = session_data
            st.session_state['loaded_graph_decisions'] = session_data['decisions']

            st.success("✅ Session graph loaded successfully!")

            # Show summary
            st.markdown("**Loaded Session Summary:**")
            accumulated = session_data['accumulated_outputs']

            for level in sorted(accumulated.keys(), reverse=True):
                level_data = accumulated[level]
                st.markdown(f"- **L{level}**: {level_data.get('row_count', '?')} items - {level_data.get('decision_description', '')[:50]}")

            # Show decisions path
            st.markdown("**Navigation Path:**")
            for decision in session_data['decisions']:
                action = decision.get('action', 'entry')
                desc = decision.get('decision_description', '')
                st.markdown(f"  {decision['step']}. L{decision['level']} ({action}): {desc[:40]}...")

            # Add continue button to trigger rerun with loaded state
            st.divider()
            if st.button("🚀 Continue to Free Exploration", type="primary"):
                st.rerun()

            return True

        except Exception as e:
            st.error(f"Failed to load session graph: {e}")
            return False

    return False


def render_free_navigation_sidebar():
    """Render the decision-tree sidebar for free navigation mode."""
    nav_session = st.session_state.nav_session
    if nav_session is None:
        return

    st.sidebar.divider()
    st.sidebar.markdown("### Navigation Tree")

    # Get tree visualization
    tree_viz = nav_session.get_tree_visualization()

    # Decision tree component
    decision_tree = DecisionTreeComponent()

    def on_node_click(node_id: str):
        """Handle click on a tree node for time-travel."""
        try:
            nav_session.restore(node_id)
            st.session_state.nav_action = 'restored'
        except NavigationError as e:
            st.sidebar.error(str(e))

    decision_tree.render(
        tree_viz,
        on_node_click=on_node_click,
        available_options=nav_session.get_available_options()
    )


def render_loaded_graph_view():
    """Render the view for a loaded session graph (ascent phase ready)."""
    session_data = st.session_state.get('loaded_session_graph')
    if not session_data:
        return False

    accumulated = session_data.get('accumulated_outputs', {})
    decisions = session_data.get('decisions', [])
    current_level = session_data.get('current_level', 0)
    graph = session_data.get('graph')  # SessionGraph instance

    # Track ascent progress in session state
    if 'ascent_level' not in st.session_state:
        st.session_state.ascent_level = 0  # Start at L0
    if 'ascent_l1_data' not in st.session_state:
        st.session_state.ascent_l1_data = None
    if 'ascent_l2_data' not in st.session_state:
        st.session_state.ascent_l2_data = None
    if 'ascent_l3_data' not in st.session_state:
        st.session_state.ascent_l3_data = None

    # Constitution v1.2.0: Use domain-friendly level names (French for ascent phase)
    level_names = {
        0: "Résultat calculé",
        1: "Valeurs sélectionnées",
        2: "Éléments par catégorie",
        3: "Informations connectées",
        4: "Fichiers téléchargés"
    }

    # Note: ascent progress bar is now rendered at the top of Free Exploration mode

    st.subheader(f"📊 Phase de remontée - {level_names.get(st.session_state.ascent_level, f'Niveau {st.session_state.ascent_level}')}")

    # Show L0 result prominently
    if 0 in accumulated:
        l0_data = accumulated[0]
        l0_formatted = format_l0_value_for_display(l0_data.get('output_value'))
        st.success("**Vérité terrain L0:**")
        st.markdown(l0_formatted)
        st.caption(f"Méthode de calcul: {l0_data.get('decision_description', '')}")

    st.divider()

    # Show navigation history
    with st.expander("📜 Navigation History (from descent)", expanded=False):
        for decision in decisions:
            action = decision.get('action', 'entry')
            level = decision.get('level', '?')
            desc = decision.get('decision_description', '')
            st.markdown(f"- **L{level}** ({action}): {desc[:60]}...")

    st.divider()

    # ========================================================================
    # ASCENT STEP 1: L0 → L1 (Source Recovery) - Spec Step 9
    # ========================================================================
    if st.session_state.ascent_level == 0:
        st.subheader(f"🚀 {t('step_7_recover')}")
        st.info(
            "Your L0 ground truth anchors the analysis. Now recover the source values "
            "to explore different analytical dimensions.\n\n"
            "Votre résultat L0 ancre l'analyse. Récupérez maintenant les valeurs sources "
            "pour explorer différentes dimensions analytiques."
        )

        # Get L1 data from graph
        if graph:
            l1_df = graph.get_level_data(1)
            if l1_df is not None and not l1_df.empty:
                st.metric(t("source_values_available"), f"{len(l1_df)} {t('rows_label')}")

                with st.expander(t("preview_l1_data"), expanded=False):
                    st.dataframe(l1_df.head(10))

                if st.button(f"📈 {t('recover_source_values_btn')}", type="primary", key="ascent_l0_l1"):
                    st.session_state.ascent_l1_data = l1_df
                    st.session_state.ascent_level = 1
                    st.rerun()
            else:
                st.warning(f"⚠️ {t('l1_not_found_warning')}")
        else:
            st.error(t("session_graph_unavailable"))

    # ========================================================================
    # ASCENT STEP 2: L1 → L2 (New Categorization) - Spec Step 10
    # Reuses descent categorization UI pattern (T043 fix - user feedback)
    # ========================================================================
    elif st.session_state.ascent_level == 1:
        # Back button
        if st.button(f"⬅️ {t('back_to_step_9')}", key="ascent_back_to_9"):
            st.session_state.ascent_level = 0
            st.rerun()

        st.subheader(f"📊 {t('step_8_add_dimension')}")
        l1_df = st.session_state.ascent_l1_data

        st.metric(t("current_l1_values"), f"{len(l1_df)} {t('rows_label')}")

        st.info(t("ascent_categorize_info"))

        # Get L3 data for additional columns if available
        l3_df = graph.get_level_data(3) if graph else None

        # Combine L1 columns with L3 columns for more categorization options
        available_columns = list(l1_df.columns)
        if l3_df is not None and hasattr(l3_df, 'columns'):
            # Add L3 columns that aren't already in L1
            for col in l3_df.columns:
                if col not in available_columns:
                    available_columns.append(f"{col} (from L3)")

        # Preserve original column order (T041 pattern)
        text_columns = [col for col in available_columns if 'id' not in col.lower()]

        st.divider()
        st.subheader("🎯 Define Categories")

        # Column selector (same as Step 3)
        if text_columns:
            selected_column = st.selectbox(
                "Select column to categorize by:",
                options=text_columns,
                index=0,
                help="The values in this column will be matched against your categories",
                key="ascent_column_select"
            )

            # Determine which dataframe has the column
            is_l3_column = selected_column.endswith(" (from L3)")
            actual_column = selected_column.replace(" (from L3)", "") if is_l3_column else selected_column
            source_df = l3_df if is_l3_column and l3_df is not None else l1_df

            # Show sample values and "use as categories" button
            if actual_column in source_df.columns:
                unique_values = source_df[actual_column].dropna().unique()
                unique_count = len(unique_values)

                # Quick action: Use unique values as categories
                if unique_count <= 20:
                    st.markdown(f"**🎯 Quick option: Use `{actual_column}` unique values as categories ({unique_count} categories):**")
                    st.caption(f"Unique values: {', '.join(str(v) for v in unique_values[:10])}{'...' if unique_count > 10 else ''}")
                    if st.button(f"✨ Use '{actual_column}' values as categories", key="ascent_use_unique_values"):
                        st.session_state.ascent_categories = ", ".join(str(v) for v in unique_values)
                        st.success(f"Categories set to {unique_count} unique values from '{actual_column}'")
                        st.rerun()
                else:
                    st.warning(f"Column '{actual_column}' has {unique_count} unique values (too many for automatic categories). Enter custom categories below.")

                with st.expander(f"Sample values in '{actual_column}' column ({unique_count} unique)"):
                    st.write(list(unique_values[:20]))
        else:
            st.error(t("no_suitable_columns"))
            return

        st.divider()

        # Category input (same as Step 3)
        st.markdown(f"**{t('enter_categories')}**")

        with st.expander("💡 Examples"):
            st.markdown("""
            - **Performance tiers:** `top_performers, above_average, below_average, needs_improvement`
            - **Funding size:** `above_10k, below_10k`
            - **Priority levels:** `High, Medium, Low`
            - **Custom categories:** Any comma-separated list
            """)

        # Suggest categories based on data type
        default_categories = "Category_A, Category_B"
        if actual_column in source_df.columns:
            col_dtype = source_df[actual_column].dtype
            unique_count = source_df[actual_column].nunique()
            if unique_count <= 10:
                # Use actual unique values as default
                default_categories = ", ".join(str(v) for v in source_df[actual_column].dropna().unique()[:5])

        categories_input = st.text_input(
            "Categories (comma-separated):",
            value=st.session_state.get('ascent_categories', default_categories),
            help="E.g., top_performers, above_average, below_average",
            key="ascent_categories_input"
        )

        # Smart matching toggle + threshold (same as Step 3)
        col1, col2 = st.columns(2)
        with col1:
            use_semantic = st.checkbox(
                "Use smart matching (AI)",
                value=True,
                help="Use AI to find similar values (smarter but slower)",
                key="ascent_use_semantic"
            )
        with col2:
            threshold = st.slider(
                "Matching strictness:",
                min_value=0.1,
                max_value=0.9,
                value=0.3,
                step=0.05,
                help="How strict should matching be? (higher = fewer matches)",
                key="ascent_threshold"
            )

        categories_list = [c.strip() for c in categories_input.split(",") if c.strip()]

        if categories_list and st.button("🏷️ Apply Categorization", type="primary", key="ascent_l1_l2"):
            import pandas as pd
            import numpy as np

            l2_df = l1_df.copy()

            # Add L3 column to L1 if selected from L3
            if is_l3_column and l3_df is not None and actual_column in l3_df.columns:
                if len(l2_df) == len(l3_df):
                    l2_df[actual_column] = l3_df[actual_column].values
                else:
                    st.warning(f"Row count mismatch (L1: {len(l2_df)}, L3: {len(l3_df)}). Using L1 data only.")

            # Apply categorization using semantic matching (same pattern as descent)
            if use_semantic and actual_column in l2_df.columns:
                from intuitiveness.models import get_batch_similarities
                import numpy as np

                values = l2_df[actual_column].astype(str).tolist()

                # OPTIMIZED: Batch compute similarities (not O(n*k) individual calls)
                with st.spinner("Computing semantic similarities..."):
                    # Get unique values to reduce encoding overhead
                    unique_values = list(set(v for v in values if v and str(v).strip()))

                    if unique_values and categories_list:
                        # Single batch call: encode all unique values against all categories
                        # Returns similarity matrix [len(unique_values) x len(categories)]
                        similarity_matrix = get_batch_similarities(unique_values, categories_list)

                        # Build lookup: value -> best category
                        value_to_category = {}
                        for i, val in enumerate(unique_values):
                            if similarity_matrix is not None and len(similarity_matrix) > i:
                                row = similarity_matrix[i]
                                if isinstance(row, (list, np.ndarray)) and len(row) > 0:
                                    best_idx = int(np.argmax(row))
                                    best_score = row[best_idx] if isinstance(row[best_idx], (int, float)) else float(row[best_idx])
                                    if best_score > threshold:
                                        value_to_category[val] = categories_list[best_idx]
                                    else:
                                        value_to_category[val] = 'uncategorized'
                                else:
                                    value_to_category[val] = 'uncategorized'
                            else:
                                value_to_category[val] = 'uncategorized'

                        # Map all values using the lookup
                        assignments = [value_to_category.get(str(v).strip(), 'uncategorized') if v and str(v).strip() else 'uncategorized' for v in values]
                    else:
                        assignments = ['uncategorized'] * len(values)

                    l2_df['ascent_category'] = assignments
            else:
                # Direct matching without AI
                def match_category(value):
                    val_str = str(value).lower().strip()
                    for cat in categories_list:
                        if cat.lower() in val_str or val_str in cat.lower():
                            return cat
                    return 'uncategorized'

                if actual_column in l2_df.columns:
                    l2_df['ascent_category'] = l2_df[actual_column].apply(match_category)
                else:
                    l2_df['ascent_category'] = 'uncategorized'

            # Show results
            cat_counts = l2_df['ascent_category'].value_counts().to_dict()
            result_parts = [f"{cat}={count}" for cat, count in cat_counts.items()]
            st.success(f"✅ Applied categories: {', '.join(result_parts)}")

            # Add location column from L3 if available (like descent does)
            if l3_df is not None and 'Commune' in l3_df.columns and 'Commune' not in l2_df.columns:
                if len(l2_df) == len(l3_df):
                    l2_df['Commune'] = l3_df['Commune'].values
                    st.info(f"📍 Added Commune location ({l2_df['Commune'].nunique()} unique)")

            st.session_state.ascent_l2_data = l2_df
            st.session_state.ascent_categories = categories_input
            st.session_state.ascent_level = 2
            st.rerun()

        with st.expander("Preview L1 Data", expanded=False):
            st.dataframe(l1_df.head(10))

    # ========================================================================
    # ASCENT STEP 3: L2 → L3 (Table Enrichment) - Spec Step 11
    # ========================================================================
    elif st.session_state.ascent_level == 2:
        # Back button
        if st.button(f"⬅️ {t('back_to_step_10')}", key="ascent_back_to_10"):
            st.session_state.ascent_level = 1
            st.rerun()

        st.subheader(f"🔗 {t('step_9_linkage')}")
        l2_df = st.session_state.ascent_l2_data

        # Show current L2 state - find the category column
        # 'ascent_category' is created by Step 10, others are from descent flow
        category_col = None
        for col in ['ascent_category', 'score_quartile', 'performance_category', 'funding_size', 'value_category']:
            if col in l2_df.columns:
                category_col = col
                break

        if category_col:
            categories = l2_df[category_col].value_counts().to_dict()
            st.metric("L2 Categories", f"{len(categories)} categories")
            st.markdown(f"**Dimension: {category_col}**")
            for cat, count in categories.items():
                st.write(f"  - **{cat}**: {count} {t('rows_label')}")
        else:
            st.warning(t("no_category_column"))

        # Show Commune location if present
        if 'Commune' in l2_df.columns:
            st.info(f"📍 {l2_df['Commune'].nunique()} unique Communes")

        # Show L2 dataframe prominently (user feedback 2025-12-12)
        st.markdown(f"**📊 {t('current_l2_table')}**")
        st.dataframe(l2_df, use_container_width=True, height=300)

        st.divider()

        # Explanation of what linkage keys are
        st.markdown(f"""
        ---
        **🔗 {t('what_are_linkage_keys')}**

        {t('linkage_keys_description')}
        - {t('postal_codes_link')}
        - {t('commune_names_link')}
        - {t('uai_codes_link')}
        ---
        """)

        # Get L3 data for column selection
        l3_df_preview = None
        available_columns = []
        linkage_candidates = []

        if graph:
            l3_df_preview = graph.get_level_data(3)
            if l3_df_preview is not None and not l3_df_preview.empty:
                available_columns = list(l3_df_preview.columns)
                # Identify potential linkage key columns
                for col in available_columns:
                    col_lower = col.lower()
                    if any(key in col_lower for key in ['postal', 'code', 'commune', 'cp', 'département', 'region', 'uai', 'objet']):
                        linkage_candidates.append(col)

        st.markdown(f"**{t('available_columns_from_datasets', count=len(available_columns))}**")

        # Show linkage key selection with improved UX
        if linkage_candidates:
            st.markdown(f"**🔗 {t('select_linkage_key_columns')}**")
            st.caption(t("auto_detected_caption"))
            selected_linkage_cols = st.multiselect(
                t("select_columns_linkage"),
                options=linkage_candidates,
                default=linkage_candidates[:3] if len(linkage_candidates) >= 3 else linkage_candidates,
                key="ascent_linkage_cols",
                help=t("columns_for_joins_help")
            )
        else:
            st.info(f"💡 {t('no_linkage_detected')}")
            # Allow user to select any column as linkage key
            selected_linkage_cols = st.multiselect(
                t("select_columns_linkage"),
                options=available_columns,
                default=[],
                key="ascent_linkage_cols_fallback",
                help=t("choose_unique_identifiers_help")
            )

        # Show available columns preview
        with st.expander(f"📋 {t('all_available_columns', count=len(available_columns))}", expanded=False):
            col_cols = st.columns(3)
            for i, col in enumerate(sorted(available_columns)):
                with col_cols[i % 3]:
                    st.text(col[:40] + "..." if len(col) > 40 else col)

        if st.button(f"✨ {t('complete_enrichment')}", type="primary", key="ascent_l2_l3"):
            # Get L3 data from graph and merge with new categorization
            if graph:
                l3_df = graph.get_level_data(3)
                if l3_df is not None and not l3_df.empty:
                    # Merge L2 categorization into L3
                    # Find the category column and add it to L3
                    # 'ascent_category' is created by Step 10, others are from descent flow
                    category_col = None
                    for col in ['ascent_category', 'score_quartile', 'performance_category', 'funding_size', 'value_category']:
                        if col in l2_df.columns:
                            category_col = col
                            break

                    if category_col:
                        # Handle row count mismatch by using reset index or broadcasting
                        if len(l2_df) == len(l3_df):
                            l3_df[category_col] = l2_df[category_col].values
                        else:
                            # L2 is grouped data - need to broadcast based on original L3
                            st.warning(t("row_count_mismatch", l2=len(l2_df), l3=len(l3_df)))
                            # For grouped ascent, just add the category column with a default
                            l3_df[category_col] = 'categorized'

                    # Store selected linkage columns for display
                    st.session_state.ascent_selected_linkage_cols = selected_linkage_cols if selected_linkage_cols else linkage_candidates

                    st.session_state.ascent_l3_data = l3_df
                    st.session_state.ascent_level = 3
                    st.success(f"✅ {t('enriched_l3_success', rows=len(l3_df), cols=len(l3_df.columns))}")
                    if selected_linkage_cols:
                        st.info(f"🔗 {t('linkage_keys_selected')}: {', '.join(selected_linkage_cols)}")
                    st.rerun()
                else:
                    st.error(t("l3_data_not_found"))
            else:
                st.error(t("session_graph_unavailable"))

    # ========================================================================
    # ASCENT COMPLETE: Show L3 Result - Spec Step 12
    # ========================================================================
    elif st.session_state.ascent_level == 3:
        # Back button
        if st.button(f"⬅️ {t('back_to_step_11')}", key="ascent_back_to_11"):
            st.session_state.ascent_level = 2
            st.rerun()

        st.subheader(f"🎉 {t('step_10_verification')} - {t('ascent_completed')}")
        l3_df = st.session_state.ascent_l3_data
        l2_df = st.session_state.get('ascent_l2_data')

        st.success(f"**{t('enriched_l3_table')}**: {len(l3_df)} {t('rows_label')} × {len(l3_df.columns)} {t('columns_label')}")

        col1, col2 = st.columns(2)
        with col1:
            st.metric(t("rows_metric"), len(l3_df))
        with col2:
            st.metric(t("columns_metric"), len(l3_df.columns))

        # Show the new dimension column
        category_col = None
        for col in ['ascent_category', 'score_quartile', 'performance_category', 'funding_size', 'value_category']:
            if col in l3_df.columns:
                category_col = col
                break

        if category_col:
            st.markdown(f"**{t('new_dimension_label', column=category_col)}**")
            st.write(l3_df[category_col].value_counts().to_dict())

        # Show selected linkage keys prominently (from Step 11 selection)
        selected_linkage_cols = st.session_state.get('ascent_selected_linkage_cols', [])
        if selected_linkage_cols:
            st.markdown(f"**🔗 {t('selected_linkage_keys_label')}**")
            for col in selected_linkage_cols:
                if col in l3_df.columns:
                    unique_count = l3_df[col].nunique()
                    st.write(f"  - **{col}**: {t('unique_values_count', count=unique_count)}")
        else:
            # Fallback to auto-detected linkage keys
            linkage_cols = []
            for col in l3_df.columns:
                col_lower = col.lower()
                if 'postal' in col_lower or 'commune' in col_lower or 'cp' == col_lower:
                    linkage_cols.append(col)
            if linkage_cols:
                st.markdown(f"**🔗 {t('demographic_linkage_keys_label')}**")
                for col in linkage_cols:
                    unique_count = l3_df[col].nunique() if col in l3_df.columns else 0
                    st.write(f"  - **{col}**: {t('unique_values_count', count=unique_count)}")

        st.divider()

        # Build simplified view: L2 columns + selected linkage columns only (user feedback 2025-12-12)
        st.markdown(f"**📊 {t('simplified_l3_view')}**")
        st.caption(t("simplified_l3_caption"))

        # Determine columns to show in simplified view
        simplified_cols = []
        if l2_df is not None:
            simplified_cols = list(l2_df.columns)
        if selected_linkage_cols:
            for col in selected_linkage_cols:
                if col not in simplified_cols and col in l3_df.columns:
                    simplified_cols.append(col)

        if simplified_cols:
            # Create simplified dataframe
            simplified_cols_available = [c for c in simplified_cols if c in l3_df.columns]
            simplified_df = l3_df[simplified_cols_available]
            st.dataframe(simplified_df, use_container_width=True, height=400)
            st.caption(t("showing_columns_of_total", count=len(simplified_cols_available), total=len(l3_df.columns)))
        else:
            # Fallback to full L3 if no L2 data
            st.dataframe(l3_df.head(20), use_container_width=True, height=400)

        with st.expander(f"📋 {t('full_l3_table', count=len(l3_df.columns))}", expanded=False):
            st.dataframe(l3_df)

        with st.expander(t("all_columns"), expanded=False):
            st.write(list(l3_df.columns))

        # Export ascent artifacts
        st.markdown("---")
        st.subheader(f"📥 {t('export_ascent_artifacts')}")
        export_col1, export_col2, export_col3 = st.columns(3)

        with export_col1:
            if st.session_state.get('ascent_l1_data') is not None:
                l1_csv_bytes = st.session_state.ascent_l1_data.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=f"📥 {t('download_l1_values')}",
                    data=l1_csv_bytes,
                    file_name="ascent_L1_values.csv",
                    mime="text/csv",
                    key="export_ascent_l1",
                    type="primary"
                )

        with export_col2:
            if st.session_state.get('ascent_l2_data') is not None:
                l2_csv_bytes = st.session_state.ascent_l2_data.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=f"📥 {t('download_l2_categorized')}",
                    data=l2_csv_bytes,
                    file_name="ascent_L2_categorized.csv",
                    mime="text/csv",
                    key="export_ascent_l2",
                    type="primary"
                )

        with export_col3:
            l3_csv_bytes = l3_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📥 {t('download_l3_enriched')}",
                data=l3_csv_bytes,
                file_name="ascent_L3_enriched.csv",
                mime="text/csv",
                key="export_ascent_l3",
                type="primary"
            )

        # Continue exploration options (user feedback 2025-12-12)
        st.divider()
        st.subheader(f"🚀 {t('continue_exploration')}")
        st.info(t("ascent_complete_info"))

        continue_col1, continue_col2, continue_col3 = st.columns(3)

        with continue_col1:
            if st.button(f"🔄 {t('try_different_dimension')}", key="try_different_dimension", type="secondary"):
                # Go back to L1→L2 to try a different categorization
                st.session_state.ascent_level = 1
                st.session_state.ascent_l2_data = None
                st.session_state.ascent_l3_data = None
                st.rerun()

        with continue_col2:
            if st.button(f"🔗 {t('try_different_linkage')}", key="try_different_linkage", type="secondary"):
                # Go back to L2→L3 to try different linkage columns
                st.session_state.ascent_level = 2
                st.session_state.ascent_l3_data = None
                st.rerun()

        with continue_col3:
            if st.button(f"🔄 {t('start_new_ascent')}", key="reset_ascent"):
                st.session_state.ascent_level = 0
                st.session_state.ascent_l1_data = None
                st.session_state.ascent_l2_data = None
                st.session_state.ascent_l3_data = None
                st.rerun()

    return True


def render_free_navigation_main():
    """Render the main content area for free navigation mode."""
    # Check for loaded session graph first
    if st.session_state.get('loaded_session_graph'):
        render_loaded_graph_view()
        return

    nav_session = st.session_state.nav_session
    if nav_session is None:
        if not init_free_navigation():
            return
        nav_session = st.session_state.nav_session

    # Header
    current_level = nav_session.current_level
    # Constitution v1.2.0: Use domain-friendly level names
    level_names = {
        0: "Your Computed Result",
        1: "Your Selected Values",
        2: "Items by Category",
        3: "Connected Information",
        4: "Your Uploaded Files"
    }

    # Constitution v1.2.0: Use domain-friendly labels
    st.subheader(f"Current View: {level_names.get(current_level.value, current_level.name)}")

    # Display current data
    render_current_data(nav_session)

    st.divider()

    # Exploration options
    st.subheader("What would you like to do?")
    options = nav_session.get_available_options()

    cols = st.columns(len(options))

    for i, option in enumerate(options):
        with cols[i]:
            action = option["action"]
            description = option["description"]

            if action == "exit":
                if st.button(f"Exit: {description}", key=f"nav_exit_{i}", type="secondary"):
                    handle_exit_action(nav_session)

            elif action == "descend":
                # Constitution v1.2.0: Use domain-friendly labels
                target = option.get("target_level", "")
                if st.button(f"🔍 Explore deeper to {target}", key=f"nav_descend_{i}"):
                    st.session_state.nav_action = 'descend'
                    st.session_state.nav_target = target

                # Show form if this descend action is active
                if st.session_state.nav_action == 'descend' and st.session_state.nav_target == target:
                    render_descend_options(nav_session, target)

            elif action == "ascend":
                # Constitution v1.2.0: Use domain-friendly labels
                target = option.get("target_level", "")
                if st.button(f"🔨 Build up to {target}", key=f"nav_ascend_{i}", type="primary"):
                    st.session_state.nav_action = 'ascend'
                    st.session_state.nav_target = target

                # Show form if this ascend action is active
                if st.session_state.nav_action == 'ascend' and st.session_state.nav_target == target:
                    render_ascend_options(nav_session, target, option)


def render_free_nav_graph(G, node_types: dict):
    """Render graph visualization for Free Navigation mode using same approach as Guided mode."""
    import matplotlib.pyplot as plt

    # Type colors
    type_colors = {
        'Source': '#E74C3C',
        'College': '#3498DB',
        'Students': '#2ECC71',
        'StudentEnrollment': '#2ECC71',
        'Performance': '#9B59B6',
        'SchoolPerformance': '#9B59B6',
        'Indicator': '#1ABC9C',
        'Beneficiary': '#F39C12',
        'Project': '#E91E63',
        'Funding': '#00BCD4',
        'Commune': '#FF5722',
        'EnergyPrice': '#795548',
        'EnergyExchange': '#607D8B',
        'BusinessDomain': '#F39C12',
        'Unknown': '#95A5A6'
    }

    max_nodes = 50

    # Calculate dm_degree (exclude FROM_SOURCE and HAS_SOURCE edges)
    node_dm_degrees = {}
    node_degrees = dict(G.degree())

    for node in G.nodes():
        dm_degree = 0
        for neighbor in G.neighbors(node):
            edge_data = G.get_edge_data(node, neighbor)
            if edge_data:
                edge_type = edge_data.get('type', '')
                if edge_type not in ['FROM_SOURCE', 'HAS_SOURCE']:
                    dm_degree += 1
        node_dm_degrees[node] = dm_degree

    if G.number_of_nodes() > max_nodes:
        sorted_nodes = sorted(node_dm_degrees.items(), key=lambda x: x[1], reverse=True)
        seed_count = max(10, max_nodes // 3)
        seed_nodes = set(node for node, degree in sorted_nodes[:seed_count])

        nodes_to_include = set(seed_nodes)
        for seed in seed_nodes:
            for neighbor in G.successors(seed):
                edge_type = G.get_edge_data(seed, neighbor, {}).get('type', '')
                if edge_type not in ['FROM_SOURCE', 'HAS_SOURCE']:
                    nodes_to_include.add(neighbor)
            for neighbor in G.predecessors(seed):
                edge_type = G.get_edge_data(neighbor, seed, {}).get('type', '')
                if edge_type not in ['FROM_SOURCE', 'HAS_SOURCE']:
                    nodes_to_include.add(neighbor)

        if len(nodes_to_include) > max_nodes * 2:
            neighbor_only = nodes_to_include - seed_nodes
            sorted_neighbors = sorted(neighbor_only, key=lambda n: node_dm_degrees.get(n, 0), reverse=True)
            nodes_to_include = seed_nodes | set(sorted_neighbors[:max_nodes - seed_count])

        subgraph = G.subgraph(nodes_to_include).copy()
        edges_to_remove = [(u, v) for u, v, d in subgraph.edges(data=True) if d.get('type') in ['FROM_SOURCE', 'HAS_SOURCE']]
        subgraph.remove_edges_from(edges_to_remove)
    else:
        subgraph = G.copy()
        edges_to_remove = [(u, v) for u, v, d in subgraph.edges(data=True) if d.get('type') in ['FROM_SOURCE', 'HAS_SOURCE']]
        subgraph.remove_edges_from(edges_to_remove)

    fig, ax = plt.subplots(figsize=(10, 8))

    node_colors = []
    node_sizes = []
    labels = {}

    degrees_in_subgraph = [node_degrees.get(n, 1) for n in subgraph.nodes()]
    min_deg = min(degrees_in_subgraph) if degrees_in_subgraph else 1
    max_deg = max(degrees_in_subgraph) if degrees_in_subgraph else 1
    deg_range = max_deg - min_deg if max_deg > min_deg else 1

    for node in subgraph.nodes():
        attrs = subgraph.nodes[node]
        ntype = attrs.get('type', 'Unknown')
        node_colors.append(type_colors.get(ntype, type_colors['Unknown']))

        degree = node_degrees.get(node, 1)
        if ntype == 'Source':
            node_sizes.append(1000)
        else:
            normalized = (degree - min_deg) / deg_range
            node_sizes.append(200 + normalized * 600)

        name = attrs.get('name', str(node))
        labels[node] = name[:12] + '...' if len(name) > 12 else name

    if subgraph.number_of_nodes() > 0:
        pos = nx.spring_layout(subgraph, k=2, iterations=50, seed=42)
        nx.draw_networkx_edges(subgraph, pos, ax=ax, edge_color='#CCCCCC', arrows=True, arrowsize=12, alpha=0.6)
        nx.draw_networkx_nodes(subgraph, pos, ax=ax, node_color=node_colors, node_size=node_sizes, alpha=0.9)
        nx.draw_networkx_labels(subgraph, pos, labels, ax=ax, font_size=7, font_weight='bold')

    ax.set_title(f"Knowledge Graph: {subgraph.number_of_nodes()} Nodes, {subgraph.number_of_edges()} Entity Relationships")
    ax.axis('off')
    plt.tight_layout()

    st.pyplot(fig)
    plt.close(fig)


def render_current_data(nav_session: NavigationSession):
    """Display the current dataset based on level.

    FR-014: Uses shared display functions for consistency with Guided Mode.
    """
    current_level = nav_session.current_level
    data = nav_session.current_dataset.get_data()

    if current_level.value == 0:  # L0
        # Use shared L0 datum display (FR-014)
        render_l0_datum(
            data,
            aggregation_method=nav_session.current_dataset.description or "computed",
            source_info=None
        )

    elif current_level.value == 1:  # L1
        # Use shared L1 vector display (FR-014)
        # Level1Dataset uses 'name' attribute, not 'description'
        column_name = getattr(nav_session.current_dataset, 'name', None) or "vector"
        render_l1_vector(
            data,
            column_name=column_name
        )

    elif current_level.value == 2:  # L2
        # Use shared L2 domain table display (FR-014)
        if hasattr(data, 'head'):
            render_l2_domain_table({"Current Table": data})
        else:
            st.write("**Table Data:**")
            st.dataframe(data, use_container_width=True)

    elif current_level.value == 3:  # L3
        st.write("**Graph Data:**")
        if hasattr(data, 'number_of_nodes'):
            G = data
            col1, col2 = st.columns([2, 1])

            with col2:
                st.markdown("**Graph Statistics:**")
                st.metric("Nodes", G.number_of_nodes())
                st.metric("Edges", G.number_of_edges())

                # Node types
                node_types = {}
                for _, attrs in G.nodes(data=True):
                    t = attrs.get('type', 'Unknown')
                    node_types[t] = node_types.get(t, 0) + 1
                st.markdown("**Node Types:**")
                for ntype, count in node_types.items():
                    st.write(f"- {ntype}: {count}")

            with col1:
                # Visualization using same approach as Guided mode
                render_free_nav_graph(G, node_types)

            # Use shared entity/relationship tabs display (FR-014)
            st.divider()
            entity_tabs_data = extract_entity_tabs(G)
            relationship_tabs_data = extract_relationship_tabs(G)
            render_entity_relationship_tabs(
                entity_tabs_data,
                relationship_tabs_data,
                graph=G,
                max_rows=50,
                show_summary=True
            )

        elif hasattr(data, 'shape'):
            st.dataframe(data.head(50), use_container_width=True)

    elif current_level.value == 4:  # L4
        # Use shared L4 file list display (FR-014)
        if isinstance(data, dict):
            files_data = [
                {
                    "name": name,
                    "dataframe": df,
                    "rows": df.shape[0],
                    "columns": df.shape[1]
                }
                for name, df in data.items()
            ]
            render_l4_file_list(files_data, show_preview=True, max_preview_rows=5)
        else:
            st.write("**Raw Sources:**")
            st.write(data)


def render_descend_options(nav_session: NavigationSession, target: str):
    """Render options for descending to a lower level.

    FR-013: Show navigation direction indicator.
    """
    current_level = nav_session.current_level
    source_level = current_level.value
    target_level = source_level - 1  # Descent goes to lower level

    # Show navigation direction indicator (FR-013)
    render_navigation_direction_indicator(
        NavigationDirection.DESCEND,
        source_level,
        target_level
    )

    st.write(f"**Configure descent to {target}**")

    params = {}

    if current_level.value == 4:  # L4 -> L3
        # Multi-step descent workflow
        if st.session_state.nav_descend_step == 1:
            # Step 1: Define entities - OUTSIDE form so selectbox updates dynamically
            st.markdown("""
            Define the **entities** that will become nodes in your knowledge graph.
            """)

            # Entity input - outside form for immediate updates
            default_entities = st.session_state.get('free_nav_entities_value', "Indicator, Source, BusinessDomain")
            entities_input = st.text_input(
                "Enter entities (comma-separated):",
                value=default_entities,
                key="free_nav_entities_input"
            )
            # Store the value for persistence
            st.session_state.free_nav_entities_value = entities_input

            entities_list = [e.strip() for e in entities_input.split(",") if e.strip()]

            # Core entity selection - now updates immediately when entities change
            core_entity = None
            if entities_list:
                core_entity = st.selectbox(
                    "Select the core/central entity:",
                    options=entities_list,
                    key="free_nav_core_entity_select"
                )

            # Generate Data Model button - using regular button, not form
            if st.button("Generate Data Model", key="free_nav_generate_model_btn"):
                if entities_list and core_entity:
                    # Generate the data model
                    data_model = DataModelGenerator.generate_from_entities(
                        entities=entities_list,
                        core_entity=core_entity,
                        source_data=nav_session.current_dataset.get_data()
                    )
                    st.session_state.nav_temp_data_model = data_model
                    st.session_state.nav_descend_step = 2
                    st.rerun()
                else:
                    st.error("Please define entities and select a core entity")
            return  # Don't show Descend button yet

        elif st.session_state.nav_descend_step == 2:
            # Step 2: Entity mapping and relationship config - NO FORM for dynamic updates
            # Step 2: Show data model preview with Entity and Relationship mapping
            data_model = st.session_state.nav_temp_data_model
            raw_data = nav_session.current_dataset.get_data()

            if data_model:
                st.markdown("### 📦 Generated Data Model")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Nodes:**")
                    for node in data_model.nodes:
                        props = ", ".join([p['name'] for p in node.properties])
                        st.code(f"({node.label}) Key: {node.key_property} Props: {props}")

                with col2:
                    st.markdown("**Relationships:**")
                    for rel in data_model.relationships:
                        st.code(f"(:{rel.start_node_label})-[:{rel.type}]->(:{rel.end_node_label})")

                # Initialize nav entity mapping in session state
                if 'nav_entity_mapping' not in st.session_state:
                    st.session_state.nav_entity_mapping = {}
                if 'nav_relationship_mapping' not in st.session_state:
                    st.session_state.nav_relationship_mapping = {}

                # ========== ENTITY MAPPING SECTION ==========
                st.markdown("### 📦 Entity Mapping")
                st.caption("Map each entity from the data model to a CSV file and columns")

                file_options = list(raw_data.keys())

                for node in data_model.nodes:
                    entity_label = node.label
                    st.markdown(f"**{entity_label}**")

                    ecol1, ecol2, ecol3 = st.columns([1, 1, 1])

                    with ecol1:
                        current_file = st.session_state.nav_entity_mapping.get(entity_label, {}).get('source_file', file_options[0] if file_options else None)
                        file_idx = file_options.index(current_file) if current_file in file_options else 0
                        source_file = st.selectbox(
                            f"Source File",
                            options=file_options,
                            index=file_idx,
                            key=f"nav_entity_file_{entity_label}"
                        )

                    if source_file and source_file in raw_data:
                        df = raw_data[source_file]
                        col_options = list(df.columns)

                        with ecol2:
                            current_key = st.session_state.nav_entity_mapping.get(entity_label, {}).get('key_column', col_options[0] if col_options else None)
                            key_idx = col_options.index(current_key) if current_key in col_options else 0
                            key_column = st.selectbox(
                                f"Key Column (unique ID)",
                                options=col_options,
                                index=key_idx,
                                key=f"nav_entity_key_{entity_label}"
                            )

                        with ecol3:
                            if key_column:
                                sample_vals = df[key_column].dropna().head(3).tolist()
                                st.caption(f"Sample: {', '.join(str(v)[:15] for v in sample_vals)}")

                        # Update session state
                        st.session_state.nav_entity_mapping[entity_label] = {
                            'source_file': source_file,
                            'key_column': key_column
                        }

                # ========== RELATIONSHIP MAPPING SECTION ==========
                if data_model.relationships:
                    st.markdown("### 🔗 Relationship Mapping")
                    st.caption("Define how entities connect: Key Matching or Semantic Similarity")

                    for rel in data_model.relationships:
                        rel_key = f"{rel.start_node_label}_{rel.type}_{rel.end_node_label}"
                        st.markdown(f"**{rel.start_node_label}** -[{rel.type}]-> **{rel.end_node_label}**")

                        rcol1, rcol2 = st.columns(2)

                        with rcol1:
                            current_mode = st.session_state.nav_relationship_mapping.get(rel_key, {}).get('mode', 'key_matching')
                            mode = st.radio(
                                "Mode",
                                options=['key_matching', 'semantic'],
                                index=0 if current_mode == 'key_matching' else 1,
                                key=f"nav_rel_mode_{rel_key}",
                                horizontal=True
                            )

                        if mode == 'key_matching':
                            start_file = st.session_state.nav_entity_mapping.get(rel.start_node_label, {}).get('source_file')
                            end_file = st.session_state.nav_entity_mapping.get(rel.end_node_label, {}).get('source_file')

                            kcol1, kcol2 = st.columns(2)

                            with kcol1:
                                if start_file and start_file in raw_data:
                                    start_cols = list(raw_data[start_file].columns)
                                    start_key_col = st.selectbox(
                                        f"Join column in {rel.start_node_label}",
                                        options=start_cols,
                                        key=f"nav_rel_start_{rel_key}"
                                    )
                                else:
                                    start_key_col = None
                                    st.warning(f"Map {rel.start_node_label} first")

                            with kcol2:
                                if end_file and end_file in raw_data:
                                    end_cols = list(raw_data[end_file].columns)
                                    end_key_col = st.selectbox(
                                        f"Join column in {rel.end_node_label}",
                                        options=end_cols,
                                        key=f"nav_rel_end_{rel_key}"
                                    )
                                else:
                                    end_key_col = None
                                    st.warning(f"Map {rel.end_node_label} first")

                            st.session_state.nav_relationship_mapping[rel_key] = {
                                'mode': 'key_matching',
                                'start_key_column': start_key_col,
                                'end_key_column': end_key_col
                            }
                        else:
                            threshold = st.slider(
                                "Similarity Threshold",
                                min_value=0.5,
                                max_value=1.0,
                                value=0.8,
                                step=0.05,
                                key=f"nav_rel_thresh_{rel_key}"
                            )
                            st.session_state.nav_relationship_mapping[rel_key] = {
                                'mode': 'semantic',
                                'threshold': threshold
                            }

            def build_graph_with_mapping(data, data_model, entity_mapping, relationship_mapping):
                """Build knowledge graph using entity and relationship mapping."""
                G = nx.DiGraph()
                entity_nodes = {node.label: {} for node in data_model.nodes}

                # Create nodes from entity mapping
                for entity_label, mapping in entity_mapping.items():
                    source_file = mapping.get('source_file')
                    key_column = mapping.get('key_column')

                    if not source_file or source_file not in data:
                        continue

                    df = data[source_file]
                    if key_column not in df.columns:
                        continue

                    # Find name column (first string column after key)
                    name_col = key_column
                    for col in df.columns:
                        if col != key_column and df[col].dtype == 'object':
                            name_col = col
                            break

                    for idx, row in df.iterrows():
                        key_value = str(row.get(key_column, '')).strip()
                        if not key_value or key_value == 'nan':
                            continue

                        entity_id = f"{entity_label}_{key_value}"
                        entity_name = str(row.get(name_col, key_value))

                        node_attrs = {
                            'type': entity_label,
                            'name': entity_name,
                            'source_file': source_file,
                            key_column: key_value
                        }

                        for col in df.columns:
                            if col not in [key_column, name_col]:
                                node_attrs[col] = row[col]

                        G.add_node(entity_id, **node_attrs)
                        entity_nodes[entity_label][key_value] = entity_id

                # Create relationships from relationship mapping
                for rel in data_model.relationships:
                    rel_key = f"{rel.start_node_label}_{rel.type}_{rel.end_node_label}"
                    rel_config = relationship_mapping.get(rel_key, {})

                    start_entities = entity_nodes.get(rel.start_node_label, {})
                    end_entities = entity_nodes.get(rel.end_node_label, {})

                    if not start_entities or not end_entities:
                        continue

                    mode = rel_config.get('mode', 'key_matching')

                    if mode == 'key_matching':
                        start_key_col = rel_config.get('start_key_column')
                        end_key_col = rel_config.get('end_key_column')

                        start_file = entity_mapping.get(rel.start_node_label, {}).get('source_file')
                        end_file = entity_mapping.get(rel.end_node_label, {}).get('source_file')

                        if not all([start_key_col, end_key_col, start_file, end_file]):
                            continue

                        start_df = data.get(start_file)
                        end_df = data.get(end_file)

                        if start_df is None or end_df is None:
                            continue

                        # Build lookup
                        end_entity_key_col = entity_mapping.get(rel.end_node_label, {}).get('key_column')
                        end_lookup = {}
                        for _, row in end_df.iterrows():
                            join_val = str(row.get(end_key_col, '')).strip()
                            entity_key = str(row.get(end_entity_key_col, '')).strip()
                            if join_val and entity_key:
                                node_id = f"{rel.end_node_label}_{entity_key}"
                                if node_id in G:
                                    if join_val not in end_lookup:
                                        end_lookup[join_val] = []
                                    end_lookup[join_val].append(node_id)

                        # Create edges
                        start_entity_key_col = entity_mapping.get(rel.start_node_label, {}).get('key_column')
                        for _, row in start_df.iterrows():
                            join_val = str(row.get(start_key_col, '')).strip()
                            entity_key = str(row.get(start_entity_key_col, '')).strip()
                            if join_val and entity_key:
                                start_node_id = f"{rel.start_node_label}_{entity_key}"
                                if start_node_id in G and join_val in end_lookup:
                                    for end_node_id in end_lookup[join_val]:
                                        if not G.has_edge(start_node_id, end_node_id):
                                            G.add_edge(start_node_id, end_node_id,
                                                       type=rel.type, label=rel.type, matched_value=join_val)

                return G

            params['builder_func'] = lambda data: build_graph_with_mapping(
                data,
                st.session_state.nav_temp_data_model,
                st.session_state.nav_entity_mapping,
                st.session_state.nav_relationship_mapping
            )
            params['_reset_step'] = True

            # Button to explore deeper (no form needed) - Constitution v1.2.0
            if st.button("🔍 Explore Connected Information", key="nav_descend_graph_btn"):
                try:
                    reset_step = params.pop('_reset_step', False)
                    nav_session.descend(**params)
                    st.success(f"Now viewing {target}")
                    st.session_state.nav_action = None
                    st.session_state.nav_target = None
                    if reset_step:
                        st.session_state.nav_descend_step = 1
                        st.session_state.nav_temp_data_model = None
                    st.rerun()
                except NavigationError as e:
                    st.error(str(e))

    elif current_level.value == 3:  # L3 -> L2
        # Initialize L3→L2 descend step in session state if not present
        if 'nav_l3_descend_step' not in st.session_state:
            st.session_state.nav_l3_descend_step = 1

        graph = nav_session.current_dataset.get_data()

        # Extract entity data from graph for domain categorization
        entity_tabs_data = extract_entity_tabs(graph)

        if not entity_tabs_data:
            st.warning("No entity nodes found in the graph.")
            return

        # Build entities_by_type dict
        entities_by_type = {
            tab.entity_type: tab.data
            for tab in entity_tabs_data
        }
        entity_type_names = [tab.entity_type for tab in entity_tabs_data]

        st.markdown("### 🎯 Define Domain Categories")
        st.markdown("Choose an entity type and column for domain categorization.")

        # Entity type selector (outside form for dynamic updates)
        selected_entity_type = st.selectbox(
            "Select entity type to categorize:",
            options=entity_type_names,
            index=0,
            key="nav_l3_entity_type"
        )

        # Get dataframe for selected entity type
        graph_df = pd.DataFrame(entities_by_type.get(selected_entity_type, []))

        if graph_df.empty:
            st.warning(f"No data for entity type '{selected_entity_type}'")
            return

        # Get available text columns
        text_columns = [col for col in graph_df.columns if col != 'id' and graph_df[col].dtype == 'object']
        if not text_columns:
            text_columns = list(graph_df.columns)

        # Column selector
        default_col = 'name' if 'name' in text_columns else text_columns[0] if text_columns else None

        if default_col:
            selected_column = st.selectbox(
                "Select column to categorize by:",
                options=text_columns,
                index=text_columns.index(default_col) if default_col in text_columns else 0,
                key="nav_l3_column"
            )

            # Show unique values
            unique_values = graph_df[selected_column].dropna().unique()[:10]
            with st.expander(f"Sample values in '{selected_column}' ({len(graph_df[selected_column].dropna().unique())} unique)"):
                st.write(list(unique_values))
        else:
            st.error("No suitable columns found for categorization")
            return

        st.divider()

        # Domain input - Use shared component (FR-009, T007)
        domains_input, use_semantic, threshold = _render_domain_categorization_inputs(
            key_prefix="nav_l3_descent",
            default_domains="Revenue, Volume, ETP",
            show_help=True
        )

        domains_list = _parse_domains(domains_input)

        if domains_list and st.button("Categorize & Descend", key="nav_l3_categorize_btn", type="primary"):
            st.info("Categorizing data by domains...")
            # Build query function that performs domain categorization
            # Using shared _apply_domain_categorization function (FR-009)
            def categorize_and_extract(G):
                """Extract entities and categorize by domain."""
                # Get the entity dataframe
                df = pd.DataFrame(entities_by_type.get(selected_entity_type, []))
                if df.empty:
                    return df

                # Use shared categorization function (FR-009)
                return _apply_domain_categorization(
                    df=df,
                    column=selected_column,
                    domains=domains_list,
                    use_semantic=use_semantic,
                    threshold=threshold
                )

            params['query_func'] = categorize_and_extract

            try:
                nav_session.descend(**params)
                st.success(f"Now viewing {target} with category filters applied")
                st.session_state.nav_action = None
                st.session_state.nav_target = None
                st.session_state.nav_l3_descend_step = 1
                st.rerun()
            except NavigationError as e:
                st.error(str(e))

        # Also offer simple extraction option
        st.divider()
        with st.expander("Or extract all entities without categorization"):
            if st.button("Extract All Nodes", key="nav_l3_extract_all"):
                def default_query(G):
                    rows = []
                    for node, attrs in G.nodes(data=True):
                        row = {'id': node, **attrs}
                        rows.append(row)
                    return pd.DataFrame(rows)

                params['query_func'] = default_query
                try:
                    nav_session.descend(**params)
                    st.success(f"Now viewing {target}")
                    st.session_state.nav_action = None
                    st.session_state.nav_target = None
                    st.rerun()
                except NavigationError as e:
                    st.error(str(e))

    elif current_level.value == 2:  # L2 -> L1
        with st.form(f"descend_form_L2_{target}"):
            data = nav_session.current_dataset.get_data()
            column = st.selectbox("Select column to extract:", options=list(data.columns))
            params['column'] = column

            if st.form_submit_button("Descend"):
                try:
                    nav_session.descend(**params)
                    st.success(f"Now viewing {target}")
                    st.session_state.nav_action = None
                    st.session_state.nav_target = None
                    st.rerun()
                except NavigationError as e:
                    st.error(str(e))

    elif current_level.value == 1:  # L1 -> L0
        with st.form(f"descend_form_L1_{target}"):
            aggregation = st.selectbox(
                "Aggregation method:",
                options=['count', 'sum', 'mean', 'min', 'max']
            )
            params['aggregation'] = aggregation

            if st.form_submit_button("Descend"):
                try:
                    nav_session.descend(**params)
                    st.success(f"Now viewing {target}")
                    st.session_state.nav_action = None
                    st.session_state.nav_target = None
                    st.rerun()
                except NavigationError as e:
                    st.error(str(e))


def render_ascend_options(nav_session: NavigationSession, target: str, option: Dict):
    """Render options for ascending to a higher level.

    FR-012: Show visualization from LOWER level (source) during ascent.
    FR-013: Show navigation direction indicator.

    Feature 004-ascent-precision: Enhanced with dedicated forms for each transition.
    """
    current_level = nav_session.current_level
    source_level = current_level.value
    target_level = source_level + 1  # Ascent goes to higher level

    # Show navigation direction indicator (FR-013)
    render_navigation_direction_indicator(
        NavigationDirection.ASCEND,
        source_level,
        target_level
    )

    # FR-012: Show source level visualization (what we're ascending FROM)
    st.markdown("#### Source Data (what you're expanding/enriching)")
    data = nav_session.current_dataset.get_data()

    if current_level.value == 0:  # L0 -> L1: Show datum
        render_l0_datum(
            data,
            aggregation_method=nav_session.current_dataset.description or "computed",
            source_info="Expanding to vector"
        )
    elif current_level.value == 1:  # L1 -> L2: Show vector
        # Level1Dataset uses 'name' attribute, not 'description'
        column_name = getattr(nav_session.current_dataset, 'name', None) or "vector"
        render_l1_vector(
            data,
            column_name=column_name
        )
    elif current_level.value == 2:  # L2 -> L3: Show domain table
        if isinstance(data, pd.DataFrame):
            render_l2_domain_table({"Current Table": data})

    st.divider()

    # Use dedicated ascent forms (004-ascent-precision)
    st.write(f"**Configure ascent to {target}**")

    params = None

    if current_level.value == 0:  # L0 -> L1: Unfold Form (T010)
        # Use the dedicated unfold form (FR-001 to FR-004)
        params = render_l0_to_l1_unfold_form(
            dataset=nav_session.current_dataset,
            key_prefix=f"nav_ascend_l0_l1_{target}"
        )

    elif current_level.value == 1:  # L1 -> L2: Domain Enrichment Form (T016)
        # Use the dedicated domain enrichment form (FR-005 to FR-010)
        form_result = render_l1_to_l2_domain_form(
            dataset=nav_session.current_dataset,
            key_prefix=f"nav_ascend_l1_l2_{target}"
        )
        if form_result:
            # Convert form result to ascent params
            params = {
                'dimensions': form_result.get('dimensions', []),
                'use_semantic': form_result.get('use_semantic', True),
                'threshold': form_result.get('threshold', 0.5)
            }

    elif current_level.value == 2:  # L2 -> L3: Entity Form (T025)
        # Use the dedicated entity/graph building form (FR-011 to FR-015)
        form_result = render_l2_to_l3_entity_form(
            dataset=nav_session.current_dataset,
            key_prefix=f"nav_ascend_l2_l3_{target}"
        )
        if form_result:
            # Convert form result to ascent params
            params = {
                'entity_column': form_result.get('entity_column'),
                'entity_type_name': form_result.get('entity_type_name'),
                'relationship_type': form_result.get('relationship_type')
            }

    # Execute ascent if params were provided (form submitted)
    if params is not None:
        try:
            nav_session.ascend(**params)
            st.success(f"Built up to {target}")
            # Clear the form state
            st.session_state.nav_action = None
            st.session_state.nav_target = None
            st.rerun()
        except NavigationError as e:
            st.error(str(e))


def handle_exit_action(nav_session: NavigationSession):
    """Handle the exit action with JSON export."""
    export_data = nav_session.exit()
    st.session_state.nav_export = export_data
    st.success("Navigation session ended!")
    st.rerun()


def render_export_view():
    """Render the export view after exiting navigation."""
    export_data = st.session_state.nav_export

    st.subheader("Navigation Export")

    # Use the JSON visualizer component
    render_navigation_export(export_data)

    # Option to start new session
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Start New Session"):
            st.session_state.nav_session = None
            st.session_state.nav_export = None
            st.session_state.nav_mode = 'guided'
            st.rerun()

    with col2:
        if st.button("Continue Navigation"):
            # Resume from export
            if st.session_state.nav_session:
                try:
                    session_id = st.session_state.nav_session.session_id
                    st.session_state.nav_session = NavigationSession.resume(session_id)
                    st.session_state.nav_export = None
                    st.rerun()
                except Exception:
                    st.error("Could not resume session")


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """Main Streamlit app entry point."""
    st.set_page_config(
        page_title="Data Redesign Method",
        page_icon="🔄",
        layout="wide"
    )

    # Inject centralized design styles (007-streamlit-design-makeup)
    inject_all_styles()

    # Inject CSS for right sidebar progress indicator (must be early)
    inject_right_sidebar_css()

    # Initialize session state
    init_session_state()

    # Handle ascent mode switch (before sidebar widget renders)
    if st.session_state.get(SessionStateKeys.SWITCH_TO_ASCENT):
        del st.session_state[SessionStateKeys.SWITCH_TO_ASCENT]
        st.session_state[SessionStateKeys.NAV_MODE] = 'free'
        # Delete widget key so it reinitializes with new nav_mode value
        if SessionStateKeys.MODE_SELECTOR in st.session_state:
            del st.session_state[SessionStateKeys.MODE_SELECTOR]

    # Keep free mode when in ascent workflow (has loaded_session_graph)
    # This prevents the radio widget from resetting nav_mode during ascent
    if st.session_state.get(SessionStateKeys.LOADED_SESSION_GRAPH) and st.session_state.get(SessionStateKeys.NAV_MODE) != 'free':
        st.session_state[SessionStateKeys.NAV_MODE] = 'free'

    # Session persistence (005-session-persistence)
    store = SessionStore()

    # Handle session recovery (only on first load)
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

    # Check if we're on the pure landing page (no data, no search performed)
    # In this state, we hide EVERYTHING except the search bar
    is_pure_landing = (
        st.session_state.get(SessionStateKeys.NAV_MODE) == 'guided' and
        st.session_state.get(SessionStateKeys.CURRENT_STEP) == 0 and
        st.session_state.get(SessionStateKeys.RAW_DATA) is None and
        not st.session_state.get('datagouv_loaded_datasets') and
        not st.session_state.get('datagouv_results')  # No search results yet
    )

    # Hide sidebar completely on pure landing page
    if is_pure_landing:
        st.markdown("""
        <style>
        [data-testid="stSidebar"] { display: none !important; }
        .stApp > header { display: none !important; }
        </style>
        """, unsafe_allow_html=True)
    else:
        # Sidebar - only show after user has interacted
        with st.sidebar:
            # Animated gear cube logo + branding
            st.markdown(_get_sidebar_branding_html(), unsafe_allow_html=True)
            st.markdown("---")

            # Language toggle (006-playwright-mcp-e2e: Bilingual support)
            render_language_toggle_compact()
            st.divider()

            # Dataset basket in sidebar (008-datagouv-search)
            if render_basket_sidebar():
                # User clicked "Continue" - proceed with loaded datasets
                raw_data = st.session_state.datagouv_loaded_datasets.copy()
                st.session_state.raw_data = raw_data
                st.session_state.datasets['l4'] = Level4Dataset(raw_data)
                st.session_state.datagouv_loaded_datasets = {}

                # Go to upload step to show column selection wizard
                # (upload step has the wizard when raw_data is set)
                st.session_state.current_step = 0
                # Initialize wizard to step 1 (column selection)
                _set_wizard_step(1)
                # Reset and show tutorial for new data session
                reset_tutorial()  # Clears completion state and shows tutorial
                st.rerun()

            # Mode toggle - Constitution v1.2.0: Use domain-friendly labels
            st.markdown(f"### {t('exploration_mode')}")
            mode = st.radio(
                t('select_mode'),
                options=['guided', 'free'],
                format_func=lambda x: t('step_by_step') if x == 'guided' else t('free_exploration'),
                index=0 if st.session_state.nav_mode == 'guided' else 1,
                key='mode_selector',
                help=t('step_by_step_help')
            )

            # Sync radio with nav_mode, but skip if in ascent mode (has loaded_session_graph)
            # During ascent, we force free mode regardless of radio selection
            if mode != st.session_state.nav_mode and not st.session_state.get('loaded_session_graph'):
                st.session_state.nav_mode = mode
                st.rerun()

            st.divider()

            # Data modeling Tools section (009-quality-data-platform)
            st.markdown("### Data modeling Tools")
            quality_tool = st.radio(
                "Select tool",
                options=['none', 'quality', 'catalog'],
                format_func=lambda x: {
                    'none': 'None',
                    'quality': '📊 Quality Assessment',
                    'catalog': '📁 Dataset Catalog'
                }.get(x, x),
                index=0,
                key='quality_tool_selector',
                label_visibility='collapsed',
            )
            if quality_tool != st.session_state.get('active_quality_tool', 'none'):
                st.session_state.active_quality_tool = quality_tool
                st.rerun()

            st.divider()

            # Free exploration mode - render exploration tree (only when active)
            if st.session_state.nav_mode == 'free' and st.session_state.nav_session:
                render_free_navigation_sidebar()
                st.divider()
            if st.button(f"🔄 {t('reset_workflow')}"):
                reset_workflow()
                st.rerun()

            # Tutorial replay button (007-streamlit-design-makeup, Phase 9)
            if is_tutorial_completed() and st.session_state.raw_data is not None:
                render_tutorial_replay_button()

            # Session persistence buttons (005-session-persistence)
            st.markdown(f"### {t('sidebar_session')}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"💾 {t('save_button')}", help=t('save_help')):
                    try:
                        result = store.save(force=True)
                        if result.success:
                            st.success(t('saved_success'))
                        else:
                            st.warning(t('save_too_large'))
                    except Exception as e:
                        st.error(t('save_failed', error=str(e)))
            with col2:
                if st.button(f"🗑️ {t('clear_button')}", help=t('clear_help')):
                    store.clear()
                    reset_workflow()
                    st.session_state.session_recovery_handled = True
                    st.rerun()

    # Main content
    # Check for Quality Tools (009-quality-data-platform)
    active_quality_tool = st.session_state.get('active_quality_tool', 'none')
    if active_quality_tool == 'quality':
        render_quality_dashboard()
        return
    elif active_quality_tool == 'catalog':
        render_catalog_browser()
        return

    if st.session_state.nav_mode == 'guided':
        # Check if we're in the search/selection flow (hide header throughout)
        # This includes: landing page, search results, and basket selection
        is_in_search_flow = (
            st.session_state.current_step == 0 and
            st.session_state.raw_data is None
        )
        # Keep old name for backwards compatibility with render_upload_step
        is_search_landing = is_in_search_flow

        # Check if tutorial dialog should show (after data loaded, before workflow)
        should_show_tutorial_dialog = (
            st.session_state.get('show_tutorial', False) and
            not is_tutorial_completed()
        )

        # Show tutorial dialog as overlay (007-streamlit-design-makeup, Phase 9)
        # Dialog appears on top of underlying content
        if should_show_tutorial_dialog:
            render_tutorial()

        # Headers removed for minimal SaaS design (007-streamlit-design-makeup)

        # Render current step content (dialog overlays on top if active)
        step_id = STEPS[st.session_state.current_step]['id']

        if step_id == "upload":
            render_upload_step(skip_header=is_search_landing)
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

    else:
        # Free Exploration Mode - headers removed for minimal design

        # Check for export view
        if st.session_state.nav_export:
            render_export_view()
        else:
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

                # Session graph loader (Phase 2B - 006-playwright-mcp-e2e)
                render_session_graph_loader()
            else:
                render_free_navigation_main()

    # Render the fixed right sidebar progress indicator (always visible)
    render_vertical_progress_sidebar()


if __name__ == "__main__":
    main()
