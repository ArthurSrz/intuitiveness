# Contract: Navigation API (Session + Tree)

Realizes FR-015, FR-016, FR-017..FR-022, FR-028.

## `NavigationSession` (stateful path-legality owner)

```text
NavigationSession(dataset: Dataset)                 # dataset MUST be L4, else error (no use_tree flag)
  .descend(params: TransitionParams) -> Self          # delegates transition to Redesigner, records tree node
  .ascend(params: TransitionParams)  -> Self
  .time_travel(node_id: str)         -> Dataset        # restore prior node's full state
  .branch_from(node_id: str, params) -> Self           # sibling trajectory from a historical node
  .get_history()                     -> list[dict]      # = current branch path (derived from tree)
  .prune(node_id: str)               -> None            # explicit, user-triggered
  .archive(node_id: str)             -> None
  .save()                            -> SessionExportRecord   # full-fidelity (R8)
  classmethod load(record) -> NavigationSession
  .current_dataset / .current_level / .session_id / .state
```

### Behavioral guarantees

| ID | Guarantee | Maps to |
|----|-----------|---------|
| NS-1 | Constructor rejects a non-L4 entry dataset. | FR-015 |
| NS-2 | Any attempt to re-enter L4 after departure is refused. | FR-015 |
| NS-3 | Session holds exactly one history structure (a tree); no flat `_history`, no `use_tree`. | FR-017, FR-018, R6 |
| NS-4 | `get_history()` returns the active branch path derived from the tree. | FR-018 |
| NS-5 | Transition rules (adjacency/row-count/no-L4-target) are NOT re-checked here — delegated to Redesigner. | FR-016 |

## `NavigationTree` / `NavigationTreeNode`

```text
NavigationTreeNode: { id, level, dataset (full payload), parent_id, children_ids, edge_decision, timestamp }

NavigationTree:
  .branch(parent_id, dataset, edge_decision) -> node_id
  .restore(node_id) -> Dataset
  .get_current_branch_path() -> list[Node]
  .branches() -> list[list[Node]]                      # all root→leaf paths
  .nodes_at_level(level) -> list[Node]                 # generator: every L_k produced this session
  .siblings(node) -> list[Node]
  .divergence_point(a_id, b_id) -> Node                # where two trajectories split
```

### Behavioral guarantees

| ID | Guarantee | Maps to |
|----|-----------|---------|
| NT-1 | `restore(id)` returns the node's dataset exactly as created. | FR-019 |
| NT-2 | `branch(...)` adds a sibling without mutating any existing node's dataset or lineage. | FR-013, SC-005 |
| NT-3 | Every node retains the COMPLETE dataset (payload+lineage+edge_decision). | FR-020 |
| NT-4 | `branches()/nodes_at_level()/siblings()/divergence_point()` available for the generator consumer. | FR-021, SC-012 |
| NT-5 | `to_dict()`/`from_dict()` include the payload (full fidelity) — the current exclusion is removed. | FR-023, R8 |
| NT-6 | `from_dict()` re-links shared ancestors to the same node object. | FR-028 |
| NT-7 | `prune/archive` only via explicit call; nothing auto-evicts. | FR-022 |
