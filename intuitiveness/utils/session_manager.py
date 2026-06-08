"""
Session State Manager

Centralizes all Streamlit session state keys and provides type-safe access.
Eliminates scattered magic strings and provides spec traceability.

Created: 2026-01-09 (Phase 0 - Code Simplification)
"""

from typing import Any, Dict, List, Optional, TypeVar
from dataclasses import dataclass
try:
    import streamlit as st  # optional: only needed with the "app" extra
except ImportError:
    st = None


# =============================================================================
# SESSION STATE KEYS - Centralized with Spec Traceability
# =============================================================================

class SessionStateKeys:
    """
    Centralized session state key definitions with spec traceability.

    Each key is annotated with the spec it belongs to:
    - 001: dataset-redesign-package
    - 002: ascent-functionality
    - 003: level-dataviz-display
    - 004: ascent-precision
    - 005: session-persistence
    - 006: playwright-mcp-e2e (i18n)
    - 007: streamlit-design-makeup (tutorial)
    - 008: datagouv-search
    - 009: quality-data-platform
    - 010: quality-ds-workflow
    """

    # =========================================================================
    # GUIDED MODE WORKFLOW (001-004)
    # =========================================================================

    # Current step in guided wizard (001)
    CURRENT_STEP = "current_step"

    # User answers collected during descent (001)
    ANSWERS = "answers"

    # Datasets at each level (001)
    DATASETS = "datasets"

    # Generated data model from discovery (001)
    DATA_MODEL = "data_model"

    # Raw uploaded data (001)
    RAW_DATA = "raw_data"

    # Neo4j execution state - guided mode (001)
    NEO4J_EXECUTED = "neo4j_executed"

    # Column mapping for graph building (001)
    COLUMN_MAPPING = "column_mapping"

    # =========================================================================
    # FREE NAVIGATION MODE (002-003)
    # =========================================================================

    # Navigation mode: 'guided' or 'free' (002)
    NAV_MODE = "nav_mode"

    # NavigationSession instance (002)
    NAV_SESSION = "nav_session"

    # Current navigation action (002)
    NAV_ACTION = "nav_action"

    # Navigation target (level/node) (002)
    NAV_TARGET = "nav_target"

    # Navigation export data (002)
    NAV_EXPORT = "nav_export"

    # Relationship builder instance (002)
    RELATIONSHIP_BUILDER = "relationship_builder"

    # Free navigation descent step (1=entities, 2=preview, 3=cypher) (002)
    NAV_DESCEND_STEP = "nav_descend_step"

    # Temporary data model during free descent (002)
    NAV_TEMP_DATA_MODEL = "nav_temp_data_model"

    # Temporary cypher queries during free descent (002)
    NAV_TEMP_CYPHER_QUERIES = "nav_temp_cypher_queries"

    # Neo4j execution state - free mode (002)
    NAV_NEO4J_EXECUTED = "nav_neo4j_executed"

    # Loaded session graph from import (002, 005)
    LOADED_SESSION_GRAPH = "loaded_session_graph"

    # Loaded graph decisions (002, 005)
    LOADED_GRAPH_DECISIONS = "loaded_graph_decisions"

    # Last saved graph filepath (002, 005)
    LAST_SAVED_GRAPH = "last_saved_graph"

    # Switch to ascent flag (internal) (002)
    SWITCH_TO_ASCENT = "_switch_to_ascent"

    # Mode selector widget state (internal) (002)
    MODE_SELECTOR = "mode_selector"

    # =========================================================================
    # SESSION PERSISTENCE (005)
    # =========================================================================

    # Recovery action from banner (005)
    RECOVERY_ACTION = "recovery_action"

    # =========================================================================
    # INTERNATIONALIZATION (006)
    # =========================================================================

    # UI language preference (006)
    LANGUAGE = "ui_language"

    # =========================================================================
    # TUTORIAL SYSTEM (007)
    # =========================================================================

    # Tutorial completed flag (007)
    TUTORIAL_COMPLETED = "tutorial_completed"

    # Tutorial step (legacy, keep for backwards compat) (007)
    TUTORIAL_STEP = "tutorial_step"

    # Show tutorial dialog flag (007)
    SHOW_TUTORIAL = "show_tutorial"

    # =========================================================================
    # DATA.GOUV.FR SEARCH (008)
    # =========================================================================

    # Catalog minimum score filter (008)
    CATALOG_FILTER_SCORE = "catalog_filter_score"

    # Catalog domain filter (008)
    CATALOG_FILTER_DOMAINS = "catalog_filter_domains"

    # Catalog search query (008)
    CATALOG_SEARCH_QUERY = "catalog_search_query"

    # Selected dataset ID in catalog (008)
    CATALOG_SELECTED_DATASET = "catalog_selected_dataset"

    # =========================================================================
    # QUALITY DASHBOARD (009-010)
    # =========================================================================

    # Quality report object (009)
    QUALITY_REPORT = "quality_report"

    # Quality assessment DataFrame (009)
    QUALITY_DF = "quality_df"

    # Quality assessment file name (009)
    QUALITY_FILE_NAME = "quality_file_name"

    # Assessment progress tracking (009)
    ASSESSMENT_PROGRESS = "assessment_progress"

    # Applied suggestions set (010)
    APPLIED_SUGGESTIONS = "applied_suggestions"

    # Transformed DataFrame after suggestions (010)
    TRANSFORMED_DF = "transformed_df"

    # Transformation log (010)
    TRANSFORMATION_LOG = "transformation_log"

    # Benchmark report (010)
    BENCHMARK_REPORT = "benchmark_report"

    # Export format preference (010)
    EXPORT_FORMAT = "export_format"

    # Quality reports history for versioning (010 - P0 Fix)
    QUALITY_REPORTS_HISTORY = "quality_reports_history"

    # Current report index in history (010 - P0 Fix)
    CURRENT_REPORT_INDEX = "current_report_index"

    # =========================================================================
    # DISCOVERY WIZARD (001, UI improvements)
    # =========================================================================

    # Wizard step (1=columns, 2=connections, 3=confirm) (001)
    WIZARD_STEP = "wizard_step"

    # Discovery results from auto-discovery (001)
    DISCOVERY_RESULTS = "discovery_results"

    # =========================================================================
    # CART-BASED DATASET SELECTION (Cart Workflow)
    # =========================================================================

    # Cart holding selected datasets (cart workflow)
    DATASET_CART = "dataset_cart"

    # Cart mode: 'selection' or 'processing' (cart workflow)
    CART_MODE = "cart_mode"

    # Analysis started flag (cart workflow)
    ANALYSIS_STARTED = "analysis_started"


# =============================================================================
# SESSION STATE MANAGER - Type-Safe Access
# =============================================================================

class SessionStateManager:
    """
    Type-safe session state access with centralized keys.

    Provides getter/setter methods for all session state values,
    eliminating scattered st.session_state[...] accesses.

    Example:
        >>> mgr = SessionStateManager()
        >>> mgr.nav_mode  # Get current mode
        'guided'
        >>> mgr.nav_mode = 'free'  # Set mode
    """

    # =========================================================================
    # GUIDED MODE PROPERTIES
    # =========================================================================

    @property
    def current_step(self) -> int:
        """Get current wizard step (0-based)."""
        return st.session_state.get(SessionStateKeys.CURRENT_STEP, 0)

    @current_step.setter
    def current_step(self, value: int) -> None:
        st.session_state[SessionStateKeys.CURRENT_STEP] = value

    @property
    def answers(self) -> Dict[str, Any]:
        """Get user answers dictionary."""
        return st.session_state.get(SessionStateKeys.ANSWERS, {})

    @answers.setter
    def answers(self, value: Dict[str, Any]) -> None:
        st.session_state[SessionStateKeys.ANSWERS] = value

    @property
    def datasets(self) -> Dict[str, Any]:
        """Get datasets dictionary (by level)."""
        return st.session_state.get(SessionStateKeys.DATASETS, {})

    @datasets.setter
    def datasets(self, value: Dict[str, Any]) -> None:
        st.session_state[SessionStateKeys.DATASETS] = value

    @property
    def data_model(self) -> Optional[Any]:
        """Get generated data model."""
        return st.session_state.get(SessionStateKeys.DATA_MODEL)

    @data_model.setter
    def data_model(self, value: Any) -> None:
        st.session_state[SessionStateKeys.DATA_MODEL] = value

    @property
    def raw_data(self) -> Optional[Any]:
        """Get raw uploaded data."""
        return st.session_state.get(SessionStateKeys.RAW_DATA)

    @raw_data.setter
    def raw_data(self, value: Any) -> None:
        st.session_state[SessionStateKeys.RAW_DATA] = value

    # =========================================================================
    # FREE NAVIGATION PROPERTIES
    # =========================================================================

    @property
    def nav_mode(self) -> str:
        """Get navigation mode ('guided' or 'free')."""
        return st.session_state.get(SessionStateKeys.NAV_MODE, 'guided')

    @nav_mode.setter
    def nav_mode(self, value: str) -> None:
        st.session_state[SessionStateKeys.NAV_MODE] = value

    @property
    def nav_session(self) -> Optional[Any]:
        """Get NavigationSession instance."""
        return st.session_state.get(SessionStateKeys.NAV_SESSION)

    @nav_session.setter
    def nav_session(self, value: Any) -> None:
        st.session_state[SessionStateKeys.NAV_SESSION] = value

    @property
    def nav_action(self) -> Optional[str]:
        """Get current navigation action."""
        return st.session_state.get(SessionStateKeys.NAV_ACTION)

    @nav_action.setter
    def nav_action(self, value: Optional[str]) -> None:
        st.session_state[SessionStateKeys.NAV_ACTION] = value

    @property
    def loaded_session_graph(self) -> Optional[Dict]:
        """Get loaded session graph data."""
        return st.session_state.get(SessionStateKeys.LOADED_SESSION_GRAPH)

    @loaded_session_graph.setter
    def loaded_session_graph(self, value: Optional[Dict]) -> None:
        st.session_state[SessionStateKeys.LOADED_SESSION_GRAPH] = value

    # =========================================================================
    # QUALITY DASHBOARD PROPERTIES (009-010)
    # =========================================================================

    @property
    def quality_report(self) -> Optional[Any]:
        """Get current quality report."""
        return st.session_state.get(SessionStateKeys.QUALITY_REPORT)

    @quality_report.setter
    def quality_report(self, value: Any) -> None:
        st.session_state[SessionStateKeys.QUALITY_REPORT] = value

    @property
    def quality_df(self) -> Optional[Any]:
        """Get quality assessment DataFrame."""
        return st.session_state.get(SessionStateKeys.QUALITY_DF)

    @quality_df.setter
    def quality_df(self, value: Any) -> None:
        st.session_state[SessionStateKeys.QUALITY_DF] = value

    @property
    def quality_reports_history(self) -> List[Any]:
        """Get quality reports history list."""
        return st.session_state.get(SessionStateKeys.QUALITY_REPORTS_HISTORY, [])

    @quality_reports_history.setter
    def quality_reports_history(self, value: List[Any]) -> None:
        st.session_state[SessionStateKeys.QUALITY_REPORTS_HISTORY] = value

    @property
    def transformed_df(self) -> Optional[Any]:
        """Get transformed DataFrame after suggestions."""
        return st.session_state.get(SessionStateKeys.TRANSFORMED_DF)

    @transformed_df.setter
    def transformed_df(self, value: Any) -> None:
        st.session_state[SessionStateKeys.TRANSFORMED_DF] = value

    @property
    def applied_suggestions(self) -> set:
        """Get set of applied suggestion IDs."""
        return st.session_state.get(SessionStateKeys.APPLIED_SUGGESTIONS, set())

    @applied_suggestions.setter
    def applied_suggestions(self, value: set) -> None:
        st.session_state[SessionStateKeys.APPLIED_SUGGESTIONS] = value

    # =========================================================================
    # I18N PROPERTIES (006)
    # =========================================================================

    @property
    def language(self) -> str:
        """Get UI language preference."""
        return st.session_state.get(SessionStateKeys.LANGUAGE, "en")

    @language.setter
    def language(self, value: str) -> None:
        st.session_state[SessionStateKeys.LANGUAGE] = value

    # =========================================================================
    # TUTORIAL PROPERTIES (007)
    # =========================================================================

    @property
    def tutorial_completed(self) -> bool:
        """Check if tutorial is completed."""
        return st.session_state.get(SessionStateKeys.TUTORIAL_COMPLETED, False)

    @tutorial_completed.setter
    def tutorial_completed(self, value: bool) -> None:
        st.session_state[SessionStateKeys.TUTORIAL_COMPLETED] = value

    # =========================================================================
    # CATALOG PROPERTIES (008)
    # =========================================================================

    @property
    def catalog_search_query(self) -> str:
        """Get catalog search query."""
        return st.session_state.get(SessionStateKeys.CATALOG_SEARCH_QUERY, "")

    @catalog_search_query.setter
    def catalog_search_query(self, value: str) -> None:
        st.session_state[SessionStateKeys.CATALOG_SEARCH_QUERY] = value

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get(self, key: str, default: Any = None) -> Any:
        """Get session state value by key string."""
        return st.session_state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set session state value by key string."""
        st.session_state[key] = value

    def pop(self, key: str, default: Any = None) -> Any:
        """Remove and return session state value."""
        return st.session_state.pop(key, default)

    def has(self, key: str) -> bool:
        """Check if key exists in session state."""
        return key in st.session_state

    def clear_quality_state(self) -> None:
        """Clear all quality dashboard state (for fresh start)."""
        keys_to_clear = [
            SessionStateKeys.QUALITY_REPORT,
            SessionStateKeys.QUALITY_DF,
            SessionStateKeys.QUALITY_FILE_NAME,
            SessionStateKeys.QUALITY_REPORTS_HISTORY,
            SessionStateKeys.CURRENT_REPORT_INDEX,
            SessionStateKeys.TRANSFORMED_DF,
            SessionStateKeys.TRANSFORMATION_LOG,
            SessionStateKeys.BENCHMARK_REPORT,
            SessionStateKeys.APPLIED_SUGGESTIONS,
        ]
        for key in keys_to_clear:
            st.session_state.pop(key, None)

    def clear_navigation_state(self) -> None:
        """Clear all navigation state (for fresh start)."""
        keys_to_clear = [
            SessionStateKeys.NAV_SESSION,
            SessionStateKeys.NAV_ACTION,
            SessionStateKeys.NAV_TARGET,
            SessionStateKeys.NAV_EXPORT,
            SessionStateKeys.LOADED_SESSION_GRAPH,
            SessionStateKeys.LOADED_GRAPH_DECISIONS,
        ]
        for key in keys_to_clear:
            st.session_state.pop(key, None)


# =============================================================================
# INITIALIZATION HELPER
# =============================================================================

def init_session_state() -> None:
    """
    Initialize all session state keys with default values.

    Call this at app startup to ensure all keys exist.
    Consolidated from streamlit_app.py:init_session_state().
    """
    defaults = {
        # Guided mode (001-004)
        SessionStateKeys.CURRENT_STEP: 0,
        SessionStateKeys.ANSWERS: {},
        SessionStateKeys.DATASETS: {},
        SessionStateKeys.DATA_MODEL: None,
        SessionStateKeys.RAW_DATA: None,
        SessionStateKeys.NEO4J_EXECUTED: False,
        SessionStateKeys.COLUMN_MAPPING: {},

        # Free navigation (002-003)
        SessionStateKeys.NAV_MODE: 'guided',
        SessionStateKeys.NAV_SESSION: None,
        SessionStateKeys.NAV_ACTION: None,
        SessionStateKeys.NAV_TARGET: None,
        SessionStateKeys.NAV_EXPORT: None,
        SessionStateKeys.RELATIONSHIP_BUILDER: None,
        SessionStateKeys.NAV_DESCEND_STEP: 1,
        SessionStateKeys.NAV_TEMP_DATA_MODEL: None,
        SessionStateKeys.NAV_TEMP_CYPHER_QUERIES: None,
        SessionStateKeys.NAV_NEO4J_EXECUTED: False,

        # Quality dashboard (009-010)
        SessionStateKeys.QUALITY_REPORTS_HISTORY: [],
        SessionStateKeys.APPLIED_SUGGESTIONS: set(),

        # Cart-based dataset selection
        SessionStateKeys.DATASET_CART: {},
        SessionStateKeys.CART_MODE: 'selection',
        SessionStateKeys.ANALYSIS_STARTED: False,
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

# Singleton instance for convenient access
session = SessionStateManager()
