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

# Export all functions
__all__ = [
    "t",
    "get_language",
    "set_language",
    "SUPPORTED_LANGUAGES",
    "SESSION_KEY_LANGUAGE",
    "DEFAULT_LANGUAGE",
]
