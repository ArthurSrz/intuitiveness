"""
Session persistence module.

Provides session state persistence to browser localStorage
for the Data Redesign wizard.
"""

from .session_store import (
    SessionStore,
    SaveResult,
    LoadResult,
    SessionInfo,
    PersistenceError,
    StorageQuotaExceeded,
    SessionCorrupted,
    VersionMismatch,
)

from .serializers import (
    serialize_dataframe,
    deserialize_dataframe,
    serialize_graph,
    deserialize_graph,
    serialize_value,
    deserialize_value,
)

from .storage_backend import StorageBackend

# Cache manager (Spec 005: FR-001-005)
from .cache_manager import CacheManager, CacheEntry

__all__ = [
    # Main API
    'SessionStore',
    'SaveResult',
    'LoadResult',
    'SessionInfo',

    # Exceptions
    'PersistenceError',
    'StorageQuotaExceeded',
    'SessionCorrupted',
    'VersionMismatch',

    # Serializers
    'serialize_dataframe',
    'deserialize_dataframe',
    'serialize_graph',
    'deserialize_graph',
    'serialize_value',
    'deserialize_value',

    # Backend
    'StorageBackend',

    # Cache manager (Spec 005)
    'CacheManager',
    'CacheEntry',
]
