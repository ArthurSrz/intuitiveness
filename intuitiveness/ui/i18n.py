"""
Internationalization (i18n) - Thin Wrapper

Implements Spec 011: Code Simplification (2,280 → 50 lines)

This module is now a thin wrapper around intuitiveness.i18n.
All translations are stored in JSON files:
- intuitiveness/i18n/en.json (455 keys)
- intuitiveness/i18n/fr.json (455 keys)

Backward compatible with existing imports:
    from intuitiveness.ui.i18n import t
    t('upload_success', filename='data.csv', rows=100, cols=5)
"""

import streamlit as st

# Import from the new i18n package
from intuitiveness.i18n import (
    t,
    get_language,
    set_language,
    SUPPORTED_LANGUAGES,
)

# Session state key for language preference (for backward compatibility)
SESSION_KEY_LANGUAGE = "ui_language"

# Default language (for backward compatibility)
DEFAULT_LANGUAGE = "en"

# Translation dictionary for backward compatibility
TRANSLATIONS = {}  # Empty - translations are in JSON files


def render_language_toggle():
    """
    Render language toggle button (full version).

    Provides bilingual support (English/French).
    Spec 006: Playwright MCP E2E Testing - Bilingual support
    """
    col1, col2 = st.columns(2)

    current_lang = get_language()

    with col1:
        if st.button("🇬🇧 English", use_container_width=True,
                    disabled=(current_lang == "en"),
                    key="lang_toggle_en"):
            set_language("en")
            st.rerun()

    with col2:
        if st.button("🇫🇷 Français", use_container_width=True,
                    disabled=(current_lang == "fr"),
                    key="lang_toggle_fr"):
            set_language("fr")
            st.rerun()


def render_language_toggle_compact():
    """
    Render compact language toggle (sidebar version).

    Single-line toggle for sidebar display.
    Spec 006: Playwright MCP E2E Testing - Bilingual support
    """
    current_lang = get_language()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🇬🇧 EN" if current_lang != "en" else "**🇬🇧 EN**",
                    use_container_width=True,
                    key="lang_compact_en"):
            if current_lang != "en":
                set_language("en")
                st.rerun()

    with col2:
        if st.button("🇫🇷 FR" if current_lang != "fr" else "**🇫🇷 FR**",
                    use_container_width=True,
                    key="lang_compact_fr"):
            if current_lang != "fr":
                set_language("fr")
                st.rerun()


# Export all functions
__all__ = [
    "t",
    "get_language",
    "set_language",
    "SUPPORTED_LANGUAGES",
    "SESSION_KEY_LANGUAGE",
    "DEFAULT_LANGUAGE",
    "TRANSLATIONS",
    "render_language_toggle",
    "render_language_toggle_compact",
]
