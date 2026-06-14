from .complexity import (
    ComplexityLevel,
    Dataset,
    Level4Dataset,
    Level3Dataset,
    Level2Dataset,
    Level1Dataset,
    Level0Dataset
)
from .complexity_measure import (
    complexity as dataset_complexity,
    linking_complexity,
    reduction_ratio,
    complexity_report,
)
from .redesign import Redesigner
from .navigation import (
    NavigationSession,
    NavigationState,
    NavigationError,
    SessionNotFoundError,
    NavigationTree,
    NavigationTreeNode,
    NavigationAction,
)
from .ascent import (
    EnrichmentFunction,
    EnrichmentRegistry,
    DimensionDefinition,
    DimensionRegistry,
    suggest_dimensions,
    find_duplicates,
    create_dimension_groups,
    get_dimension_hierarchy,
)

# Neo4j client (optional — requires 'neo4j' package)
try:
    from .neo4j_client import Neo4jClient, Neo4jResult
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    Neo4jClient = None
    Neo4jResult = None

__all__ = [
    "ComplexityLevel",
    "Dataset",
    "Level4Dataset",
    "Level3Dataset",
    "Level2Dataset",
    "Level1Dataset",
    "Level0Dataset",
    "Redesigner",
    "NavigationSession",
    "NavigationState",
    "NavigationError",
    "SessionNotFoundError",
    "NavigationTree",
    "NavigationTreeNode",
    "NavigationAction",
    "EnrichmentFunction",
    "EnrichmentRegistry",
    "DimensionDefinition",
    "DimensionRegistry",
    "suggest_dimensions",
    "find_duplicates",
    "create_dimension_groups",
    "get_dimension_hierarchy",
    "NEO4J_AVAILABLE",
    "Neo4jClient",
    "Neo4jResult",
]
