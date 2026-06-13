"""
Navigation Session Module

Phase 1.2 - Code Simplification (011-code-simplification)
Extracted from navigation.py

Spec Traceability:
------------------
- 002-ascent-functionality: US-5 (Navigate Dataset Hierarchy)
- 005-session-persistence: Session save/load/resume

Contains:
- NavigationSession: Stateful exploration of dataset hierarchy
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
import json
import os

from intuitiveness.complexity import (
    Dataset, ComplexityLevel,
    Level0Dataset, Level1Dataset, Level2Dataset, Level3Dataset, Level4Dataset
)
from intuitiveness.redesign.engine import Redesigner as Engine
from intuitiveness.redesign.params import (
    L4toL3Params, L3toL2Params, L2toL1Params, L1toL0Params,
    L0toL1Params, L1toL2Params, L2toL3Params,
)
from intuitiveness.persistence.session_graph import SessionGraph

# Import from package submodules (011-code-simplification)
from intuitiveness.navigation.exceptions import NavigationError, SessionNotFoundError
from intuitiveness.navigation.state import NavigationState, NavigationAction
# NavigationHistory (flat linear log) was removed in spec 015: the session is
# now tree-only (branching + time-travel are always available).
from intuitiveness.navigation.tree import NavigationTree, NavigationTreeNode


class NavigationSession:
    """
    Stateful exploration of dataset hierarchy.

    Implements step-by-step navigation through abstraction levels with
    the L4 entry-only constraint.

    Spec Traceability:
    - 002-ascent-functionality: US-5 (Navigate Dataset Hierarchy)
    - 005-session-persistence: Session save/load/resume

    Usage:
        >>> sources = {"sales": df_sales, "products": df_products}
        >>> l4_dataset = Level4Dataset(sources)
        >>> nav = NavigationSession(l4_dataset)
        >>> nav.descend(linking_function=my_link_func)  # L4→L3
        >>> nav.descend(entity_type="sale")  # L3→L2
        >>> nav.get_available_moves()
        {'descend': [...], 'ascend': [...]}
    """

    # Class-level session storage for resume functionality
    _sessions: Dict[str, 'NavigationSession'] = {}

    def __init__(self, dataset: Dataset):
        """
        Initialize a navigation session.

        The session is always backed by a ``NavigationTree`` (spec 015): every
        transition becomes a tree node, so branching and time-travel are always
        available — there is no separate "linear" mode.

        Args:
            dataset: Must be an L4 (UNLINKABLE) dataset - the entry point.

        Raises:
            NavigationError: If dataset is not L4.
        """
        if not isinstance(dataset, Level4Dataset):
            raise NavigationError(
                f"Navigation must begin at L4 (UNLINKABLE). "
                f"Got: {dataset.complexity_level.name}. "
                f"Wrap your data with Level4Dataset first."
            )

        self._session_id = str(uuid.uuid4())
        self._state = NavigationState.ENTRY
        self._initial_dataset = dataset
        self._current_dataset = dataset

        # FR-019: Track accumulated outputs from all levels visited
        self._accumulated_outputs: Dict[int, Any] = {}  # level -> dataset
        self._accumulated_outputs[4] = dataset  # Entry at L4

        # FR-020: Store raw data columns for entity selection at L2→L3
        self._raw_data_columns: List[str] = []
        if isinstance(dataset.get_data(), dict):
            for source_name, source_data in dataset.get_data().items():
                if hasattr(source_data, 'columns'):
                    self._raw_data_columns.extend(list(source_data.columns))
            self._raw_data_columns = list(set(self._raw_data_columns))

        # Tree-backed navigation (the only mode).
        self._tree = NavigationTree(dataset)
        self._current_node_id = self._tree.root_id

        # Store for resume
        NavigationSession._sessions[self._session_id] = self

    @property
    def session_id(self) -> str:
        """Unique session identifier."""
        return self._session_id

    @property
    def state(self) -> NavigationState:
        """Current navigation state."""
        return self._state

    @property
    def current_level(self) -> ComplexityLevel:
        """Current abstraction level."""
        return self._current_dataset.complexity_level

    @property
    def current_node(self) -> Any:
        """Current data at this position."""
        return self._current_dataset.get_data()

    @property
    def current_dataset(self) -> Dataset:
        """Current dataset wrapper."""
        return self._current_dataset

    # -------------------------------------------------------------------------
    # descend() - Move down one level
    # -------------------------------------------------------------------------

    def _descent_params(self, current_level, target_level, params):
        """Adapt UI kwargs into a typed descent params object (spec 015).

        For graph edges (L4→L3, L3→L2) the UI passes callables; we invoke them
        on the current payload — exactly as the legacy Redesigner did — and hand
        the resulting payload to the engine as a prebuilt value, so behavior is
        preserved while the engine remains the sole typed constructor.
        """
        edge = (current_level.value, target_level.value)
        data = self._current_dataset.get_data()
        if edge == (4, 3):
            builder = params.get("builder_func") or params.get("linking_function")
            if builder is None:
                raise NavigationError("L4→L3 requires a builder_func/linking_function.")
            return L4toL3Params(prebuilt_graph=builder(data), model=params.get("model"))
        if edge == (3, 2):
            query = params.get("query_func")
            if query is not None:
                return L3toL2Params(prebuilt_table=query(data), domains=params.get("domains", []))
            return L3toL2Params(domains=params.get("domains", []))
        if edge == (2, 1):
            return L2toL1Params(
                column=params.get("column"),
                filter_query=params.get("filter_query"),
                prebuilt_series=params.get("prebuilt_series"),
            )
        if edge == (1, 0):
            return L1toL0Params(
                aggregation=params.get("aggregation", "sum"),
                prebuilt_value=params.get("prebuilt_value"),
            )
        raise NavigationError(f"Unsupported descent edge {current_level.name}→{target_level.name}.")

    def _ascent_params(self, current_level, target_level, params):
        """Adapt UI kwargs into a typed ascent params object (spec 015).

        The legacy kwarg names (``enrichment_func``, ``dimensions``,
        ``relationships``) map onto the typed params; the engine then runs the
        same enrichment/dimension transforms, so behavior is preserved.
        """
        edge = (current_level.value, target_level.value)
        if edge == (0, 1):
            return L0toL1Params(enrichment_function=params.get("enrichment_func"))
        if edge == (1, 2):
            return L1toL2Params(
                dimensions=params.get("dimensions", []),
                prebuilt_dataframe=params.get("prebuilt_dataframe"),
            )
        if edge == (2, 3):
            return L2toL3Params(
                dimensions=params.get("dimensions", []),
                relationships=params.get("relationships", []),
                source_column=params.get("source_column"),
            )
        raise NavigationError(f"Unsupported ascent edge {current_level.name}→{target_level.name}.")

    def descend(self, **params) -> 'NavigationSession':
        """
        Move down one level.

        Parameters depend on the current level:
        - L4→L3: requires `linking_function` or `builder_func`
        - L3→L2: requires `query_func` or `entity_type`
        - L2→L1: requires `column`, optional `filter_query`

        Returns:
            Self for method chaining.

        Raises:
            NavigationError: If at L0 (cannot descend further) or session exited.
        """
        if self._state == NavigationState.EXITED:
            raise NavigationError("Session has exited. Use resume() to continue.")

        current_level = self.current_level

        if current_level == ComplexityLevel.LEVEL_0:
            raise NavigationError(
                "Cannot descend from L0 (DATUM). "
                "L0 is the ground truth - you've reached maximum simplicity."
            )

        # Determine target level
        target_level = ComplexityLevel(current_level.value - 1)

        # Spec 015 cutover: route descent through the unified Engine. The
        # session adapts the UI's callable/kwarg inputs into typed params,
        # invoking builder_func/query_func exactly as legacy did (so the
        # produced payload — and thus behavior — is identical), then the engine
        # wraps it + stamps lineage. See IMPLEMENTATION_NOTES Deviation 2.
        try:
            typed = self._descent_params(current_level, target_level, params)
            new_dataset = Engine.reduce_complexity(
                self._current_dataset, target_level, typed
            )
        except NavigationError:
            raise
        except Exception as e:
            raise NavigationError(f"Descent failed: {str(e)}")

        # Update state
        self._current_dataset = new_dataset
        self._state = NavigationState.EXPLORING

        # FR-019: Track accumulated output at this level
        self._accumulated_outputs[target_level.value] = new_dataset

        # Generate node_id based on operation
        node_id = self._generate_node_id("descend", params)
        self._current_node_id = node_id

        # FR-021: Generate decision_description
        decision_description = self._generate_decision_description("descend", current_level, target_level, params)

        # Record step as a tree node.
        metadata = {"params": {k: str(v) for k, v in params.items()}}
        self._current_node_id = self._tree.branch(
            NavigationAction.DESCEND,
            new_dataset,
            metadata,
            decision_description=decision_description  # FR-021
        )

        return self

    # -------------------------------------------------------------------------
    # ascend() - Move up one level
    # -------------------------------------------------------------------------

    def ascend(self, **params) -> 'NavigationSession':
        """
        Move up one level.

        Returns:
            Self for method chaining.

        Raises:
            NavigationError: If at L3 (cannot return to L4) or at L4 or session exited.
        """
        if self._state == NavigationState.EXITED:
            raise NavigationError("Session has exited. Use resume() to continue.")

        current_level = self.current_level

        if current_level == ComplexityLevel.LEVEL_4:
            raise NavigationError(
                "Already at L4 (UNLINKABLE). Cannot ascend further."
            )

        if current_level == ComplexityLevel.LEVEL_3:
            raise NavigationError(
                "L4 is entry-only; cannot return. "
                "Once you leave L4, you cannot go back. "
                "Continue descending or work with the current data."
            )

        # Determine target level
        target_level = ComplexityLevel(current_level.value + 1)

        # Spec 015 cutover: route ascent through the unified Engine, which calls
        # the SAME enrichment/dimension transforms legacy used (identical output)
        # and stamps lineage. The session adapts UI kwargs into typed params.
        try:
            typed = self._ascent_params(current_level, target_level, params)
            new_dataset = Engine.increase_complexity(
                self._current_dataset, target_level, typed
            )
        except NavigationError:
            raise
        except Exception as e:
            raise NavigationError(f"Ascent failed: {str(e)}")

        # Update state
        self._current_dataset = new_dataset

        # FR-019: Track accumulated output at this level
        self._accumulated_outputs[target_level.value] = new_dataset

        # Generate node_id
        node_id = self._generate_node_id("ascend", params)
        self._current_node_id = node_id

        # FR-021: Generate decision_description
        decision_description = self._generate_decision_description("ascend", current_level, target_level, params)

        # Record step as a tree node, with ascent-specific metadata.
        metadata = {}
        if "enrichment_func" in params:
            metadata["enrichment"] = params["enrichment_func"]
        if "dimensions" in params:
            metadata["dimensions"] = params["dimensions"]
        if "relationships" in params:
            metadata["relationships"] = [str(r) for r in params["relationships"]]
        self._current_node_id = self._tree.branch(
            NavigationAction.ASCEND,
            new_dataset,
            metadata,
            decision_description=decision_description  # FR-021
        )

        return self

    # -------------------------------------------------------------------------
    # get_available_moves() - List valid moves from current position
    # -------------------------------------------------------------------------

    def get_available_moves(self) -> Dict[str, List[str]]:
        """
        List valid moves from current position.

        Navigation is VERTICAL ONLY (no horizontal movement):
        - Descend: Move down one level (L4→L3→L2→L1→L0)
        - Ascend: Move up one level (L0→L1→L2→L3), but NEVER to L4

        Returns:
            Dictionary with 'descend' and 'ascend' keys,
            each containing a list of available target descriptions.
        """
        current_level = self.current_level
        moves = {
            "descend": [],
            "ascend": []
        }

        # Descend options - each level uses specific workflow features
        if current_level != ComplexityLevel.LEVEL_0:
            target = ComplexityLevel(current_level.value - 1)
            if current_level == ComplexityLevel.LEVEL_4:
                moves["descend"].append({
                    "target": "L3",
                    "target_name": target.name,
                    "step": "entities",
                    "description": "Define entities and link sources into a knowledge graph"
                })
            elif current_level == ComplexityLevel.LEVEL_3:
                moves["descend"].append({
                    "target": "L2",
                    "target_name": target.name,
                    "step": "domains",
                    "description": "Query the graph to isolate domain-specific tables"
                })
            elif current_level == ComplexityLevel.LEVEL_2:
                moves["descend"].append({
                    "target": "L1",
                    "target_name": target.name,
                    "step": "features",
                    "description": "Extract a column to create feature vectors"
                })
            elif current_level == ComplexityLevel.LEVEL_1:
                moves["descend"].append({
                    "target": "L0",
                    "target_name": target.name,
                    "step": "metric",
                    "description": "Aggregate to compute atomic metrics"
                })

        # Ascend options - blocked at L3 (cannot return to L4)
        if current_level == ComplexityLevel.LEVEL_0:
            enrichment_options = self.get_enrichment_options()
            moves["ascend"].append({
                "target": "L1",
                "target_name": "LEVEL_1",
                "step": "enrich",
                "description": "Enrich the datum back to a vector",
                "enrichment_functions": enrichment_options
            })
        elif current_level == ComplexityLevel.LEVEL_1:
            dimension_options = self.get_dimension_options()
            moves["ascend"].append({
                "target": "L2",
                "target_name": "LEVEL_2",
                "step": "dimension",
                "description": "Add dimensions to create a table",
                "dimensions": dimension_options
            })
        elif current_level == ComplexityLevel.LEVEL_2:
            dimension_options = self.get_dimension_options()
            moves["ascend"].append({
                "target": "L3",
                "target_name": "LEVEL_3",
                "step": "hierarchy",
                "description": "Group into hierarchical relationships",
                "dimensions": dimension_options
            })
        # L3 cannot ascend to L4 - L4 is entry-only

        return moves

    def can_descend(self) -> bool:
        """Check if descent is possible from current level."""
        return self.current_level != ComplexityLevel.LEVEL_0

    def can_ascend(self) -> bool:
        """Check if ascent is possible from current level (L4 is blocked)."""
        return self.current_level not in [ComplexityLevel.LEVEL_3, ComplexityLevel.LEVEL_4]

    def get_enrichment_options(self) -> List[Dict[str, str]]:
        """
        Get available enrichment functions for L0→L1 ascent.

        Returns:
            List of dicts with 'name', 'description', 'requires_context' keys.
            Empty list if not at L0 or no enrichments available.
        """
        if self.current_level != ComplexityLevel.LEVEL_0:
            return []

        try:
            from intuitiveness.ascent.enrichment import EnrichmentRegistry
            registry = EnrichmentRegistry.get_instance()
            funcs = registry.list_for_transition(
                ComplexityLevel.LEVEL_0, ComplexityLevel.LEVEL_1
            )
            return [
                {
                    'name': f.name,
                    'description': f.description,
                    'requires_context': f.requires_context
                }
                for f in funcs
            ]
        except ImportError:
            return []

    def get_dimension_options(self, target_level: ComplexityLevel = None) -> List[Dict[str, str]]:
        """
        Get available dimension definitions for L1→L2 or L2→L3 ascent.

        Args:
            target_level: Target level (L2 or L3). If None, inferred from current level.

        Returns:
            List of dicts with 'name', 'description', 'possible_values' keys.
            Empty list if not at L1/L2 or no dimensions available.
        """
        current = self.current_level
        if target_level is None:
            if current == ComplexityLevel.LEVEL_1:
                target_level = ComplexityLevel.LEVEL_2
            elif current == ComplexityLevel.LEVEL_2:
                target_level = ComplexityLevel.LEVEL_3
            else:
                return []

        try:
            from intuitiveness.ascent.dimensions import DimensionRegistry
            registry = DimensionRegistry.get_instance()
            dims = registry.list_for_transition(current, target_level)
            return [
                {
                    'name': d.name,
                    'description': d.description,
                    'possible_values': d.possible_values
                }
                for d in dims
            ]
        except ImportError:
            return []

    def get_current_step_id(self) -> str:
        """Get the step ID corresponding to the current level for UI integration."""
        level_to_step = {
            ComplexityLevel.LEVEL_4: "upload",      # Entry point
            ComplexityLevel.LEVEL_3: "entities",    # After L4→L3 transition
            ComplexityLevel.LEVEL_2: "domains",     # After L3→L2 transition
            ComplexityLevel.LEVEL_1: "features",    # After L2→L1 transition
            ComplexityLevel.LEVEL_0: "metric"       # After L1→L0 transition
        }
        return level_to_step.get(self.current_level, "unknown")

    # -------------------------------------------------------------------------
    # get_history() - Get the navigation path
    # -------------------------------------------------------------------------

    def get_history(self) -> List[Dict[str, Any]]:
        """
        Get the navigation path as a list of step dictionaries.

        Returns:
            List of dicts with level, node_id, action, timestamp for each step.
        """
        path = self._tree.get_current_branch_path()
        return [node.to_dict() for node in path]

    # -------------------------------------------------------------------------
    # exit() - End navigation session
    # -------------------------------------------------------------------------

    def exit(self) -> Dict[str, Any]:
        """
        End navigation session, preserving position for later resumption.

        Returns:
            Export data with navigation tree and current output (FR-015).
        """
        self._state = NavigationState.EXITED

        # Return export data per FR-015
        return self.export()

    # -------------------------------------------------------------------------
    # save() and load() - Session persistence
    # -------------------------------------------------------------------------

    def save(self, location: Optional[str] = None) -> str:
        """
        Persist the session as a full-fidelity, package-free-readable record.

        Spec 015 T034/T038: the whole navigation tree (every branch, every
        point's data + lineage) is serialized via the cross-service export
        contract and written to a durable file/blob backend — no pickle, so the
        record can be read by a separate program using only the documented
        schema.

        Args:
            location: Optional explicit file path. If omitted, the durable
                      backend's default location keyed by ``session_id`` is used.

        Returns:
            The durable location the record was written to.
        """
        from intuitiveness.persistence.session_export import export_session
        from intuitiveness.persistence.durable_backend import get_durable_backend

        record = export_session(self._tree, metadata={
            "session_id": self._session_id,
            "state": self._state.value,
        })

        if location is not None:
            os.makedirs(os.path.dirname(location) or ".", exist_ok=True)
            with open(location, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False)
            return location

        # Postgres (e.g. Railway) when configured, else local files.
        return get_durable_backend().save_record(self._session_id, record)

    @classmethod
    def load(cls, location: str) -> 'NavigationSession':
        """
        Restore a session from a full-fidelity record (spec 015 T038).

        Args:
            location: A file path to a record, or a session id resolved against
                      the durable backend's default location.

        Returns:
            Restored NavigationSession.

        Raises:
            SessionNotFoundError: If no record can be found.
        """
        from intuitiveness.persistence.session_export import import_session
        from intuitiveness.persistence.durable_backend import get_durable_backend

        if os.path.exists(location):
            with open(location, "r", encoding="utf-8") as f:
                record = json.load(f)
        else:
            try:
                record = get_durable_backend().load_record(location)
            except FileNotFoundError:
                raise SessionNotFoundError(f"Session record not found: {location}")

        tree = import_session(record)
        return cls._from_tree(tree, record.get("metadata", {}))

    @classmethod
    def _from_tree(cls, tree: NavigationTree, metadata: Dict[str, Any]) -> 'NavigationSession':
        """Build a session around an already-rebuilt navigation tree."""
        root_dataset = tree.nodes[tree.root_id].dataset_snapshot
        session = cls(root_dataset)          # builds a throwaway tree we replace
        session._tree = tree
        session._current_node_id = tree.current_id
        session._current_dataset = tree.current_node.dataset_snapshot

        # Rebuild the per-level accumulated outputs from the active branch path.
        session._accumulated_outputs = {
            node.level.value: node.dataset_snapshot
            for node in tree.get_current_branch_path()
        }
        session._state = NavigationState.EXPLORING

        # Restore the saved session id (re-registering under it).
        saved_id = metadata.get("session_id")
        if saved_id:
            cls._sessions.pop(session._session_id, None)
            session._session_id = saved_id
        cls._sessions[session._session_id] = session
        return session

    # -------------------------------------------------------------------------
    # resume() - Resume a previously exited session
    # -------------------------------------------------------------------------

    @classmethod
    def resume(cls, session_id: str) -> 'NavigationSession':
        """
        Resume a previously exited session.

        Args:
            session_id: UUID from exited session.

        Returns:
            Restored NavigationSession.

        Raises:
            SessionNotFoundError: If session not found or expired.
        """
        if session_id not in cls._sessions:
            raise SessionNotFoundError(
                f"Session '{session_id}' not found. "
                f"It may have expired or been cleared. "
                f"Use NavigationSession.load(path) to restore from file."
            )

        session = cls._sessions[session_id]

        # Resume from exited state
        if session._state == NavigationState.EXITED:
            session._state = NavigationState.EXPLORING

        return session

    # -------------------------------------------------------------------------
    # Tree navigation methods (002-ascent-functionality)
    # -------------------------------------------------------------------------

    def restore(self, node_id: str) -> 'NavigationSession':
        """
        Time-travel to a previous navigation state.

        Args:
            node_id: ID of the tree node to restore

        Returns:
            Self for method chaining

        Raises:
            NavigationError: If the node is not found
        """
        try:
            self._current_dataset = self._tree.restore(node_id)
            self._current_node_id = node_id
            self._state = NavigationState.EXPLORING
        except KeyError:
            raise NavigationError(f"Node '{node_id}' not found in navigation tree")

        return self

    def time_travel(self, node_id: str) -> 'NavigationSession':
        """Move the current position to an existing node (spec 015 T025).

        This is the explicit, intention-revealing name for jumping to a node
        without creating a new branch; it is equivalent to :meth:`restore`.

        Args:
            node_id: ID of the tree node to jump to

        Returns:
            Self for method chaining
        """
        return self.restore(node_id)

    def branch_from(self, node_id: str, action: str = "descend",
                    **params) -> 'NavigationSession':
        """Start a NEW branch from an earlier node (spec 015 T025).

        Time-travels to ``node_id``, then performs one transition through the
        unified engine (descend or ascend). Because the engine always branches
        off the current position, this creates a fresh child of ``node_id`` —
        a new exploration branch that leaves the original path untouched.

        Args:
            node_id: ID of the node to branch from
            action: "descend" or "ascend"
            **params: Transition params forwarded to descend()/ascend()

        Returns:
            Self for method chaining

        Raises:
            NavigationError: If the node is missing or the action is invalid
        """
        self.restore(node_id)
        normalized = action.lower().strip()
        if normalized == "descend":
            return self.descend(**params)
        if normalized == "ascend":
            return self.ascend(**params)
        raise NavigationError(
            f"branch_from() action must be 'descend' or 'ascend', got '{action}'."
        )

    def prune(self, node_id: str) -> int:
        """Explicitly remove a branch and its subtree (spec 015 T027).

        There is no automatic eviction — branches persist until the user removes
        them. The current branch and the root are protected.

        Args:
            node_id: ID of the node whose subtree to remove

        Returns:
            Number of nodes removed

        Raises:
            NavigationError: If the node is missing or protected
        """
        try:
            return self._tree.prune(node_id)
        except KeyError:
            raise NavigationError(f"Node '{node_id}' not found in navigation tree")
        except ValueError as e:
            raise NavigationError(str(e))

    def archive(self, node_id: str) -> int:
        """Explicitly soft-hide a branch and its subtree (spec 015 T027).

        Reversible alternative to :meth:`prune`: the subtree is marked archived
        (kept in the tree, data and lineage intact) so a UI can filter it out.

        Args:
            node_id: ID of the node whose subtree to archive

        Returns:
            Number of nodes marked archived

        Raises:
            NavigationError: If the node is missing or protected
        """
        try:
            return self._tree.archive(node_id)
        except KeyError:
            raise NavigationError(f"Node '{node_id}' not found in navigation tree")
        except ValueError as e:
            raise NavigationError(str(e))

    def get_tree_visualization(self) -> Dict[str, Any]:
        """
        Get decision tree for sidebar rendering.

        Returns:
            Dict with nodes, current_path, and branches for UI display.
        """
        # Get all nodes as NavigationNodeInfo-like dicts
        # Per FR-021, includes decision_description and output_snapshot for each node
        nodes = []
        for node in self._tree.nodes.values():
            nodes.append({
                "id": node.id,
                "level": node.level.name,
                "action": node.action,
                "timestamp": node.timestamp.isoformat(),
                "depth": node.depth,
                "is_current": node.id == self._tree.current_id,
                "has_children": len(node.children_ids) > 0,
                "children_ids": node.children_ids.copy(),
                "metadata": {k: v for k, v in node.metadata.items() if not k.startswith('_')},
                "decision_description": node.decision_description,  # FR-021
                "output_snapshot": node.output_snapshot  # FR-021
            })

        # Get current path
        current_path = [n.id for n in self._tree.get_current_branch_path()]

        # Find branch points (nodes with multiple children)
        branches = [
            node_id for node_id, node in self._tree.nodes.items()
            if len(node.children_ids) > 1
        ]

        return {
            "nodes": nodes,
            "current_path": current_path,
            "branches": branches
        }

    def export(self) -> Dict[str, Any]:
        """
        Export current state as JSON-serializable dict.

        Per FR-015, includes navigation tree and current output.
        Per FR-019, includes cumulative outputs from ALL levels visited.

        Returns:
            Dict suitable for JSON export and JSON Crack visualization.
        """
        # Build output summary
        output_summary = {
            "level": self.current_level.value,
            "level_name": self.current_level.name,
        }

        # Determine output type and add relevant info
        current_data = self._current_dataset.get_data()
        if self.current_level == ComplexityLevel.LEVEL_0:
            output_summary["output_type"] = "datum"
            output_summary["value"] = str(current_data)
        elif self.current_level == ComplexityLevel.LEVEL_1:
            output_summary["output_type"] = "vector"
            if hasattr(current_data, '__len__'):
                output_summary["row_count"] = len(current_data)
        elif self.current_level == ComplexityLevel.LEVEL_2:
            output_summary["output_type"] = "dataframe"
            if hasattr(current_data, 'shape'):
                output_summary["row_count"] = current_data.shape[0]
                output_summary["column_names"] = list(current_data.columns) if hasattr(current_data, 'columns') else []
        elif self.current_level == ComplexityLevel.LEVEL_3:
            output_summary["output_type"] = "graph"
            if hasattr(current_data, 'number_of_nodes'):
                output_summary["node_count"] = current_data.number_of_nodes()
                output_summary["edge_count"] = current_data.number_of_edges()
        else:
            output_summary["output_type"] = "unknown"

        # Build export structure
        export_data = {
            "version": "1.0",
            "feature": "002-ascent-functionality",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "session_id": self._session_id,
            "current_output": output_summary
        }

        # Add navigation structure (tree is always present).
        export_data["navigation_tree"] = self._tree.export_to_json()
        export_data["current_path"] = [n.id for n in self._tree.get_current_branch_path()]

        # FR-019: Add cumulative outputs from all levels visited
        cumulative = self.get_cumulative_export()
        export_data["cumulative_outputs"] = cumulative.to_dict()

        return export_data

    def get_available_options(self) -> List[Dict[str, Any]]:
        """
        Get all available navigation options at current level.

        Returns options per FR-011 through FR-014:
        - At L3: Exit with graph + path, or Descend to L2
        - At L2: Exit, Descend to L1, or Ascend to L3
        - At L1: Exit, Descend to L0, or Ascend to L2
        - At L0: Exit with datum + path, or Ascend to L1
        """
        options = []
        current_level = self.current_level

        # Exit option (always available)
        if current_level == ComplexityLevel.LEVEL_0:
            options.append({
                "action": "exit",
                "target_level": None,
                "description": "Exit with datum + path"
            })
        elif current_level == ComplexityLevel.LEVEL_3:
            options.append({
                "action": "exit",
                "target_level": None,
                "description": "Exit with graph + path"
            })
        else:
            options.append({
                "action": "exit",
                "target_level": None,
                "description": f"Exit with {current_level.name.lower().replace('level_', 'L')} output + path"
            })

        # Descend option
        if current_level != ComplexityLevel.LEVEL_0:
            target = ComplexityLevel(current_level.value - 1)
            options.append({
                "action": "descend",
                "target_level": target.name,
                "description": f"Descend to {target.name.replace('LEVEL_', 'L')}"
            })

        # Ascend option (blocked at L3 and L4)
        if current_level == ComplexityLevel.LEVEL_0:
            options.append({
                "action": "ascend",
                "target_level": "LEVEL_1",
                "description": "Ascend to L1 (unfold datum)",
                "enrichment_options": self.get_enrichment_options()
            })
        elif current_level == ComplexityLevel.LEVEL_1:
            options.append({
                "action": "ascend",
                "target_level": "LEVEL_2",
                "description": "Ascend to L2 (add domain)",
                "dimension_options": self.get_dimension_options()
            })
        elif current_level == ComplexityLevel.LEVEL_2:
            options.append({
                "action": "ascend",
                "target_level": "LEVEL_3",
                "description": "Ascend to L3 (specify relationships)",
                "dimension_options": self.get_dimension_options()
            })
        # L3 and L4 cannot ascend

        return options

    # -------------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------------

    def _generate_node_id(self, action: str, params: Dict) -> str:
        """Generate a node ID based on the action and parameters."""
        history_len = len(self._tree)

        if action == "descend":
            if "column" in params:
                return f"col_{params['column']}"
            elif "entity_type" in params:
                return f"entity_{params['entity_type']}"
            elif "aggregation" in params:
                return f"agg_{params['aggregation']}"
            else:
                return f"node_{history_len}"
        elif action == "ascend":
            return f"expanded_{history_len}"
        else:
            return f"node_{history_len}"

    def _generate_decision_description(
        self,
        action: str,
        source_level: ComplexityLevel,
        target_level: ComplexityLevel,
        params: Dict
    ) -> str:
        """
        Generate a human-readable description of the navigation decision (FR-021).

        Args:
            action: "descend" or "ascend"
            source_level: Starting level
            target_level: Ending level
            params: Parameters used for the transition

        Returns:
            Human-readable description like "Make graph with Indicator, Source"
        """
        source_name = source_level.name.replace("LEVEL_", "L")
        target_name = target_level.name.replace("LEVEL_", "L")

        if action == "descend":
            if source_level == ComplexityLevel.LEVEL_4:
                # L4→L3: entities
                entities = params.get("entities", [])
                if entities:
                    return f"Make graph with {', '.join(str(e) for e in entities[:3])}"
                return "Create linkable graph from sources"
            elif source_level == ComplexityLevel.LEVEL_3:
                # L3→L2: domain table
                domain = params.get("entity_type") or params.get("domain", "")
                if domain:
                    return f"Filter domain {domain}"
                return "Extract domain table from graph"
            elif source_level == ComplexityLevel.LEVEL_2:
                # L2→L1: column extraction
                column = params.get("column", "")
                if column:
                    return f"Extract column {column}"
                return "Extract column to vector"
            elif source_level == ComplexityLevel.LEVEL_1:
                # L1→L0: aggregation
                agg = params.get("aggregation", "sum")
                return f"Aggregate {agg}"

        elif action == "ascend":
            if source_level == ComplexityLevel.LEVEL_0:
                # L0→L1: enrichment
                enrichment = params.get("enrichment_func", "")
                if enrichment:
                    return f"Ascend with {enrichment} enrichment"
                return "Unfold datum to vector"
            elif source_level == ComplexityLevel.LEVEL_1:
                # L1→L2: dimensions
                dims = params.get("dimensions", [])
                if dims:
                    return f"Add dimensions {', '.join(str(d) for d in dims[:3])}"
                return "Add dimensions to create table"
            elif source_level == ComplexityLevel.LEVEL_2:
                # L2→L3: relationships
                rels = params.get("relationships", [])
                dims = params.get("dimensions", [])
                if rels:
                    return f"Define relationships ({len(rels)} defined)"
                elif dims:
                    return f"Add analytic dimensions {', '.join(str(d) for d in dims[:3])}"
                return "Create hierarchical grouping"

        return f"{action.capitalize()} from {source_name} to {target_name}"

    def get_available_graph_entities(self) -> List[str]:
        """
        Get available columns from original L4 data for L2→L3 entity selection (FR-020).

        When ascending from L2 to L3, users can select columns from the original
        raw data to become node types in their graph.

        Returns:
            List of column names from original L4 sources
        """
        return self._raw_data_columns.copy()

    def get_cumulative_export(self) -> 'CumulativeOutputs':
        """
        Get cumulative outputs from all levels visited (FR-019).

        Returns:
            CumulativeOutputs object with summaries for each level
        """
        from intuitiveness.export.json_export import OutputSummary, CumulativeOutputs

        cumulative = CumulativeOutputs()

        # Build output summaries for each accumulated level
        for level_value, dataset in self._accumulated_outputs.items():
            summary = self._create_output_summary(dataset)

            if level_value == 3:
                cumulative.graph = summary
            elif level_value == 2:
                cumulative.table = summary
            elif level_value == 1:
                cumulative.vector = summary
            elif level_value == 0:
                cumulative.datum = summary

        return cumulative

    def _create_output_summary(self, dataset: Dataset) -> 'OutputSummary':
        """Create an OutputSummary for a dataset."""
        from intuitiveness.export.json_export import OutputSummary

        level = dataset.complexity_level
        data = dataset.get_data()

        # Determine output type
        if level == ComplexityLevel.LEVEL_0:
            return OutputSummary(
                level=level.value,
                level_name=level.name,
                output_type="datum",
                sample_data=str(data)
            )
        elif level == ComplexityLevel.LEVEL_1:
            row_count = len(data) if hasattr(data, '__len__') else None
            return OutputSummary(
                level=level.value,
                level_name=level.name,
                output_type="vector",
                row_count=row_count
            )
        elif level == ComplexityLevel.LEVEL_2:
            row_count = data.shape[0] if hasattr(data, 'shape') else None
            columns = list(data.columns) if hasattr(data, 'columns') else []
            return OutputSummary(
                level=level.value,
                level_name=level.name,
                output_type="dataframe",
                row_count=row_count,
                column_names=columns
            )
        elif level == ComplexityLevel.LEVEL_3:
            if hasattr(data, 'number_of_nodes'):
                return OutputSummary(
                    level=level.value,
                    level_name=level.name,
                    output_type="graph",
                    node_count=data.number_of_nodes(),
                    edge_count=data.number_of_edges()
                )
            else:
                row_count = data.shape[0] if hasattr(data, 'shape') else None
                return OutputSummary(
                    level=level.value,
                    level_name=level.name,
                    output_type="graph",
                    row_count=row_count
                )
        else:
            return OutputSummary(
                level=level.value,
                level_name=level.name,
                output_type="unknown"
            )

    @property
    def navigation_tree(self) -> NavigationTree:
        """Get the navigation tree (always present)."""
        return self._tree

    def __repr__(self) -> str:
        step_count = len(self._tree)
        return (
            f"NavigationSession("
            f"id={self._session_id[:8]}..., "
            f"state={self._state.value}, "
            f"level={self.current_level.name}, "
            f"steps={step_count})"
        )

    # -------------------------------------------------------------------------
    # Session Graph Persistence (Phase 2B - 006-playwright-mcp-e2e)
    # -------------------------------------------------------------------------

    def save_graph(self, filepath: str) -> SessionGraph:
        """
        Save session state to a NetworkX graph JSON file.

        Creates a SessionGraph with all level states and transitions,
        including full data artifacts for future ML training.

        Args:
            filepath: Path to output JSON file

        Returns:
            The SessionGraph that was saved
        """
        import pandas as pd

        graph = SessionGraph()

        # Build graph from accumulated outputs and history
        prev_node_id = None

        # Traverse the tree from root to the current node.
        steps = []
        current = self._tree.nodes.get(self._current_node_id)
        while current:
            steps.insert(0, current)
            if current.parent_id:
                current = self._tree.nodes.get(current.parent_id)
            else:
                break

        # Add each step (a NavigationTreeNode) as a graph node.
        for i, step in enumerate(steps):
            level = step.level.value
            action = step.action
            metadata = step.metadata.copy() if step.metadata else {}
            metadata["decision_description"] = step.decision_description
            # Get data from accumulated outputs
            data = self._accumulated_outputs.get(level)

            # Determine output value based on level
            if level == 0:
                output_value = data.get_data() if hasattr(data, 'get_data') else data
            elif level == 1:
                d = data.get_data() if hasattr(data, 'get_data') else data
                output_value = {"row_count": len(d) if hasattr(d, '__len__') else 1}
            elif level == 2:
                d = data.get_data() if hasattr(data, 'get_data') else data
                if isinstance(d, pd.DataFrame):
                    output_value = {"row_count": len(d), "columns": list(d.columns)}
                else:
                    output_value = {"data_type": str(type(d))}
            elif level == 3:
                d = data.get_data() if hasattr(data, 'get_data') else data
                if isinstance(d, pd.DataFrame):
                    output_value = {"row_count": len(d), "columns": list(d.columns)}
                elif hasattr(d, 'number_of_nodes'):
                    output_value = {"nodes": d.number_of_nodes(), "edges": d.number_of_edges()}
                else:
                    output_value = {"data_type": str(type(d))}
            else:  # level 4
                d = data.get_data() if hasattr(data, 'get_data') else data
                if isinstance(d, dict):
                    output_value = {"sources": list(d.keys())}
                else:
                    output_value = {"data_type": str(type(d))}

            # Get data artifact (DataFrame or value)
            raw_data = data.get_data() if hasattr(data, 'get_data') else data
            if isinstance(raw_data, dict) and level == 4:
                # L4: combine source DataFrames info
                artifact_data = {k: v.shape if hasattr(v, 'shape') else str(type(v)) for k, v in raw_data.items()}
            elif isinstance(raw_data, pd.DataFrame):
                artifact_data = raw_data
            else:
                artifact_data = raw_data

            # Add node to graph
            node_id = graph.add_level_state(
                level=level,
                output_value=output_value,
                data_artifact=artifact_data,
                metadata=metadata
            )

            # Add transition edge
            if prev_node_id:
                # Determine action based on level change
                prev_level = graph.G.nodes[prev_node_id]["level"]
                if level < prev_level:
                    edge_action = "descend"
                elif level > prev_level:
                    edge_action = "ascend"
                else:
                    edge_action = action

                graph.add_transition(
                    prev_node_id, node_id,
                    action=edge_action,
                    params=metadata
                )

            prev_node_id = node_id

        # Export to file
        graph.export_to_json(filepath)

        return graph

    @classmethod
    def load_graph(cls, filepath: str) -> Dict[str, Any]:
        """
        Load session data from a SessionGraph JSON file.

        This restores the accumulated outputs and decisions for use
        in Free Exploration mode to continue the ascent phase.

        Args:
            filepath: Path to input JSON file

        Returns:
            Dict with session data:
                - accumulated_outputs: Dict[int, Any] (level -> data)
                - decisions: List of decision dicts
                - current_level: int
                - graph: SessionGraph instance
        """
        graph = SessionGraph.load_from_json(filepath)

        # Extract accumulated outputs from graph
        accumulated = {}
        for node_id in graph.G.nodes:
            node_attrs = graph.G.nodes[node_id]
            level = node_attrs["level"]
            # Get the data artifact (most recent at each level)
            accumulated[level] = {
                "output_value": node_attrs.get("output_value"),
                "row_count": node_attrs.get("row_count", 0),
                "column_names": node_attrs.get("column_names", []),
                "decision_description": node_attrs.get("decision_description", ""),
            }

        # Get current level from current node
        current_level = graph.G.nodes[graph.current_id]["level"] if graph.current_id else 0

        return {
            "accumulated_outputs": accumulated,
            "decisions": graph.get_all_decisions(),
            "current_level": current_level,
            "graph": graph,
        }
