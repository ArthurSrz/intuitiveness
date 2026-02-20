"""
L1→L2 Domain Enrichment Form - Categorization

Implements Spec 004: FR-005-010 (L1→L2 Domain Enrichment)
Extracted from ui/ascent_forms.py (lines 333-403)

Features:
- Allow users to specify domain names (comma-separated input)
- Support both semantic matching and keyword-based categorization
- Allow users to set a similarity threshold (0.1 to 0.9)
- Assign "Unmatched" domain to values that don't meet threshold
- Reuse existing domain categorization logic from L3→L2 descent
- Create a 2D table with original vector values plus "domain" column

Usage:
    from intuitiveness.ui.ascent import render_l1_to_l2_domain_form

    result = render_l1_to_l2_domain_form(l1_dataset)
    if result:
        # User submitted domain enrichment
        dimensions = result['dimensions']
        use_semantic = result['use_semantic']
        threshold = result['threshold']
"""

from typing import Any, Dict, Optional
import streamlit as st

from intuitiveness.ui.i18n import t
from intuitiveness.ui.ascent.shared import (
    render_domain_categorization_inputs,
    parse_domains,
    DEFAULT_DOMAINS,
)


def render_l1_to_l2_domain_form(
    dataset: Any,
    key_prefix: str = "l1_to_l2"
) -> Optional[Dict[str, Any]]:
    """
    Render L1→L2 domain enrichment form.

    FR-005: Allow users to specify domain names (comma-separated input)
    FR-006: Support both semantic matching and keyword-based categorization
    FR-007: Allow users to set a similarity threshold (0.1 to 0.9)
    FR-008: Assign "Unmatched" domain to values that don't meet threshold
    FR-009: Reuse the existing domain categorization logic from L3→L2 descent
    FR-010: Create a 2D table with the original vector values plus a "domain" column

    Args:
        dataset: Level1Dataset with vector data
        key_prefix: Unique prefix for session state keys

    Returns:
        Dict with domain enrichment parameters if submitted, None if not ready
    """
    st.markdown(f"### {t('add_categories_title')}")

    # Info tooltip explaining categorization operation
    st.info(
        f"**{t('add_categories_title')}**: {t('add_categories_info')}"
    )

    st.markdown(t("add_categories_desc"))

    # Reuse shared domain categorization inputs (FR-009)
    domains_input, use_semantic, threshold = render_domain_categorization_inputs(
        key_prefix=key_prefix,
        default_domains=DEFAULT_DOMAINS,
        show_help=True
    )

    domains_list = parse_domains(domains_input)

    # Validation
    if not domains_list:
        st.warning(t("enter_at_least_one_category"))
        return None

    st.divider()

    # Show preview of categorization effect
    data = dataset.get_data() if hasattr(dataset, 'get_data') else dataset
    column_name = getattr(dataset, 'name', None) or 'value'

    with st.expander(t("preview_categorization")):
        st.caption(t("categories_to_apply", categories=', '.join(domains_list)))
        st.caption(f"{t('matching_method')} {t('method_smart_matching') if use_semantic else t('method_exact_matching')}")
        if use_semantic:
            st.caption(t("strictness_label", value=threshold))

    # Submit button
    if st.button(t("apply_categories_btn"), key=f"{key_prefix}_submit_btn", type="primary"):
        return {
            'dimensions': domains_list,
            'use_semantic': use_semantic,
            'threshold': threshold,
            'column_name': column_name
        }

    return None
