"""
Navigation Tree Module

Phase 1.2 - Code Simplification (011-code-simplification)
Extracted from navigation.py

Spec Traceability:
------------------
- 002-ascent-functionality: Branching navigation tree (time-travel support)

Contains:
- NavigationTreeNode: Single node in navigation tree
- NavigationTree: Branching tree structure
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from intuitiveness.complexity import Dataset, ComplexityLevel
from intuitiveness.navigation.state import NavigationAction


@dataclass
class NavigationTreeNode:
    """
    A single node in the navigation tree, supporting branching paths.

    Per FR-021, each node records:
    - (a) The navigation step taken (action)
    - (b) Decision made at each step (decision_description)
    - (c) Generated output snapshot (output_snapshot)

    Attributes:
        id: Unique identifier for this node
        level: Complexity level at this node (L0-L4)
        dataset_snapshot: Full dataset at this point (for restoration)
        parent_id: Parent node ID (None for root)
        children_ids: List of child node IDs (branches)
        action: Action that created this node ("entry", "descend", "ascend", "restore")
        timestamp: When this node was created
        metadata: Additional info (enrichment used, dimensions added, etc.)
        decision_description: Human-readable description of decision (FR-021)
        output_snapshot: Summary of output at this step (FR-021)
    """
    id: str
    level: ComplexityLevel
    dataset_snapshot: Dataset
    parent_id: Optional[str]
    children_ids: List[str] = field(default_factory=list)
    action: str = "entry"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    decision_description: str = ""  # FR-021
    output_snapshot: Dict[str, Any] = field(default_factory=dict)  # FR-021
    edge_decision: Dict[str, Any] = field(default_factory=dict)  # spec 015 FR-020: params on incoming edge

    @property
    def depth(self) -> int:
        """Depth in tree (for UI indentation). Root is depth 0."""
        return self.metadata.get('_depth', 0)

    @property
    def dataset(self) -> Dataset:
        """Spec-015 alias: the complete retained dataset (payload + lineage)."""
        return self.dataset_snapshot

    def to_dict(self, include_payload: bool = False) -> Dict[str, Any]:
        """Serialize a node to a JSON-safe dict.

        By default this is the LIGHTWEIGHT view (no data payload) used by the UI
        tree visualization and the JSON-Crack session export — keeping those
        views small and readable.

        Pass ``include_payload=True`` for a FULL-fidelity node record (spec 015
        T037): it additionally encodes the dataset payload (by type) and the
        lineage, so :meth:`from_dict` can rebuild the exact node. The payload is
        encoded with the same serializers as the cross-service export contract.
        """
        base = {
            "id": self.id,
            "level": self.level.value,
            "level_name": self.level.name,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids.copy(),
            "action": self.action,
            "timestamp": self.timestamp.isoformat(),
            "metadata": {k: v for k, v in self.metadata.items() if not k.startswith('_')},
            "decision_description": self.decision_description,
            "output_snapshot": self.output_snapshot,
        }
        if not include_payload:
            return base

        # Full fidelity: encode payload + lineage (lazy import avoids a cycle).
        from intuitiveness.persistence.session_export import _encode_payload
        kind, payload = _encode_payload(self.dataset_snapshot.get_data())
        base["payload_kind"] = kind
        base["payload"] = payload
        base["lineage"] = [ref.to_dict() for ref in self.dataset_snapshot.lineage.operations]
        base["edge_decision"] = dict(self.edge_decision or {})
        return base

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NavigationTreeNode":
        """Rebuild a node from a FULL-fidelity dict (``to_dict(include_payload=True)``).

        Spec 015 T037 — the inverse of the full-fidelity serialization, restoring
        the dataset payload and its lineage.
        """
        from intuitiveness.persistence.session_export import _rebuild_dataset
        from intuitiveness.redesign.lineage import DataLineage, SourceReference

        lineage = DataLineage()
        lineage.operations = [SourceReference.from_dict(r) for r in data.get("lineage", [])]
        ds = _rebuild_dataset(data["level"], data["payload_kind"], data["payload"], lineage)
        return cls(
            id=data["id"],
            level=ComplexityLevel(data["level"]),
            dataset_snapshot=ds,
            parent_id=data.get("parent_id"),
            children_ids=list(data.get("children_ids", [])),
            action=data.get("action", "entry"),
            decision_description=data.get("decision_description", ""),
            output_snapshot=dict(data.get("output_snapshot", {})),
            edge_decision=dict(data.get("edge_decision", {})),
        )


class NavigationTree:
    """
    Branching tree structure tracking all navigation decisions.

    Supports time-travel navigation by preserving multiple exploration branches.
    Replaces linear NavigationHistory for sessions requiring branching.

    Usage:
        >>> tree = NavigationTree(root_dataset)
        >>> tree.branch(NavigationAction.DESCEND, new_dataset, {"step": "entities"})
        >>> tree.restore("node_abc123")  # Time-travel back
    """

    def __init__(self, root_dataset: Dataset):
        """
        Initialize navigation tree with root node.

        Args:
            root_dataset: The L4 dataset at entry point
        """
        self._nodes: Dict[str, NavigationTreeNode] = {}
        self._root_id = str(uuid.uuid4())
        self._current_id = self._root_id

        # Create root node
        root_node = NavigationTreeNode(
            id=self._root_id,
            level=root_dataset.complexity_level,
            dataset_snapshot=root_dataset,
            parent_id=None,
            action=NavigationAction.ENTRY.value,
            metadata={'_depth': 0}
        )
        self._nodes[self._root_id] = root_node

    @property
    def root_id(self) -> str:
        """Get the root node ID."""
        return self._root_id

    @property
    def current_id(self) -> str:
        """Get the current node ID."""
        return self._current_id

    @property
    def current_node(self) -> NavigationTreeNode:
        """Get the current node."""
        return self._nodes[self._current_id]

    @property
    def nodes(self) -> Dict[str, NavigationTreeNode]:
        """Get all nodes."""
        return self._nodes

    def branch(
        self,
        action: NavigationAction,
        dataset: Dataset,
        metadata: Optional[Dict[str, Any]] = None,
        decision_description: str = "",
        output_snapshot: Optional[Dict[str, Any]] = None,
        edge_decision_payload: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new branch from current position.

        Per FR-021, records decision_description and output_snapshot at each node.

        Args:
            action: The navigation action taken (DESCEND, ASCEND, etc.)
            dataset: The dataset at this new position
            metadata: Additional info (enrichment used, dimensions added)
            decision_description: Human-readable description of the decision (FR-021)
            output_snapshot: Summary of output at this step (FR-021)

        Returns:
            ID of the newly created node
        """
        new_id = str(uuid.uuid4())
        parent = self._nodes[self._current_id]
        parent_depth = parent.metadata.get('_depth', 0)

        # Build metadata with depth
        node_metadata = metadata.copy() if metadata else {}
        node_metadata['_depth'] = parent_depth + 1

        # Generate output_snapshot if not provided (FR-021)
        if output_snapshot is None:
            output_snapshot = self._generate_output_snapshot(dataset)

        # Create new node
        new_node = NavigationTreeNode(
            id=new_id,
            level=dataset.complexity_level,
            dataset_snapshot=dataset,
            parent_id=self._current_id,
            action=action.value if isinstance(action, NavigationAction) else action,
            metadata=node_metadata,
            decision_description=decision_description,
            output_snapshot=output_snapshot,
            edge_decision=edge_decision_payload or {}
        )

        # Add to tree
        self._nodes[new_id] = new_node
        parent.children_ids.append(new_id)

        # Move current pointer
        self._current_id = new_id

        return new_id

    def _generate_output_snapshot(self, dataset: Dataset) -> Dict[str, Any]:
        """
        Generate an output snapshot for a dataset (FR-021).

        Spec 015 (T019/R5): each level describes itself via ``summary()`` —
        the former type-switch is replaced by polymorphism. The L0 value is
        coerced to ``str`` for JSON-safe display in the snapshot.

        Args:
            dataset: The dataset to summarize

        Returns:
            Dict with output summary info
        """
        snapshot = dataset.summary()
        if "value" in snapshot:
            snapshot["value"] = str(snapshot["value"])
        return snapshot

    def restore(self, node_id: str) -> Dataset:
        """
        Restore navigation state to a previous node (time-travel).

        Args:
            node_id: ID of the node to restore to

        Returns:
            The dataset at the restored node

        Raises:
            KeyError: If node_id not found in tree
        """
        if node_id not in self._nodes:
            raise KeyError(f"Node '{node_id}' not found in navigation tree")

        self._current_id = node_id
        return self._nodes[node_id].dataset_snapshot

    def get_current_branch_path(self) -> List[NavigationTreeNode]:
        """
        Get path from root to current node.

        Returns:
            List of nodes from root to current position
        """
        path = []
        current = self._current_id

        while current is not None:
            node = self._nodes[current]
            path.insert(0, node)
            current = node.parent_id

        return path

    def get_all_branches(self) -> List[List[NavigationTreeNode]]:
        """
        Get all paths from root to leaf nodes.

        Returns:
            List of paths, where each path is a list of nodes from root to leaf
        """
        branches = []

        def find_leaves(node_id: str, path: List[NavigationTreeNode]):
            node = self._nodes[node_id]
            new_path = path + [node]

            if not node.children_ids:
                branches.append(new_path)
            else:
                for child_id in node.children_ids:
                    find_leaves(child_id, new_path)

        find_leaves(self._root_id, [])
        return branches

    # ------------------------------------------------------------------ #
    # Generator-facing query API (spec 015 FR-021) — consumed by a future
    # synthetic-generation service as well as the UI.
    # ------------------------------------------------------------------ #
    def branches(self) -> List[List[NavigationTreeNode]]:
        """All root→leaf trajectories (alias of get_all_branches)."""
        return self.get_all_branches()

    def nodes_at_level(self, level: ComplexityLevel) -> List[NavigationTreeNode]:
        """Every node produced at a given granularity level this session."""
        return [n for n in self._nodes.values() if n.level == level]

    def siblings(self, node_or_id) -> List[NavigationTreeNode]:
        """Nodes sharing the same parent as the given node (excluding itself)."""
        node = node_or_id if isinstance(node_or_id, NavigationTreeNode) else self._nodes[node_or_id]
        if node.parent_id is None:
            return []
        parent = self._nodes[node.parent_id]
        return [self._nodes[cid] for cid in parent.children_ids if cid != node.id]

    def divergence_point(self, a_id: str, b_id: str) -> NavigationTreeNode:
        """Deepest common ancestor of two nodes — where two trajectories split."""
        def ancestry(nid: str) -> List[str]:
            chain = []
            cur = nid
            while cur is not None:
                chain.append(cur)
                cur = self._nodes[cur].parent_id
            return chain  # leaf → root

        a_chain = ancestry(a_id)
        b_set = set(ancestry(b_id))
        for nid in a_chain:  # first (deepest) shared ancestor
            if nid in b_set:
                return self._nodes[nid]
        raise ValueError("Nodes are not in the same tree (no common ancestor).")

    def export_to_json(self) -> Dict[str, Any]:
        """
        Export full tree for JSON visualization.

        Returns:
            Dict with nodes, root_id, and current_id
        """
        return {
            "nodes": [node.to_dict() for node in self._nodes.values()],
            "root_id": self._root_id,
            "current_id": self._current_id
        }

    def get_node(self, node_id: str) -> NavigationTreeNode:
        """Get a specific node by ID."""
        if node_id not in self._nodes:
            raise KeyError(f"Node '{node_id}' not found")
        return self._nodes[node_id]

    # ------------------------------------------------------------------ #
    # Explicit branch management (spec 015 FR — no automatic eviction)
    # ------------------------------------------------------------------ #
    def _subtree_ids(self, node_id: str) -> List[str]:
        """All node ids in the subtree rooted at node_id (node included)."""
        collected: List[str] = []

        def walk(nid: str) -> None:
            collected.append(nid)
            for child_id in self._nodes[nid].children_ids:
                walk(child_id)

        walk(node_id)
        return collected

    def prune(self, node_id: str) -> int:
        """Permanently remove a node and its entire subtree (explicit only).

        Branches are never auto-evicted; pruning is a deliberate user action.
        The root and any node on the current branch path are protected — pruning
        them would orphan the active position, so time-travel away first.

        Returns the number of nodes removed.
        """
        if node_id not in self._nodes:
            raise KeyError(f"Node '{node_id}' not found in navigation tree")
        if node_id == self._root_id:
            raise ValueError("Cannot prune the root node.")
        on_current_path = {n.id for n in self.get_current_branch_path()}
        if node_id in on_current_path:
            raise ValueError(
                "Cannot prune a node on the current branch (it holds your current "
                "position or an ancestor of it). Time-travel to another branch first."
            )

        to_remove = self._subtree_ids(node_id)
        parent_id = self._nodes[node_id].parent_id
        if parent_id is not None:
            self._nodes[parent_id].children_ids.remove(node_id)
        for nid in to_remove:
            del self._nodes[nid]
        return len(to_remove)

    def archive(self, node_id: str) -> int:
        """Soft-hide a node and its subtree without deleting it (reversible).

        Marks each node in the subtree with ``metadata['_archived'] = True`` so a
        UI can filter it out, while the data and lineage stay intact. The root
        cannot be archived. Returns the number of nodes marked.
        """
        if node_id not in self._nodes:
            raise KeyError(f"Node '{node_id}' not found in navigation tree")
        if node_id == self._root_id:
            raise ValueError("Cannot archive the root node.")

        subtree = self._subtree_ids(node_id)
        for nid in subtree:
            self._nodes[nid].metadata['_archived'] = True
        return len(subtree)

    def __len__(self) -> int:
        """Number of nodes in tree."""
        return len(self._nodes)
