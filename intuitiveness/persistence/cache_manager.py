"""
Cache Manager - Comprehensive Session Caching

Implements Spec 005: FR-001-005 (Comprehensive Caching)
Handles caching of expensive operations for session persistence.

Features:
- Cache semantic join results (avoid re-computation)
- Cache wizard step position
- Cache user selections and form values
- Cache joined datasets
- Automatic cache invalidation on data changes

Usage:
    from intuitiveness.persistence.cache_manager import CacheManager

    cache = CacheManager()

    # Cache semantic results
    cache.set_semantic_results("file1_file2", matches)
    results = cache.get_semantic_results("file1_file2")

    # Cache joined dataset
    cache.set_joined_dataset(joined_df)
    df = cache.get_joined_dataset()
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL_SECONDS = 3600  # 1 hour default TTL
MAX_CACHE_SIZE_MB = 50  # Maximum cache size in memory


@dataclass
class CacheEntry:
    """A single cache entry with metadata."""
    key: str
    value: Any
    timestamp: datetime
    size_bytes: int
    ttl_seconds: int = CACHE_TTL_SECONDS

    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        age = datetime.now() - self.timestamp
        return age.total_seconds() > self.ttl_seconds

    def get_age_seconds(self) -> float:
        """Get the age of this cache entry in seconds."""
        age = datetime.now() - self.timestamp
        return age.total_seconds()


class CacheManager:
    """
    Manages comprehensive session caching.

    Implements Spec 005: FR-001-005
    - Caches semantic join results (expensive computation)
    - Caches wizard step position
    - Caches user selections
    - Caches joined datasets
    - Auto-invalidates on data changes
    """

    def __init__(self):
        """Initialize cache manager with session state."""
        if 'cache_entries' not in st.session_state:
            st.session_state['cache_entries'] = {}

    def _compute_hash(self, data: Any) -> str:
        """
        Compute a hash for cache key generation.

        Args:
            data: Data to hash (dict, list, DataFrame, etc.)

        Returns:
            SHA256 hash string
        """
        if isinstance(data, pd.DataFrame):
            # Hash DataFrame shape and first/last rows
            key_data = f"{data.shape}_{data.head(1).to_json()}_{data.tail(1).to_json()}"
        elif isinstance(data, dict):
            key_data = json.dumps(data, sort_keys=True)
        elif isinstance(data, list):
            key_data = json.dumps(data)
        else:
            key_data = str(data)

        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = CACHE_TTL_SECONDS
    ) -> None:
        """
        Set a cache entry.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds
        """
        # Estimate size
        try:
            if isinstance(value, pd.DataFrame):
                size_bytes = value.memory_usage(deep=True).sum()
            else:
                size_bytes = len(json.dumps(value, default=str))
        except Exception:
            size_bytes = 1024  # Default estimate

        entry = CacheEntry(
            key=key,
            value=value,
            timestamp=datetime.now(),
            size_bytes=size_bytes,
            ttl_seconds=ttl_seconds
        )

        st.session_state['cache_entries'][key] = entry
        logger.info(f"Cached '{key}' ({size_bytes} bytes, TTL={ttl_seconds}s)")

    def get(self, key: str) -> Optional[Any]:
        """
        Get a cache entry.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        entries = st.session_state.get('cache_entries', {})
        entry = entries.get(key)

        if entry is None:
            return None

        if entry.is_expired():
            logger.info(f"Cache expired: '{key}'")
            del entries[key]
            return None

        logger.debug(f"Cache hit: '{key}' (age={entry.get_age_seconds():.1f}s)")
        return entry.value

    def invalidate(self, key: str) -> None:
        """
        Invalidate a specific cache entry.

        Args:
            key: Cache key to invalidate
        """
        entries = st.session_state.get('cache_entries', {})
        if key in entries:
            del entries[key]
            logger.info(f"Invalidated cache: '{key}'")

    def clear_all(self) -> None:
        """Clear all cache entries."""
        st.session_state['cache_entries'] = {}
        logger.info("Cleared all cache entries")

    # Semantic results caching (FR-002)

    def set_semantic_results(
        self,
        pair_key: str,
        matches: List[Tuple[str, str, float]]
    ) -> None:
        """
        Cache semantic matching results.

        Args:
            pair_key: Unique identifier for the column pair (e.g., "file1_col1__file2_col2")
            matches: List of (value1, value2, similarity_score) tuples
        """
        cache_key = f"semantic_{pair_key}"
        self.set(cache_key, matches, ttl_seconds=7200)  # 2 hour TTL

    def get_semantic_results(
        self,
        pair_key: str
    ) -> Optional[List[Tuple[str, str, float]]]:
        """
        Get cached semantic matching results.

        Args:
            pair_key: Column pair identifier

        Returns:
            List of matches or None if not cached
        """
        cache_key = f"semantic_{pair_key}"
        return self.get(cache_key)

    # Wizard step caching (FR-003)

    def set_wizard_step(self, step: int) -> None:
        """
        Cache current wizard step.

        Args:
            step: Wizard step number (0-based)
        """
        self.set("wizard_step", step, ttl_seconds=86400)  # 24 hour TTL

    def get_wizard_step(self) -> Optional[int]:
        """
        Get cached wizard step.

        Returns:
            Step number or None if not cached
        """
        return self.get("wizard_step")

    # Joined dataset caching (FR-004)

    def set_joined_dataset(self, df: pd.DataFrame, config: Dict) -> None:
        """
        Cache joined dataset with configuration.

        Args:
            df: Joined DataFrame
            config: Join configuration used
        """
        config_hash = self._compute_hash(config)
        cache_key = f"joined_dataset_{config_hash}"
        self.set(cache_key, df, ttl_seconds=3600)  # 1 hour TTL

    def get_joined_dataset(self, config: Dict) -> Optional[pd.DataFrame]:
        """
        Get cached joined dataset if configuration matches.

        Args:
            config: Join configuration to match

        Returns:
            Cached DataFrame or None
        """
        config_hash = self._compute_hash(config)
        cache_key = f"joined_dataset_{config_hash}"
        return self.get(cache_key)

    # User selections caching (FR-005)

    def set_user_selections(self, selections: Dict[str, Any]) -> None:
        """
        Cache user selections (columns, domains, etc.).

        Args:
            selections: Dictionary of user selections
        """
        self.set("user_selections", selections, ttl_seconds=86400)  # 24 hour TTL

    def get_user_selections(self) -> Optional[Dict[str, Any]]:
        """
        Get cached user selections.

        Returns:
            Dictionary of selections or None
        """
        return self.get("user_selections")

    # Cache statistics

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (size, entry count, hit rate, etc.)
        """
        entries = st.session_state.get('cache_entries', {})

        total_size_bytes = sum(e.size_bytes for e in entries.values())
        total_entries = len(entries)
        expired_entries = sum(1 for e in entries.values() if e.is_expired())

        return {
            'total_entries': total_entries,
            'active_entries': total_entries - expired_entries,
            'expired_entries': expired_entries,
            'total_size_bytes': total_size_bytes,
            'total_size_mb': total_size_bytes / (1024 * 1024),
        }
