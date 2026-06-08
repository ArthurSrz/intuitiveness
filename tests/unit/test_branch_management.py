"""T025 + T027 — explicit branch management: branch_from, time_travel, prune, archive.

Spec 015 US2: the session is tree-only, and branch creation / time-travel /
pruning / archiving are all explicit operations routed through the engine
(transitions) or the tree (structure). There is no automatic eviction.
"""

import networkx as nx
import pandas as pd
import pytest

from intuitiveness.complexity import ComplexityLevel, Level2Dataset, Level4Dataset
from intuitiveness.navigation.session import NavigationSession
from intuitiveness.navigation.exceptions import NavigationError
from intuitiveness.navigation.tree import NavigationTree
from intuitiveness.navigation.state import NavigationAction
from intuitiveness.redesign.engine import Redesigner
from intuitiveness.redesign.params import L2toL1Params


def _l4():
    schools = pd.DataFrame({
        "school": ["A", "B", "C", "D"],
        "score": [80, 90, 70, 100],
        "category": ["down town", "country side", "down town", "country side"],
    })
    return Level4Dataset({"schools": schools})


def _build_graph(sources: dict) -> nx.Graph:
    df = sources["schools"]
    g = nx.DiGraph()
    for _, row in df.iterrows():
        g.add_node(row["school"], node_type="school", score=row["score"])
        g.add_node(row["category"], node_type="category")
        g.add_edge(row["school"], row["category"], relationship="in_category")
    return g


def _query_table(graph: nx.Graph) -> pd.DataFrame:
    rows = [
        {"school": n, "score": attrs.get("score")}
        for n, attrs in graph.nodes(data=True)
        if attrs.get("node_type") == "school"
    ]
    return pd.DataFrame(rows)


def _session_at_l2() -> NavigationSession:
    """Drive a session down to L2 so there are real branch points to play with."""
    session = NavigationSession(_l4())
    session.descend(builder_func=_build_graph)   # L4→L3
    session.descend(query_func=_query_table)     # L3→L2
    return session


# --- time_travel -------------------------------------------------------------- #

def test_time_travel_jumps_to_existing_node():
    session = _session_at_l2()
    l2_node_id = session.navigation_tree.current_id

    session.descend(column="score")              # L2→L1
    assert session.current_level == ComplexityLevel.LEVEL_1

    session.time_travel(l2_node_id)
    assert session.current_level == ComplexityLevel.LEVEL_2
    assert session.navigation_tree.current_id == l2_node_id


def test_time_travel_unknown_node_raises():
    session = _session_at_l2()
    with pytest.raises(NavigationError):
        session.time_travel("does-not-exist")


# --- branch_from -------------------------------------------------------------- #

def test_branch_from_creates_a_new_sibling_branch():
    session = _session_at_l2()
    l2_node_id = session.navigation_tree.current_id

    # First decision from L2: extract 'score'.
    session.descend(column="score")
    first_l1 = session.navigation_tree.current_id

    # Branch a DIFFERENT decision off the same L2 node: extract 'school'.
    session.branch_from(l2_node_id, action="descend", column="school")
    second_l1 = session.navigation_tree.current_id

    assert second_l1 != first_l1
    # Both L1 nodes hang off the same L2 parent → siblings.
    sibling_ids = {n.id for n in session.navigation_tree.siblings(first_l1)}
    assert second_l1 in sibling_ids


def test_branch_from_invalid_action_raises():
    session = _session_at_l2()
    node_id = session.navigation_tree.current_id
    with pytest.raises(NavigationError):
        session.branch_from(node_id, action="sideways", column="score")


# --- prune -------------------------------------------------------------------- #

def test_prune_removes_subtree_off_current_branch():
    session = _session_at_l2()
    l2_node_id = session.navigation_tree.current_id

    session.descend(column="score")                  # branch A (current)
    session.branch_from(l2_node_id, column="school")  # branch B (now current)
    branch_b_leaf = session.navigation_tree.current_id

    # Move current OFF branch B so it can be pruned.
    session.time_travel(l2_node_id)
    n_before = len(session.navigation_tree)
    removed = session.prune(branch_b_leaf)

    assert removed == 1
    assert len(session.navigation_tree) == n_before - 1
    assert branch_b_leaf not in session.navigation_tree.nodes


def test_prune_current_branch_is_blocked():
    session = _session_at_l2()
    session.descend(column="score")
    current = session.navigation_tree.current_id
    # Pruning the node we are standing on would orphan us → blocked.
    with pytest.raises(NavigationError):
        session.prune(current)


def test_prune_root_is_blocked():
    session = _session_at_l2()
    with pytest.raises(NavigationError):
        session.prune(session.navigation_tree.root_id)


# --- archive ------------------------------------------------------------------ #

def test_archive_marks_subtree_without_deleting():
    session = _session_at_l2()
    l2_node_id = session.navigation_tree.current_id
    session.descend(column="score")
    leaf = session.navigation_tree.current_id

    marked = session.archive(leaf)

    assert marked == 1
    # Node still exists (reversible) but is flagged archived.
    assert leaf in session.navigation_tree.nodes
    assert session.navigation_tree.nodes[leaf].metadata.get("_archived") is True


# --- tree-level prune protects the active path -------------------------------- #

def test_tree_prune_protects_ancestor_of_current():
    """Direct tree check: cannot prune an ancestor of the current node."""
    root = Level2Dataset(pd.DataFrame({"score": [1, 2, 3]}), name="s")
    tree = NavigationTree(root)
    child = Redesigner.reduce_complexity(root, ComplexityLevel.LEVEL_1, L2toL1Params(column="score"))
    tree.branch(NavigationAction.DESCEND, child)
    # current is now the child; root is its ancestor → pruning root must fail.
    with pytest.raises(ValueError):
        tree.prune(tree.root_id)
