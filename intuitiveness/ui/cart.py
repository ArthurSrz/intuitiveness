"""
Cart UI Components

Provides unified cart interface for dataset selection workflow:
- Sidebar cart display with item cards
- Cart badge showing item count
- Main area preview grid
- Add/remove/clear operations

Created: 2026-02-03
Spec: Cart-based dataset selection workflow
"""

import streamlit as st
from typing import Optional, Dict, Any
import pandas as pd

from intuitiveness.app.models.cart import CartManager, CartItem
from intuitiveness.ui import t


def render_cart_sidebar() -> bool:
    """
    Render cart in sidebar with all items and "Start Analysis" button.

    Returns:
        True if user clicked "Start Analysis", False otherwise

    UI Layout:
        📦 Selection Cart (N)
        ─────────────────
        [Dataset Card 1]
        [Dataset Card 2]
        ...
        ─────────────────
        ✅ Start Analysis
        🗑️ Clear All
    """
    cart = CartManager()

    # Header with item count
    item_count = cart.count()
    st.markdown(f"### 📦 {t('cart_title')} ({item_count})")

    if cart.is_empty():
        st.info(t('cart_empty'))
        return False

    st.markdown("---")

    # Render each cart item
    items = cart.get_all_items()
    for name, item in items.items():
        _render_cart_item_card(name, item)

    st.markdown("---")

    # Action buttons
    col1, col2 = st.columns(2)

    with col1:
        start_clicked = st.button(
            f"✅ {t('start_analysis')}",
            type="primary",
            use_container_width=True,
            key="cart_start_analysis"
        )

    with col2:
        if st.button(
            f"🗑️ {t('clear_all')}",
            use_container_width=True,
            key="cart_clear_all"
        ):
            cart.clear()
            st.rerun()

    return start_clicked


def _render_cart_item_card(name: str, item: CartItem) -> None:
    """
    Render a single cart item as a card with metadata and remove button.

    Args:
        name: Dataset name
        item: CartItem to display
    """
    cart = CartManager()

    # Source icon mapping
    source_icons = {
        'upload': '📁',
        'datagouv': '🌐',
        'demo': '🎯'
    }

    icon = source_icons.get(item.source, '📄')

    with st.container():
        # Item header with source icon
        st.markdown(f"**{icon} {name}**")

        # Metadata
        st.caption(f"{item.rows:,} rows × {item.columns} columns")

        # Source-specific metadata
        if item.source == 'datagouv' and 'organization' in item.source_metadata:
            st.caption(f"from {item.source_metadata['organization']}")

        # Remove button
        if st.button(
            t('cart_item_remove'),
            key=f"cart_remove_{name}",
            use_container_width=True,
            type="secondary"
        ):
            cart.remove_item(name)
            st.rerun()

        st.markdown("")  # Spacing


def render_cart_badge() -> None:
    """
    Render floating cart badge showing item count.

    Displays in top-right corner of main area.
    Only shown when cart is not empty.
    """
    cart = CartManager()
    count = cart.count()

    if count == 0:
        return

    st.markdown(f"""
    <style>
    .cart-badge {{
        position: fixed;
        top: 4rem;
        right: 2rem;
        background: #3b82f6;
        color: white;
        border-radius: 50%;
        width: 3rem;
        height: 3rem;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 1.2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 999;
    }}
    </style>
    <div class="cart-badge">{count}</div>
    """, unsafe_allow_html=True)


def render_cart_preview_grid() -> None:
    """
    Render cart contents as a preview grid in main area.

    Shows all datasets with quick stats and preview option.
    Used in selection mode before starting analysis.
    """
    cart = CartManager()

    if cart.is_empty():
        st.info(t('cart_empty'))
        return

    items = cart.get_all_items()

    st.markdown(f"### {t('cart_title')} ({cart.count()})")
    st.markdown(f"**{cart.get_total_rows():,}** total rows · **{cart.get_total_columns()}** total columns")

    # Grid layout - 2 columns
    cols = st.columns(2)

    for idx, (name, item) in enumerate(items.items()):
        with cols[idx % 2]:
            _render_cart_preview_card(name, item)


def _render_cart_preview_card(name: str, item: CartItem) -> None:
    """
    Render a dataset preview card in the main area grid.

    Args:
        name: Dataset name
        item: CartItem to display
    """
    # Source icon
    source_icons = {
        'upload': '📁',
        'datagouv': '🌐',
        'demo': '🎯'
    }
    icon = source_icons.get(item.source, '📄')

    with st.container():
        st.markdown(f"""
        <div style="
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            background: white;
        ">
            <h4 style="margin: 0 0 0.5rem 0;">{icon} {name}</h4>
            <p style="margin: 0; color: #64748b; font-size: 0.9rem;">
                {item.rows:,} rows × {item.columns} columns
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Expandable preview
        with st.expander("Preview data"):
            st.dataframe(item.dataframe.head(5), use_container_width=True)


def render_cart_state_indicator() -> None:
    """
    Render visual indicator of cart mode (selection vs processing).

    Shows current workflow state to the user.
    """
    cart_mode = st.session_state.get('cart_mode', 'selection')

    if cart_mode == 'selection':
        st.info("🛒 **Building your selection...** Add datasets to cart, then click 'Start Analysis'")
    else:
        st.success("⚙️ **Analyzing datasets...** Configure connections and proceed")


def add_to_cart_button(
    dataset_name: str,
    df: pd.DataFrame,
    source: str,
    metadata: Optional[Dict[str, Any]] = None,
    key_suffix: str = ""
) -> bool:
    """
    Render "Add to Cart" button and handle adding dataset.

    Args:
        dataset_name: Name for the dataset
        df: DataFrame to add
        source: Source type ('upload', 'datagouv', 'demo')
        metadata: Optional metadata
        key_suffix: Suffix for button key uniqueness

    Returns:
        True if dataset was added, False otherwise
    """
    cart = CartManager()

    button_key = f"add_to_cart_{key_suffix}_{dataset_name}"

    # Check if already in cart
    if cart.get_item(dataset_name):
        st.success(f"✓ {t('added_to_cart')}")
        return False

    if st.button(
        f"➕ {t('add_to_selection')}",
        key=button_key,
        type="primary"
    ):
        cart.add_item(
            name=dataset_name,
            source=source,
            df=df,
            metadata=metadata
        )
        st.success(t('added_to_cart'))
        st.rerun()
        return True

    return False
