"""
Ascent Controller

Unified ascent logic for both Guided and Free navigation modes.

Phase 2 - Code Simplification (011-code-simplification)
Created: 2026-01-09

Spec Traceability:
------------------
- 002-ascent-functionality: US-5 (Navigate Dataset Hierarchy)
- 004-ascent-precision: Domain categorization, linkage keys

This controller consolidates ~150 lines of duplicated ascent logic
between guided mode (streamlit_app.py:3207-3712) and free mode
(streamlit_app.py:4501-4594).

Features:
---------
- Unified L0→L1, L1→L2, L2→L3 transitions
- Shared validation and error handling
- Mode-agnostic execution interface
"""

import streamlit as st
import pandas as pd
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum

from intuitiveness.utils import SessionStateKeys


# =============================================================================
# ASCENT RESULT TYPES
# =============================================================================

class AscentResult(Enum):
    """Result of an ascent operation."""
    SUCCESS = "success"
    VALIDATION_ERROR = "validation_error"
    EXECUTION_ERROR = "execution_error"
    NO_DATA = "no_data"


@dataclass
class AscentOutcome:
    """Outcome of an ascent operation with details."""
    result: AscentResult
    message: str
    data: Optional[Any] = None
    error: Optional[Exception] = None


# =============================================================================
# ASCENT CONTROLLER
# =============================================================================

class AscentController:
    """
    Unified ascent logic for both modes.

    Implements ascent operations from specs 002-004.

    Usage (Guided Mode):
        controller = AscentController.from_session_graph()
        outcome = controller.execute_l0_to_l1()

    Usage (Free Mode):
        controller = AscentController.from_nav_session(nav_session)
        outcome = controller.execute_l1_to_l2(params)
    """

    def __init__(
        self,
        session_graph: Optional[Any] = None,
        nav_session: Optional[Any] = None,
        datasets: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize controller with data source.

        Args:
            session_graph: SessionGraph for guided mode
            nav_session: NavigationSession for free mode
            datasets: Datasets dict from session state (fallback)
        """
        self._session_graph = session_graph
        self._nav_session = nav_session
        self._datasets = datasets or {}

    @classmethod
    def from_session_graph(cls) -> "AscentController":
        """Create controller from session state graph (guided mode)."""
        graph = st.session_state.get(SessionStateKeys.LOADED_SESSION_GRAPH)
        return cls(session_graph=graph)

    @classmethod
    def from_nav_session(cls, nav_session: Any) -> "AscentController":
        """Create controller from NavigationSession (free mode)."""
        return cls(nav_session=nav_session)

    # =========================================================================
    # L0 → L1: Source Recovery (Spec Step 9)
    # =========================================================================

    def execute_l0_to_l1(self, params: Optional[Dict] = None) -> AscentOutcome:
        """
        Execute L0→L1 transition (recover source values).

        Spec: 002-ascent-functionality, Step 9

        Args:
            params: Optional parameters (usually deterministic)

        Returns:
            AscentOutcome with result and L1 data
        """
        try:
            # Get L1 data from appropriate source
            if self._nav_session is not None:
                # Free mode - use NavigationSession
                self._nav_session.ascend(**(params or {}))
                return AscentOutcome(
                    result=AscentResult.SUCCESS,
                    message="Recovered source values (L1)",
                    data=self._nav_session.current_dataset.get_data()
                )
            elif self._session_graph is not None:
                # Guided mode - use session graph
                l1_df = self._session_graph.get_level_data(1)
                if l1_df is None or l1_df.empty:
                    return AscentOutcome(
                        result=AscentResult.NO_DATA,
                        message="L1 data not found in session graph"
                    )
                return AscentOutcome(
                    result=AscentResult.SUCCESS,
                    message=f"Recovered {len(l1_df)} source values",
                    data=l1_df
                )
            elif 'l1' in self._datasets:
                # Fallback: datasets dict from descent workflow
                l1_obj = self._datasets['l1']
                l1_df = l1_obj.get_data() if hasattr(l1_obj, 'get_data') else l1_obj
                return AscentOutcome(
                    result=AscentResult.SUCCESS,
                    message=f"Recovered {len(l1_df)} source values from descent",
                    data=l1_df
                )
            elif 'l0' in self._datasets:
                # Have L0 but no L1: unfold L0 datum into a single-row DataFrame
                l0_obj = self._datasets['l0']
                value = l0_obj.value if hasattr(l0_obj, 'value') else l0_obj
                l1_df = pd.DataFrame({'value': [value]})
                return AscentOutcome(
                    result=AscentResult.SUCCESS,
                    message="Unfolded L0 datum into L1 vector",
                    data=l1_df
                )
            else:
                return AscentOutcome(
                    result=AscentResult.NO_DATA,
                    message="No data source available"
                )

        except Exception as e:
            return AscentOutcome(
                result=AscentResult.EXECUTION_ERROR,
                message=f"L0→L1 failed: {str(e)}",
                error=e
            )

    # =========================================================================
    # L1 → L2: New Categorization (Spec Step 10)
    # =========================================================================

    def validate_l1_to_l2_params(
        self,
        categories: Union[str, List[str]],
        column: Optional[str] = None,
    ) -> Tuple[bool, str, List[str]]:
        """
        Validate L1→L2 categorization parameters.

        Args:
            categories: Category string (comma-separated) or list
            column: Column to categorize by

        Returns:
            Tuple of (is_valid, error_message, parsed_categories)
        """
        # Parse categories
        if isinstance(categories, str):
            parsed = [c.strip() for c in categories.split(",") if c.strip()]
        else:
            parsed = [c for c in categories if c]

        if not parsed:
            return False, "At least one category is required", []

        if len(parsed) < 2:
            return False, "At least 2 categories recommended for meaningful analysis", parsed

        return True, "", parsed

    def execute_l1_to_l2(
        self,
        categories: Union[str, List[str]],
        column: Optional[str] = None,
        use_semantic: bool = True,
        threshold: float = 0.5,
        l1_data: Optional[pd.DataFrame] = None,
    ) -> AscentOutcome:
        """
        Execute L1→L2 transition (domain categorization).

        Spec: 004-ascent-precision, Step 10

        Args:
            categories: Category definitions
            column: Column to categorize by
            use_semantic: Use semantic matching
            threshold: Similarity threshold
            l1_data: L1 DataFrame (for guided mode)

        Returns:
            AscentOutcome with result and L2 data
        """
        # Validate parameters
        is_valid, error_msg, parsed_categories = self.validate_l1_to_l2_params(
            categories, column
        )
        if not is_valid:
            return AscentOutcome(
                result=AscentResult.VALIDATION_ERROR,
                message=error_msg
            )

        try:
            if self._nav_session is not None:
                # Free mode - use NavigationSession
                params = {
                    'dimensions': parsed_categories,
                    'use_semantic': use_semantic,
                    'threshold': threshold,
                }
                self._nav_session.ascend(**params)
                return AscentOutcome(
                    result=AscentResult.SUCCESS,
                    message=f"Categorized into {len(parsed_categories)} domains",
                    data=self._nav_session.current_dataset.get_data()
                )
            elif l1_data is not None:
                # Guided mode - apply categorization to L1 data
                l2_df = self._apply_categorization(
                    l1_data, column, parsed_categories, use_semantic, threshold
                )
                return AscentOutcome(
                    result=AscentResult.SUCCESS,
                    message=f"Created L2 with {len(parsed_categories)} categories",
                    data=l2_df
                )
            elif 'l1' in self._datasets:
                # Fallback: use L1 from datasets dict
                l1_obj = self._datasets['l1']
                df = l1_obj.get_data() if hasattr(l1_obj, 'get_data') else l1_obj
                l2_df = self._apply_categorization(
                    df, column, parsed_categories, use_semantic, threshold
                )
                return AscentOutcome(
                    result=AscentResult.SUCCESS,
                    message=f"Created L2 with {len(parsed_categories)} categories",
                    data=l2_df
                )
            else:
                return AscentOutcome(
                    result=AscentResult.NO_DATA,
                    message="No L1 data available for categorization"
                )

        except Exception as e:
            return AscentOutcome(
                result=AscentResult.EXECUTION_ERROR,
                message=f"L1→L2 failed: {str(e)}",
                error=e
            )

    def _apply_categorization(
        self,
        df: pd.DataFrame,
        column: Optional[str],
        categories: List[str],
        use_semantic: bool,
        threshold: float,
    ) -> pd.DataFrame:
        """
        Apply categorization to DataFrame (guided mode).

        This is the shared categorization logic extracted from
        streamlit_app.py:3237-3445.
        """
        result_df = df.copy()

        if column and column in df.columns:
            # Categorize based on column values
            if use_semantic:
                # Semantic matching (simplified - full impl in descent/semantic_join.py)
                result_df['ascent_category'] = df[column].apply(
                    lambda x: self._semantic_match(x, categories, threshold)
                )
            else:
                # Exact matching
                result_df['ascent_category'] = df[column].apply(
                    lambda x: x if x in categories else "Unmatched"
                )
        else:
            # Numeric-based categorization (quartiles)
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                primary_col = numeric_cols[0]
                result_df['ascent_category'] = pd.qcut(
                    df[primary_col],
                    q=min(len(categories), 4),
                    labels=categories[:min(len(categories), 4)],
                    duplicates='drop'
                )

        return result_df

    def _semantic_match(
        self,
        value: Any,
        categories: List[str],
        threshold: float,
    ) -> str:
        """Simple semantic matching (placeholder - full impl uses sentence-transformers)."""
        value_str = str(value).lower()
        for cat in categories:
            if cat.lower() in value_str or value_str in cat.lower():
                return cat
        return "Unmatched"

    # =========================================================================
    # L2 → L3: Linkage Enrichment (Spec Step 11)
    # =========================================================================

    def validate_l2_to_l3_params(
        self,
        entity_column: Optional[str],
        entity_type_name: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Validate L2→L3 linkage parameters.

        Args:
            entity_column: Column to use for entity linkage
            entity_type_name: Name for the entity type

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not entity_column:
            return False, "Entity column is required for linkage"
        return True, ""

    def execute_l2_to_l3(
        self,
        entity_column: str,
        entity_type_name: Optional[str] = None,
        relationship_type: Optional[str] = None,
        l2_data: Optional[pd.DataFrame] = None,
    ) -> AscentOutcome:
        """
        Execute L2→L3 transition (linkage enrichment).

        Spec: 004-ascent-precision, Step 11

        Args:
            entity_column: Column for entity linkage
            entity_type_name: Name for entity type
            relationship_type: Type of relationship
            l2_data: L2 DataFrame (for guided mode)

        Returns:
            AscentOutcome with result and L3 data
        """
        # Validate parameters
        is_valid, error_msg = self.validate_l2_to_l3_params(
            entity_column, entity_type_name
        )
        if not is_valid:
            return AscentOutcome(
                result=AscentResult.VALIDATION_ERROR,
                message=error_msg
            )

        try:
            if self._nav_session is not None:
                # Free mode - use NavigationSession
                params = {
                    'entity_column': entity_column,
                    'entity_type_name': entity_type_name,
                    'relationship_type': relationship_type,
                }
                self._nav_session.ascend(**params)
                return AscentOutcome(
                    result=AscentResult.SUCCESS,
                    message=f"Linked via {entity_column}",
                    data=self._nav_session.current_dataset.get_data()
                )
            elif l2_data is not None:
                # Guided mode - merge categorization into L3
                l3_data = self._apply_linkage(l2_data, entity_column)
                return AscentOutcome(
                    result=AscentResult.SUCCESS,
                    message=f"Created L3 with entity linkage",
                    data=l3_data
                )
            elif 'l2' in self._datasets:
                # Fallback: use L2 from datasets dict
                l2_obj = self._datasets['l2']
                df = l2_obj.get_data() if hasattr(l2_obj, 'get_data') else l2_obj
                l3_data = self._apply_linkage(df, entity_column)
                return AscentOutcome(
                    result=AscentResult.SUCCESS,
                    message=f"Created L3 with entity linkage",
                    data=l3_data
                )
            else:
                return AscentOutcome(
                    result=AscentResult.NO_DATA,
                    message="No L2 data available for linkage"
                )

        except Exception as e:
            return AscentOutcome(
                result=AscentResult.EXECUTION_ERROR,
                message=f"L2→L3 failed: {str(e)}",
                error=e
            )

    def _apply_linkage(
        self,
        l2_df: pd.DataFrame,
        entity_column: str,
    ) -> pd.DataFrame:
        """
        Apply entity linkage to create L3 (guided mode).

        This merges L2 categorization back into L3 structure.
        """
        result_df = l2_df.copy()

        # Ensure entity column exists
        if entity_column not in result_df.columns:
            # Try to find a suitable linkage column
            potential_cols = [c for c in result_df.columns if 'id' in c.lower()]
            if potential_cols:
                entity_column = potential_cols[0]

        # Mark as L3 linked data
        result_df['_l3_linked'] = True
        result_df['_linkage_column'] = entity_column

        return result_df


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_ascent_controller() -> AscentController:
    """
    Get appropriate AscentController based on current mode.

    Priority: nav_session > session_graph > datasets dict.

    Returns:
        AscentController configured for current mode
    """
    nav_session = st.session_state.get(SessionStateKeys.NAV_SESSION)
    datasets = st.session_state.get(SessionStateKeys.DATASETS, {})

    if nav_session is not None:
        return AscentController.from_nav_session(nav_session)
    else:
        graph = st.session_state.get(SessionStateKeys.LOADED_SESSION_GRAPH)
        return AscentController(session_graph=graph, datasets=datasets)
