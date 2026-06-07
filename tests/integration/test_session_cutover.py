"""Session-path regression net (pre-cutover safety asset).

The deployed app drives transitions through ``NavigationSession(l4, use_tree=True)``
(streamlit_app.py:1050), but no pure-Python test covered that path — only the
browser E2E did. This test locks the full descent→ascent cycle through the
session so the eventual `session.py` rewire onto the unified Engine can be
verified without the browser (spec 015 / IMPLEMENTATION_NOTES Deviation 2, step 5).

Greened against the CURRENT (legacy-backed) session first; it must stay green
after the cutover.
"""

import networkx as nx
import pandas as pd
import pytest

from intuitiveness.complexity import ComplexityLevel, Level4Dataset
from intuitiveness.navigation.session import NavigationSession


# --- simple, deterministic transform callables (mirror the app's UI inputs) --- #

def _build_graph(sources: dict) -> nx.Graph:
    """L4→L3 builder_func: link schools to their category via a bipartite graph."""
    df = sources["schools"]
    g = nx.DiGraph()
    for _, row in df.iterrows():
        school, cat = row["school"], row["category"]
        g.add_node(school, node_type="school", score=row["score"])
        g.add_node(cat, node_type="category")
        g.add_edge(school, cat, relationship="in_category")
    return g


def _query_table(graph: nx.Graph) -> pd.DataFrame:
    """L3→L2 query_func: pull school nodes with their score back into a table."""
    rows = [
        {"school": n, "score": attrs.get("score")}
        for n, attrs in graph.nodes(data=True)
        if attrs.get("node_type") == "school"
    ]
    return pd.DataFrame(rows)


def _l4():
    schools = pd.DataFrame({
        "school": ["A", "B", "C", "D"],
        "score": [80, 90, 70, 100],
        "category": ["down town", "country side", "down town", "country side"],
    })
    return Level4Dataset({"schools": schools})


def test_full_descent_through_session():
    session = NavigationSession(_l4(), use_tree=True)

    session.descend(builder_func=_build_graph)       # L4→L3
    assert session.current_level == ComplexityLevel.LEVEL_3

    session.descend(query_func=_query_table)         # L3→L2
    assert session.current_level == ComplexityLevel.LEVEL_2

    session.descend(column="score")                  # L2→L1
    assert session.current_level == ComplexityLevel.LEVEL_1

    session.descend(aggregation="mean")              # L1→L0
    assert session.current_level == ComplexityLevel.LEVEL_0

    # average of 80,90,70,100 == 85
    assert session.current_dataset.get_data() == 85


def test_session_enforces_entry_at_l4():
    # path-legality: a session must begin at L4 (FR-015)
    from intuitiveness.complexity import Level2Dataset
    with pytest.raises(Exception):
        NavigationSession(Level2Dataset(pd.DataFrame({"x": [1]})), use_tree=True)


def test_session_tree_records_descent_path():
    session = NavigationSession(_l4(), use_tree=True)
    session.descend(builder_func=_build_graph)
    session.descend(query_func=_query_table)
    history = session.get_history()
    # entry + 2 descents recorded on the branch path
    assert len(history) >= 2
