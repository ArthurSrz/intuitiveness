"""
Dimension definitions for ascending through abstraction levels.

Phase 2.1 - Code Simplification (011-code-simplification)
Refactored to support dependency injection while maintaining backward compatibility.

DimensionDefinition: Specifies a categorical dimension to add during ascent.
DimensionRegistry: Manages available dimensions and provides defaults.

Spec Traceability:
------------------
- 002-ascent-functionality: Dimension classification for L1→L2, L2→L3 transitions
- 004-ascent-precision: Domain categorization (business object, pattern type)
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
import pandas as pd
import re

from ..complexity import ComplexityLevel


@dataclass
class DimensionDefinition:
    """
    Specifies a categorical dimension to add during ascent.

    Attributes:
        name: Column name to create
        description: User-facing description
        possible_values: Known categories (should include default_value)
        classifier: Function to classify each item
        default_value: Fallback for unclassifiable items
        applicable_levels: Which transitions this dimension applies to
    """
    name: str
    description: str
    possible_values: List[str]
    classifier: Callable[[Any], str]
    default_value: str = "Unknown"
    applicable_levels: List[tuple] = None  # List of (source, target) tuples

    def __post_init__(self):
        if not self.possible_values:
            raise ValueError("possible_values cannot be empty")
        if self.default_value not in self.possible_values:
            self.possible_values = self.possible_values + [self.default_value]
        if self.applicable_levels is None:
            # Default: applies to L1→L2 and L2→L3
            self.applicable_levels = [
                (ComplexityLevel.LEVEL_1, ComplexityLevel.LEVEL_2),
                (ComplexityLevel.LEVEL_2, ComplexityLevel.LEVEL_3)
            ]

    def classify(self, item: Any) -> str:
        """Classify a single item into a category."""
        try:
            result = self.classifier(item)
            return result if result in self.possible_values else self.default_value
        except Exception:
            return self.default_value

    def apply_to_series(self, series: pd.Series) -> pd.Series:
        """Apply classification to an entire series."""
        return series.apply(self.classify)

    def apply_to_dataframe(self, df: pd.DataFrame, source_column: str = None) -> pd.DataFrame:
        """
        Apply classification to a DataFrame, adding a new column.

        Args:
            df: The DataFrame to classify
            source_column: Column to use for classification (if None, uses index or first column)

        Returns:
            DataFrame with new dimension column added
        """
        result = df.copy()
        if source_column and source_column in df.columns:
            result[self.name] = df[source_column].apply(self.classify)
        elif len(df.columns) > 0:
            # Use first column as source
            result[self.name] = df.iloc[:, 0].apply(self.classify)
        else:
            result[self.name] = self.default_value
        return result


class DimensionRegistry:
    """
    Registry of available dimension definitions.

    Phase 2.1 (011-code-simplification): Supports both singleton access for
    backward compatibility and fresh instances for testing/session isolation.

    Usage:
        # Singleton (backward compatible)
        registry = DimensionRegistry.get_instance()

        # Fresh instance (for testing or session isolation)
        registry = DimensionRegistry(auto_register_defaults=True)

        # Inject into function
        def my_function(registry: DimensionRegistry = None):
            registry = registry or DimensionRegistry.get_instance()
    """

    _instance: Optional['DimensionRegistry'] = None
    _defaults_registered: bool = False

    def __init__(self, auto_register_defaults: bool = False):
        """
        Initialize a new registry.

        Args:
            auto_register_defaults: If True, register default dimension definitions.
                                   Set to True for fresh instances that need defaults.
        """
        self._dimensions: Dict[str, DimensionDefinition] = {}
        self._defaults: Dict[tuple, List[str]] = {}  # (source, target) -> list of default names

        if auto_register_defaults:
            self._register_builtin_defaults()

    @classmethod
    def get_instance(cls) -> 'DimensionRegistry':
        """
        Get the singleton instance of the registry.

        The singleton is lazily initialized with default dimensions registered.
        For fresh instances without singleton behavior, use the constructor directly.
        """
        if cls._instance is None:
            cls._instance = cls()
            # Register defaults on first access (lazy initialization)
            if not cls._defaults_registered:
                cls._instance._register_builtin_defaults()
                cls._defaults_registered = True
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None
        cls._defaults_registered = False

    @classmethod
    def create_fresh(cls, with_defaults: bool = True) -> 'DimensionRegistry':
        """
        Create a fresh registry instance (not singleton).

        Use this for:
        - Testing (isolated state)
        - Per-session registries
        - Custom configurations

        Args:
            with_defaults: Whether to register default dimensions

        Returns:
            New DimensionRegistry instance
        """
        return cls(auto_register_defaults=with_defaults)

    def register(self, dimension: DimensionDefinition, is_default: bool = False) -> None:
        """
        Register a dimension definition.

        Args:
            dimension: The DimensionDefinition to register
            is_default: Whether this is a default dimension for its transitions

        Raises:
            ValueError: If name already registered
        """
        if dimension.name in self._dimensions:
            raise ValueError(f"Dimension '{dimension.name}' already registered")

        self._dimensions[dimension.name] = dimension

        if is_default:
            for level_pair in dimension.applicable_levels:
                if level_pair not in self._defaults:
                    self._defaults[level_pair] = []
                self._defaults[level_pair].append(dimension.name)

    def has(self, name: str) -> bool:
        """Return True if a dimension with this name is registered."""
        return name in self._dimensions

    def get(self, name: str) -> DimensionDefinition:
        """
        Retrieve dimension by name.

        Raises:
            KeyError: If name not found
        """
        if name not in self._dimensions:
            raise KeyError(f"No dimension named '{name}'")
        return self._dimensions[name]

    def list_for_transition(
        self,
        source: ComplexityLevel,
        target: ComplexityLevel
    ) -> List[DimensionDefinition]:
        """
        List all dimensions available for a specific transition.

        Returns:
            List of matching DimensionDefinition objects (may be empty)
        """
        key = (source, target)
        return [
            dim for dim in self._dimensions.values()
            if key in dim.applicable_levels
        ]

    def get_defaults(
        self,
        source: ComplexityLevel,
        target: ComplexityLevel
    ) -> List[DimensionDefinition]:
        """
        Get default dimensions for a transition.

        Returns:
            List of default DimensionDefinition objects
        """
        key = (source, target)
        if key not in self._defaults:
            return []
        return [self._dimensions[name] for name in self._defaults[key]]

    def list_all(self) -> List[DimensionDefinition]:
        """List all registered dimensions."""
        return list(self._dimensions.values())

    def _register_builtin_defaults(self) -> None:
        """
        Register all default dimension definitions.

        Phase 2.1 (011-code-simplification): Instance method for DI support.
        Called lazily on first get_instance() access or when creating fresh instances
        with auto_register_defaults=True.
        """
        # L1 → L2 defaults
        try:
            self.register(
                DimensionDefinition(
                    name='business_object',
                    description='Classify by business object type (revenue, volume, ETP, other)',
                    possible_values=['revenue', 'volume', 'ETP', 'other'],
                    classifier=_classify_business_object,
                    default_value='other',
                    applicable_levels=[(ComplexityLevel.LEVEL_1, ComplexityLevel.LEVEL_2)]
                ),
                is_default=True
            )
        except ValueError:
            pass

        try:
            self.register(
                DimensionDefinition(
                    name='pattern_type',
                    description='Classify by naming pattern (aggregated, averaged, ratio, temporal, raw)',
                    possible_values=['aggregated', 'averaged', 'ratio', 'temporal', 'raw'],
                    classifier=_classify_pattern,
                    default_value='raw',
                    applicable_levels=[(ComplexityLevel.LEVEL_1, ComplexityLevel.LEVEL_2)]
                ),
                is_default=True
            )
        except ValueError:
            pass

        # L2 → L3 defaults
        try:
            self.register(
                DimensionDefinition(
                    name='client_segment',
                    description='Classify by client segment (B2B, B2C, Government)',
                    possible_values=['B2B', 'B2C', 'Government', 'Unknown'],
                    classifier=_classify_client_segment,
                    default_value='Unknown',
                    applicable_levels=[(ComplexityLevel.LEVEL_2, ComplexityLevel.LEVEL_3)]
                ),
                is_default=True
            )
        except ValueError:
            pass

        try:
            self.register(
                DimensionDefinition(
                    name='financial_view',
                    description='Classify by financial perspective (Revenue, Cost, Margin)',
                    possible_values=['Revenue', 'Cost', 'Margin', 'Unknown'],
                    classifier=_classify_financial_view,
                    default_value='Unknown',
                    applicable_levels=[(ComplexityLevel.LEVEL_2, ComplexityLevel.LEVEL_3)]
                ),
                is_default=True
            )
        except ValueError:
            pass


# =============================================================================
# Default Dimensions for L1 → L2
# =============================================================================

def _classify_business_object(item: Any) -> str:
    """Classify item by business object type based on naming patterns."""
    if not isinstance(item, str):
        # Handle dict/signature format from naming_signatures
        if isinstance(item, dict):
            item = item.get('original', str(item))
        else:
            item = str(item)

    item_lower = item.lower()

    if any(kw in item_lower for kw in ['revenue', 'rev', 'income', 'sales']):
        return 'revenue'
    elif any(kw in item_lower for kw in ['volume', 'vol', 'quantity', 'qty', 'count']):
        return 'volume'
    elif any(kw in item_lower for kw in ['etp', 'fte', 'employee', 'staff', 'headcount']):
        return 'ETP'
    else:
        return 'other'


def _classify_pattern(item: Any) -> str:
    """Classify item by naming pattern characteristics."""
    if not isinstance(item, str):
        if isinstance(item, dict):
            item = item.get('original', str(item))
        else:
            item = str(item)

    # Check for common patterns
    if item.startswith(('total_', 'sum_', 'agg_')):
        return 'aggregated'
    elif item.startswith(('avg_', 'mean_', 'median_')):
        return 'averaged'
    elif item.startswith(('pct_', 'percent_', 'ratio_')):
        return 'ratio'
    elif re.search(r'_\d{4}$', item):  # Ends with year
        return 'temporal'
    else:
        return 'raw'


# =============================================================================
# Default Dimensions for L2 → L3
# =============================================================================

def _classify_client_segment(item: Any) -> str:
    """Classify by client segment."""
    if not isinstance(item, str):
        if isinstance(item, dict):
            item = item.get('original', str(item))
        else:
            item = str(item)

    item_lower = item.lower()

    if any(kw in item_lower for kw in ['b2b', 'business', 'enterprise', 'corporate']):
        return 'B2B'
    elif any(kw in item_lower for kw in ['b2c', 'consumer', 'retail', 'individual']):
        return 'B2C'
    elif any(kw in item_lower for kw in ['gov', 'government', 'public', 'sector']):
        return 'Government'
    else:
        return 'Unknown'


def _classify_financial_view(item: Any) -> str:
    """Classify by financial perspective."""
    if not isinstance(item, str):
        if isinstance(item, dict):
            item = item.get('original', str(item))
        else:
            item = str(item)

    item_lower = item.lower()

    if any(kw in item_lower for kw in ['revenue', 'income', 'sales', 'price']):
        return 'Revenue'
    elif any(kw in item_lower for kw in ['cost', 'expense', 'spend', 'outlay']):
        return 'Cost'
    elif any(kw in item_lower for kw in ['margin', 'profit', 'net', 'gross']):
        return 'Margin'
    else:
        return 'Unknown'


# =============================================================================
# Backward compatibility (P2.1: Legacy standalone function)
# =============================================================================

def _register_defaults():
    """
    Legacy function for backward compatibility.

    Deprecated: Use DimensionRegistry.get_instance() which lazily registers defaults,
    or DimensionRegistry.create_fresh(with_defaults=True) for isolated instances.
    """
    # get_instance() already handles registration via lazy initialization
    DimensionRegistry.get_instance()


# =============================================================================
# Grouping relationships for L3 structure
# =============================================================================

def create_dimension_groups(
    df: pd.DataFrame,
    group_by: List[str],
    aggregate_columns: List[str] = None,
    aggregations: Dict[str, str] = None
) -> pd.DataFrame:
    """
    Create hierarchical grouping relationships between dimensions.

    This function groups data by specified dimension columns and optionally
    aggregates other columns, enabling linkable L3 structure.

    Args:
        df: DataFrame with dimension columns
        group_by: List of dimension column names to group by
        aggregate_columns: Optional list of columns to aggregate
        aggregations: Dict mapping column names to aggregation functions
                     (e.g., {'value': 'sum', 'count': 'mean'})

    Returns:
        DataFrame with hierarchical grouping structure

    Example:
        >>> df = pd.DataFrame({
        ...     'value': [1, 2, 3, 4],
        ...     'client_segment': ['B2B', 'B2B', 'B2C', 'B2C'],
        ...     'financial_view': ['Revenue', 'Cost', 'Revenue', 'Cost']
        ... })
        >>> grouped = create_dimension_groups(df, ['client_segment'],
        ...                                   aggregate_columns=['value'],
        ...                                   aggregations={'value': 'sum'})
    """
    if not group_by:
        return df

    # Filter to only existing columns
    valid_group_cols = [c for c in group_by if c in df.columns]
    if not valid_group_cols:
        return df

    # If no aggregation specified, just add group metadata
    if not aggregate_columns and not aggregations:
        result = df.copy()
        # Add group ID based on dimension combination
        result['_group_key'] = df[valid_group_cols].apply(
            lambda row: '|'.join(str(v) for v in row), axis=1
        )
        unique_keys = result['_group_key'].unique()
        key_to_id = {k: i + 1 for i, k in enumerate(unique_keys)}
        result['group_id'] = result['_group_key'].map(key_to_id)
        result.drop('_group_key', axis=1, inplace=True)
        return result

    # Build aggregation dictionary
    agg_dict = {}
    if aggregations:
        for col, func in aggregations.items():
            if col in df.columns:
                agg_dict[col] = func
    elif aggregate_columns:
        for col in aggregate_columns:
            if col in df.columns:
                agg_dict[col] = 'sum'  # Default aggregation

    if agg_dict:
        grouped = df.groupby(valid_group_cols, as_index=False).agg(agg_dict)
        # Add group size
        grouped['group_size'] = df.groupby(valid_group_cols).size().values
        return grouped
    else:
        return df


def get_dimension_hierarchy(
    df: pd.DataFrame,
    dimension_columns: List[str]
) -> Dict[str, Any]:
    """
    Extract hierarchical relationships between dimension values.

    This function analyzes dimension columns to identify parent-child
    relationships based on co-occurrence patterns.

    Args:
        df: DataFrame with dimension columns
        dimension_columns: Ordered list of dimension columns (outer to inner)

    Returns:
        Dictionary representing the hierarchy tree

    Example:
        >>> hierarchy = get_dimension_hierarchy(df, ['client_segment', 'financial_view'])
        >>> # Returns: {'B2B': {'Revenue': [...], 'Cost': [...]}, 'B2C': {...}}
    """
    if not dimension_columns or len(dimension_columns) < 2:
        return {}

    # Filter to valid columns
    valid_cols = [c for c in dimension_columns if c in df.columns]
    if len(valid_cols) < 2:
        return {}

    # Build hierarchy recursively
    def build_tree(data: pd.DataFrame, cols: List[str]) -> Dict:
        if not cols:
            return {}

        current_col = cols[0]
        remaining_cols = cols[1:]

        tree = {}
        for value in data[current_col].unique():
            subset = data[data[current_col] == value]
            if remaining_cols:
                tree[value] = build_tree(subset, remaining_cols)
            else:
                tree[value] = len(subset)  # Leaf: count of items

        return tree

    return build_tree(df, valid_cols)


# =============================================================================
# Auto-classification suggestion
# =============================================================================

def suggest_dimensions(series: pd.Series) -> List[Dict[str, Any]]:
    """
    Analyze a series and suggest applicable dimensions based on data patterns.

    Args:
        series: The L1 vector to analyze

    Returns:
        List of suggestions with dimension name, confidence, and reason
    """
    suggestions = []
    registry = DimensionRegistry.get_instance()

    # Get sample values for analysis
    sample = series.head(20).tolist()
    sample_strs = [str(v) for v in sample]

    # Check business_object dimension applicability
    business_keywords = {
        'revenue': ['revenue', 'rev', 'income', 'sales'],
        'volume': ['volume', 'vol', 'quantity', 'qty', 'count'],
        'ETP': ['etp', 'fte', 'employee', 'staff', 'headcount']
    }
    for category, keywords in business_keywords.items():
        if any(kw in ' '.join(sample_strs).lower() for kw in keywords):
            suggestions.append({
                'dimension': 'business_object',
                'confidence': 'high',
                'reason': f"Found '{category}'-related keywords in data"
            })
            break

    # Check pattern_type dimension applicability
    pattern_indicators = {
        'aggregated': ['total_', 'sum_', 'agg_'],
        'averaged': ['avg_', 'mean_', 'median_'],
        'ratio': ['pct_', 'percent_', 'ratio_']
    }
    for pattern, prefixes in pattern_indicators.items():
        if any(any(s.lower().startswith(p) for p in prefixes) for s in sample_strs):
            suggestions.append({
                'dimension': 'pattern_type',
                'confidence': 'medium',
                'reason': f"Found '{pattern}' naming patterns"
            })
            break

    # If no specific matches, suggest defaults
    if not suggestions:
        defaults = registry.get_defaults(ComplexityLevel.LEVEL_1, ComplexityLevel.LEVEL_2)
        for d in defaults[:2]:
            suggestions.append({
                'dimension': d.name,
                'confidence': 'low',
                'reason': 'Default dimension for L1→L2 transition'
            })

    return suggestions


def find_duplicates(df: pd.DataFrame, dimension_columns: List[str]) -> pd.DataFrame:
    """
    Find items with identical values across specified dimension columns.

    Args:
        df: DataFrame with dimension columns
        dimension_columns: Columns to check for duplicates

    Returns:
        DataFrame with duplicate groups marked
    """
    if not dimension_columns:
        return df

    # Filter to only existing columns
    valid_cols = [c for c in dimension_columns if c in df.columns]
    if not valid_cols:
        return df

    # Create a copy and add duplicate group marker
    result = df.copy()

    # Create a composite key from dimension values
    result['_dimension_key'] = df[valid_cols].apply(
        lambda row: '|'.join(str(v) for v in row), axis=1
    )

    # Count occurrences of each key
    key_counts = result['_dimension_key'].value_counts()

    # Mark duplicates (keys appearing more than once)
    result['is_potential_duplicate'] = result['_dimension_key'].apply(
        lambda k: key_counts[k] > 1
    )

    # Add duplicate group ID
    duplicate_keys = key_counts[key_counts > 1].index.tolist()
    key_to_group = {k: i + 1 for i, k in enumerate(duplicate_keys)}
    result['duplicate_group'] = result['_dimension_key'].apply(
        lambda k: key_to_group.get(k, 0)
    )

    # Clean up
    result.drop('_dimension_key', axis=1, inplace=True)

    return result


# =============================================================================
# T019: RelationshipDefinition for L2→L3 drag-and-drop (002-ascent-functionality)
# =============================================================================

@dataclass
class RelationshipDefinition:
    """
    A user-defined relationship between entities in the drag-and-drop interface.

    Used for L2→L3 ascent when users visually define relationships between
    columns/entities in their data.

    Attributes:
        source_entity: Source column/entity name
        target_entity: Target column/entity name
        relationship_type: User-provided label (e.g., "BELONGS_TO", "HAS")
        bidirectional: Whether edge is bidirectional (default False)
    """
    source_entity: str
    target_entity: str
    relationship_type: str
    bidirectional: bool = False

    def to_networkx_edge(self) -> tuple:
        """
        Convert to NetworkX edge format.

        Returns:
            Tuple of (source, target, attributes_dict)
        """
        return (
            self.source_entity,
            self.target_entity,
            {"type": self.relationship_type, "bidirectional": self.bidirectional}
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "source_entity": self.source_entity,
            "target_entity": self.target_entity,
            "relationship_type": self.relationship_type,
            "bidirectional": self.bidirectional
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RelationshipDefinition':
        """Create from dictionary."""
        return cls(
            source_entity=data["source_entity"],
            target_entity=data["target_entity"],
            relationship_type=data["relationship_type"],
            bidirectional=data.get("bidirectional", False)
        )

    def __str__(self) -> str:
        arrow = "<->" if self.bidirectional else "->"
        return f"{self.source_entity} {arrow}[{self.relationship_type}]{arrow} {self.target_entity}"


def apply_relationships_to_dataframe(
    df: pd.DataFrame,
    relationships: List[RelationshipDefinition],
    source_column: str = None
) -> pd.DataFrame:
    """
    Apply relationship definitions to create L3-ready structure.

    This function adds relationship metadata columns to a DataFrame,
    preparing it for graph construction.

    Args:
        df: The L2 DataFrame to augment
        relationships: List of relationship definitions from drag-and-drop UI
        source_column: Optional column to use as source entity identifier

    Returns:
        DataFrame with relationship metadata columns added
    """
    if not relationships:
        return df

    result = df.copy()

    # Add relationship type column based on patterns in data
    for rel in relationships:
        col_name = f"_rel_{rel.source_entity}_{rel.target_entity}"

        # Check if both entities exist as columns
        if rel.source_entity in df.columns and rel.target_entity in df.columns:
            # Create relationship indicator
            result[col_name] = rel.relationship_type
        elif rel.source_entity in df.columns:
            # Source exists, target is implicit
            result[col_name] = rel.relationship_type

    return result


def create_graph_from_relationships(
    df: pd.DataFrame,
    relationships: List[RelationshipDefinition],
    node_column: str = None
):
    """
    Create a NetworkX graph from DataFrame and relationship definitions.

    Args:
        df: The L2 DataFrame
        relationships: List of relationship definitions
        node_column: Column to use for node identifiers (if None, uses index)

    Returns:
        NetworkX DiGraph with nodes and edges based on relationships
    """
    import networkx as nx

    G = nx.DiGraph()

    # Add nodes from DataFrame
    if node_column and node_column in df.columns:
        nodes = df[node_column].unique().tolist()
    else:
        nodes = df.index.tolist()

    for node in nodes:
        G.add_node(node)

    # Add edges from relationships
    for rel in relationships:
        edge_data = {"type": rel.relationship_type}

        # If source and target are columns, create edges between their values
        if rel.source_entity in df.columns and rel.target_entity in df.columns:
            for _, row in df.iterrows():
                source_val = row[rel.source_entity]
                target_val = row[rel.target_entity]
                if pd.notna(source_val) and pd.notna(target_val):
                    G.add_edge(source_val, target_val, **edge_data)
                    if rel.bidirectional:
                        G.add_edge(target_val, source_val, **edge_data)
        else:
            # Add as metadata relationship
            G.add_edge(rel.source_entity, rel.target_entity, **edge_data)
            if rel.bidirectional:
                G.add_edge(rel.target_entity, rel.source_entity, **edge_data)

    return G


# P2.1: Removed auto-registration on module import
# Defaults are now lazily registered on first get_instance() access
# This improves testability and allows for isolated instances
