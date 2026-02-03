"""
Cart Infrastructure for Dataset Selection

Implements cart-based workflow where users can:
- Add multiple datasets from any source (upload, data.gouv.fr, demo)
- Review selections in a unified cart
- Explicitly start analysis when ready

This replaces the auto-advancement pattern with explicit user control.

Created: 2026-02-03
Spec: Cart-based dataset selection workflow
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd
import streamlit as st


@dataclass
class CartItem:
    """
    Represents a dataset in the selection cart.

    Attributes:
        name: Display name for the dataset
        source: Origin of the dataset ('upload', 'datagouv', 'demo')
        dataframe: The actual pandas DataFrame
        rows: Number of rows in the dataset
        columns: Number of columns in the dataset
        source_metadata: Source-specific metadata (e.g., dataset ID, organization)
        added_at: Timestamp when item was added to cart
    """
    name: str
    source: str  # 'upload', 'datagouv', 'demo'
    dataframe: pd.DataFrame
    rows: int
    columns: int
    source_metadata: Dict[str, Any] = field(default_factory=dict)
    added_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate cart item data."""
        if self.source not in ['upload', 'datagouv', 'demo']:
            raise ValueError(f"Invalid source: {self.source}. Must be 'upload', 'datagouv', or 'demo'")

        if self.dataframe is None or self.dataframe.empty:
            raise ValueError("DataFrame cannot be None or empty")

        if self.rows <= 0 or self.columns <= 0:
            raise ValueError(f"Invalid dimensions: rows={self.rows}, columns={self.columns}")


class CartManager:
    """
    Manages the dataset selection cart stored in Streamlit session state.

    The cart is a dictionary mapping dataset names to CartItem objects.
    Session state key: 'dataset_cart'

    Usage:
        cart = CartManager()
        cart.add_item("schools.csv", "upload", df)
        items = cart.get_all_items()
        raw_data = cart.to_raw_data()
    """

    SESSION_KEY = "dataset_cart"

    def __init__(self):
        """Initialize cart manager and ensure cart exists in session state."""
        if self.SESSION_KEY not in st.session_state:
            st.session_state[self.SESSION_KEY] = {}

    def add_item(
        self,
        name: str,
        source: str,
        df: pd.DataFrame,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a dataset to the cart.

        If an item with the same name exists, it will be replaced.

        Args:
            name: Display name for the dataset
            source: Dataset origin ('upload', 'datagouv', 'demo')
            df: The pandas DataFrame
            metadata: Optional source-specific metadata

        Raises:
            ValueError: If validation fails
        """
        cart_item = CartItem(
            name=name,
            source=source,
            dataframe=df,
            rows=df.shape[0],
            columns=df.shape[1],
            source_metadata=metadata or {},
            added_at=datetime.now()
        )

        st.session_state[self.SESSION_KEY][name] = cart_item

    def remove_item(self, name: str) -> bool:
        """
        Remove a dataset from the cart.

        Args:
            name: Name of the dataset to remove

        Returns:
            True if item was removed, False if not found
        """
        if name in st.session_state[self.SESSION_KEY]:
            del st.session_state[self.SESSION_KEY][name]
            return True
        return False

    def clear(self) -> None:
        """Remove all items from the cart."""
        st.session_state[self.SESSION_KEY] = {}

    def get_item(self, name: str) -> Optional[CartItem]:
        """
        Get a specific cart item by name.

        Args:
            name: Name of the dataset

        Returns:
            CartItem if found, None otherwise
        """
        return st.session_state[self.SESSION_KEY].get(name)

    def get_all_items(self) -> Dict[str, CartItem]:
        """
        Get all items in the cart.

        Returns:
            Dictionary mapping names to CartItem objects
        """
        return st.session_state[self.SESSION_KEY].copy()

    def is_empty(self) -> bool:
        """Check if the cart is empty."""
        return len(st.session_state[self.SESSION_KEY]) == 0

    def count(self) -> int:
        """Get the number of items in the cart."""
        return len(st.session_state[self.SESSION_KEY])

    def to_raw_data(self) -> Dict[str, pd.DataFrame]:
        """
        Convert cart items to raw_data format for workflow processing.

        Returns:
            Dictionary mapping dataset names to DataFrames
        """
        return {
            name: item.dataframe
            for name, item in st.session_state[self.SESSION_KEY].items()
        }

    def get_total_rows(self) -> int:
        """Get total row count across all datasets."""
        return sum(item.rows for item in st.session_state[self.SESSION_KEY].values())

    def get_total_columns(self) -> int:
        """Get total column count across all datasets."""
        return sum(item.columns for item in st.session_state[self.SESSION_KEY].values())
