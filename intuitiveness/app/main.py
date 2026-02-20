"""
Main App Orchestrator

Coordinates the Streamlit application flow with spec-aligned routing.
Delegates to mode-specific modules for rendering.

Phase 1 - Code Simplification (011-code-simplification)
Created: 2026-01-09

Spec Traceability:
------------------
This orchestrator routes to:
- Guided mode (001-004): Descent/ascent wizard workflow
- Free mode (002-003): Decision tree navigation
- Quality mode (009-010): DS Co-Pilot workflow
- Catalog mode (008): Data.gouv.fr search
"""

import streamlit as st

from intuitiveness.app.initialization import (
    init_app_config,
    init_styles,
    init_session_state,
    handle_mode_switching,
    handle_session_recovery,
    is_pure_landing_page,
    hide_sidebar_on_landing,
)
from intuitiveness.persistence import SessionStore
from intuitiveness.utils import SessionStateKeys


def run_app():
    """
    Main application entry point.

    Orchestrates the full application flow:
    1. Initialize configuration and styles
    2. Initialize session state
    3. Handle session recovery (005-session-persistence)
    4. Route to appropriate mode based on user selection

    This function replaces the monolithic main() in streamlit_app.py
    with a cleaner separation of concerns.
    """
    # Import rendering functions from existing streamlit_app
    # (Phase 1: Gradual migration - these will move to dedicated modules)
    from intuitiveness.streamlit_app import (
        # Sidebar components
        _get_sidebar_branding_html,
        inject_right_sidebar_css,
        render_vertical_progress_sidebar,
        render_free_navigation_sidebar,
        reset_workflow,
        STEPS,
        # Guided mode rendering
        render_upload_step,
        render_entities_step,
        render_domains_step,
        render_features_step,
        render_aggregation_step,
        render_results_step,
        # Free mode rendering
        render_session_graph_loader,
        render_free_navigation_main,
        render_export_view,
    )
    from intuitiveness.ui import (
        render_quality_dashboard,
        render_catalog_browser,
        render_basket_sidebar,
        render_language_toggle_compact,
        render_tutorial,
        render_tutorial_replay_button,
        is_tutorial_completed,
        reset_tutorial,
        _set_wizard_step,
        t,
    )
    from intuitiveness.complexity import Level4Dataset

    # ==========================================================================
    # INITIALIZATION
    # ==========================================================================
    init_app_config()
    init_styles()
    inject_right_sidebar_css()
    init_session_state()
    handle_mode_switching()

    store = SessionStore()
    if handle_session_recovery(store):
        return  # Recovery in progress, stop here

    # ==========================================================================
    # SIDEBAR RENDERING
    # ==========================================================================
    if is_pure_landing_page():
        hide_sidebar_on_landing()
    else:
        _render_sidebar(
            store=store,
            branding_html=_get_sidebar_branding_html(),
            render_basket_sidebar=render_basket_sidebar,
            render_language_toggle_compact=render_language_toggle_compact,
            render_free_navigation_sidebar=render_free_navigation_sidebar,
            render_tutorial_replay_button=render_tutorial_replay_button,
            is_tutorial_completed=is_tutorial_completed,
            reset_tutorial=reset_tutorial,
            reset_workflow=reset_workflow,
            _set_wizard_step=_set_wizard_step,
            Level4Dataset=Level4Dataset,
            t=t,
        )

    # ==========================================================================
    # MAIN CONTENT ROUTING
    # ==========================================================================

    # Route to Quality Tools (009-010)
    active_tool = st.session_state.get('active_quality_tool', 'none')
    if active_tool == 'quality':
        render_quality_dashboard()
        return
    elif active_tool == 'catalog':
        render_catalog_browser()
        return

    # Route based on navigation mode
    nav_mode = st.session_state.get(SessionStateKeys.NAV_MODE, 'guided')

    if nav_mode == 'guided':
        _render_guided_mode(
            STEPS=STEPS,
            render_upload_step=render_upload_step,
            render_entities_step=render_entities_step,
            render_domains_step=render_domains_step,
            render_features_step=render_features_step,
            render_aggregation_step=render_aggregation_step,
            render_results_step=render_results_step,
            render_tutorial=render_tutorial,
            is_tutorial_completed=is_tutorial_completed,
        )
    else:
        _render_free_mode(
            render_session_graph_loader=render_session_graph_loader,
            render_free_navigation_main=render_free_navigation_main,
            render_export_view=render_export_view,
        )

    # Always render progress sidebar
    render_vertical_progress_sidebar()


def _render_sidebar(
    store,
    branding_html,
    render_basket_sidebar,
    render_language_toggle_compact,
    render_free_navigation_sidebar,
    render_tutorial_replay_button,
    is_tutorial_completed,
    reset_tutorial,
    reset_workflow,
    _set_wizard_step,
    Level4Dataset,
    t,
):
    """
    Render the left sidebar with all controls.

    Components:
    - Branding (007-streamlit-design-makeup)
    - Language toggle (006-playwright-mcp-e2e)
    - Dataset basket (008-datagouv-search)
    - Mode toggle (002-ascent-functionality)
    - Quality tools (009-010)
    - Session persistence (005-session-persistence)
    """
    with st.sidebar:
        # Branding
        st.markdown(branding_html, unsafe_allow_html=True)
        st.markdown("---")

        # Language toggle (006)
        render_language_toggle_compact()
        st.divider()

        # Dataset basket (008)
        if render_basket_sidebar():
            raw_data = st.session_state.datagouv_loaded_datasets.copy()
            st.session_state.raw_data = raw_data
            st.session_state.datasets['l4'] = Level4Dataset(raw_data)
            st.session_state.datagouv_loaded_datasets = {}
            st.session_state.current_step = 0
            _set_wizard_step(1)
            reset_tutorial()
            st.rerun()

        # Mode toggle
        st.markdown(f"### {t('exploration_mode')}")
        mode = st.radio(
            t('select_mode'),
            options=['guided', 'free'],
            format_func=lambda x: t('step_by_step') if x == 'guided' else t('free_exploration'),
            index=0 if st.session_state.nav_mode == 'guided' else 1,
            key='mode_selector',
            help=t('step_by_step_help')
        )

        if mode != st.session_state.nav_mode and not st.session_state.get('loaded_session_graph'):
            st.session_state.nav_mode = mode
            st.rerun()

        st.divider()

        # Quality tools (009-010)
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

        # Free navigation sidebar (002)
        if st.session_state.nav_mode == 'free' and st.session_state.nav_session:
            render_free_navigation_sidebar()
            st.divider()

        if st.button(f"🔄 {t('reset_workflow')}"):
            reset_workflow()
            st.rerun()

        # Tutorial replay (007)
        if is_tutorial_completed() and st.session_state.raw_data is not None:
            render_tutorial_replay_button()

        # Session persistence (005)
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


def _render_guided_mode(
    STEPS,
    render_upload_step,
    render_entities_step,
    render_domains_step,
    render_features_step,
    render_aggregation_step,
    render_results_step,
    render_tutorial,
    is_tutorial_completed,
):
    """
    Render guided mode content (specs 001-004).

    Routes to appropriate step based on current_step in session state.
    """
    # Check for search flow
    is_search_landing = (
        st.session_state.current_step == 0 and
        st.session_state.raw_data is None
    )

    # Route to current step
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


def _render_free_mode(
    render_session_graph_loader,
    render_free_navigation_main,
    render_export_view,
):
    """
    Render free navigation mode content (specs 002-003).

    Handles:
    - Export view
    - Session graph loading
    - Main navigation interface
    """
    # Check for export view
    if st.session_state.nav_export:
        render_export_view()
        return

    # Check if data is available
    if st.session_state.raw_data is None and not st.session_state.get('loaded_session_graph'):
        st.warning(
            "Please upload data first in **Step-by-Step** mode, or load a saved session graph below."
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Switch to Step-by-Step"):
                st.session_state.nav_mode = 'guided'
                st.rerun()
        with col2:
            st.markdown("**OR**")

        render_session_graph_loader()
    else:
        render_free_navigation_main()
