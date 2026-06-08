from .complexity import (
    ComplexityLevel,
    Dataset,
    Level4Dataset,
    Level3Dataset,
    Level2Dataset,
    Level1Dataset,
    Level0Dataset
)
# Redesigner = the unified spec-015 engine (single transition chokepoint)
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
    NavigationError,
    SessionNotFoundError
)
from .ascent import (
    EnrichmentFunction,
    EnrichmentRegistry,
    DimensionDefinition,
    DimensionRegistry,
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

# UI Components — optional, require the "app" extra (streamlit). Skipped on a
# headless/library install so `import intuitiveness` works without streamlit.
try:
    from . import ui
    from . import export
    UI_AVAILABLE = True
except ImportError:
    UI_AVAILABLE = False

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
    "NavigationError",
    "SessionNotFoundError",
    # Ascent functionality (User Story 2 - Reverse Navigation)
    "EnrichmentFunction",
    "EnrichmentRegistry",
    "DimensionDefinition",
    "DimensionRegistry",
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
