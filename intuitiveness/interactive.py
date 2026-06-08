"""
Interactive Redesign Module

This module provides a question-answer driven workflow for the descent-ascent cycle
of the intuitiveness framework. Each level transition is guided by questions that
help users define the data model structure.

Key Features:
- L4 -> L3: Entity-based data modeling with Neo4j schema generation
- L3 -> L2: Domain categorization with keyword + semantic similarity (all-MiniLM)
- L2 -> L1: Feature extraction guided by user-defined columns
- L1 -> L0: Aggregation metric selection

Author: Intuitiveness Framework
"""

from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import networkx as nx
import numpy as np
import json

from .complexity import (
    Dataset, ComplexityLevel,
    Level4Dataset, Level3Dataset, Level2Dataset, Level1Dataset, Level0Dataset
)


class QuestionType(Enum):
    """Types of questions in the Q&A workflow."""
    ENTITIES = "entities"  # For L4->L3: What entities do you want?
    DOMAINS = "domains"  # For L3->L2: What domains to categorize by?
    FEATURES = "features"  # For L2->L1: What features to extract?
    AGGREGATION = "aggregation"  # For L1->L0: What metric to compute?
    DIMENSIONS = "dimensions"  # For L0->L1 (ascent): What dimensions to add?


@dataclass
class TransitionQuestion:
    """A question asked during level transition."""
    question_type: QuestionType
    prompt: str
    description: str
    examples: List[str] = field(default_factory=list)
    default_answer: Optional[str] = None


@dataclass
class UserAnswer:
    """User's answer to a transition question."""
    question_type: QuestionType
    values: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataModelNode:
    """Represents a node in the Neo4j data model."""
    label: str
    key_property: str
    properties: List[Dict[str, str]] = field(default_factory=list)
    description: Optional[str] = None


@dataclass
class DataModelRelationship:
    """Represents a relationship in the Neo4j data model."""
    type: str
    start_node_label: str
    end_node_label: str
    properties: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class Neo4jDataModel:
    """A complete Neo4j data model schema."""
    nodes: List[DataModelNode]
    relationships: List[DataModelRelationship]

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON format compatible with Neo4j MCP."""
        return {
            "nodes": [
                {
                    "label": n.label,
                    "key_property": {"name": n.key_property, "type": "STRING"},
                    "properties": n.properties,
                    "metadata": {}
                }
                for n in self.nodes
            ],
            "relationships": [
                {
                    "type": r.type,
                    "start_node_label": r.start_node_label,
                    "end_node_label": r.end_node_label,
                    "properties": r.properties,
                    "metadata": {}
                }
                for r in self.relationships
            ],
            "metadata": {}
        }

    def to_arrows_format(self) -> Dict[str, Any]:
        """Convert to Arrows.app format for visualization."""
        nodes_list = []
        relationships_list = []

        for i, node in enumerate(self.nodes):
            # Handle both dict properties and string properties
            props = {}
            for p in node.properties:
                if isinstance(p, dict):
                    props[p.get("name", "")] = p.get("type", "STRING")
                else:
                    props[str(p)] = "STRING"
            nodes_list.append({
                "id": f"n{i}",
                "position": {"x": i * 200, "y": (i % 2) * 150},
                "caption": node.label,
                "labels": [node.label],
                "properties": props
            })

        node_id_map = {n.label: f"n{i}" for i, n in enumerate(self.nodes)}

        for i, rel in enumerate(self.relationships):
            if rel.start_node_label in node_id_map and rel.end_node_label in node_id_map:
                relationships_list.append({
                    "id": f"r{i}",
                    "type": rel.type,
                    "fromId": node_id_map[rel.start_node_label],
                    "toId": node_id_map[rel.end_node_label],
                    "properties": {}
                })

        return {
            "graph": {
                "nodes": nodes_list,
                "relationships": relationships_list
            }
        }


class TransitionQuestions:
    """Predefined questions for each level transition."""

    @staticmethod
    def l4_to_l3() -> TransitionQuestion:
        return TransitionQuestion(
            question_type=QuestionType.ENTITIES,
            prompt="What are the main entities you want to see in your Level 3 knowledge graph?",
            description=(
                "Define the core entities that will become nodes in your knowledge graph. "
                "Think about: What are the main 'things' in your data? "
                "What relationships exist between them?"
            ),
            examples=[
                "Indicator, Source, BusinessDomain",
                "Product, Customer, Order, Location",
                "Employee, Department, Project, Skill"
            ],
            default_answer="Indicator, Source"
        )

    @staticmethod
    def l3_to_l2() -> TransitionQuestion:
        return TransitionQuestion(
            question_type=QuestionType.DOMAINS,
            prompt="What domains do you want to categorize your data by?",
            description=(
                "Define semantic categories/domains to filter your knowledge graph. "
                "These will be used for keyword matching AND semantic similarity. "
                "Each domain becomes a separate Level 2 table."
            ),
            examples=[
                "Revenue, Volume, ETP",
                "Sales, Marketing, Operations",
                "Finance, HR, IT"
            ],
            default_answer="Revenue, Volume, ETP"
        )

    @staticmethod
    def l2_to_l1() -> TransitionQuestion:
        return TransitionQuestion(
            question_type=QuestionType.FEATURES,
            prompt="What feature/column do you want to extract as a vector?",
            description=(
                "Select a single column to extract from the table. "
                "This reduces the data to a single variable/series."
            ),
            examples=["name", "indicator_name", "value"],
            default_answer="name"
        )

    @staticmethod
    def l1_to_l0() -> TransitionQuestion:
        return TransitionQuestion(
            question_type=QuestionType.AGGREGATION,
            prompt="What aggregation metric do you want to compute?",
            description=(
                "Choose how to reduce the vector to a single atomic value. "
                "This becomes the 'ground truth' for the audit."
            ),
            examples=["count", "sum", "mean", "min", "max"],
            default_answer="count"
        )

    @staticmethod
    def l0_to_l1_ascent() -> TransitionQuestion:
        return TransitionQuestion(
            question_type=QuestionType.DIMENSIONS,
            prompt="What structural features do you want to extract from each item?",
            description=(
                "Define how to reconstruct a vector from the atomic metric. "
                "Typically involves extracting naming patterns or structural features."
            ),
            examples=[
                "first_word, num_parts, num_capitals",
                "prefix, suffix, length",
                "category, subcategory"
            ],
            default_answer="first_word, num_parts, num_capitals"
        )


class DataModelGenerator:
    """Generates Neo4j data models from user answers or LLM."""

    OLLAMA_URL = "http://localhost:11434/api/generate"
    OPENAI_URL = "https://api.openai.com/v1/chat/completions"

    @staticmethod
    def generate_from_llm(
        user_query: str,
        source_data: Dict[str, pd.DataFrame] = None,
        llm_provider: str = "ollama",  # "ollama" or "openai"
        model: str = None,  # Model name
        api_key: str = None,  # Required for OpenAI
        verbose: bool = False
    ) -> Neo4jDataModel:
        """
        Generate a Neo4j data model using LLM based on user description.

        Args:
            user_query: Natural language description of desired data model
            source_data: Optional CSV data to provide context
            llm_provider: "ollama" or "openai"
            model: Model name (default: smollm2 for Ollama, gpt-4o-mini for OpenAI)
            api_key: API key for OpenAI
            verbose: Print debug information

        Returns:
            Neo4jDataModel with nodes and relationships
        """
        import requests
        import re

        # Default models
        if model is None:
            model = "hf.co/HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF:Q4_K_M" if llm_provider == "ollama" else "gpt-4o-mini"

        # Build context from source data
        data_context = ""
        if source_data:
            data_context = "\n\nAvailable CSV data:\n"
            for filename, df in source_data.items():
                data_context += f"\n{filename}:\n"
                data_context += f"  Columns: {list(df.columns)}\n"
                data_context += f"  Sample rows: {df.head(3).to_dict('records')}\n"

        # System prompt for data model generation
        system_prompt = """You are a Neo4j data modeling expert. Generate a graph data model based on the user's description.

Return your response in EXACTLY this JSON format (no markdown, no explanation, ONLY valid JSON):
{
  "nodes": [
    {
      "label": "EntityName",
      "key_property": "entity_id",
      "properties": [{"name": "prop_name", "type": "STRING"}],
      "description": "Description of this entity"
    }
  ],
  "relationships": [
    {
      "type": "RELATIONSHIP_TYPE",
      "start_node_label": "StartEntity",
      "end_node_label": "EndEntity"
    }
  ]
}

Rules:
- Node labels should be PascalCase (e.g., Customer, Product)
- Relationship types should be SCREAMING_SNAKE_CASE (e.g., HAS_ORDER, BELONGS_TO)
- Each node must have a key_property ending in _id
- Include relevant properties based on the data context
- Create meaningful relationships between entities"""

        full_prompt = f"{system_prompt}\n{data_context}\n\nUser request: {user_query}\n\nJSON response:"

        if verbose:
            print(f"[LLM DataModel] Provider: {llm_provider}, Model: {model}")
            print(f"[LLM DataModel] Prompt length: {len(full_prompt)} chars")

        try:
            if llm_provider == "ollama":
                response = requests.post(
                    DataModelGenerator.OLLAMA_URL,
                    json={
                        "model": model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {"temperature": 0.1, "num_predict": 1500}
                    },
                    timeout=300  # Increased timeout for larger models
                )
                response.raise_for_status()
                llm_response = response.json().get("response", "")

            elif llm_provider == "openai":
                if not api_key:
                    raise ValueError("OpenAI API key required")

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                response = requests.post(
                    DataModelGenerator.OPENAI_URL,
                    headers=headers,
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"{data_context}\n\nUser request: {user_query}"}
                        ],
                        "temperature": 0.1,
                        "max_tokens": 1500
                    },
                    timeout=60
                )
                response.raise_for_status()
                llm_response = response.json()["choices"][0]["message"]["content"]
            else:
                raise ValueError(f"Unknown LLM provider: {llm_provider}")

            if verbose:
                print(f"[LLM DataModel] Response: {llm_response[:500]}...")

            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', llm_response)
            if not json_match:
                raise ValueError("No JSON found in LLM response")

            data_model_dict = json.loads(json_match.group())

            # Convert to Neo4jDataModel
            nodes = []
            for node_dict in data_model_dict.get("nodes", []):
                nodes.append(DataModelNode(
                    label=node_dict["label"],
                    key_property=node_dict["key_property"],
                    properties=node_dict.get("properties", [{"name": "name", "type": "STRING"}]),
                    description=node_dict.get("description")
                ))

            relationships = []
            for rel_dict in data_model_dict.get("relationships", []):
                relationships.append(DataModelRelationship(
                    type=rel_dict["type"],
                    start_node_label=rel_dict["start_node_label"],
                    end_node_label=rel_dict["end_node_label"],
                    properties=rel_dict.get("properties", [])
                ))

            return Neo4jDataModel(nodes=nodes, relationships=relationships)

        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Cannot connect to {llm_provider}. Make sure it's running.")
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            raise RuntimeError(f"LLM data model generation failed: {e}")

    @staticmethod
    def generate_from_entities(
        entities: List[str],
        core_entity: str = None,
        source_data: Dict[str, pd.DataFrame] = None
    ) -> Neo4jDataModel:
        """
        Generate a Neo4j data model from user-specified entities.

        Args:
            entities: List of entity names (e.g., ["Indicator", "Source", "Domain"])
            core_entity: The central entity (defaults to first entity)
            source_data: Optional raw data to infer properties from

        Returns:
            Neo4jDataModel with nodes and relationships
        """
        if not entities:
            raise ValueError("At least one entity is required")

        core_entity = core_entity or entities[0]
        nodes = []
        relationships = []

        # Create nodes
        for entity in entities:
            label = entity.strip().replace(" ", "")
            # Use PascalCase for labels
            label = ''.join(word.capitalize() for word in label.split('_'))

            key_prop = f"{label.lower()}_id"
            properties = [{"name": "name", "type": "STRING"}]

            # Infer additional properties from source data if available
            if source_data and entity.lower() in [e.lower() for e in entities[:1]]:
                for df in source_data.values():
                    for col in df.columns[:3]:  # Limit to first 3 columns
                        prop_name = col.lower().replace(" ", "_")
                        if prop_name not in [key_prop, "name"]:
                            properties.append({"name": prop_name, "type": "STRING"})
                    break

            nodes.append(DataModelNode(
                label=label,
                key_property=key_prop,
                properties=properties,
                description=f"{label} entity in the knowledge graph"
            ))

        # Create relationships (star schema with core entity at center)
        core_label = ''.join(word.capitalize() for word in core_entity.strip().replace(" ", "").split('_'))

        for node in nodes:
            if node.label != core_label:
                rel_type = f"HAS_{node.label.upper()}"
                relationships.append(DataModelRelationship(
                    type=rel_type,
                    start_node_label=core_label,
                    end_node_label=node.label
                ))

        return Neo4jDataModel(nodes=nodes, relationships=relationships)

    @staticmethod
    def generate_ingest_queries(data_model: Neo4jDataModel) -> Dict[str, str]:
        """Generate Cypher queries to ingest data into Neo4j."""
        queries = {}

        for node in data_model.nodes:
            props = ", ".join([f"{p['name']}: record.{p['name']}" for p in node.properties])
            key = node.key_property

            query = f"""
UNWIND $records AS record
MERGE (n:{node.label} {{{key}: record.{key}}})
SET n += {{{props}}}
RETURN count(n) as created
"""
            queries[f"create_{node.label.lower()}"] = query.strip()

        for rel in data_model.relationships:
            query = f"""
UNWIND $records AS record
MATCH (source:{rel.start_node_label} {{{data_model.nodes[0].key_property}: record.sourceId}})
MATCH (target:{rel.end_node_label} {{{data_model.nodes[0].key_property}: record.targetId}})
MERGE (source)-[r:{rel.type}]->(target)
RETURN count(r) as created
"""
            queries[f"create_{rel.type.lower()}"] = query.strip()

        return queries


class SemanticMatcher:
    """
    Handles semantic similarity matching for L3->L2 domain categorization.
    Uses keyword matching + sentence embeddings via the configured embeddings API.
    """

    def __init__(self, use_embeddings: bool = True):
        """
        Initialize the semantic matcher.

        Args:
            use_embeddings: Whether to use HF Inference API for semantic similarity.
                           Set to False to use only keyword matching.
        """
        self.use_embeddings = use_embeddings

    def categorize_by_domains(
        self,
        items: List[str],
        domains: List[str],
        similarity_threshold: float = 0.3
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Categorize items into domains using keyword + semantic matching.

        Optimized: Uses batch API call for semantic matching instead of per-item calls.

        Args:
            items: List of item names/texts to categorize
            domains: List of domain names (e.g., ["Revenue", "Volume", "ETP"])
            similarity_threshold: Minimum similarity score to assign to domain

        Returns:
            Dict mapping domain -> list of (item, score) tuples
        """
        results = {domain: [] for domain in domains}
        unmatched_items = []  # Collect items needing semantic matching

        # Pass 1: Fast keyword matching (no API calls)
        for item in items:
            item_lower = item.lower()
            matched = False

            for domain in domains:
                keywords = self._get_domain_keywords(domain)

                for keyword in keywords:
                    if keyword in item_lower:
                        results[domain].append((item, 1.0))  # Perfect match
                        matched = True
                        break

                if matched:
                    break

            # Collect unmatched items for batch processing
            if not matched:
                unmatched_items.append(item)

        # Pass 2: Batch semantic matching (single API call for ALL unmatched items)
        if unmatched_items and self.use_embeddings:
            print(f"[Categorization] Batch semantic matching for {len(unmatched_items)} items...", flush=True)

            try:
                from intuitiveness.models import get_batch_similarities

                # Single API call for all unmatched items vs all domains
                similarity_matrix = get_batch_similarities(unmatched_items, domains)

                if similarity_matrix is not None:
                    # Process results from the similarity matrix
                    for i, item in enumerate(unmatched_items):
                        best_idx = int(np.argmax(similarity_matrix[i]))
                        best_score = float(similarity_matrix[i][best_idx])

                        if best_score >= similarity_threshold:
                            best_domain = domains[best_idx]
                            results[best_domain].append((item, best_score))

                    print(f"[Categorization] Batch matching complete.", flush=True)
                else:
                    print(f"[Categorization] Warning: Batch API call failed, items uncategorized.", flush=True)

            except Exception as e:
                print(f"[Categorization] Error in batch matching: {e}", flush=True)

        return results

    def _get_domain_keywords(self, domain: str) -> List[str]:
        """Get keywords associated with a domain."""
        domain_lower = domain.lower()

        # Predefined keyword mappings
        keyword_map = {
            "revenue": ["revenue", "ca", "chiffre", "income", "sales", "recette"],
            "volume": ["volume", "vol", "quantity", "qty", "tonnage", "colis"],
            "etp": ["etp", "fte", "employee", "effectif", "staff", "personnel"],
            "cost": ["cost", "cout", "expense", "charge", "depense"],
            "margin": ["margin", "marge", "profit", "benefice"],
            "quality": ["quality", "qualite", "satisfaction", "nps"],
            "delivery": ["delivery", "livraison", "expedition", "shipping"],
            "customer": ["customer", "client", "account", "compte"]
        }

        return keyword_map.get(domain_lower, [domain_lower])

    def _compute_semantic_scores(
        self,
        item: str,
        domains: List[str]
    ) -> Dict[str, float]:
        """Compute semantic similarity scores between item and each domain.

        Uses the configured embeddings API (intuitiveness.models) for
        multilingual support (French, etc).
        """
        try:
            from intuitiveness.models import get_sentence_similarity

            # Compare the item against all domains in one embeddings API call
            similarity_scores = get_sentence_similarity(item, domains)

            if similarity_scores is None:
                return {}

            # Build dict mapping domain -> similarity score
            scores = {}
            for i, domain in enumerate(domains):
                scores[domain] = float(similarity_scores[i])

            return scores
        except Exception:
            return {}


class InteractiveRedesigner:
    """
    Orchestrates the interactive question-answer workflow for the descent-ascent cycle.
    """

    def __init__(self, verbose: bool = True):
        """
        Initialize the interactive redesigner.

        Args:
            verbose: Whether to print progress messages
        """
        self.verbose = verbose
        self.answers: Dict[str, UserAnswer] = {}
        self.data_model: Optional[Neo4jDataModel] = None
        self.semantic_matcher = SemanticMatcher(use_embeddings=True)

    def _log(self, message: str):
        """Print a message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def ask_question(self, question: TransitionQuestion) -> UserAnswer:
        """
        Display a question and collect user input.

        In a Jupyter notebook, this will be interactive.
        For testing, you can override this method or use set_answer().
        """
        print("\n" + "=" * 60)
        print(f"QUESTION: {question.prompt}")
        print("=" * 60)
        print(f"\n{question.description}\n")
        print("Examples:")
        for ex in question.examples:
            print(f"  - {ex}")
        print(f"\nDefault: {question.default_answer}")
        print()

        # In a notebook, this would be input()
        # For now, we'll use the default or a pre-set answer
        if question.question_type.value in self.answers:
            return self.answers[question.question_type.value]

        user_input = input("Your answer (press Enter for default): ").strip()
        if not user_input:
            user_input = question.default_answer

        values = [v.strip() for v in user_input.split(",")]
        answer = UserAnswer(question_type=question.question_type, values=values)
        self.answers[question.question_type.value] = answer
        return answer

    def set_answer(self, question_type: QuestionType, values: List[str]):
        """Pre-set an answer for testing or non-interactive use."""
        self.answers[question_type.value] = UserAnswer(
            question_type=question_type,
            values=values
        )

    def transition_l4_to_l3(
        self,
        l4_dataset: Level4Dataset,
        answer: Optional[UserAnswer] = None
    ) -> Tuple[Level3Dataset, Neo4jDataModel]:
        """
        Execute L4 -> L3 transition with question-answer workflow.

        1. Ask user for entities
        2. Generate Neo4j data model
        3. Build knowledge graph from raw data

        Returns:
            Tuple of (Level3Dataset, Neo4jDataModel)
        """
        self._log("\n--- L4 -> L3 TRANSITION ---")

        # Step 1: Get user's entity choices
        if answer is None:
            question = TransitionQuestions.l4_to_l3()
            answer = self.ask_question(question)

        entities = answer.values
        self._log(f"Entities chosen: {entities}")

        # Step 2: Generate Neo4j data model
        self.data_model = DataModelGenerator.generate_from_entities(
            entities=entities,
            core_entity=entities[0] if entities else "Indicator",
            source_data=l4_dataset.get_data()
        )

        self._log(f"Generated data model with {len(self.data_model.nodes)} nodes, "
                  f"{len(self.data_model.relationships)} relationships")

        # Step 3: Build knowledge graph
        graph = self._build_graph_from_model(l4_dataset.get_data(), self.data_model)

        self._log(f"Built graph with {graph.number_of_nodes()} nodes, "
                  f"{graph.number_of_edges()} edges")

        return Level3Dataset(graph), self.data_model

    def _build_graph_from_model(
        self,
        source_data: Dict[str, pd.DataFrame],
        data_model: Neo4jDataModel
    ) -> nx.Graph:
        """Build a NetworkX graph based on the data model and source data."""
        G = nx.Graph()

        core_label = data_model.nodes[0].label

        # Add nodes from each source file
        for filename, df in source_data.items():
            # Add source node
            source_id = f"source_{filename}"
            G.add_node(source_id, type="Source", name=filename)

            # Find the best column for entity names
            name_col = None
            for col in df.columns:
                if df[col].dtype == 'object':
                    name_col = col
                    break

            if name_col:
                for idx, row in df.iterrows():
                    entity_name = str(row.get(name_col, 'Unknown'))
                    if entity_name == 'nan' or pd.isna(entity_name):
                        continue

                    entity_id = f"{filename}_{idx}"

                    # Add entity node with properties
                    node_attrs = {
                        "type": core_label,
                        "name": entity_name,
                        "source_file": filename
                    }

                    # Add additional properties from the row
                    for col in df.columns[:5]:  # Limit properties
                        if col != name_col:
                            node_attrs[col.lower().replace(" ", "_")] = str(row.get(col, ""))

                    G.add_node(entity_id, **node_attrs)
                    G.add_edge(entity_id, source_id, relation="FOUND_IN")

        return G

    def transition_l3_to_l2(
        self,
        l3_dataset: Level3Dataset,
        answer: Optional[UserAnswer] = None,
        use_semantic: bool = True
    ) -> Dict[str, Level2Dataset]:
        """
        Execute L3 -> L2 transition with question-answer workflow.

        1. Ask user for domain categories
        2. Apply keyword + semantic matching to categorize nodes
        3. Return a Level2Dataset for each domain

        Returns:
            Dict mapping domain name -> Level2Dataset
        """
        self._log("\n--- L3 -> L2 TRANSITION ---")

        # Step 1: Get user's domain choices
        if answer is None:
            question = TransitionQuestions.l3_to_l2()
            answer = self.ask_question(question)

        domains = answer.values
        self._log(f"Domains chosen: {domains}")

        # Step 2: Extract items from graph
        graph = l3_dataset.get_data()
        items = []
        item_data = []

        for node, attrs in graph.nodes(data=True):
            if attrs.get("type") not in ["Source"]:
                name = attrs.get("name", str(node))
                items.append(name)
                item_data.append({"id": node, "name": name, **attrs})

        self._log(f"Found {len(items)} items to categorize")

        # Step 3: Categorize by domains
        self.semantic_matcher.use_embeddings = use_semantic
        categorized = self.semantic_matcher.categorize_by_domains(items, domains)

        # Step 4: Create Level2 datasets
        results = {}
        for domain, matches in categorized.items():
            matched_ids = {item for item, score in matches}
            domain_data = [d for d in item_data if d.get("name") in matched_ids]

            if domain_data:
                df = pd.DataFrame(domain_data)
                results[domain] = Level2Dataset(df, name=f"{domain}_indicators")
                self._log(f"  {domain}: {len(domain_data)} items")
            else:
                results[domain] = Level2Dataset(pd.DataFrame(), name=f"{domain}_indicators")
                self._log(f"  {domain}: 0 items")

        return results

    def transition_l2_to_l1(
        self,
        l2_dataset: Level2Dataset,
        answer: Optional[UserAnswer] = None
    ) -> Level1Dataset:
        """Execute L2 -> L1 transition."""
        self._log("\n--- L2 -> L1 TRANSITION ---")

        if answer is None:
            question = TransitionQuestions.l2_to_l1()
            answer = self.ask_question(question)

        column = answer.values[0] if answer.values else "name"
        df = l2_dataset.get_data()

        if column not in df.columns:
            available = ", ".join(df.columns[:10])
            raise ValueError(f"Column '{column}' not found. Available: {available}")

        series = df[column]
        self._log(f"Extracted column '{column}' with {len(series)} values")

        return Level1Dataset(series, name=column)

    def transition_l1_to_l0(
        self,
        l1_dataset: Level1Dataset,
        answer: Optional[UserAnswer] = None
    ) -> Level0Dataset:
        """Execute L1 -> L0 transition."""
        self._log("\n--- L1 -> L0 TRANSITION ---")

        if answer is None:
            question = TransitionQuestions.l1_to_l0()
            answer = self.ask_question(question)

        aggregation = answer.values[0] if answer.values else "count"
        series = l1_dataset.get_data()

        if aggregation == "count":
            value = series.count()
        elif aggregation == "sum":
            value = series.sum()
        elif aggregation == "mean":
            value = series.mean()
        elif aggregation == "min":
            value = series.min()
        elif aggregation == "max":
            value = series.max()
        else:
            raise ValueError(f"Unknown aggregation: {aggregation}")

        self._log(f"Computed {aggregation}: {value}")

        return Level0Dataset(value, description=f"{aggregation} of {l1_dataset.name}")

    def full_descent(
        self,
        l4_dataset: Level4Dataset,
        entities: List[str] = None,
        domains: List[str] = None,
        feature_column: str = None,
        aggregation: str = None
    ) -> Dict[str, Any]:
        """
        Execute full descent from L4 to L0.

        Args:
            l4_dataset: Starting Level 4 dataset
            entities: Pre-set entity choices for L4->L3
            domains: Pre-set domain choices for L3->L2
            feature_column: Pre-set column for L2->L1
            aggregation: Pre-set aggregation for L1->L0

        Returns:
            Dict with all intermediate datasets and the data model
        """
        results = {"l4": l4_dataset}

        # Pre-set answers if provided
        if entities:
            self.set_answer(QuestionType.ENTITIES, entities)
        if domains:
            self.set_answer(QuestionType.DOMAINS, domains)
        if feature_column:
            self.set_answer(QuestionType.FEATURES, [feature_column])
        if aggregation:
            self.set_answer(QuestionType.AGGREGATION, [aggregation])

        # L4 -> L3
        l3_dataset, data_model = self.transition_l4_to_l3(l4_dataset)
        results["l3"] = l3_dataset
        results["data_model"] = data_model

        # L3 -> L2 (multiple domains)
        l2_datasets = self.transition_l3_to_l2(l3_dataset)
        results["l2"] = l2_datasets

        # L2 -> L1 (for first non-empty domain)
        l1_results = {}
        l0_results = {}

        for domain, l2_ds in l2_datasets.items():
            if not l2_ds.get_data().empty:
                l1_ds = self.transition_l2_to_l1(l2_ds)
                l1_results[domain] = l1_ds

                l0_ds = self.transition_l1_to_l0(l1_ds)
                l0_results[domain] = l0_ds

        results["l1"] = l1_results
        results["l0"] = l0_results

        return results

    def get_data_model_json(self) -> Optional[Dict[str, Any]]:
        """Get the generated data model as JSON for Neo4j MCP."""
        if self.data_model:
            return self.data_model.to_json()
        return None

    def get_arrows_export(self) -> Optional[Dict[str, Any]]:
        """Get the data model in Arrows.app format for visualization."""
        if self.data_model:
            return self.data_model.to_arrows_format()
        return None


# Convenience function for quick use
def run_interactive_descent(
    raw_data_sources: Dict[str, pd.DataFrame],
    entities: List[str] = None,
    domains: List[str] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Run the full interactive descent workflow.

    Args:
        raw_data_sources: Dict of filename -> DataFrame
        entities: Optional pre-set entities for L4->L3
        domains: Optional pre-set domains for L3->L2
        verbose: Print progress messages

    Returns:
        Dict with all results including data model
    """
    l4 = Level4Dataset(raw_data_sources)
    redesigner = InteractiveRedesigner(verbose=verbose)
    return redesigner.full_descent(l4, entities=entities, domains=domains)
