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

    # Generate cube faces HTML (scaled down version)
    def make_gear(level: str, spin: str) -> str:
        return f'<div class="sb-gear sb-{level} sb-spin-{spin}"></div>'

    patterns = {
        'front':  [('l4','cw'), ('l3','ccw'), ('l4','cw'),
                   ('l2','ccw'), ('l0','cw'), ('l2','ccw'),
                   ('l4','cw'), ('l3','ccw'), ('l4','cw')],
        'back':   [('l3','cw'), ('l2','ccw'), ('l3','cw'),
                   ('l1','ccw'), ('l0','cw'), ('l1','ccw'),
                   ('l3','cw'), ('l2','ccw'), ('l3','cw')],
        'right':  [('l4','cw'), ('l2','ccw'), ('l3','cw'),
                   ('l3','ccw'), ('l1','cw'), ('l2','ccw'),
                   ('l4','cw'), ('l2','ccw'), ('l3','cw')],
        'left':   [('l3','cw'), ('l2','ccw'), ('l4','cw'),
                   ('l2','ccw'), ('l1','cw'), ('l3','ccw'),
                   ('l3','cw'), ('l2','ccw'), ('l4','cw')],
        'top':    [('l4','cw'), ('l4','ccw'), ('l4','cw'),
                   ('l4','ccw'), ('l2','cw'), ('l4','ccw'),
                   ('l4','cw'), ('l4','ccw'), ('l4','cw')],
        'bottom': [('l3','cw'), ('l3','ccw'), ('l3','cw'),
                   ('l3','ccw'), ('l1','cw'), ('l3','ccw'),
                   ('l3','cw'), ('l3','ccw'), ('l3','cw')],
    }

    cube_faces = ''
    for face, gears in patterns.items():
        gears_html = ''.join(make_gear(g[0], g[1]) for g in gears)
        cube_faces += f'<div class="sb-cube-face sb-{face}">{gears_html}</div>'

    return f"""
    <style>
    /* Sidebar animated cube - scaled down */
    .sb-cube-container {{
        width: 100px;
        height: 100px;
        perspective: 400px;
        margin: 0 auto;
    }}
    .sb-cube {{
        width: 100px;
        height: 100px;
        transform-style: preserve-3d;
        animation: sb-shuffle 16s ease-in-out infinite;
    }}
    @keyframes sb-shuffle {{
        0%   {{ transform: rotateX(-15deg) rotateY(0deg); }}
        8%   {{ transform: rotateX(25deg) rotateY(45deg); }}
        16%  {{ transform: rotateX(-30deg) rotateY(120deg); }}
        24%  {{ transform: rotateX(20deg) rotateY(200deg); }}
        32%  {{ transform: rotateX(-25deg) rotateY(280deg); }}
        40%  {{ transform: rotateX(35deg) rotateY(340deg); }}
        55%  {{ transform: rotateX(-10deg) rotateY(380deg); }}
        70%  {{ transform: rotateX(-15deg) rotateY(360deg); }}
        100% {{ transform: rotateX(-15deg) rotateY(360deg); }}
    }}
    .sb-cube-face {{
        position: absolute;
        width: 100px;
        height: 100px;
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1px;
        padding: 4px;
        background: rgba(0, 47, 167, 0.03);
        border-radius: 6px;
        backface-visibility: visible;
    }}
    .sb-cube-face.sb-front  {{ transform: translateZ(50px); }}
    .sb-cube-face.sb-back   {{ transform: rotateY(180deg) translateZ(50px); }}
    .sb-cube-face.sb-right  {{ transform: rotateY(90deg) translateZ(50px); }}
    .sb-cube-face.sb-left   {{ transform: rotateY(-90deg) translateZ(50px); }}
    .sb-cube-face.sb-top    {{ transform: rotateX(90deg) translateZ(50px); }}
    .sb-cube-face.sb-bottom {{ transform: rotateX(-90deg) translateZ(50px); }}
    .sb-gear {{
        width: 28px;
        height: 28px;
        border-radius: 50%;
        position: relative;
    }}
    .sb-gear::after {{
        content: '';
        position: absolute;
        width: 100%;
        height: 100%;
        background: inherit;
        border-radius: 50%;
        clip-path: polygon(
            50% 0%, 58% 8%, 65% 0%, 73% 8%,
            80% 0%, 85% 12%, 100% 15%, 92% 27%,
            100% 35%, 92% 42%, 100% 50%, 92% 58%,
            100% 65%, 92% 73%, 100% 85%, 85% 88%,
            80% 100%, 73% 92%, 65% 100%, 58% 92%,
            50% 100%, 42% 92%, 35% 100%, 27% 92%,
            20% 100%, 15% 88%, 0% 85%, 8% 73%,
            0% 65%, 8% 58%, 0% 50%, 8% 42%,
            0% 35%, 8% 27%, 0% 15%, 15% 12%,
            20% 0%, 27% 8%, 35% 0%, 42% 8%
        );
    }}
    .sb-gear.sb-l0 {{ background: #002fa7; }}
    .sb-gear.sb-l1 {{ background: #0041d1; }}
    .sb-gear.sb-l2 {{ background: #3b82f6; }}
    .sb-gear.sb-l3 {{ background: #60a5fa; }}
    .sb-gear.sb-l4 {{ background: #93c5fd; }}
    .sb-gear.sb-spin-cw {{ animation: sb-spin-cw 6s linear infinite; }}
    .sb-gear.sb-spin-ccw {{ animation: sb-spin-ccw 6s linear infinite; }}
    @keyframes sb-spin-cw {{ to {{ transform: rotate(360deg); }} }}
    @keyframes sb-spin-ccw {{ to {{ transform: rotate(-360deg); }} }}
    </style>
    <div style="text-align: center; padding: 1rem 0;">
        <div class="sb-cube-container">
            <div class="sb-cube">
                {cube_faces}
            </div>
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
