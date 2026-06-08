"""
Shared Ascent Form Utilities

Implements Spec 011: Code Simplification (Shared Components)
Extracted from ui/ascent_forms.py (lines 23-265)

Common components reused by all ascent forms:
- Session state management
- Form state dataclasses
- Domain categorization UI
- Semantic matching utilities
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple
import streamlit as st
import pandas as pd

from intuitiveness.ui.i18n import t


# =============================================================================
# Session State Keys
# =============================================================================

SESSION_KEY_L0_TO_L1_FORM = "ascent_l0_to_l1_form_state"
SESSION_KEY_L1_TO_L2_FORM = "ascent_l1_to_l2_form_state"
SESSION_KEY_L2_TO_L3_FORM = "ascent_l2_to_l3_form_state"

# Domain categorization defaults
DEFAULT_SIMILARITY_THRESHOLD = 0.5
MIN_SIMILARITY_THRESHOLD = 0.1
MAX_SIMILARITY_THRESHOLD = 0.9
DEFAULT_UNMATCHED_LABEL = "Unmatched"
DEFAULT_DOMAINS = "Revenue, Volume, ETP"


# =============================================================================
# Form State Dataclasses
# =============================================================================

@dataclass
class L0ToL1FormState:
    """State for L0→L1 unfold form."""
    confirmed: bool = False
    error_message: Optional[str] = None


@dataclass
class L1ToL2FormState:
    """State for L1→L2 domain enrichment form."""
    domain_input: str = ""
    parsed_domains: List[str] = field(default_factory=list)
    use_semantic: bool = True
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD

    def parse_domains(self) -> List[str]:
        """Parse comma-separated domain input into list."""
        if not self.domain_input:
            return []
        return [d.strip() for d in self.domain_input.split(",") if d.strip()]

    def is_valid(self) -> bool:
        """Check if form state is valid for submission."""
        return len(self.parse_domains()) > 0


@dataclass
class L2ToL3FormState:
    """State for L2→L3 graph building form."""
    available_columns: List[str] = field(default_factory=list)
    selected_column: Optional[str] = None
    entity_type_name: str = ""
    relationship_type: str = ""

    def is_valid(self) -> bool:
        """Check if form state is valid for submission."""
        return (
            self.selected_column is not None
            and self.entity_type_name.strip() != ""
            and self.relationship_type.strip() != ""
        )


# =============================================================================
# Form State Helpers
# =============================================================================

def get_ascent_form_state(form_key: str, state_class: type) -> Any:
    """
    Get or initialize ascent form state from session state.

    Args:
        form_key: The session state key for the form
        state_class: The dataclass type to instantiate if not present

    Returns:
        The form state object
    """
    if form_key not in st.session_state:
        st.session_state[form_key] = state_class()
    return st.session_state[form_key]


def clear_ascent_form_state(form_key: str) -> None:
    """Clear a specific form state from session."""
    if form_key in st.session_state:
        del st.session_state[form_key]


def clear_all_ascent_form_states() -> None:
    """Clear all ascent form states from session."""
    for key in [SESSION_KEY_L0_TO_L1_FORM, SESSION_KEY_L1_TO_L2_FORM, SESSION_KEY_L2_TO_L3_FORM]:
        clear_ascent_form_state(key)


# =============================================================================
# Shared Domain Categorization Component
# =============================================================================

def render_domain_categorization_inputs(
    key_prefix: str,
    default_domains: str = DEFAULT_DOMAINS,
    show_help: bool = True
) -> Tuple[str, bool, float]:
    """
    Render shared domain categorization UI inputs.

    This function is reused by both L3→L2 descent and L1→L2 ascent (FR-009).

    Args:
        key_prefix: Unique prefix for session state keys
        default_domains: Default domains to show in input
        show_help: Whether to show help text

    Returns:
        Tuple of (domains_input, use_semantic, threshold)
    """
    # Category input field
    if show_help:
        st.markdown(f"**{t('enter_categories_label')}**")

    stored_domains = st.session_state.get(f'{key_prefix}_domains', default_domains)
    domains_input = st.text_input(
        t("categories_label"),
        value=stored_domains,
        key=f"{key_prefix}_domains_input",
        help=t("categories_help")
    )
    st.session_state[f'{key_prefix}_domains'] = domains_input

    # Semantic/keyword toggle and threshold
    col1, col2 = st.columns(2)

    with col1:
        use_semantic = st.checkbox(
            t("use_smart_matching"),
            value=st.session_state.get(f'{key_prefix}_semantic', True),
            key=f"{key_prefix}_semantic_toggle",
            help=t("smart_matching_help")
        )
        st.session_state[f'{key_prefix}_semantic'] = use_semantic

    with col2:
        # Threshold slider (disabled when not using smart matching)
        threshold = st.slider(
            t("matching_strictness_label"),
            min_value=MIN_SIMILARITY_THRESHOLD,
            max_value=MAX_SIMILARITY_THRESHOLD,
            value=st.session_state.get(f'{key_prefix}_threshold', DEFAULT_SIMILARITY_THRESHOLD),
            step=0.05,
            key=f"{key_prefix}_threshold_slider",
            disabled=not use_semantic,
            help=t("matching_strictness_help")
        )
        if use_semantic:
            st.session_state[f'{key_prefix}_threshold'] = threshold

    return domains_input, use_semantic, threshold


def parse_domains(domains_input: str) -> List[str]:
    """Parse comma-separated domain input into a clean list."""
    if not domains_input:
        return []
    return [d.strip() for d in domains_input.split(",") if d.strip()]


def apply_domain_categorization(
    df: pd.DataFrame,
    column: str,
    domains: List[str],
    use_semantic: bool,
    threshold: float
) -> pd.DataFrame:
    """
    Apply domain categorization to a DataFrame column.

    This is the core categorization logic reused by both descent and ascent.
    Uses the configured embeddings API (intuitiveness.models) for semantic matching.

    Args:
        df: DataFrame to categorize
        column: Column to use for categorization
        domains: List of domain names
        use_semantic: Whether to use semantic matching
        threshold: Similarity threshold for semantic matching

    Returns:
        DataFrame with 'domain' column added
    """
    import numpy as np
    result_df = df.copy()

    if use_semantic:
        try:
            from intuitiveness.models import get_batch_similarities

            # Get values to categorize
            values = result_df[column].fillna('').astype(str).tolist()

            # Use batch similarities via the configured embeddings API
            # Shows progress bar during API calls
            similarities = get_batch_similarities(values, domains)

            if similarities is None:
                # API failed - fallback to keyword matching
                result_df['domain'] = result_df[column].apply(
                    lambda x: next(
                        (d for d in domains if d.lower() in str(x).lower()),
                        DEFAULT_UNMATCHED_LABEL
                    )
                )
            else:
                # Assign best matching domain for each value
                assigned_domains = []
                for i, sims in enumerate(similarities):
                    max_idx = int(np.argmax(sims))
                    if sims[max_idx] >= threshold:
                        assigned_domains.append(domains[max_idx])
                    else:
                        assigned_domains.append(DEFAULT_UNMATCHED_LABEL)

                result_df['domain'] = assigned_domains

        except Exception:
            # Fallback to keyword matching if API fails
            result_df['domain'] = result_df[column].apply(
                lambda x: next(
                    (d for d in domains if d.lower() in str(x).lower()),
                    DEFAULT_UNMATCHED_LABEL
                )
            )
    else:
        # Keyword matching
        result_df['domain'] = result_df[column].apply(
            lambda x: next(
                (d for d in domains if d.lower() in str(x).lower()),
                DEFAULT_UNMATCHED_LABEL
            )
        )

    return result_df
