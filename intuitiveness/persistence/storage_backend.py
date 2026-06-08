"""
Storage backend for session persistence.

Provides localStorage access via streamlit-javascript bridge.
"""

from typing import Optional

try:
    import streamlit as st  # optional: only needed with the "app" extra
except ImportError:
    st = None

try:
    from streamlit_javascript import st_javascript
    HAS_JS = True
except ImportError:
    HAS_JS = False


class StorageBackend:
    """
    localStorage backend for session persistence.

    Uses streamlit-javascript to interact with browser localStorage.
    """

    def __init__(self, storage_key: str = "data_redesign_session"):
        """
        Initialize the storage backend.

        Args:
            storage_key: localStorage key name
        """
        self.storage_key = storage_key
        self._js_available = HAS_JS

    def is_available(self) -> bool:
        """Check if localStorage is available."""
        return self._js_available

    def get(self) -> Optional[str]:
        """
        Get data from localStorage.

        Returns:
            Stored data as string, or None if not found
        """
        if not self._js_available:
            return None

        try:
            result = st_javascript(f"localStorage.getItem('{self.storage_key}')")
            return result if result else None
        except Exception:
            return None

    def set(self, data: str) -> bool:
        """
        Set data in localStorage.

        Args:
            data: Data to store (must be string)

        Returns:
            True if successful, False otherwise
        """
        if not self._js_available:
            return False

        try:
            # Check data size - localStorage has ~5MB limit per key
            data_size = len(data.encode('utf-8'))
            if data_size > 4 * 1024 * 1024:  # 4MB limit to be safe
                # Too large - skip silently
                return False

            # Escape quotes and special characters for JS
            escaped_data = data.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '\\r')
            st_javascript(f"localStorage.setItem('{self.storage_key}', '{escaped_data}')")
            return True
        except Exception:
            # Silently fail - don't call st.warning during lifecycle
            return False

    def remove(self) -> bool:
        """
        Remove data from localStorage.

        Returns:
            True if successful, False otherwise
        """
        if not self._js_available:
            return False

        try:
            st_javascript(f"localStorage.removeItem('{self.storage_key}')")
            return True
        except Exception:
            return False

    def has(self) -> bool:
        """
        Check if data exists in localStorage.

        Returns:
            True if data exists, False otherwise
        """
        if not self._js_available:
            return False

        try:
            result = st_javascript(f"localStorage.getItem('{self.storage_key}') !== null")
            return bool(result)
        except Exception:
            return False

    def get_available_space(self) -> int:
        """
        Estimate available localStorage space.

        Returns:
            Estimated available bytes (conservative estimate)
        """
        # localStorage limit is typically 5-10MB per origin
        # Return conservative estimate of 5MB
        return 5 * 1024 * 1024
