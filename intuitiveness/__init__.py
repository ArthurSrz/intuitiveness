from .complexity import (
    ComplexityLevel,
    Dataset,
    Level4Dataset,
    Level3Dataset,
    Level2Dataset,
    Level1Dataset,
    Level0Dataset
)
# Import Redesigner from redesign package (uses legacy redesign_legacy.py for now)
from .redesign import Redesigner
from .interactive import (
    InteractiveRedesigner,
    TransitionQuestions,
    QuestionType,
    UserAnswer,
    DataModelGenerator,
    Neo4jDataModel,
    SemanticMatcher,
    run_interactive_descent
)
from .neo4j_writer import (
    Neo4jMCPWriter,
    Neo4jWriteResult,
    generate_constraint_queries,
    generate_node_ingest_query,
    generate_relationship_ingest_query,
    generate_full_ingest_script,
    graph_to_neo4j_records
)
from .navigation import (
    NavigationSession,
    NavigationState,
    NavigationStep,
    NavigationHistory,
    NavigationError,
    SessionNotFoundError
)
from .ascent import (
    EnrichmentFunction,
    EnrichmentRegistry,
    DimensionDefinition,
    DimensionRegistry,
    AscentOperation,
    suggest_dimensions,
    find_duplicates,
    create_dimension_groups,
    get_dimension_hierarchy
)
from .navigation import (
    NavigationTree,
    NavigationTreeNode,
    NavigationAction
)

# UI Components (002-ascent-functionality)
from . import ui
from . import export

# Neo4j Agent integration (optional - requires 'neo4j' package)
try:
    from .neo4j_client import Neo4jClient, Neo4jResult
    from .agent import SmolLM2Agent, AgentResult, AgentStep, AgentAction, simple_chat
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    Neo4jClient = None
    Neo4jResult = None
    SmolLM2Agent = None
    AgentResult = None
    AgentStep = None
    AgentAction = None
    simple_chat = None

__all__ = [
    # Core complexity classes
    "ComplexityLevel",
    "Dataset",
    "Level4Dataset",
    "Level3Dataset",
    "Level2Dataset",
    "Level1Dataset",
    "Level0Dataset",
    # Redesigner (imported from redesign package)
    "Redesigner",
    # Interactive workflow
    "InteractiveRedesigner",
    "TransitionQuestions",
    "QuestionType",
    "UserAnswer",
    "DataModelGenerator",
    "Neo4jDataModel",
    "SemanticMatcher",
    "run_interactive_descent",
    # Neo4j writer
    "Neo4jMCPWriter",
    "Neo4jWriteResult",
    "generate_constraint_queries",
    "generate_node_ingest_query",
    "generate_relationship_ingest_query",
    "generate_full_ingest_script",
    "graph_to_neo4j_records",
    # Navigation (User Story 5)
    "NavigationSession",
    "NavigationState",
    "NavigationStep",
    "NavigationHistory",
    "NavigationError",
    "SessionNotFoundError",
    # Ascent functionality (User Story 2 - Reverse Navigation)
    "EnrichmentFunction",
    "EnrichmentRegistry",
    "DimensionDefinition",
    "DimensionRegistry",
    "AscentOperation",
    "suggest_dimensions",
    "find_duplicates",
    "create_dimension_groups",
    "get_dimension_hierarchy",
    # Navigation Tree (002-ascent-functionality)
    "NavigationTree",
    "NavigationTreeNode",
    "NavigationAction",
    # UI and Export subpackages (002-ascent-functionality)
    "ui",
    "export",
    # Neo4j Agent (optional)
    "NEO4J_AVAILABLE",
    "Neo4jClient",
    "Neo4jResult",
    "SmolLM2Agent",
    "AgentResult",
    "AgentStep",
    "AgentAction",
    "simple_chat"
]
