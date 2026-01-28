"""
Sidebar Module

Implements Spec 011: Code Simplification
Extracted from streamlit_app.py (lines 4720-4816)

Responsibilities:
- Branding and logo display
- Language toggle
- Dataset basket (data.gouv.fr)
- Mode selection (guided/free)
- Quality tools selector
- Navigation tree (free mode)
- Session persistence buttons

Target: <200 lines (focused sidebar logic)
"""

import streamlit as st
from typing import Optional

from intuitiveness.complexity import Level4Dataset
from intuitiveness.ui import (
    render_language_toggle_compact,
    render_basket_sidebar,
    _set_wizard_step,
    t,
    render_tutorial_replay_button,
    is_tutorial_completed,
    reset_tutorial,
)
from intuitiveness.persistence import SessionStore


def _get_sidebar_branding_html() -> str:
    """Generate animated gear cube logo HTML for sidebar."""
    from pathlib import Path
    
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    ASSETS_DIR = PROJECT_ROOT / "assets"
    
    # Try to load SVG logo
    logo_path = ASSETS_DIR / "gear_cube_logo.svg"
    if logo_path.exists():
        with open(logo_path, 'r') as f:
            logo_svg = f.read()
    else:
        logo_svg = '<div style="width: 100px; height: 100px; background: #002fa7;"></div>'
    
    return f"""
    <div style="text-align: center; padding: 1rem 0;">
        <div style="width: 100px; height: 100px; margin: 0 auto;">
            {logo_svg}
        </div>
        <h3 style="margin: 0.5rem 0 0 0; font-size: 1.1rem; font-weight: 600;">
            Data Redesign Method
        </h3>
        <p style="margin: 0.25rem 0 0 0; font-size: 0.8rem; color: #666;">
            Intuitive Datasets Framework
        </p>
    </div>
    """


def render_sidebar(store: SessionStore) -> None:
    """
    Render complete sidebar with all controls.
    
    Args:
        store: SessionStore instance for save/load operations
    """
    # Animated gear cube logo + branding
    st.markdown(_get_sidebar_branding_html(), unsafe_allow_html=True)
    st.markdown("---")
    
    # Language toggle (006-playwright-mcp-e2e: Bilingual support)
    render_language_toggle_compact()
    st.divider()
    
    # Dataset basket in sidebar (008-datagouv-search)
    if render_basket_sidebar():
        _handle_basket_continue()
    
    # Mode toggle - Constitution v1.2.0: Use domain-friendly labels
    _render_mode_selector()
    
    st.divider()
    
    # Data modeling Tools section (009-quality-data-platform)
    _render_quality_tools_selector()
    
    st.divider()
    
    # Free exploration mode - render exploration tree (only when active)
    if st.session_state.nav_mode == 'free' and st.session_state.nav_session:
        from intuitiveness.streamlit_app import render_free_navigation_sidebar
        render_free_navigation_sidebar()
        st.divider()
    
    # Reset workflow button
    if st.button(f"🔄 {t('reset_workflow')}"):
        from intuitiveness.streamlit_app import reset_workflow
        reset_workflow()
        st.rerun()
    
    # Tutorial replay button (007-streamlit-design-makeup, Phase 9)
    if is_tutorial_completed() and st.session_state.raw_data is not None:
        render_tutorial_replay_button()
    
    # Session persistence buttons (005-session-persistence)
    _render_persistence_buttons(store)


def _handle_basket_continue() -> None:
    """Handle user clicking 'Continue' in dataset basket."""
    # User clicked "Continue" - proceed with loaded datasets
    raw_data = st.session_state.datagouv_loaded_datasets.copy()
    st.session_state.raw_data = raw_data
    st.session_state.datasets['l4'] = Level4Dataset(raw_data)
    st.session_state.datagouv_loaded_datasets = {}
    
    # Go to upload step to show column selection wizard
    st.session_state.current_step = 0
    # Initialize wizard to step 1 (column selection)
    _set_wizard_step(1)
    # Reset and show tutorial for new data session
    reset_tutorial()
    st.rerun()


def _render_mode_selector() -> None:
    """Render guided/free mode selector."""
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


def _render_quality_tools_selector() -> None:
    """Render quality tools selector (assessment/catalog)."""
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


def _render_persistence_buttons(store: SessionStore) -> None:
    """Render session save/clear buttons."""
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
            from intuitiveness.streamlit_app import reset_workflow
            store.clear()
            reset_workflow()
            st.session_state.session_recovery_handled = True
            st.rerun()
