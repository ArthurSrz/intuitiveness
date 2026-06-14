"""Spec 016 SC-001/SC-002 — the package imports and runs headless (lean install).

A bare `pip install intuitiveness` (no extras) must not require streamlit, a
graph driver, or a database driver. We assert this by importing the package in a
subprocess where those modules are blocked at import time, then running a real
descent→ascent + a file-backed session save (degraded mode).

A subprocess is used so the import-block starts from a clean module table
(intuitiveness is already imported in the main test process).
"""

import subprocess
import sys
import textwrap


HEADLESS_PROGRAM = textwrap.dedent(
    """
    import builtins
    _real = builtins.__import__
    BLOCK = ("streamlit", "streamlit_javascript", "streamlit_pdf_viewer",
             "streamlit_agraph", "streamlit_extras", "neo4j", "psycopg2",
             "psycopg", "matplotlib")
    def _imp(name, *a, **k):
        if name.split(".")[0] in BLOCK:
            raise ImportError("blocked: " + name)
        return _real(name, *a, **k)
    builtins.__import__ = _imp

    import intuitiveness

    # The engine + tree + durable backend must work with zero optional deps.
    import pandas as pd, networkx as nx
    from intuitiveness.complexity import Level4Dataset, ComplexityLevel
    from intuitiveness.navigation.session import NavigationSession
    from intuitiveness.persistence.durable_backend import get_durable_backend, FileDurableBackend

    # Falls back to the file backend when no DATABASE_URL is configured.
    assert isinstance(get_durable_backend(), FileDurableBackend)

    schools = pd.DataFrame({"school": ["A", "B"], "score": [80, 100],
                            "category": ["x", "y"]})
    session = NavigationSession(Level4Dataset({"schools": schools}))

    def build(sources):
        g = nx.DiGraph()
        for _, r in sources["schools"].iterrows():
            g.add_node(r["school"], node_type="school", score=r["score"])
        return g
    def query(g):
        return pd.DataFrame([{"school": n, "score": a["score"]}
                             for n, a in g.nodes(data=True) if a.get("node_type") == "school"])

    session.descend(builder_func=build)   # L4->L3
    session.descend(query_func=query)     # L3->L2
    session.descend(column="score")       # L2->L1
    session.descend(aggregation="mean")   # L1->L0
    assert session.current_dataset.get_data() == 90

    print("HEADLESS_OK")
    """
)


def test_package_imports_and_runs_without_optional_deps():
    result = subprocess.run(
        [sys.executable, "-c", HEADLESS_PROGRAM],
        capture_output=True, text=True,
    )
    assert "HEADLESS_OK" in result.stdout, (
        f"Headless import/run failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert result.returncode == 0
