"""
SessionGraph: NetworkX DiGraph-based session persistence.

Replaces browser localStorage (5MB limit) with file-based graph storage
to enable mode switching for ascent phase. Stores full data artifacts
for future ML training on descent/ascent patterns.

Graph Model:
    Nodes = Level States (L0-L4 with FULL data artifacts)
        - id: UUID
        - level: int (0-4)
        - data_artifact: serialized DataFrame/value
        - output_value: Any (L0 datum, L1 vector, L2 table summary, L3 graph)
        - row_count: int
        - column_names: List[str]
        - timestamp: ISO string
        - decision_description: str

    Edges = Transformations (descent/ascent operations)
        - action: "descend" | "ascend"
        - from_level: int
        - to_level: int
        - parameters: dict
        - decision_description: str
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import networkx as nx
import pandas as pd

from .serializers import (
    serialize_dataframe,
    deserialize_dataframe,
    serialize_value,
    deserialize_value,
)


class SessionGraph:
    """
    NetworkX DiGraph for session state persistence.

    Constitution Compliance:
        - No orphan nodes (all states connected by transitions)
        - Core entity centered (root L4 is center)
        - End-to-end interpretability (edge metadata tracks decisions)
    """

    def __init__(self):
        """Initialize empty session graph."""
        self.G = nx.DiGraph()
        self.root_id: Optional[str] = None
        self.current_id: Optional[str] = None

    def add_level_state(
        self,
        level: int,
        output_value: Any,
        data_artifact: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add a level state node to the graph.

        Args:
            level: Complexity level (0-4)
            output_value: The computed value at this level
                - L0: single datum (e.g., 88.16)
                - L1: vector of values
                - L2: categorized summary
                - L3: linked table info
                - L4: file metadata
            data_artifact: Full data for ML training
                - DataFrame for L1-L4
                - scalar/dict for L0
            metadata: Additional info (decision_description, column_names, etc.)

        Returns:
            Node ID (UUID string)
        """
        node_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        # Serialize data artifact based on type
        if isinstance(data_artifact, pd.DataFrame):
            serialized_artifact = serialize_dataframe(data_artifact)
            row_count = len(data_artifact)
            column_names = list(data_artifact.columns)
        elif isinstance(data_artifact, pd.Series):
            # Convert Series to DataFrame for consistent serialization
            serialized_artifact = serialize_dataframe(data_artifact.to_frame(name=data_artifact.name or 'value'))
            row_count = len(data_artifact)
            column_names = [data_artifact.name or 'value']
        else:
            serialized_artifact = serialize_value(data_artifact)
            row_count = 1 if data_artifact is not None else 0
            column_names = []

        # Build node attributes
        node_attrs = {
            "level": level,
            "output_value": output_value,
            "data_artifact": serialized_artifact,
            "row_count": row_count,
            "column_names": column_names,
            "timestamp": timestamp,
            "decision_description": (metadata or {}).get("decision_description", ""),
            "metadata": metadata or {},
        }

        self.G.add_node(node_id, **node_attrs)

        # Track root and current
        if self.root_id is None:
            self.root_id = node_id
        self.current_id = node_id

        return node_id

    def add_transition(
        self,
        from_id: str,
        to_id: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a transition edge between two level states.

        Args:
            from_id: Source node ID
            to_id: Target node ID
            action: "descend" or "ascend"
            params: Transformation parameters (column, aggregation, categories, etc.)
        """
        if from_id not in self.G:
            raise ValueError(f"Source node {from_id} not in graph")
        if to_id not in self.G:
            raise ValueError(f"Target node {to_id} not in graph")

        from_level = self.G.nodes[from_id]["level"]
        to_level = self.G.nodes[to_id]["level"]

        edge_attrs = {
            "action": action,
            "from_level": from_level,
            "to_level": to_level,
            "parameters": params or {},
            "timestamp": datetime.now().isoformat(),
        }

        self.G.add_edge(from_id, to_id, **edge_attrs)

    def export_to_json(self, filepath: str) -> None:
        """
        Export session graph to JSON file.

        Uses nx.node_link_data() for portable serialization.

        Args:
            filepath: Path to output JSON file
        """
        graph_data = nx.node_link_data(self.G)

        # Add session metadata
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "root_id": self.root_id,
            "current_id": self.current_id,
            "graph": graph_data,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, default=str)

    @classmethod
    def load_from_json(cls, filepath: str) -> "SessionGraph":
        """
        Load session graph from JSON file.

        Args:
            filepath: Path to input JSON file

        Returns:
            Reconstructed SessionGraph instance
        """
        with open(filepath, "r", encoding="utf-8") as f:
            export_data = json.load(f)

        session = cls()
        session.G = nx.node_link_graph(export_data["graph"])
        session.root_id = export_data.get("root_id")
        session.current_id = export_data.get("current_id")

        return session

    def get_path_to_current(self) -> List[str]:
        """
        Get the path from root to current node.

        Returns:
            List of node IDs from root to current
        """
        if self.root_id is None or self.current_id is None:
            return []

        try:
            path = nx.shortest_path(self.G, self.root_id, self.current_id)
            return path
        except nx.NetworkXNoPath:
            return [self.current_id]

    def get_level_output(self, level: int) -> Optional[Any]:
        """
        Get the output value for a specific level.

        Searches the path to current for the most recent node at the given level.

        Args:
            level: Complexity level (0-4)

        Returns:
            Output value at that level, or None if not found
        """
        path = self.get_path_to_current()

        # Search backwards for the level
        for node_id in reversed(path):
            node_attrs = self.G.nodes[node_id]
            if node_attrs["level"] == level:
                return node_attrs["output_value"]

        return None

    def get_level_data(self, level: int) -> Optional[pd.DataFrame]:
        """
        Get the full data artifact for a specific level.

        Args:
            level: Complexity level (0-4)

        Returns:
            DataFrame at that level, or None if not found/not a DataFrame
        """
        path = self.get_path_to_current()

        # Search backwards for the level
        for node_id in reversed(path):
            node_attrs = self.G.nodes[node_id]
            if node_attrs["level"] == level:
                serialized = node_attrs.get("data_artifact")
                if serialized:
                    try:
                        return deserialize_dataframe(serialized)
                    except (ValueError, TypeError):
                        # Not a DataFrame, try as value
                        return deserialize_value(serialized)

        return None

    def get_all_decisions(self) -> List[Dict[str, Any]]:
        """
        Get all decisions made along the path to current.

        Returns:
            List of dicts with level, action, decision_description, timestamp
        """
        path = self.get_path_to_current()
        decisions = []

        for i, node_id in enumerate(path):
            node_attrs = self.G.nodes[node_id]
            decision = {
                "step": i,
                "level": node_attrs["level"],
                "decision_description": node_attrs.get("decision_description", ""),
                "row_count": node_attrs.get("row_count", 0),
                "timestamp": node_attrs.get("timestamp", ""),
            }

            # Add transition info if not root
            if i > 0:
                prev_id = path[i - 1]
                edge_data = self.G.edges.get((prev_id, node_id), {})
                decision["action"] = edge_data.get("action", "unknown")
                decision["parameters"] = edge_data.get("parameters", {})

            decisions.append(decision)

        return decisions

    def __repr__(self) -> str:
        """String representation of session graph."""
        return (
            f"SessionGraph(nodes={self.G.number_of_nodes()}, "
            f"edges={self.G.number_of_edges()}, "
            f"root={self.root_id[:8] if self.root_id else None}, "
            f"current={self.current_id[:8] if self.current_id else None})"
        )
