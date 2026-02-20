"""
Guided Mode Module

Implements the guided descent/ascent wizard workflow (specs 001-004).

Phase 1 - Code Simplification (011-code-simplification)
Created: 2026-01-09

Spec Traceability:
------------------
- 001-dataset-redesign-package: Descent operations (L4→L0)
- 002-ascent-functionality: Ascent operations (L0→L3)
- 003-level-dataviz-display: Level-specific visualizations
- 004-ascent-precision: Domain categorization, linkage keys

Workflow Steps:
---------------
DESCENT (L4→L0):
  Step 1 (upload): L4 - Unlinkable datasets
  Step 2 (entities): L4→L3 - Define linkable entities
  Step 3 (domains): L3→L2 - Define domain categories
  Step 4 (features): L2→L1 - Extract feature vectors
  Step 5 (aggregation): L1→L0 - Aggregate to datum
  Step 6 (results): L0 - View computed results

ASCENT (L0→L3):
  Step 7 (l0_to_l1): L0→L1 - Recover source values
  Step 8 (l1_to_l2): L1→L2 - Define new categories
  Step 9 (l2_to_l3): L2→L3 - Enrich with linkage keys
"""

import streamlit as st
from typing import Dict, Any, Optional

from intuitiveness.utils import SessionStateKeys


# =============================================================================
# STEP DEFINITIONS
# =============================================================================

# Descent phase steps (Steps 1-6) - Bilingual: English // Français
DESCENT_STEPS = [
    {
        "id": "upload",
        "title": "Unlinkable datasets // Données non-structurées",
        "level": "Step 1",
        "level_num": 4,
        "description": "Upload your raw data files (CSV format)"
    },
    {
        "id": "entities",
        "title": "Linkable data // Données liables",
        "level": "Step 2",
        "level_num": 3,
        "description": "What are the main things you want to see in your connected information?"
    },
    {
        "id": "domains",
        "title": "Table // Tableau de données",
        "level": "Step 3",
        "level_num": 2,
        "description": "What categories do you want to organize your data by?"
    },
    {
        "id": "features",
        "title": "Vector // Vecteur de données",
        "level": "Step 4",
        "level_num": 1,
        "description": "What values do you want to extract?"
    },
    {
        "id": "aggregation",
        "title": "Datum // Datum",
        "level": "Step 5",
        "level_num": 0,
        "description": "What computation do you want to run on your values?"
    },
    {
        "id": "results",
        "title": "Analytic core // Cœur analytique",
        "level": "Step 6",
        "level_num": 0,
        "description": "View your computed results"
    }
]

# Ascent phase steps (Steps 7-9) - Bilingual: English // Français
# IDs must match streamlit_app.py ASCENT_STEPS for unified dispatch
ASCENT_STEPS = [
    {
        "id": "l0_to_l1",
        "title": "Datum → Vector // Datum → Vecteur",
        "level": "Step 7",
        "level_num": 0,
        "description": "L0 → L1: Recover source values // Récupérer les valeurs sources"
    },
    {
        "id": "l1_to_l2",
        "title": "Vector → Table // Vecteur → Tableau",
        "level": "Step 8",
        "level_num": 1,
        "description": "L1 → L2: Define new categories // Définir de nouvelles catégories"
    },
    {
        "id": "l2_to_l3",
        "title": "Table → Graph // Tableau → Graphe",
        "level": "Step 9",
        "level_num": 2,
        "description": "L2 → L3: Enrich with linkage keys // Enrichir avec des clés de liaison"
    },
]

# Combined for backward compatibility
STEPS = DESCENT_STEPS


# =============================================================================
# RENDERING FACADE
# =============================================================================

def render_guided_content():
    """
    Render the guided mode main content.

    Routes to appropriate step based on current_step in session state.
    Implements specs 001-004.
    """
    # Import rendering functions from existing streamlit_app
    from intuitiveness.streamlit_app import (
        render_upload_step,
        render_entities_step,
        render_domains_step,
        render_features_step,
        render_aggregation_step,
        render_results_step,
    )
    from intuitiveness.ui import (
        render_tutorial,
        is_tutorial_completed,
    )

    # Check for search flow (hide header)
    is_search_landing = (
        st.session_state.get(SessionStateKeys.CURRENT_STEP, 0) == 0 and
        st.session_state.get(SessionStateKeys.RAW_DATA) is None
    )

    # Route to current step
    current_step = st.session_state.get(SessionStateKeys.CURRENT_STEP, 0)
    step_id = DESCENT_STEPS[current_step]['id']

    # Dispatch to step renderer
    step_renderers = {
        "upload": lambda: render_upload_step(skip_header=is_search_landing),
        "entities": render_entities_step,
        "domains": render_domains_step,
        "features": render_features_step,
        "aggregation": render_aggregation_step,
        "results": render_results_step,
    }

    renderer = step_renderers.get(step_id)
    if renderer:
        renderer()


def get_current_step() -> int:
    """Get current wizard step index."""
    return st.session_state.get(SessionStateKeys.CURRENT_STEP, 0)


def set_current_step(step: int) -> None:
    """Set current wizard step index."""
    st.session_state[SessionStateKeys.CURRENT_STEP] = step


def get_current_step_info() -> Dict[str, Any]:
    """Get information about current step."""
    step_idx = get_current_step()
    if 0 <= step_idx < len(DESCENT_STEPS):
        return DESCENT_STEPS[step_idx]
    return DESCENT_STEPS[0]


def advance_step() -> bool:
    """
    Advance to next step if possible.

    Returns:
        True if advanced, False if already at last step
    """
    current = get_current_step()
    if current < len(DESCENT_STEPS) - 1:
        set_current_step(current + 1)
        return True
    return False


def go_back_step() -> bool:
    """
    Go back to previous step if possible.

    Returns:
        True if went back, False if already at first step
    """
    current = get_current_step()
    if current > 0:
        set_current_step(current - 1)
        return True
    return False


def is_descent_complete() -> bool:
    """Check if descent phase is complete (at results step)."""
    return get_current_step() >= len(DESCENT_STEPS) - 1


def get_current_level() -> int:
    """
    Get current abstraction level based on step.

    Returns:
        Level number (4=L4, 0=L0)
    """
    step_info = get_current_step_info()
    return step_info.get('level_num', 4)


# =============================================================================
# PROGRESS INDICATORS
# =============================================================================

def get_descent_progress() -> Dict[str, Any]:
    """
    Get descent progress information.

    Returns:
        Dict with:
        - current_step: Current step index
        - total_steps: Total descent steps
        - current_level: Current abstraction level
        - percent: Completion percentage
    """
    current = get_current_step()
    total = len(DESCENT_STEPS)
    return {
        'current_step': current,
        'total_steps': total,
        'current_level': get_current_level(),
        'percent': (current / (total - 1)) * 100 if total > 1 else 0
    }


def render_progress_indicator():
    """
    Render progress bar for guided mode.

    Delegates to existing implementation.
    """
    from intuitiveness.streamlit_app import render_progress_bar
    render_progress_bar()
