"""
L2→L3 Graph Building Module

Implements Spec 004: FR-011-015 (L2→L3 Graph Building)

Provides graph construction from L2 tables with orphan node prevention.
Ensures all nodes have at least one edge (Design Constraint 1 from CLAUDE.md).

Functions:
----------
- build_l2_to_l3_graph: Main graph construction with orphan prevention
- validate_no_orphan_nodes: Validation function
- OrphanNodeError: Exception raised when orphan nodes detected

Example:
--------
>>> from intuitiveness.complexity import Level2Dataset, Level3Dataset
>>> import pandas as pd
>>>
>>> # Create L2 table with school data
>>> df = pd.DataFrame({
...     'school_id': ['A', 'B', 'C'],
...     'score': [85, 90, 78],
...     'category': ['high', 'high', 'low']
... })
>>> l2 = Level2Dataset(df)
>>>
>>> # Build graph extracting 'category' as entity
>>> l3 = build_l2_to_l3_graph(l2, entity_column='category', value_column='score')
>>>
>>> # Result: Graph with category nodes linked to schools
>>> # No orphan nodes guaranteed
"""

from typing import Optional, List, Set, Dict, Any
import pandas as pd
import networkx as nx

from complexity import Level2Dataset, Level3Dataset


class OrphanNodeError(Exception):
    """
    Exception raised when graph construction would create orphan nodes.

    Implements Spec 004: FR-014 (Orphan Node Prevention)
    Design Constraint 1: Nodes must always have relations

    This enforces the framework's design principle that orphan nodes
    are not allowed in the interface.
    """
    pass


def build_l2_to_l3_graph(
    table: Level2Dataset,
    entity_column: str,
    value_column: Optional[str] = None,
    relationship_type: str = "belongs_to",
    validate_orphans: bool = True
) -> Level3Dataset:
    """
    Build L3 graph from L2 table by extracting column as new entity type.

    Implements Spec 004: FR-011-015 (L2→L3 Graph Building)
    Design Constraint 1: No orphan nodes allowed

    Creates a bipartite graph:
    - Type 1 nodes: Original entities (from table index)
    - Type 2 nodes: New entities (from entity_column unique values)
    - Edges: Relationships between them

    Architectural Decision (from CLAUDE.md):
    -----------------------------------------
    We enforce **no orphan nodes** (Design Constraint 1).
    All nodes must have at least one edge. If extraction would create
    orphan nodes, raises OrphanNodeError.

    This ensures:
    - Graph visualization is always meaningful
    - Queries always traverse relationships
    - No isolated data points confuse users

    Parameters:
    -----------
    table : Level2Dataset
        The L2 table to extract from
    entity_column : str
        Column to extract as new entity type
    value_column : Optional[str]
        Column containing edge weights/values (optional)
    relationship_type : str
        Relationship label (default: "belongs_to")
    validate_orphans : bool
        If True (default), raises OrphanNodeError if orphans detected

    Returns:
    --------
    Level3Dataset
        Graph with no orphan nodes

    Raises:
    -------
    OrphanNodeError
        If graph would contain orphan nodes and validate_orphans=True
    ValueError
        If entity_column not found in table

    Example:
    --------
    >>> # Example from test0 dataset (schools)
    >>> import pandas as pd
    >>> df = pd.DataFrame({
    ...     'school_id': ['School_A', 'School_B', 'School_C', 'School_D'],
    ...     'score': [95, 78, 92, 65],
    ...     'category': ['high', 'low', 'high', 'low'],
    ...     'students': [410, 380, 425, 350]
    ... })
    >>> l2 = Level2Dataset(df)
    >>>
    >>> # Build graph: schools connected to categories
    >>> l3 = build_l2_to_l3_graph(
    ...     l2,
    ...     entity_column='category',
    ...     value_column='score',
    ...     relationship_type='has_score_category'
    ... )
    >>>
    >>> # Result: Bipartite graph
    >>> # Nodes: School_A, School_B, School_C, School_D (type: school)
    >>> #        high, low (type: category)
    >>> # Edges: School_A --[has_score_category]--> high
    >>> #        School_B --[has_score_category]--> low
    >>> #        (etc.)
    >>> # No orphan nodes guaranteed!
    """
    if not isinstance(table, Level2Dataset):
        raise TypeError(f"Expected Level2Dataset, got {type(table).__name__}")

    df = table.get_data()

    if entity_column not in df.columns:
        raise ValueError(f"Column '{entity_column}' not found in table. Available: {list(df.columns)}")

    # Create NetworkX graph
    G = nx.DiGraph()

    # Add original entities as nodes (Type 1)
    original_entities = df.index.tolist() if df.index.name else range(len(df))
    for entity in original_entities:
        G.add_node(entity, node_type="original", entity_type="row")

    # Add new entities from entity_column as nodes (Type 2)
    new_entities = df[entity_column].unique()
    for entity in new_entities:
        if pd.notna(entity):  # Skip NaN values
            G.add_node(entity, node_type="extracted", entity_type=entity_column)

    # Add edges between original and new entities
    for idx, row in df.iterrows():
        original_entity = idx if df.index.name else original_entities[idx if isinstance(idx, int) else list(df.index).index(idx)]
        new_entity = row[entity_column]

        if pd.notna(new_entity):
            edge_attrs = {
                "relationship": relationship_type,
                "source_column": entity_column
            }

            # Add edge weight if value_column specified
            if value_column and value_column in df.columns:
                edge_attrs["weight"] = row[value_column]

            G.add_edge(original_entity, new_entity, **edge_attrs)

    # Validate no orphan nodes (Design Constraint 1)
    if validate_orphans:
        orphans = validate_no_orphan_nodes(G)
        if orphans:
            raise OrphanNodeError(
                f"Graph construction would create {len(orphans)} orphan node(s).\\n"
                f"Orphan nodes: {orphans}\\n\\n"
                f"Design Constraint 1: All nodes must have at least one edge.\\n"
                f"Suggestions:\\n"
                f"  1. Remove rows with missing values in '{entity_column}'\\n"
                f"  2. Choose a different entity_column with better connectivity\\n"
                f"  3. Add relationship columns to connect isolated entities"
            )

    # Create L3 dataset
    l3 = Level3Dataset(G)

    # Attach metadata
    l3._metadata = {
        "built_from": "L2_table",
        "entity_column": entity_column,
        "relationship_type": relationship_type,
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "bipartite": True,
        "source_operation": f"Built graph extracting '{entity_column}' as entities"
    }

    return l3


def validate_no_orphan_nodes(graph: nx.Graph) -> List[Any]:
    """
    Validate that graph has no orphan nodes (Design Constraint 1).

    An orphan node is a node with degree 0 (no edges).

    Parameters:
    -----------
    graph : nx.Graph
        The graph to validate

    Returns:
    --------
    List[Any]
        List of orphan node IDs (empty if no orphans)

    Example:
    --------
    >>> G = nx.Graph()
    >>> G.add_nodes_from([1, 2, 3, 4])
    >>> G.add_edge(1, 2)
    >>> orphans = validate_no_orphan_nodes(G)
    >>> print(f"Orphan nodes: {orphans}")  # [3, 4]
    """
    orphans = [node for node in graph.nodes() if graph.degree(node) == 0]
    return orphans


def get_graph_statistics(l3_graph: Level3Dataset) -> Dict[str, Any]:
    """
    Get statistics about graph structure.

    Returns dictionary with:
    - node_count: Total number of nodes
    - edge_count: Total number of edges
    - node_types: Distribution of node types
    - avg_degree: Average node degree
    - orphan_count: Number of orphan nodes (should be 0)

    Parameters:
    -----------
    l3_graph : Level3Dataset
        The L3 graph

    Returns:
    --------
    dict
        Graph statistics for analysis

    Example:
    --------
    >>> stats = get_graph_statistics(l3)
    >>> print(f"Graph: {stats['node_count']} nodes, {stats['edge_count']} edges")
    >>> print(f"Orphan nodes: {stats['orphan_count']} (should be 0)")
    """
    G = l3_graph.get_data()

    if not isinstance(G, nx.Graph):
        raise TypeError(f"Expected NetworkX graph, got {type(G).__name__}")

    # Count node types
    node_types = {}
    for node in G.nodes():
        node_type = G.nodes[node].get('node_type', 'unknown')
        node_types[node_type] = node_types.get(node_type, 0) + 1

    # Calculate degrees
    degrees = [G.degree(node) for node in G.nodes()]
    avg_degree = sum(degrees) / len(degrees) if degrees else 0

    # Count orphans
    orphans = validate_no_orphan_nodes(G)

    stats = {
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "node_types": node_types,
        "avg_degree": avg_degree,
        "min_degree": min(degrees) if degrees else 0,
        "max_degree": max(degrees) if degrees else 0,
        "orphan_count": len(orphans),
        "orphan_nodes": orphans,
        "is_connected": nx.is_weakly_connected(G) if G.is_directed() else nx.is_connected(G),
        "density": nx.density(G)
    }

    return stats


def remove_orphan_nodes(graph: nx.Graph) -> nx.Graph:
    """
    Remove orphan nodes from graph (in-place).

    Use this as a cleanup step if orphan nodes are acceptable
    in your use case (not recommended per Design Constraint 1).

    Parameters:
    -----------
    graph : nx.Graph
        The graph to clean

    Returns:
    --------
    nx.Graph
        The same graph with orphans removed

    Example:
    --------
    >>> G = nx.Graph()
    >>> G.add_nodes_from([1, 2, 3, 4])
    >>> G.add_edge(1, 2)
    >>> G_clean = remove_orphan_nodes(G)
    >>> print(G_clean.number_of_nodes())  # 2 (orphans 3, 4 removed)
    """
    orphans = validate_no_orphan_nodes(graph)
    graph.remove_nodes_from(orphans)
    return graph
