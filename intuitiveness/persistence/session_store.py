"""
Session store for persistence.

Main class for managing session state persistence to browser localStorage.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd
import networkx as nx
try:
    import streamlit as st  # optional: only needed with the "app" extra
except ImportError:
    st = None

from .serializers import (
    serialize_dataframe,
    deserialize_dataframe,
    serialize_graph,
    deserialize_graph,
    serialize_value,
    deserialize_value,
    get_compressed_size,
)
from .storage_backend import StorageBackend

logger = logging.getLogger(__name__)

# Schema version for migration support
SCHEMA_VERSION = "1.0.0"

# Session keys to persist
PERSIST_KEYS = [
    'wizard_step',
    'current_step',  # Guided mode step
    'nav_mode',
    'raw_data',
    'datasets',
    'form_values',
    'entity_mapping',
    'relationship_mapping',
    'semantic_results',
    'selected_files',
    'connections',
    'connection_methods',
    'domains',
    'categorizations',
    'joined_l3_dataset',
    'answers',  # User answers in guided mode
    'data_model',
]

# Maximum session age in seconds (7 days)
MAX_SESSION_AGE = 7 * 24 * 60 * 60

# Debounce interval in seconds
DEBOUNCE_INTERVAL = 2.0


class PersistenceError(Exception):
    """Base class for persistence errors."""
    pass


class StorageQuotaExceeded(PersistenceError):
    """Raised when localStorage quota is exceeded."""
    def __init__(self, required_bytes: int, available_bytes: int):
        self.required_bytes = required_bytes
        self.available_bytes = available_bytes
        super().__init__(
            f"Storage quota exceeded: need {required_bytes} bytes, "
            f"only {available_bytes} available"
        )


class SessionCorrupted(PersistenceError):
    """Raised when stored session data is invalid."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Session data corrupted: {reason}")


class VersionMismatch(PersistenceError):
    """Raised when session schema version is incompatible."""
    def __init__(self, stored_version: str, current_version: str):
        self.stored_version = stored_version
        self.current_version = current_version
        super().__init__(
            f"Session version mismatch: stored={stored_version}, "
            f"current={current_version}"
        )


@dataclass
class SaveResult:
    """Result of a save operation."""
    success: bool
    bytes_saved: int = 0
    warnings: List[str] = field(default_factory=list)


@dataclass
class LoadResult:
    """Result of a load operation."""
    success: bool
    wizard_step: int = 0
    file_count: int = 0
    dataset_levels: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class SessionInfo:
    """Metadata about a saved session."""
    timestamp: datetime
    wizard_step: int
    file_count: int
    total_size_bytes: int
    version: str


class SessionStore:
    """
    Manages session state persistence to browser localStorage.

    Usage:
        store = SessionStore()

        # Save current session
        store.save()

        # Load session on app start
        if store.has_saved_session():
            store.load()

        # Clear session
        store.clear()
    """

    def __init__(self, storage_key: str = "data_redesign_session"):
        """
        Initialize the session store.

        Args:
            storage_key: localStorage key name
        """
        self.storage_key = storage_key
        self._backend = StorageBackend(storage_key)
        self._last_save_time = 0.0

    def save(self, force: bool = False) -> SaveResult:
        """
        Save current st.session_state to localStorage.

        Args:
            force: If True, bypass debounce check

        Returns:
            SaveResult with success status and any warnings

        Raises:
            StorageQuotaExceeded: If data exceeds localStorage limit
        """
        # Debounce check
        current_time = time.time()
        if not force and (current_time - self._last_save_time) < DEBOUNCE_INTERVAL:
            return SaveResult(success=True, warnings=["Save debounced"])

        warnings = []
        session_data = {
            'version': SCHEMA_VERSION,
            'timestamp': datetime.now().isoformat(),
            'data': {},
        }

        # Serialize each persisted key
        for key in PERSIST_KEYS:
            if key in st.session_state:
                try:
                    value = st.session_state[key]
                    serialized = self._serialize_value(key, value)
                    if serialized is not None:
                        session_data['data'][key] = serialized
                except Exception as e:
                    warnings.append(f"Failed to serialize {key}: {e}")
                    logger.warning(f"Failed to serialize {key}: {e}")

        # Convert to JSON
        try:
            json_data = json.dumps(session_data)
        except Exception as e:
            return SaveResult(success=False, warnings=[f"JSON serialization failed: {e}"])

        # Check size
        data_size = len(json_data.encode('utf-8'))
        available = self._backend.get_available_space()

        if data_size > available:
            raise StorageQuotaExceeded(data_size, available)

        # Save to localStorage
        success = self._backend.set(json_data)

        if success:
            self._last_save_time = current_time
            logger.info(f"Session saved: {data_size} bytes")

        return SaveResult(
            success=success,
            bytes_saved=data_size if success else 0,
            warnings=warnings
        )

    def load(self) -> LoadResult:
        """
        Load session from localStorage into st.session_state.

        Returns:
            LoadResult with success status and loaded data summary

        Raises:
            SessionCorrupted: If stored data is invalid
            VersionMismatch: If schema version is incompatible
        """
        warnings = []
        dataset_levels = []

        # Get data from localStorage
        json_data = self._backend.get()
        if not json_data:
            return LoadResult(success=False, warnings=["No saved session found"])

        # Parse JSON
        try:
            session_data = json.loads(json_data)
        except json.JSONDecodeError as e:
            raise SessionCorrupted(f"Invalid JSON: {e}")

        # Check version
        stored_version = session_data.get('version', '0.0.0')
        if stored_version.split('.')[0] != SCHEMA_VERSION.split('.')[0]:
            raise VersionMismatch(stored_version, SCHEMA_VERSION)

        # Check timestamp
        try:
            timestamp = datetime.fromisoformat(session_data.get('timestamp', ''))
            age = (datetime.now() - timestamp).total_seconds()
            if age > MAX_SESSION_AGE:
                warnings.append(f"Session is {age // 86400:.0f} days old")
        except Exception:
            warnings.append("Could not verify session age")

        # Deserialize data
        data = session_data.get('data', {})
        wizard_step = 0
        file_count = 0

        for key, serialized in data.items():
            try:
                value = self._deserialize_value(key, serialized)
                if value is not None:
                    st.session_state[key] = value

                    # Track stats
                    if key == 'wizard_step' or key == 'current_step':
                        wizard_step = value if isinstance(value, int) else wizard_step
                    elif key == 'raw_data' and isinstance(value, dict):
                        file_count = len(value)
                    elif key == 'datasets' and isinstance(value, dict):
                        dataset_levels = list(value.keys())

            except Exception as e:
                warnings.append(f"Failed to restore {key}: {e}")
                logger.warning(f"Failed to deserialize {key}: {e}")

        logger.info(f"Session loaded: step={wizard_step}, files={file_count}")

        return LoadResult(
            success=True,
            wizard_step=wizard_step,
            file_count=file_count,
            dataset_levels=dataset_levels,
            warnings=warnings
        )

    def has_saved_session(self) -> bool:
        """
        Check if a saved session exists in localStorage.

        Returns:
            True if valid session data exists
        """
        json_data = self._backend.get()
        if not json_data:
            return False

        try:
            session_data = json.loads(json_data)
            return 'version' in session_data and 'data' in session_data
        except Exception:
            return False

    def clear(self) -> None:
        """
        Remove all session data from localStorage and reset session_state.
        """
        self._backend.remove()

        # Clear persisted keys from session_state
        for key in PERSIST_KEYS:
            if key in st.session_state:
                del st.session_state[key]

        logger.info("Session cleared")

    def export_session(self) -> Dict[str, Any]:
        """
        Export current session state as a serializable dictionary.

        Returns a dict containing all persisted session data, suitable for
        JSON serialization and download.

        Returns:
            Dictionary with version, timestamp, and serialized session data.
        """
        export_data = {
            'version': SCHEMA_VERSION,
            'timestamp': datetime.now().isoformat(),
            'data': {},
        }

        for key in PERSIST_KEYS:
            if key in st.session_state:
                try:
                    value = st.session_state[key]
                    serialized = self._serialize_value(key, value)
                    if serialized is not None:
                        export_data['data'][key] = serialized
                except Exception as e:
                    logger.warning(f"Failed to export {key}: {e}")

        return export_data

    def get_session_info(self) -> Optional[SessionInfo]:
        """
        Get metadata about saved session without loading it.

        Returns:
            SessionInfo with timestamp, step, file count, or None if no session
        """
        json_data = self._backend.get()
        if not json_data:
            return None

        try:
            session_data = json.loads(json_data)
            data = session_data.get('data', {})

            timestamp = datetime.fromisoformat(session_data.get('timestamp', datetime.now().isoformat()))
            wizard_step = 0

            # Try to get wizard_step or current_step from different serialization formats
            for step_key in ['wizard_step', 'current_step']:
                ws_data = data.get(step_key)
                if ws_data:
                    if isinstance(ws_data, dict):
                        if 'value' in ws_data:
                            wizard_step = ws_data['value']
                        elif 'data' in ws_data:
                            try:
                                wizard_step = deserialize_value(ws_data['data'])
                            except Exception:
                                pass
                    elif isinstance(ws_data, int):
                        wizard_step = ws_data
                    if wizard_step > 0:
                        break

            # Count files
            file_count = 0
            raw_data = data.get('raw_data')
            if raw_data:
                try:
                    if isinstance(raw_data, dict):
                        file_count = len(raw_data)
                    else:
                        deserialized = deserialize_value(raw_data)
                        if isinstance(deserialized, dict):
                            file_count = len(deserialized)
                except Exception:
                    pass

            return SessionInfo(
                timestamp=timestamp,
                wizard_step=wizard_step,
                file_count=file_count,
                total_size_bytes=len(json_data.encode('utf-8')),
                version=session_data.get('version', '0.0.0')
            )
        except Exception as e:
            logger.warning(f"Failed to get session info: {e}")
            return None

    def _serialize_value(self, key: str, value: Any) -> Optional[Dict[str, Any]]:
        """
        Serialize a value based on its type.

        Args:
            key: Session state key name
            value: Value to serialize

        Returns:
            Serialized data dict with type info, or None if not serializable
        """
        if value is None:
            return None

        if isinstance(value, pd.DataFrame):
            return {
                'type': 'dataframe',
                'data': serialize_dataframe(value),
                'metadata': {
                    'columns': list(value.columns),
                    'rows': len(value),
                }
            }
        elif isinstance(value, nx.Graph):
            return {
                'type': 'graph',
                'data': serialize_graph(value),
                'metadata': {
                    'nodes': value.number_of_nodes(),
                    'edges': value.number_of_edges(),
                }
            }
        elif isinstance(value, dict):
            # Handle dict of DataFrames or Graphs
            serialized_dict = {}
            for k, v in value.items():
                if isinstance(v, pd.DataFrame):
                    serialized_dict[k] = {
                        'type': 'dataframe',
                        'data': serialize_dataframe(v),
                    }
                elif isinstance(v, nx.Graph):
                    serialized_dict[k] = {
                        'type': 'graph',
                        'data': serialize_graph(v),
                    }
                elif hasattr(v, 'data'):
                    # Handle Level datasets (L0-L4)
                    if isinstance(v.data, pd.DataFrame):
                        serialized_dict[k] = {
                            'type': 'level_dataframe',
                            'data': serialize_dataframe(v.data),
                            'class': v.__class__.__name__,
                        }
                    elif isinstance(v.data, nx.Graph):
                        serialized_dict[k] = {
                            'type': 'level_graph',
                            'data': serialize_graph(v.data),
                            'class': v.__class__.__name__,
                        }
                    else:
                        serialized_dict[k] = {
                            'type': 'value',
                            'data': serialize_value(v.data),
                        }
                else:
                    try:
                        serialized_dict[k] = {
                            'type': 'value',
                            'data': serialize_value(v),
                        }
                    except Exception:
                        pass
            return {
                'type': 'dict',
                'data': serialized_dict,
            }
        else:
            # Try generic serialization
            try:
                return {
                    'type': 'value',
                    'data': serialize_value(value),
                }
            except Exception:
                return None

    def _deserialize_value(self, key: str, serialized: Dict[str, Any]) -> Any:
        """
        Deserialize a value based on its type.

        Args:
            key: Session state key name
            serialized: Serialized data dict

        Returns:
            Deserialized value
        """
        if not isinstance(serialized, dict) or 'type' not in serialized:
            return None

        value_type = serialized['type']
        data = serialized.get('data')

        if value_type == 'dataframe':
            return deserialize_dataframe(data)
        elif value_type == 'graph':
            return deserialize_graph(data)
        elif value_type == 'dict':
            result = {}
            for k, v in data.items():
                if isinstance(v, dict) and 'type' in v:
                    sub_type = v['type']
                    sub_data = v.get('data')

                    if sub_type == 'dataframe':
                        result[k] = deserialize_dataframe(sub_data)
                    elif sub_type == 'graph':
                        result[k] = deserialize_graph(sub_data)
                    elif sub_type in ('level_dataframe', 'level_graph'):
                        # Reconstruct Level datasets
                        class_name = v.get('class', '')
                        if sub_type == 'level_dataframe':
                            df = deserialize_dataframe(sub_data)
                            result[k] = self._reconstruct_level_dataset(class_name, df)
                        else:
                            graph = deserialize_graph(sub_data)
                            result[k] = self._reconstruct_level_dataset(class_name, graph)
                    elif sub_type == 'value':
                        result[k] = deserialize_value(sub_data)
                else:
                    result[k] = v
            return result
        elif value_type == 'value':
            return deserialize_value(data)

        return None

    def _reconstruct_level_dataset(self, class_name: str, data: Any) -> Any:
        """
        Reconstruct a Level dataset from its class name and data.

        Args:
            class_name: Name of the Level class (e.g., 'Level4Dataset')
            data: DataFrame or Graph data

        Returns:
            Reconstructed Level dataset
        """
        try:
            from intuitiveness.entities import (
                Level0Datum,
                Level1Vector,
                Level2Dataset,
                Level3Dataset,
                Level4Dataset,
            )

            class_map = {
                'Level0Datum': Level0Datum,
                'Level1Vector': Level1Vector,
                'Level2Dataset': Level2Dataset,
                'Level3Dataset': Level3Dataset,
                'Level4Dataset': Level4Dataset,
            }

            if class_name in class_map:
                return class_map[class_name](data)
        except ImportError:
            pass

        return data
