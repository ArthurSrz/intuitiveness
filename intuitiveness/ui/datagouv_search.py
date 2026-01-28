"""
Data.gouv.fr Search Interface Component - Simplified Direct Loading.

Feature: 008-datagouv-search
Provides search-first entry point for discovering and loading French open data.
Inspired by OpenDataSoft's direct, card-based interface.

Design principles:
- One-click loading (no expanders, no multi-step selection)
- Card-based grid layout for visual browsing
- Direct CSV access with instant loading
"""

import streamlit as st
import pandas as pd
from typing import Optional, List, Tuple
from datetime import datetime

from intuitiveness.ui.i18n import t
from intuitiveness.services.datagouv_client import (
    DataGouvSearchService,
    SearchResult,
    DatasetInfo,
    ResourceInfo,
    DataGouvAPIError,
    DataGouvLoadError,
)
from intuitiveness.styles.search import get_search_styles
from intuitiveness.styles.layout import LAYOUT_CSS
from intuitiveness.styles.palette import PALETTE_CSS, COLORS


# =============================================================================
# Session State Keys (prefixed to avoid conflicts)
# =============================================================================

SESSION_KEYS = {
    "query": "datagouv_query",
    "results": "datagouv_results",
    "loading": "datagouv_loading",
    "error": "datagouv_error",
    "page": "datagouv_page",
    "dataset_resources": "datagouv_dataset_resources",  # Cache: dataset_id -> resources
}


def _init_session_state() -> None:
    """Initialize all search-related session state keys."""
    defaults = {
        SESSION_KEYS["query"]: "",
        SESSION_KEYS["results"]: None,
        SESSION_KEYS["loading"]: False,
        SESSION_KEYS["error"]: None,
        SESSION_KEYS["page"]: 1,
        SESSION_KEYS["dataset_resources"]: {},
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _clear_search_state() -> None:
    """Clear all search-related session state."""
    for key in SESSION_KEYS.values():
        if key in st.session_state:
            del st.session_state[key]


def _get_service() -> DataGouvSearchService:
    """Get or create the search service instance."""
    # Recreate service if missing NL support (after upgrade)
    if "datagouv_service" in st.session_state:
        svc = st.session_state.datagouv_service
        if not hasattr(svc, '_nl_engine'):
            del st.session_state.datagouv_service

    if "datagouv_service" not in st.session_state:
        st.session_state.datagouv_service = DataGouvSearchService()
    return st.session_state.datagouv_service


# =============================================================================
# Direct Loading Functions
# =============================================================================

def _load_dataset_csv(service: DataGouvSearchService, dataset: DatasetInfo) -> Optional[Tuple[pd.DataFrame, str]]:
    """
    Directly load the first CSV from a dataset.

    Returns:
        Tuple of (DataFrame, filename) if successful, None otherwise
    """
    try:
        resources = service.get_dataset_resources(dataset.id, format_filter="csv")
        if not resources:
            return None

        # Load the first available CSV
        resource = resources[0]
        df = service.load_resource(resource.url, resource.title)
        return (df, resource.title)
    except (DataGouvAPIError, DataGouvLoadError):
        return None


# =============================================================================
# UI Components - Simplified Direct Interface
# =============================================================================

def _get_klein_blue_landing_css() -> str:
    """
    Return CSS for International Klein Blue landing page.

    Design inspired by Yves Klein's iconic pigment - a bold,
    refined luxury aesthetic with geometric precision.
    """
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

    /* Klein Blue Landing - Full immersion */
    .klein-landing {
        background: linear-gradient(180deg, #002fa7 0%, #001d6e 100%);
        border-radius: 0;
        margin: -1rem -1rem 0 -1rem;
        padding: 80px 40px 60px 40px;
        position: relative;
        overflow: hidden;
        min-height: 320px;
    }

    /* Geometric overlay pattern */
    .klein-landing::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background:
            radial-gradient(circle at 20% 80%, rgba(255,255,255,0.03) 0%, transparent 50%),
            radial-gradient(circle at 80% 20%, rgba(255,255,255,0.05) 0%, transparent 40%),
            radial-gradient(circle at 50% 50%, rgba(255,255,255,0.02) 0%, transparent 60%);
        pointer-events: none;
    }

    /* Subtle animated gradient shimmer */
    .klein-landing::after {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(
            45deg,
            transparent 40%,
            rgba(255,255,255,0.03) 50%,
            transparent 60%
        );
        animation: shimmer 8s ease-in-out infinite;
        pointer-events: none;
    }

    @keyframes shimmer {
        0%, 100% { transform: translateX(-30%) translateY(-30%); }
        50% { transform: translateX(30%) translateY(30%); }
    }

    /* Content container */
    .klein-content {
        position: relative;
        z-index: 1;
        text-align: center;
        max-width: 700px;
        margin: 0 auto;
    }

    /* Main headline - Outfit font, bold statement */
    .klein-headline {
        font-family: 'Outfit', sans-serif;
        font-size: 2.8rem;
        font-weight: 700;
        color: #ffffff;
        margin: 0 0 16px 0;
        letter-spacing: -0.03em;
        line-height: 1.1;
        text-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
    }

    /* Accent word styling */
    .klein-headline .accent {
        color: rgba(255, 255, 255, 0.7);
        font-weight: 300;
    }

    /* Tagline */
    .klein-tagline {
        font-family: 'Outfit', sans-serif;
        font-size: 1.1rem;
        font-weight: 300;
        color: rgba(255, 255, 255, 0.65);
        margin: 0;
        letter-spacing: 0.02em;
    }

    /* Search container styling */
    .klein-search-wrap {
        margin-top: 40px;
        padding: 0 20px;
    }

    /* Decorative bottom edge */
    .klein-edge {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg,
            transparent 0%,
            rgba(255,255,255,0.3) 20%,
            rgba(255,255,255,0.5) 50%,
            rgba(255,255,255,0.3) 80%,
            transparent 100%
        );
    }

    /* Override Streamlit form styling within landing */
    .klein-search-wrap .stForm {
        background: transparent !important;
        border: none !important;
    }

    /* Custom search input styling */
    .klein-search-wrap input[type="text"] {
        background: rgba(255, 255, 255, 0.12) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
        color: #ffffff !important;
        font-family: 'Outfit', sans-serif !important;
        font-size: 1.1rem !important;
        padding: 16px 20px !important;
        transition: all 0.3s ease !important;
    }

    .klein-search-wrap input[type="text"]::placeholder {
        color: rgba(255, 255, 255, 0.5) !important;
    }

    .klein-search-wrap input[type="text"]:focus {
        background: rgba(255, 255, 255, 0.18) !important;
        border-color: rgba(255, 255, 255, 0.4) !important;
        box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.1) !important;
    }

    /* Search button styling */
    .klein-search-wrap button[kind="primaryFormSubmit"] {
        background: #ffffff !important;
        color: #002fa7 !important;
        border: none !important;
        border-radius: 12px !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
        padding: 16px 24px !important;
        transition: all 0.2s ease !important;
    }

    .klein-search-wrap button[kind="primaryFormSubmit"]:hover {
        background: rgba(255, 255, 255, 0.9) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2) !important;
    }
    </style>
    """


def _generate_cube_face_html(face_class: str) -> str:
    """
    Generate HTML for a single cube face with 9 interlocking gears.

    Layout (3x3 grid with alternating spin directions):
    ┌───────────────────┐
    │ ⚙️cw  ⚙️ccw  ⚙️cw │  Edge gears spin one way
    │ ⚙️ccw ⚙️cw  ⚙️ccw │  Center gear opposite
    │ ⚙️cw  ⚙️ccw  ⚙️cw │  Creates meshing illusion
    └───────────────────┘
    """
    # Pattern of colors (L0=deep, L4=light) and spin directions (alternating for mesh)
    # Position 4 (center) is always L0, edges gradient outward
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
                   ('l3','ccw'), ('l2','cw'), ('l3','ccw'),
                   ('l2','cw'), ('l1','ccw'), ('l2','cw')],
        'bottom': [('l2','cw'), ('l1','ccw'), ('l2','cw'),
                   ('l3','ccw'), ('l2','cw'), ('l3','ccw'),
                   ('l4','cw'), ('l4','ccw'), ('l4','cw')],
    }
    gears = ''.join(
        f'<div class="gear {color} spin-{spin}"></div>'
        for color, spin in patterns.get(face_class, patterns['front'])
    )
    return f'<div class="cube-face {face_class}">{gears}</div>'


def render_search_bar(show_hero: bool = True) -> Optional[str]:
    """
    Render search bar with optional hero section (gear cube + headline).

    Args:
        show_hero: If True, show the animated gear cube and headline (landing page).
                   If False, show only the compact search bar (after search).

    Returns:
        Search query if submitted (via Enter or button click), None otherwise
    """
    # Inject CSS
    st.markdown(_get_minimal_landing_css(), unsafe_allow_html=True)

    if show_hero:
        # Landing page: Full hero with gear cube + headline
        cube_faces = ''.join(_generate_cube_face_html(face) for face in ['front', 'back', 'right', 'left', 'top', 'bottom'])
        st.markdown(f"""
        <div class="landing-wrapper">
            <div class="cube-container">
                <div class="cube">
                    {cube_faces}
                </div>
            </div>
            <div class="landing-content">
                <h1 class="minimal-headline">
                    {t("search_headline")}
                </h1>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Full-width search form
    col_spacer1, col_search, col_spacer2 = st.columns([0.5, 5, 0.5])
    with col_search:
        with st.form(key="datagouv_search_form", clear_on_submit=False):
            query = st.text_input(
                label=t("search_datasets_label"),
                placeholder=t("search_placeholder"),
                key="datagouv_search_input",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button(
                t("search_button"),
                use_container_width=True,
                type="primary",
            )

            if submitted and query:
                return query.strip()

        # Small upload nudge below search button
        st.markdown("""
            <div style="text-align: center; margin-top: 8px;">
                <span style="font-size: 0.8rem; color: #94a3b8;">
                    or
                </span>
            </div>
        """, unsafe_allow_html=True)

        from intuitiveness.streamlit_app import smart_load_csv

        # Absolutely centered upload button (hide if data already uploaded)
        if not st.session_state.get("raw_data"):
            upload_placeholder = st.empty()

            with upload_placeholder.container():
                # Use columns to center the uploader - wider side columns
                col1, col2, col3 = st.columns([2, 1, 2])
                with col2:
                    uploaded_file = st.file_uploader(
                        "Upload your CSV data",
                        type=["csv"],
                        key="search_bar_csv_upload",
                        label_visibility="collapsed"
                    )

            if uploaded_file is not None:
                # Hide uploader and show centered spinner
                with upload_placeholder.container():
                    col1, col2, col3 = st.columns([2, 1, 2])
                    with col2:
                        st.markdown('<div style="text-align: center; padding: 10px 0;">', unsafe_allow_html=True)
                        st.spinner("Loading...")
                        st.markdown('</div>', unsafe_allow_html=True)

                # Check if file is already loaded
                raw_data = st.session_state.get("raw_data", {})
                if not isinstance(raw_data, dict):
                    st.session_state.raw_data = {}
                    raw_data = {}

                already_loaded = uploaded_file.name in raw_data

                # Only process if this is a new file
                if not already_loaded:
                    with st.spinner("Loading your data..."):
                        try:
                            df, info_msg = smart_load_csv(uploaded_file)

                            if df is not None and not df.empty:
                                # Store in raw_data
                                st.session_state.raw_data[uploaded_file.name] = df

                                # Success - stay on step 0 but wizard will show
                                st.rerun()
                            else:
                                st.error(f"Failed to load CSV: {info_msg if info_msg else 'Unknown error'}")
                        except Exception as e:
                            import traceback
                            st.error(f"Error loading file: {str(e)}")
                            st.code(traceback.format_exc())
        else:
            uploaded_file = None

    return None


def _get_minimal_landing_css() -> str:
    """
    Return CSS for landing page with animated gear cube background.

    The gear cube represents interlocking data transformations:
    - Gears = data processing units at each abstraction level
    - Meshing = how levels connect and influence each other
    - Counter-rotation = bidirectional ascent/descent flow
    """
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

    /* Landing wrapper - positions cube behind content */
    .landing-wrapper {
        position: relative;
        min-height: 200px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 40px 20px 20px 20px;
    }

    /* Gear cube container */
    .cube-container {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -60%);
        perspective: 600px;
        z-index: 0;
        opacity: 0.12;
    }

    /* 3D cube - shuffle and reorganize animation */
    .cube {
        width: 150px;
        height: 150px;
        transform-style: preserve-3d;
        animation: shuffle-cube 16s ease-in-out infinite;
    }

    /* Shuffle → reorganize → pause cycle */
    @keyframes shuffle-cube {
        0%   { transform: rotateX(-15deg) rotateY(0deg) rotateZ(0deg); }
        8%   { transform: rotateX(25deg) rotateY(45deg) rotateZ(-10deg); }
        16%  { transform: rotateX(-30deg) rotateY(120deg) rotateZ(15deg); }
        24%  { transform: rotateX(20deg) rotateY(200deg) rotateZ(-20deg); }
        32%  { transform: rotateX(-25deg) rotateY(280deg) rotateZ(10deg); }
        40%  { transform: rotateX(35deg) rotateY(340deg) rotateZ(-15deg); }
        55%  { transform: rotateX(-10deg) rotateY(380deg) rotateZ(5deg); }
        70%  { transform: rotateX(-15deg) rotateY(360deg) rotateZ(0deg); }
        100% { transform: rotateX(-15deg) rotateY(360deg) rotateZ(0deg); }
    }

    /* Cube faces */
    .cube-face {
        position: absolute;
        width: 150px;
        height: 150px;
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 2px;
        padding: 6px;
        background: rgba(0, 47, 167, 0.03);
        border-radius: 10px;
        backface-visibility: visible;
    }

    .cube-face.front  { transform: translateZ(75px); }
    .cube-face.back   { transform: rotateY(180deg) translateZ(75px); }
    .cube-face.right  { transform: rotateY(90deg) translateZ(75px); }
    .cube-face.left   { transform: rotateY(-90deg) translateZ(75px); }
    .cube-face.top    { transform: rotateX(90deg) translateZ(75px); }
    .cube-face.bottom { transform: rotateX(-90deg) translateZ(75px); }

    /* Individual gear - circular with teeth */
    .gear {
        width: 42px;
        height: 42px;
        border-radius: 50%;
        position: relative;
    }

    .gear::after {
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
    }

    /* Klein Blue palette (L0=deep → L4=light) */
    .gear.l0 { background: #002fa7; }
    .gear.l1 { background: #0041d1; }
    .gear.l2 { background: #3b82f6; }
    .gear.l3 { background: #60a5fa; }
    .gear.l4 { background: #93c5fd; }

    /* Counter-rotation animations */
    .gear.spin-cw { animation: spin-cw 6s linear infinite; }
    .gear.spin-ccw { animation: spin-ccw 6s linear infinite; }

    @keyframes spin-cw { to { transform: rotate(360deg); } }
    @keyframes spin-ccw { to { transform: rotate(-360deg); } }

    /* Landing content - above cube */
    .landing-content {
        position: relative;
        z-index: 1;
        text-align: center;
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .minimal-headline {
        font-size: 2.2rem;
        font-weight: 600;
        color: #1e293b;
        margin: 0 0 8px 0;
        line-height: 1.3;
    }

    .minimal-headline .accent {
        color: #002fa7;
    }

    /* Style the search input */
    .stTextInput input {
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif !important;
        font-size: 1rem !important;
        padding: 12px 16px !important;
        border-radius: 8px !important;
        border: 1px solid #e2e8f0 !important;
        background: #fff !important;
    }

    .stTextInput input:focus {
        border-color: #002fa7 !important;
        box-shadow: 0 0 0 2px rgba(0, 47, 167, 0.1) !important;
    }

    /* File Uploader - Clean Button Only */
    [data-testid="stFileUploader"] {
        width: 100% !important;
        text-align: center !important;
    }
    [data-testid="stFileUploader"] > div {
        width: 100% !important;
        text-align: center !important;
    }
    [data-testid="stFileUploader"] section {
        border: none !important;
        padding: 0 !important;
        background: transparent !important;
        min-height: auto !important;
        width: 100% !important;
        text-align: center !important;
    }
    [data-testid="stFileUploader"] section > div {
        width: 100% !important;
        text-align: center !important;
    }
    [data-testid="stFileUploader"] section > div > div {
        width: 100% !important;
        text-align: center !important;
        display: inline-block !important;
    }
    /* Hide text elements */
    [data-testid="stFileUploader"] small {
        display: none !important;
    }
    [data-testid="stFileUploader"] ul {
        display: none !important;
    }
    [data-testid="stFileUploader"] section span:not(:has(button)) {
        display: none !important;
    }
    [data-testid="stFileUploader"] section svg {
        display: none !important;
    }
    /* FORCE button to be visible and CENTERED */
    [data-testid="stFileUploader"] button {
        display: inline-flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        font-size: 0 !important;
        padding: 8px 20px !important;
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%) !important;
        border: 1.5px solid #e2e8f0 !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06) !important;
        transition: all 0.2s ease !important;
        cursor: pointer !important;
        margin: 0 auto !important;
    }
    [data-testid="stFileUploader"] button::before {
        content: 'Upload your data (CSV)' !important;
        font-size: 0.85rem !important;
        color: #475569 !important;
        font-weight: 500 !important;
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    [data-testid="stFileUploader"] button:hover {
        background: linear-gradient(135deg, #002fa7 0%, #0041d1 100%) !important;
        border-color: #002fa7 !important;
        box-shadow: 0 4px 12px rgba(0, 47, 167, 0.2) !important;
        transform: translateY(-1px) !important;
    }
    [data-testid="stFileUploader"] button:hover::before {
        color: white !important;
    }

    /* Style the search button */
    .stFormSubmitButton button {
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif !important;
        font-weight: 500 !important;
        background: #002fa7 !important;
        border-radius: 8px !important;
        padding: 12px 24px !important;
    }

    .stFormSubmitButton button:hover {
        background: #001d6e !important;
    }
    </style>
    """


def render_dataset_card(
    dataset: DatasetInfo,
    service: DataGouvSearchService,
    card_idx: int
) -> Optional[Tuple[pd.DataFrame, str]]:
    """
    Render an expandable dataset card with full title/description.

    Returns:
        Tuple of (DataFrame, filename) if user clicked load and it succeeded
    """
    # Format date (short)
    date_str = dataset.last_modified.strftime("%b %Y") if dataset.last_modified else ""

    # Short title for collapsed view
    short_title = dataset.title[:40] + "…" if len(dataset.title) > 40 else dataset.title

    # Truncate org name (short)
    org = dataset.organization_name[:18] + "…" if len(dataset.organization_name) > 18 else dataset.organization_name

    # CSV indicator
    csv_icon = "●" if dataset.has_csv else "○"
    csv_color = COLORS["success"] if dataset.has_csv else COLORS["text_muted"]

    # Expander with full details
    with st.expander(f"{csv_icon} {short_title}", expanded=False):
        # Full title
        st.markdown(f"**{dataset.title}**")

        # Description
        if dataset.description:
            st.markdown(f"<div style='font-size: 0.85rem; color: {COLORS['text_secondary']}; margin: 8px 0;'>{dataset.description}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='font-size: 0.85rem; color: {COLORS['text_muted']}; font-style: italic;'>{t('no_description_available')}</div>", unsafe_allow_html=True)

        # Metadata row
        st.markdown(f"<div style='font-size: 0.75rem; color: {COLORS['text_muted']}; margin-top: 8px;'>📦 {org} · 📅 {date_str}</div>", unsafe_allow_html=True)

        # Action button
        if dataset.has_csv:
            if st.button(
                f"➕ {t('add_to_selection')}",
                key=f"add_{card_idx}_{dataset.id}",
                use_container_width=True,
                type="primary",
            ):
                with st.spinner(t("loading")):
                    result = _load_dataset_csv(service, dataset)
                    if result:
                        _add_to_basket(dataset.title, result[1], len(result[0]))
                        return result
                    else:
                        st.error(t("failed_to_load"))
        else:
            st.button(
                t("no_csv"),
                key=f"no_csv_{card_idx}_{dataset.id}",
                use_container_width=True,
                disabled=True,
            )

    return None


def _add_to_basket(dataset_title: str, filename: str, row_count: int) -> None:
    """Add a loaded dataset to the basket (session state)."""
    if "datagouv_basket" not in st.session_state:
        st.session_state.datagouv_basket = []

    # Avoid duplicates
    for item in st.session_state.datagouv_basket:
        if item["filename"] == filename:
            return

    st.session_state.datagouv_basket.append({
        "title": dataset_title[:30] + "…" if len(dataset_title) > 30 else dataset_title,
        "filename": filename,
        "rows": row_count,
    })


def render_basket_sidebar() -> bool:
    """
    Render the dataset basket in the sidebar.

    Returns:
        True if user clicked "Continue with datasets", False otherwise
    """
    loaded = st.session_state.get("datagouv_loaded_datasets", {})

    if not loaded:
        return False

    # Elegant basket header
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {COLORS['accent']}15 0%, {COLORS['accent']}05 100%);
        border-left: 3px solid {COLORS['accent']};
        border-radius: 0 8px 8px 0;
        padding: 12px 14px;
        margin-bottom: 12px;
    ">
        <div style="
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            color: {COLORS['accent']};
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 10px;
        ">
            📦 {t("selected")} ({len(loaded)})
        </div>
    """, unsafe_allow_html=True)

    # Compact dataset chips
    for name, df in loaded.items():
        short_name = name[:20] + "…" if len(name) > 20 else name
        st.markdown(f"""
        <div style="
            background: white;
            border-radius: 6px;
            padding: 8px 10px;
            margin-bottom: 6px;
            border: 1px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        ">
            <div>
                <div style="font-size: 0.75rem; font-weight: 500; color: {COLORS['text_primary']};">{short_name}</div>
                <div style="font-size: 0.65rem; color: {COLORS['text_muted']};">{df.shape[0]:,} × {df.shape[1]}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Continue button
    if st.button(f"✅ {t('continue_button')}", type="primary", use_container_width=True, key="basket_continue"):
        return True

    # Clear basket link
    if st.button(f"🗑️ {t('clear_all')}", use_container_width=True, key="basket_clear"):
        st.session_state.datagouv_loaded_datasets = {}
        st.rerun()

    st.divider()
    return False


def render_dataset_grid(
    datasets: List[DatasetInfo],
    service: DataGouvSearchService,
    columns: int = 3
) -> Optional[Tuple[pd.DataFrame, str]]:
    """
    Render datasets in a side-by-side card grid layout.

    Args:
        datasets: List of datasets to display
        service: The search service for loading data
        columns: Number of columns in the grid (default: 2)

    Returns:
        Tuple of (DataFrame, filename) if user loaded a dataset
    """
    if not datasets:
        return None

    # Process datasets in rows of `columns` cards each
    for row_start in range(0, len(datasets), columns):
        row_datasets = datasets[row_start:row_start + columns]
        cols = st.columns(columns)

        for col_idx, dataset in enumerate(row_datasets):
            with cols[col_idx]:
                result = render_dataset_card(dataset, service, row_start + col_idx)
                if result:
                    return result

    return None


def render_no_results(query: str) -> None:
    """Render no results message using 007 design system."""
    st.markdown(f"""
    <div class="content-card" style="text-align: center; padding: 48px 24px;">
        <div style="font-size: 48px; margin-bottom: 16px;">🔍</div>
        <p style="color: {COLORS['text_primary']}; font-size: 1.1rem; margin-bottom: 8px;">
            {t("no_datasets_found")} "<strong style="color: {COLORS['accent']};">{query}</strong>"
        </p>
        <p style="color: {COLORS['text_muted']}; font-size: 0.9rem;">
            {t("try_different_keywords")}
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_error_state(error: str) -> None:
    """Render error message using 007 design system colors."""
    st.markdown(f"""
    <div style="background: {COLORS['error_bg']}; border: 1px solid {COLORS['error']};
                border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;">
        <span style="color: {COLORS['error']}; font-weight: 500;">⚠️ {error}</span>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# Main Search Interface - Simplified
# =============================================================================

def render_search_interface() -> Optional[pd.DataFrame]:
    """
    Render the complete search interface with direct one-click loading.
    Uses 007 design system for professional SaaS appearance.

    Returns:
        DataFrame if user loaded a dataset, None otherwise
    """
    _init_session_state()
    service = _get_service()

    # Inject 007 design system styles (palette + layout + search-specific)
    st.markdown(f"<style>{PALETTE_CSS}</style>", unsafe_allow_html=True)
    st.markdown(f"<style>{LAYOUT_CSS}</style>", unsafe_allow_html=True)
    st.markdown(get_search_styles(), unsafe_allow_html=True)

    # Check for error state
    error = st.session_state.get(SESSION_KEYS["error"])
    if error:
        render_error_state(error)
        st.session_state[SESSION_KEYS["error"]] = None

    # Check if we have results - hide hero if so
    has_results = st.session_state.get(SESSION_KEYS["results"]) is not None

    # Render search bar (hero only on landing, not after search)
    submitted_query = render_search_bar(show_hero=not has_results)

    # Handle new search
    if submitted_query:
        st.session_state[SESSION_KEYS["query"]] = submitted_query

        with st.spinner(t("searching")):
            try:
                results = service.search(submitted_query, page=1, page_size=10)
                st.session_state[SESSION_KEYS["results"]] = results
                st.session_state[SESSION_KEYS["error"]] = None

                # Store NL result for display (safe check for cached service)
                nl_result = getattr(service, 'last_nl_result', None)
                if nl_result:
                    st.session_state["datagouv_nl_keywords"] = nl_result.keywords
                else:
                    st.session_state["datagouv_nl_keywords"] = None

            except DataGouvAPIError:
                st.session_state[SESSION_KEYS["error"]] = t("search_failed")
                st.session_state[SESSION_KEYS["results"]] = None

        st.rerun()

    # Display results
    results: Optional[SearchResult] = st.session_state.get(SESSION_KEYS["results"])

    if results is not None:
        # Filter to only show datasets with CSV resources (Spec 008: CSV-only filter)
        csv_datasets = [d for d in results.datasets if d.has_csv]

        if len(csv_datasets) == 0:
            render_no_results(st.session_state.get(SESSION_KEYS["query"], ""))
        else:
            # Results count with NL keywords indicator
            nl_keywords = st.session_state.get("datagouv_nl_keywords")
            csv_count = len(csv_datasets)
            total_count = results.total

            if nl_keywords:
                keywords_display = ", ".join(nl_keywords[:4])
                st.success(f"**{t('datasets_found', count=csv_count)}** with CSV — {t('keywords_used', keywords=keywords_display)}")
            else:
                if csv_count < total_count:
                    st.success(f"**{t('datasets_found', count=csv_count)}** with CSV ({total_count} total) — {t('click_to_add')}")
                else:
                    st.success(f"**{t('datasets_found', count=csv_count)}** — {t('click_to_add')}")

            # Render dataset cards with direct load (CSV-only datasets)
            result = render_dataset_grid(csv_datasets, service)

            if result:
                df, filename = result
                # Store the loaded filename for the main app (no success message - basket shows selection)
                st.session_state['datagouv_last_dataset_name'] = filename
                return df

            # Load more button
            if results.has_more:
                if st.button(t("load_more"), use_container_width=True):
                    current_page = st.session_state.get(SESSION_KEYS["page"], 1)
                    with st.spinner(t("loading_more")):
                        try:
                            more_results = service.search(
                                st.session_state.get(SESSION_KEYS["query"], ""),
                                page=current_page + 1,
                                page_size=10
                            )
                            current_results = st.session_state.get(SESSION_KEYS["results"])
                            if current_results:
                                # Add all datasets (CSV filtering happens at display time)
                                current_results.datasets.extend(more_results.datasets)
                                current_results.has_more = more_results.has_more
                                current_results.page = more_results.page
                            st.session_state[SESSION_KEYS["page"]] = current_page + 1
                        except DataGouvAPIError:
                            st.error(t("failed_load_more"))

                    st.rerun()

    return None


# =============================================================================
# Exports (maintain backwards compatibility)
# =============================================================================

def render_resource_selector(resources: List[ResourceInfo], key_prefix: str = "") -> Optional[str]:
    """Legacy function - kept for backwards compatibility but simplified."""
    if not resources:
        return None

    # Just return the first resource URL
    return resources[0].url if resources else None


def render_loading_state(message: str) -> None:
    """Render loading spinner with message."""
    st.spinner(message)
