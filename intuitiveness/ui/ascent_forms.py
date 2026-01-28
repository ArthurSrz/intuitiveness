"""
Discovery Wizard Components - L4→L3 Workflow

Feature: 006-playwright-mcp-e2e

This module provides wizard components for the L4→L3 discovery workflow:
- Step 1: Column selection with clickable cards
- Step 2: Connection configuration (semantic matching)
- Step 3: Preview and confirmation of joined table

These wizard components handle the multi-file discovery and joining process.
For ascent-specific forms (L0→L1, L1→L2, L2→L3), see ui/ascent/ package.
"""

from typing import Any, Dict, List, Optional, Tuple
import streamlit as st
import pandas as pd

from intuitiveness.ui.i18n import t

# Import shared constants from ascent package
from intuitiveness.ui.ascent.shared import DEFAULT_UNMATCHED_LABEL

# Note: _render_domain_categorization_inputs, _parse_domains, _apply_domain_categorization
# are no longer used - these functions were moved to ui/ascent/ package during refactoring


# =============================================================================
# Discovery Wizard Components (Step 2 Simplification)
# =============================================================================

# Session state keys for wizard
SESSION_KEY_WIZARD_STEP = "discovery_wizard_step"
SESSION_KEY_DISCOVERY_RESULTS = "discovery_results"


def _get_wizard_step() -> int:
    """Get current wizard step (1, 2, or 3)."""
    if SESSION_KEY_WIZARD_STEP not in st.session_state:
        st.session_state[SESSION_KEY_WIZARD_STEP] = 1
    return st.session_state[SESSION_KEY_WIZARD_STEP]


def _set_wizard_step(step: int) -> None:
    """Set wizard step."""
    st.session_state[SESSION_KEY_WIZARD_STEP] = step


def render_wizard_step_1_columns(
    dataframes: Dict[str, Any],
    key_prefix: str = "wizard_s1"
) -> bool:
    """
    Render wizard step 1: Column selection.

    Shows clickable cards for each column. User selects columns to connect.

    Args:
        dataframes: Dict mapping filename to DataFrame
        key_prefix: Unique key prefix for UI elements

    Returns:
        True if user clicked "Continue" to proceed
    """
    st.markdown(f"### {t('step_1_of_3_columns')}")
    st.markdown(t("click_columns_instruction"))

    if not dataframes:
        st.warning(t("no_files_to_analyze"))
        return False

    # Initialize session state for selected columns
    selected_key = f"{key_prefix}_selected_columns"
    if selected_key not in st.session_state:
        st.session_state[selected_key] = set()

    # Count total columns
    total_columns = sum(len(df.columns) for df in dataframes.values())
    selected_count = len(st.session_state[selected_key])

    if selected_count > 0:
        st.success(f"✅ {t('columns_selected', count=selected_count, files=len(dataframes))}")
    else:
        st.info(f"📊 {t('files_with_columns', files=len(dataframes), columns=total_columns)}")

    # Render columns grouped by file
    for filename, df in dataframes.items():
        st.markdown(f"#### 📁 {filename}")
        st.caption(f"{len(df):,} rows")

        # Create a grid of column cards (3 per row)
        columns_list = list(df.columns)
        cols_per_row = 3

        for i in range(0, len(columns_list), cols_per_row):
            row_cols = st.columns(cols_per_row)
            for j, col in enumerate(columns_list[i:i+cols_per_row]):
                with row_cols[j]:
                    # Unique key for this column (file:column)
                    col_key = f"{filename}:{col}"
                    is_selected = col_key in st.session_state[selected_key]

                    # Get sample values
                    sample_vals = df[col].dropna().unique()[:3]
                    sample_str = ", ".join(str(v)[:20] for v in sample_vals)
                    if len(sample_str) > 50:
                        sample_str = sample_str[:50] + "..."

                    # Detect if it looks like an ID column
                    is_id_like = any(p in col.lower() for p in ['id', 'code', 'key', 'num', 'ref'])
                    uniqueness = df[col].nunique() / len(df) if len(df) > 0 else 0
                    badge = ""
                    if is_id_like and uniqueness > 0.5:
                        badge = "🔑"
                    elif uniqueness > 0.9:
                        badge = "🆔"

                    # Style based on selection
                    if is_selected:
                        border_color = "#4CAF50"
                        bg_color = "#e8f5e9"
                        check_mark = "✓ "
                    else:
                        border_color = "#e0e0e0"
                        bg_color = "#fafafa"
                        check_mark = ""

                    # Clickable card using button
                    button_label = f"{check_mark}{badge} {col}"
                    if st.button(
                        button_label,
                        key=f"{key_prefix}_{filename}_{col}",
                        use_container_width=True,
                        type="primary" if is_selected else "secondary"
                    ):
                        # Toggle selection
                        if is_selected:
                            st.session_state[selected_key].discard(col_key)
                        else:
                            st.session_state[selected_key].add(col_key)
                        st.rerun()

                    # Show sample values below button
                    st.caption(sample_str if sample_str else "_empty_")

        st.markdown("---")

    # Legend
    st.caption(f"🔑 = {t('legend_identifier')} | 🆔 = {t('legend_high_uniqueness')} | {t('legend_click_select')}")

    # Show selected columns summary
    if st.session_state[selected_key]:
        with st.expander(f"📋 {t('selected_columns_count', count=len(st.session_state[selected_key]))}"):
            for col_key in sorted(st.session_state[selected_key]):
                file_name, col_name = col_key.split(":", 1)
                st.write(f"• **{col_name}** from _{file_name}_")

    st.divider()

    # Navigation buttons
    col_clear, col_space, col_next = st.columns([1, 1, 1])

    with col_clear:
        if st.button(t("clear_all_btn"), key=f"{key_prefix}_clear"):
            st.session_state[selected_key] = set()
            st.rerun()

    with col_next:
        # Require at least 2 columns to connect
        can_continue = len(st.session_state[selected_key]) >= 2
        if st.button(
            t("continue_arrow"),
            key=f"{key_prefix}_next",
            type="primary",
            disabled=not can_continue
        ):
            return True

        if not can_continue:
            st.caption(t("select_at_least_2"))

    return False


def render_wizard_step_1_entities(
    entity_suggestions: List[Any],
    key_prefix: str = "wizard_s1"
) -> bool:
    """
    Render wizard step 1: Entity confirmation (legacy).

    Shows AI-discovered entities and lets user confirm/edit names.

    Args:
        entity_suggestions: List of EntitySuggestion objects
        key_prefix: Unique key prefix for UI elements

    Returns:
        True if user clicked "Looks Good" to proceed
    """
    st.markdown("### Step 1 of 3: Understanding Your Files")
    st.markdown("I analyzed your files and found these main data types:")

    if not entity_suggestions:
        st.warning("No files found to analyze.")
        return False

    # Render each entity as a card
    for i, entity in enumerate(entity_suggestions):
        with st.container():
            col1, col2 = st.columns([3, 1])

            with col1:
                # Entity card
                st.markdown(f"""
                <div style="
                    padding: 15px;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    margin-bottom: 10px;
                    background-color: #f8f9fa;
                ">
                    <div style="font-size: 18px; font-weight: bold; color: #1f77b4;">
                        {entity.display_name}
                    </div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;">
                        From: {entity.source_file}
                    </div>
                    <div style="font-size: 14px; margin-top: 8px;">
                        {entity.row_count:,} records | Identifier: {entity.key_column}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                # Edit name button
                if st.button("Edit name", key=f"{key_prefix}_edit_{i}"):
                    st.session_state[f"{key_prefix}_editing_{i}"] = True

        # Show edit input if editing
        if st.session_state.get(f"{key_prefix}_editing_{i}", False):
            new_name = st.text_input(
                "New name:",
                value=entity.display_name,
                key=f"{key_prefix}_name_input_{i}"
            )
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.button("Save", key=f"{key_prefix}_save_{i}"):
                    entity.user_edited_name = new_name
                    st.session_state[f"{key_prefix}_editing_{i}"] = False
                    st.rerun()
            with col_cancel:
                if st.button("Cancel", key=f"{key_prefix}_cancel_{i}"):
                    st.session_state[f"{key_prefix}_editing_{i}"] = False
                    st.rerun()

    st.divider()

    # Navigation buttons
    col_back, col_next = st.columns([1, 1])

    with col_next:
        if st.button("Looks Good →", key=f"{key_prefix}_next", type="primary"):
            # Mark all entities as accepted
            for entity in entity_suggestions:
                entity.accepted = True
            return True

    return False


def render_wizard_step_2_connections(
    dataframes: Dict[str, Any],
    selected_columns_key: str,
    key_prefix: str = "wizard_s2"
) -> bool:
    """
    Render wizard step 2: Row-level semantic matching configuration.

    Per spec FR-003: Selected columns form ROW VECTORS - each row is vectorized
    using selected column values as coordinates (multi-dimensional point).
    Semantic matching compares these row vectors between files automatically.

    This is NOT column-pair matching - it's row-level vectorization.

    Args:
        dataframes: Dict mapping filename to DataFrame
        selected_columns_key: Session state key containing selected columns from Step 1
        key_prefix: Unique key prefix for UI elements

    Returns:
        True if user clicked "Continue" to proceed
    """
    st.markdown(f"### {t('step_2_of_3_connections')}")

    # Get selected columns from Step 1
    selected_columns = st.session_state.get(selected_columns_key, set())

    if len(selected_columns) < 2:
        st.warning(t("select_columns_step1_first"))
        if st.button(t("back_to_step_1"), key=f"{key_prefix}_back_no_cols"):
            _set_wizard_step(1)
            st.rerun()
        return False

    # Group selected columns by file
    columns_by_file = {}
    for col_key in selected_columns:
        file_name, col_name = col_key.split(":", 1)
        if file_name in dataframes:
            if file_name not in columns_by_file:
                columns_by_file[file_name] = []
            columns_by_file[file_name].append(col_name)

    # Initialize connections in session state
    connections_key = f"{key_prefix}_connections"

    # Check we have columns from at least 2 files
    if len(columns_by_file) < 2:
        st.info(t("select_from_2_files"))
        if st.button(t("back_to_step_1"), key=f"{key_prefix}_back_same_file"):
            _set_wizard_step(1)
            st.rerun()
        return False

    # Domain-friendly "What's happening" explainer (006-playwright-mcp-e2e UI improvement)
    st.markdown("""
    <div style="
        padding: 16px 20px;
        border-left: 4px solid #2196F3;
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-radius: 0 8px 8px 0;
        margin-bottom: 20px;
    ">
        <div style="font-size: 15px; font-weight: 600; color: #1565C0; margin-bottom: 8px;">
            💡 What's happening here?
        </div>
        <div style="font-size: 14px; color: #424242; line-height: 1.5;">
            I'm looking at your selected columns to find <strong>matching items</strong> between your files.
            For example, if both files have a school code, I'll use that to connect related information together.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Show file connection summary with friendlier language
    st.subheader("📊 Your Files to Connect")

    # Color scheme for files (consistent, accessible colors)
    file_colors = [
        {'bg': '#e3f2fd', 'border': '#1976D2', 'icon': '📘'},
        {'bg': '#e8f5e9', 'border': '#388E3C', 'icon': '📗'},
        {'bg': '#fff3e0', 'border': '#F57C00', 'icon': '📙'},
        {'bg': '#fce4ec', 'border': '#C2185B', 'icon': '📕'},
    ]
    file_list = list(columns_by_file.keys())

    for i, (file_name, cols) in enumerate(columns_by_file.items()):
        colors = file_colors[i % len(file_colors)]
        df = dataframes[file_name]
        row_count = len(df)
        # Get short filename for display
        short_name = file_name[:40] + "..." if len(file_name) > 40 else file_name

        st.markdown(f"""
        <div style="
            padding: 16px 20px;
            border: 2px solid {colors['border']};
            border-radius: 12px;
            margin-bottom: 16px;
            background-color: {colors['bg']};
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        ">
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <span style="font-size: 24px; margin-right: 10px;">{colors['icon']}</span>
                <span style="font-size: 15px; font-weight: 600; color: #333;">{short_name}</span>
            </div>
            <div style="display: flex; gap: 20px; font-size: 14px; color: #555;">
                <div>
                    <span style="color: #888;">Items:</span>
                    <strong style="color: {colors['border']};">{row_count:,}</strong>
                </div>
                <div>
                    <span style="color: #888;">Link column:</span>
                    <code style="background: white; padding: 2px 6px; border-radius: 4px;">{cols[0]}</code>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Show sample values from the link column
        with st.expander(f"👀 Preview sample values from {short_name}"):
            sample_values = df[cols[0]].dropna().head(5).tolist()
            if sample_values:
                st.write("**Sample values from the link column:**")
                for val in sample_values:
                    display_val = str(val)[:50]
                    st.write(f"  • `{display_val}`")

    # Show matching configuration with friendlier language
    st.subheader("🔗 How Items Will Be Connected")

    # Visual connection indicator between files
    if len(file_list) >= 2:
        col1, col2, col3 = st.columns([2, 1, 2])
        with col1:
            st.markdown(f"""
            <div style="text-align: center; padding: 10px;">
                <div style="font-size: 28px;">{file_colors[0]['icon']}</div>
                <div style="font-size: 12px; color: #666; margin-top: 4px;">{file_list[0][:20]}...</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div style="text-align: center; padding: 20px 0;">
                <div style="font-size: 24px;">🔗</div>
                <div style="font-size: 11px; color: #888;">matching</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div style="text-align: center; padding: 10px;">
                <div style="font-size: 28px;">{file_colors[1]['icon']}</div>
                <div style="font-size: 12px; color: #666; margin-top: 4px;">{file_list[1][:20]}...</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("""
    <div style="
        padding: 16px 20px;
        border: 2px solid #4CAF50;
        border-radius: 12px;
        background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
        margin: 16px 0;
    ">
        <div style="font-size: 15px; font-weight: 600; color: #2E7D32; margin-bottom: 8px;">
            🧠 Smart Matching Enabled
        </div>
        <div style="font-size: 14px; color: #424242; line-height: 1.5;">
            I'll look for items in both files that share the <strong>same or similar values</strong>
            in your selected columns, then link them together automatically.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Threshold slider with friendlier labels
    threshold_key = f"{key_prefix}_threshold"
    if threshold_key not in st.session_state:
        st.session_state[threshold_key] = 0.75

    st.markdown("**How strict should the matching be?**")
    st.caption("Stricter = fewer connections but more accurate; Looser = more connections but may include mismatches")

    threshold = st.slider(
        "Matching strictness:",
        min_value=0.5,
        max_value=0.95,
        value=st.session_state[threshold_key],
        step=0.05,
        key=f"{key_prefix}_threshold_slider",
        help="Higher = stricter matching (fewer but more accurate matches)",
        label_visibility="collapsed"
    )
    st.session_state[threshold_key] = threshold

    # Show strictness level indicator
    if threshold >= 0.9:
        strictness_label = "🎯 Very Strict (exact matches only)"
    elif threshold >= 0.8:
        strictness_label = "✅ Strict (high confidence matches)"
    elif threshold >= 0.7:
        strictness_label = "⚖️ Balanced (recommended)"
    else:
        strictness_label = "🌐 Loose (may include partial matches)"
    st.caption(strictness_label)

    # Preview semantic matching if requested
    preview_key = f"{key_prefix}_preview_result"
    if st.button(f"🔍 {t('preview_connections')}", key=f"{key_prefix}_preview_btn", type="secondary"):
        with st.spinner(f"🔄 {t('finding_matching_items')}"):
            try:
                from intuitiveness.discovery import run_row_vector_match

                # Get the two files with their columns
                files = list(columns_by_file.items())
                file1, cols1 = files[0]
                file2, cols2 = files[1]

                df1 = dataframes[file1]
                df2 = dataframes[file2]

                # Run row vector matching
                match_count, avg_sim, sample_matches = run_row_vector_match(
                    df1, cols1,
                    df2, cols2,
                    threshold=threshold,
                    max_samples=5
                )

                st.session_state[preview_key] = {
                    'match_count': match_count,
                    'avg_sim': avg_sim,
                    'sample_matches': sample_matches
                }
                st.rerun()
            except ImportError:
                # Fallback if run_row_vector_match doesn't exist yet
                st.info(t("preview_not_available"))
            except Exception as e:
                st.error(t("error_during_preview", error=str(e)))

    # Display preview results with improved visualization
    if preview_key in st.session_state:
        result = st.session_state[preview_key]
        if result['match_count'] > 0:
            st.markdown(f"""
            <div style="
                padding: 16px 20px;
                border: 2px solid #4CAF50;
                border-radius: 12px;
                background-color: #f1f8e9;
                margin: 16px 0;
            ">
                <div style="font-size: 18px; font-weight: 600; color: #2E7D32; margin-bottom: 8px;">
                    ✅ Found {result['match_count']:,} connections!
                </div>
                <div style="font-size: 14px; color: #555;">
                    Average match confidence: <strong>{result['avg_sim']:.0%}</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if result.get('sample_matches'):
                st.markdown("**Sample connections found:**")
                for i, match in enumerate(result['sample_matches'][:3]):
                    left = match.get('left_preview', '...')[:25]
                    right = match.get('right_preview', '...')[:25]
                    score = match.get('score', 0)
                    st.markdown(f"""
                    <div style="
                        display: flex;
                        align-items: center;
                        padding: 8px 12px;
                        margin: 4px 0;
                        background-color: #fafafa;
                        border-radius: 8px;
                        font-size: 13px;
                    ">
                        <span style="flex: 1; text-align: right; color: #1976D2;">"{left}"</span>
                        <span style="padding: 0 12px; color: #4CAF50; font-weight: bold;">↔</span>
                        <span style="flex: 1; color: #388E3C;">"{right}"</span>
                        <span style="padding-left: 12px; color: #888; font-size: 12px;">{score:.0%}</span>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.warning(f"🔍 {t('no_connections_at_threshold')}")

    st.divider()

    # Navigation buttons
    col_back, col_space, col_next = st.columns([1, 1, 1])

    with col_back:
        if st.button(t("back_arrow"), key=f"{key_prefix}_back"):
            _set_wizard_step(1)
            st.rerun()

    with col_next:
        if st.button(t("continue_arrow"), key=f"{key_prefix}_next", type="primary"):
            # Store row vector configuration for Step 3 (per spec FR-003)
            # This is the spec-compliant format: columns form row vectors, embeddings match rows
            st.session_state[connections_key] = {
                'method': 'row_vector_embeddings',
                'threshold': threshold,
                'files': {
                    file_name: cols
                    for file_name, cols in columns_by_file.items()
                }
            }
            return True

    return False


def render_wizard_step_2_relationships(
    relationship_suggestions: List[Any],
    key_prefix: str = "wizard_s2"
) -> bool:
    """
    Render wizard step 2: Relationship suggestions (legacy).

    Shows AI-discovered relationships and lets user accept/skip each.

    Args:
        relationship_suggestions: List of RelationshipSuggestion objects
        key_prefix: Unique key prefix for UI elements

    Returns:
        True if user clicked "Continue" to proceed
    """
    st.markdown("### Step 2 of 3: Suggested Connections")
    st.markdown("I found these potential connections between your data:")

    if not relationship_suggestions:
        st.info("No automatic connections found. You can add them manually later.")
        if st.button("Continue →", key=f"{key_prefix}_no_rels_next", type="primary"):
            return True
        return False

    # Group by confidence
    high_conf = [r for r in relationship_suggestions if r.confidence >= 0.7]
    medium_conf = [r for r in relationship_suggestions if 0.4 <= r.confidence < 0.7]
    low_conf = [r for r in relationship_suggestions if r.confidence < 0.4]

    def render_suggestion_card(suggestion, index: int, confidence_label: str):
        """Render a single relationship suggestion card."""
        # Determine if already decided
        decision_key = f"{key_prefix}_decision_{suggestion.id}"
        current_decision = st.session_state.get(decision_key, None)

        # Card styling based on state
        if current_decision is True:
            border_color = "#4CAF50"
            bg_color = "#e8f5e9"
            status_text = "✓ Connected"
        elif current_decision is False:
            border_color = "#9e9e9e"
            bg_color = "#f5f5f5"
            status_text = "Skipped"
        else:
            border_color = "#2196F3" if confidence_label == "HIGH" else "#ff9800"
            bg_color = "#ffffff"
            status_text = ""

        with st.container():
            st.markdown(f"""
            <div style="
                padding: 15px;
                border: 2px solid {border_color};
                border-radius: 8px;
                margin-bottom: 15px;
                background-color: {bg_color};
            ">
                <div style="font-size: 11px; color: #666; margin-bottom: 5px;">
                    {confidence_label} CONFIDENCE {status_text}
                </div>
                <div style="font-size: 16px; margin-bottom: 10px;">
                    "{suggestion.natural_description}"
                </div>
                <div style="font-size: 12px; color: #888;">
                    Preview: {', '.join(suggestion.sample_matches[:3]) if suggestion.sample_matches else 'No preview available'}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Decision buttons (only if not yet decided)
            if current_decision is None:
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    if st.button(
                        "Yes, connect them",
                        key=f"{key_prefix}_accept_{suggestion.id}",
                        type="primary"
                    ):
                        st.session_state[decision_key] = True
                        suggestion.accepted = True
                        st.rerun()
                with col2:
                    if st.button(
                        "Skip",
                        key=f"{key_prefix}_skip_{suggestion.id}"
                    ):
                        st.session_state[decision_key] = False
                        suggestion.accepted = False
                        st.rerun()

    # Render high confidence suggestions
    if high_conf:
        for i, suggestion in enumerate(high_conf):
            render_suggestion_card(suggestion, i, "HIGH")

    # Render medium confidence suggestions
    if medium_conf:
        st.markdown("---")
        st.markdown("**Other potential connections:**")
        for i, suggestion in enumerate(medium_conf):
            render_suggestion_card(suggestion, len(high_conf) + i, "MEDIUM")

    # Don't show low confidence unless user asks
    if low_conf:
        with st.expander(f"Show {len(low_conf)} weak matches"):
            for i, suggestion in enumerate(low_conf):
                render_suggestion_card(
                    suggestion,
                    len(high_conf) + len(medium_conf) + i,
                    "LOW"
                )

    st.divider()

    # Navigation buttons
    col_back, col_next = st.columns([1, 1])

    with col_back:
        if st.button("← Back", key=f"{key_prefix}_back"):
            _set_wizard_step(1)
            st.rerun()

    with col_next:
        if st.button("Continue →", key=f"{key_prefix}_next", type="primary"):
            return True

    return False


def _build_semantic_mapping(matches: List[Tuple[str, str, float]]) -> Dict[str, str]:
    """
    Build a mapping dictionary from semantic match results.

    Args:
        matches: List of (val1, val2, score) tuples from semantic matching

    Returns:
        Dictionary mapping val1 -> val2 for use in joins
    """
    return {val1: val2 for val1, val2, score in matches}


def _perform_row_vector_join(
    dataframes: Dict[str, pd.DataFrame],
    config: Dict
) -> Optional[pd.DataFrame]:
    """
    Perform row-vector semantic join per spec FR-003.

    Each row is vectorized using selected columns as coordinates.
    Semantic matching compares row vectors between files.

    Args:
        dataframes: Dict of filename -> DataFrame
        config: Dict with 'method', 'threshold', and 'files' (columns per file)

    Returns:
        Joined DataFrame (L3 dataset) or None if join fails
    """
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np

    files_config = config.get('files', {})
    threshold = config.get('threshold', 0.75)

    if len(files_config) < 2:
        return None

    # Get the two files with their columns
    files = list(files_config.items())
    file1_name, cols1 = files[0]
    file2_name, cols2 = files[1]

    df1 = dataframes[file1_name].copy()
    df2 = dataframes[file2_name].copy()

    print(f"[L4→L3] Row vector join: {file1_name} ({len(df1)} rows) ↔ {file2_name} ({len(df2)} rows)")
    print(f"[L4→L3] File 1 columns: {cols1}")
    print(f"[L4→L3] File 2 columns: {cols2}")
    print(f"[L4→L3] Similarity threshold: {threshold}")

    # Create row vectors by concatenating selected column values
    def create_row_text(row, columns):
        """Concatenate column values into a single text for embedding."""
        parts = []
        for col in columns:
            val = row.get(col, '')
            if pd.notna(val):
                parts.append(f"{col}: {str(val)}")
        return ' | '.join(parts)

    # Create text representations for all rows
    df1['_row_text'] = df1.apply(lambda row: create_row_text(row, cols1), axis=1)
    df2['_row_text'] = df2.apply(lambda row: create_row_text(row, cols2), axis=1)

    # Filter out empty rows
    df1_valid = df1[df1['_row_text'].str.len() > 0].reset_index(drop=True)
    df2_valid = df2[df2['_row_text'].str.len() > 0].reset_index(drop=True)

    if len(df1_valid) == 0 or len(df2_valid) == 0:
        print("[L4→L3] No valid rows for matching")
        return None

    print(f"[L4→L3] Loading embedding model...")
    model = SentenceTransformer('intfloat/multilingual-e5-small')

    # Sample if datasets are too large (to avoid OOM)
    max_rows = 5000
    df1_sample = df1_valid.head(max_rows)
    df2_sample = df2_valid.head(max_rows)

    print(f"[L4→L3] Computing embeddings for {len(df1_sample)} x {len(df2_sample)} rows...")

    # Compute embeddings
    embeddings1 = model.encode(df1_sample['_row_text'].tolist(), convert_to_numpy=True)
    embeddings2 = model.encode(df2_sample['_row_text'].tolist(), convert_to_numpy=True)

    # Compute similarity matrix
    print(f"[L4→L3] Computing similarity matrix...")
    similarities = cosine_similarity(embeddings1, embeddings2)

    # Find best matches above threshold
    matches = []
    for i in range(len(df1_sample)):
        best_j = np.argmax(similarities[i])
        best_score = similarities[i][best_j]
        if best_score >= threshold:
            matches.append((i, best_j, best_score))

    print(f"[L4→L3] Found {len(matches)} row matches above threshold {threshold}")

    if len(matches) == 0:
        print("[L4→L3] No matches found - returning empty DataFrame")
        return pd.DataFrame()

    # Build joined table from matches
    result_rows = []
    for i, j, score in matches:
        row1 = df1_sample.iloc[i].to_dict()
        row2 = df2_sample.iloc[j].to_dict()

        # Combine rows, adding suffix to file2 columns to avoid conflicts
        combined = {}
        for k, v in row1.items():
            if k != '_row_text':
                combined[k] = v
        for k, v in row2.items():
            if k != '_row_text':
                new_key = k if k not in combined else f"{k}_{file2_name}"
                combined[new_key] = v

        combined['_similarity_score'] = score
        result_rows.append(combined)

    result_df = pd.DataFrame(result_rows)

    # Clean up
    if '_row_text' in result_df.columns:
        result_df = result_df.drop(columns=['_row_text'])

    print(f"[L4→L3] Joined table: {len(result_df)} rows, {len(result_df.columns)} columns")

    return result_df


def _perform_table_join(
    dataframes: Dict[str, pd.DataFrame],
    connections,
    semantic_results: Dict[str, Dict],
    key_prefix: str
) -> Optional[pd.DataFrame]:
    """
    Perform table joins based on connection definitions.

    Supports two formats:
    1. Row-vector format (spec FR-003): {'method': 'row_vector_embeddings', 'files': {...}}
    2. Legacy column-pair format: List of connection dicts

    Args:
        dataframes: Dict of filename -> DataFrame
        connections: Either row-vector config dict or list of connection dicts
        semantic_results: Dict of semantic match results keyed by pair index
        key_prefix: Key prefix used in Step 2 for semantic results

    Returns:
        Joined DataFrame (L3 dataset) or None if join fails
    """
    # Check if this is the new row-vector format (per spec FR-003)
    if isinstance(connections, dict) and connections.get('method') == 'row_vector_embeddings':
        return _perform_row_vector_join(dataframes, connections)

    # Legacy column-pair format
    if not connections:
        return None

    # Start with the first table
    first_conn = connections[0]
    result_df = dataframes[first_conn['file1']].copy()
    joined_files = {first_conn['file1']}

    for idx, conn in enumerate(connections):
        file2 = conn['file2']

        # Skip if already joined
        if file2 in joined_files:
            continue

        df2 = dataframes[file2].copy()
        left_col = conn['col1']
        right_col = conn['col2']
        method = conn['method']

        if method == 'embeddings':
            # Use semantic matching ONLY - create semantic_id as the join key
            # Use pair_idx from connection for correct key lookup (handles skipped pairs)
            pair_idx = conn.get('pair_idx', idx)
            semantic_key = f"{key_prefix}_semantic_{pair_idx}"
            has_semantic = semantic_key in semantic_results

            # Create semantic_id column - this IS the join key
            semantic_id_col = 'semantic_id'

            if has_semantic:
                matches = semantic_results[semantic_key].get('matches', [])

                # Build mapping: original value -> semantic_id
                left_to_id = {}
                right_to_id = {}
                for match_idx, (val1, val2, score) in enumerate(matches):
                    sem_id = f"sem_{match_idx}"
                    left_to_id[str(val1)] = sem_id
                    right_to_id[str(val2)] = sem_id

                # Map values to semantic_id
                result_df[semantic_id_col] = result_df[left_col].astype(str).map(left_to_id)
                df2[semantic_id_col] = df2[right_col].astype(str).map(right_to_id)
            else:
                # No semantic results - create empty semantic_id (will result in no matches)
                result_df[semantic_id_col] = None
                df2[semantic_id_col] = None

            # CRITICAL FIX: Use INNER join to avoid cartesian product explosion
            # With outer join on semantic_id, rows with None semantic_id would create
            # a cartesian product (50k x 20k = 1 billion rows -> OOM)
            # Inner join only keeps rows that have valid semantic matches
            result_df_matched = result_df[result_df[semantic_id_col].notna()]
            df2_matched = df2[df2[semantic_id_col].notna()]

            result_df = pd.merge(
                result_df_matched,
                df2_matched,
                on=semantic_id_col,
                how='inner',
                suffixes=('', f'_{file2}')
            )

        elif method == 'exact_match':
            # Exact match for numeric/ID columns - convert both to same type
            is_numeric = conn.get('is_numeric', False)

            if is_numeric:
                # Convert both columns to numeric for precise matching
                result_df[f'_join_key_left_{idx}'] = pd.to_numeric(
                    result_df[left_col], errors='coerce'
                )
                df2[f'_join_key_right_{idx}'] = pd.to_numeric(
                    df2[right_col], errors='coerce'
                )

                result_df = pd.merge(
                    result_df,
                    df2,
                    left_on=f'_join_key_left_{idx}',
                    right_on=f'_join_key_right_{idx}',
                    how='outer',
                    suffixes=('', f'_{file2}')
                )

                # Clean up temp columns
                for temp_col in [f'_join_key_left_{idx}', f'_join_key_right_{idx}']:
                    if temp_col in result_df.columns:
                        result_df = result_df.drop(columns=[temp_col])
            else:
                # String-based exact match
                result_df = pd.merge(
                    result_df,
                    df2,
                    left_on=left_col,
                    right_on=right_col,
                    how='outer',
                    suffixes=('', f'_{file2}')
                )

        elif method == 'force_match':
            # Force connection - cross join (cartesian product)
            # Use with caution - can create very large results
            result_df['_cross_key'] = 1
            df2['_cross_key'] = 1
            result_df = pd.merge(
                result_df,
                df2,
                on='_cross_key',
                how='outer',
                suffixes=('', f'_{file2}')
            )
            if '_cross_key' in result_df.columns:
                result_df = result_df.drop(columns=['_cross_key'])

        else:
            # Common key join (default - text exact match)
            result_df = pd.merge(
                result_df,
                df2,
                left_on=left_col,
                right_on=right_col,
                how='outer',
                suffixes=('', f'_{file2}')
            )

        joined_files.add(file2)

    return result_df


def render_wizard_step_3_confirm(
    dataframes: Dict[str, pd.DataFrame],
    key_prefix: str = "wizard_s3",
    step2_key_prefix: str = None
) -> Optional[pd.DataFrame]:
    """
    Render wizard step 3: Review joined table.

    Shows the L3 dataset created by joining tables through semantic links.
    Supports both row-vector (spec FR-003) and legacy column-pair formats.

    Args:
        dataframes: Dict of filename -> DataFrame
        key_prefix: Unique key prefix for UI elements
        step2_key_prefix: Key prefix used in Step 2 (for finding connections)

    Returns:
        Joined DataFrame if user confirms, None otherwise
    """
    st.markdown(f"### {t('step_3_of_3_joined')}")
    st.markdown(t("joined_l3_desc"))

    # Determine Step 2 key prefix (derive from Step 3 prefix if not provided)
    if step2_key_prefix is None:
        # Convert wizard_s3 -> wizard_s2, upload_wizard_s3 -> upload_wizard_s2
        step2_key_prefix = key_prefix.replace("_s3", "_s2").replace("s3", "s2")

    # Get connections from Step 2
    connections_key = f"{step2_key_prefix}_connections"
    connections = st.session_state.get(connections_key, {})

    # Handle both row-vector format (dict) and legacy format (list or empty)
    is_row_vector_format = isinstance(connections, dict) and connections.get('method') == 'row_vector_embeddings'

    if not connections:
        st.warning(t("no_connections_defined"))
        if st.button(t("back_to_step_2"), key=f"{key_prefix}_back_no_conn"):
            _set_wizard_step(2)
            st.rerun()
        return None

    # Gather semantic results from session state (only for legacy format)
    semantic_results = {}
    if not is_row_vector_format and isinstance(connections, list):
        for conn in connections:
            pair_idx = conn.get('pair_idx', 0)  # Fall back to 0 for legacy connections
            semantic_key = f"{step2_key_prefix}_semantic_{pair_idx}"
            if semantic_key in st.session_state:
                semantic_results[semantic_key] = st.session_state[semantic_key]

    # Build joined table preview
    joined_key = f"{key_prefix}_joined_df"

    if joined_key not in st.session_state:
        with st.spinner(t("building_joined_table") if is_row_vector_format else t("building_joined_table_simple")):
            joined_df = _perform_table_join(
                dataframes,
                connections,
                semantic_results,
                step2_key_prefix
            )
            st.session_state[joined_key] = joined_df

    joined_df = st.session_state[joined_key]

    if joined_df is None or joined_df.empty:
        st.error(t("could_not_create_joined"))
        if st.button(t("back_to_step_2"), key=f"{key_prefix}_back_empty"):
            # Clear cached joined_df so it rebuilds with new threshold
            if joined_key in st.session_state:
                del st.session_state[joined_key]
            _set_wizard_step(2)
            st.rerun()
        return None

    # Summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(t("rows_label"), f"{len(joined_df):,}")
    with col2:
        st.metric(t("columns_label"), f"{len(joined_df.columns):,}")
    with col3:
        if is_row_vector_format:
            threshold = connections.get('threshold', 0.75)
            st.metric(t("similarity_threshold"), f"{threshold:.0%}")
        else:
            st.metric(t("connections_used"), f"{len(connections)}")

    # Show connection summary
    st.markdown(f"**{t('matching_method')}**")
    if is_row_vector_format:
        files_config = connections.get('files', {})
        st.markdown(f"🧠 **{t('row_vector_semantic')}**")
        for file_name, cols in files_config.items():
            st.markdown(f"  - 📁 `{file_name}`: {', '.join(f'`{c}`' for c in cols)}")
    else:
        for conn in connections:
            method_icon = "🔗" if conn['method'] == 'common_key' else "🧠"
            method_label = t("exact_match") if conn['method'] == 'common_key' else t("semantic")
            st.markdown(f"- {method_icon} `{conn['col1']}` ↔ `{conn['col2']}` ({method_label})")

    st.divider()

    # Table preview
    st.markdown(f"**{t('preview_joined_l3')}**")

    # Show preview with pagination
    preview_rows = st.slider(
        t("rows_to_preview"),
        min_value=5,
        max_value=min(100, len(joined_df)),
        value=min(20, len(joined_df)),
        key=f"{key_prefix}_preview_rows"
    )

    st.dataframe(
        joined_df.head(preview_rows),
        use_container_width=True,
        height=400
    )

    # Column info expander
    with st.expander(f"📋 {t('column_details')}"):
        for col in joined_df.columns:
            dtype = joined_df[col].dtype
            non_null = joined_df[col].notna().sum()
            st.text(f"• {col}: {dtype} ({non_null:,} {t('non_null')})")

    st.divider()

    # Navigation buttons
    col_back, col_space, col_confirm = st.columns([1, 1, 1])

    with col_back:
        if st.button(t("back_arrow"), key=f"{key_prefix}_back"):
            # Clear cached join
            if joined_key in st.session_state:
                del st.session_state[joined_key]
            _set_wizard_step(2)
            st.rerun()

    with col_confirm:
        if st.button(
            f"✅ {t('confirm_use_dataset')}",
            key=f"{key_prefix}_confirm",
            type="primary"
        ):
            st.success(t("dataset_confirmed"))
            return joined_df

    return None


def convert_suggestions_to_mappings(
    entity_suggestions: List[Any],
    relationship_suggestions: List[Any]
) -> Tuple[Dict[str, Dict], Dict[str, Dict]]:
    """
    Convert wizard suggestions to existing entity_mapping and relationship_mapping format.

    This ensures backward compatibility with build_knowledge_graph_from_model().

    Args:
        entity_suggestions: List of EntitySuggestion objects
        relationship_suggestions: List of RelationshipSuggestion objects

    Returns:
        Tuple of (entity_mapping, relationship_mapping) dicts
    """
    entity_mapping = {}
    entity_id_to_name = {}

    for entity in entity_suggestions:
        if entity.accepted:
            name = entity.display_name
            entity_id_to_name[entity.id] = name
            entity_mapping[name] = {
                'source_file': entity.source_file,
                'key_column': entity.key_column,
                'property_columns': entity.property_columns
            }

    relationship_mapping = {}

    for rel in relationship_suggestions:
        if rel.accepted:
            start_name = entity_id_to_name.get(rel.start_entity_id, rel.start_entity_name)
            end_name = entity_id_to_name.get(rel.end_entity_id, rel.end_entity_name)

            # Generate relationship type from column names
            rel_type = "CONNECTS_TO"
            if rel.start_column.lower() == rel.end_column.lower():
                rel_type = f"LINKED_BY_{rel.start_column.upper()}"

            rel_key = f"{start_name}_{rel_type}_{end_name}"
            relationship_mapping[rel_key] = {
                'mode': 'key_matching',
                'start_key_column': rel.start_column,
                'end_key_column': rel.end_column,
                'start_entity': start_name,
                'end_entity': end_name
            }

    return entity_mapping, relationship_mapping


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Session state keys
    'SESSION_KEY_L0_TO_L1_FORM',
    'SESSION_KEY_L1_TO_L2_FORM',
    'SESSION_KEY_L2_TO_L3_FORM',
    'SESSION_KEY_WIZARD_STEP',
    'SESSION_KEY_DISCOVERY_RESULTS',
    # Constants
    'DEFAULT_SIMILARITY_THRESHOLD',
    'MIN_SIMILARITY_THRESHOLD',
    'MAX_SIMILARITY_THRESHOLD',
    'DEFAULT_UNMATCHED_LABEL',
    'DEFAULT_DOMAINS',
    # Form state classes
    'L0ToL1FormState',
    'L1ToL2FormState',
    'L2ToL3FormState',
    # Form state helpers
    '_get_ascent_form_state',
    '_clear_ascent_form_state',
    '_clear_all_ascent_form_states',
    '_get_wizard_step',
    '_set_wizard_step',
    # Note: Shared components moved to ui/ascent/ package (Spec 011)
    # Form renderers
    'render_l0_to_l1_unfold_form',
    'render_l1_to_l2_domain_form',
    'render_l2_to_l3_entity_form',
    # Discovery wizard components
    'render_wizard_step_1_columns',
    'render_wizard_step_1_entities',
    'render_wizard_step_2_connections',
    'render_wizard_step_2_relationships',
    'render_wizard_step_3_confirm',
    'convert_suggestions_to_mappings',
]
