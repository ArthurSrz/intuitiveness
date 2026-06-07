"""T028 — branching isolation, time-travel, query API (spec 015 FR-019/FR-021, SC-005/SC-012).

Driven through the engine (frozen-at-birth datasets) + NavigationTree directly,
so these are non-breaking and independent of the NavigationSession rewire.
"""

import pandas as pd

from intuitiveness.complexity import ComplexityLevel, Level2Dataset
from intuitiveness.navigation.tree import NavigationTree
from intuitiveness.navigation.state import NavigationAction
from intuitiveness.redesign.engine import Redesigner
from intuitiveness.redesign.params import L2toL1Params, L1toL0Params


def _l2():
    return Level2Dataset(pd.DataFrame({"score": [10, 20, 30], "cat": ["a", "b", "a"]}), name="scores")


def _build_tree_with_two_branches():
    """root(L2) → child A (extract 'score') ; time-travel ; child B (extract 'cat')."""
    root = _l2()
    tree = NavigationTree(root)

    # Branch A: L2 → L1 on 'score'
    a = Redesigner.reduce_complexity(root, ComplexityLevel.LEVEL_1, L2toL1Params(column="score"))
    a_id = tree.branch(NavigationAction.DESCEND, a, edge_decision_payload={"column": "score"})

    # Time-travel back to root, take a DIFFERENT decision → sibling branch B
    tree.restore(tree.root_id)
    b = Redesigner.reduce_complexity(root, ComplexityLevel.LEVEL_1, L2toL1Params(column="cat"))
    b_id = tree.branch(NavigationAction.DESCEND, b, edge_decision_payload={"column": "cat"})
    return tree, a_id, b_id


def test_branching_leaves_original_unchanged():
    tree, a_id, b_id = _build_tree_with_two_branches()
    a_node = tree.get_node(a_id)
    # Branch A's dataset + lineage are untouched by creating branch B (SC-005)
    assert a_node.dataset.lineage.operations[-1].parameters["column"] == "score"
    assert list(a_node.dataset.get_data()) == [10, 20, 30]


def test_two_branches_exist():
    tree, a_id, b_id = _build_tree_with_two_branches()
    assert len(tree.branches()) == 2


def test_time_travel_restores_exact_state():
    tree, a_id, b_id = _build_tree_with_two_branches()
    restored = tree.restore(a_id)
    assert list(restored.get_data()) == [10, 20, 30]
    assert restored.lineage.operations[-1].parameters["column"] == "score"


def test_siblings():
    tree, a_id, b_id = _build_tree_with_two_branches()
    sibs = tree.siblings(a_id)
    assert [n.id for n in sibs] == [b_id]


def test_divergence_point_is_root():
    tree, a_id, b_id = _build_tree_with_two_branches()
    dp = tree.divergence_point(a_id, b_id)
    assert dp.id == tree.root_id


def test_nodes_at_level():
    tree, a_id, b_id = _build_tree_with_two_branches()
    l1_nodes = tree.nodes_at_level(ComplexityLevel.LEVEL_1)
    assert len(l1_nodes) == 2
    l2_nodes = tree.nodes_at_level(ComplexityLevel.LEVEL_2)
    assert len(l2_nodes) == 1  # the root
