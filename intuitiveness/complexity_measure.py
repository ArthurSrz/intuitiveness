"""
Dataset complexity measure C(D) for the intuitiveness package.

This module implements the formal complexity analysis of Sarazin & Mourey,
"Intuitiveness as the Next Stage of Open Data" (Section 4), operating directly
on the level-typed datasets defined in ``intuitiveness.complexity``
(Level0Dataset ... Level4Dataset).

The complexity of a dataset is the cardinality of its extractable atomic
relationship space (Definition 4.8): the number of pairwise comparisons a user
could in principle draw from the structure. Descending one abstraction level
removes a bounded share of those relationships, which is what the function
``reduction_ratio`` reports (Definition 4.15).

The measures implemented here are, by level:

    L0 (Prop. 4.9)   C = 0
    L1 (Prop. 4.10)  C = comb(n, 2)
    L2 (Prop. 4.11)  C = comb(n,2)*m + comb(m,2)*n + comb(n,2)*comb(m,2)
    L3 (Prop. 4.12)  C = sum_k C(D2^k) + C_L
    L4 (Prop. 4.13)  C = sum_k C(D^k)            (no links, C_L = 0)

Reference values from the paper used as tests: a 2x2 Level 2 dataset has
C = 5; the minimal Level 3 structure (two 2x2 tables, one link) has C = 11,
giving the 54.5% lower bound for the L3->L2 transition; the L2->L1 transition
on that 2x2 table gives the 80% lower bound.
"""

from math import comb
from typing import Optional, Union, Mapping, Sequence

import pandas as pd
import networkx as nx


# ---------------------------------------------------------------------------
# Per-level structural measures (work on raw shapes, independent of the classes)
# ---------------------------------------------------------------------------

def _c_level1(n: int) -> int:
    """C(D1) for a vector of n elements (Proposition 4.10)."""
    return comb(n, 2)


def _c_level2(n: int, m: int) -> int:
    """C(D2) for n entities and m attributes (Proposition 4.11).

    Three relationship families: within-attribute, within-entity, and the
    cross-attribute / cross-entity interaction term.
    """
    within_attribute = comb(n, 2) * m
    within_entity = comb(m, 2) * n
    cross = comb(n, 2) * comb(m, 2)
    return within_attribute + within_entity + cross


# ---------------------------------------------------------------------------
# Helpers to read (n, m) and the constituent tables out of the wrapped objects
# ---------------------------------------------------------------------------

def _df_shape(df: pd.DataFrame) -> tuple:
    """Return (n_entities, m_attributes) = (rows, columns) of a table."""
    n, m = df.shape
    return int(n), int(m)


def _level3_components(data: Union[nx.Graph, pd.DataFrame]):
    """Decompose a Level 3 payload into its constituent L2 tables and a link count.

    A Level3Dataset wraps either a NetworkX graph or a multi-level DataFrame.

    Graph case: nodes carrying a tabular payload (attribute ``df``/``data``/
    ``table``) are treated as constituent L2 datasets; every other node is a
    scalar/entity node and contributes no internal L2 complexity. Each edge is
    one discovered link, so C_L is the edge count. This matches the case study,
    where graph construction over 8,368 indicators reported 40,279 links as the
    linking complexity.

    DataFrame case: a frame with a 2-level column MultiIndex is read as one
    table per top-level group (each group is a constituent L2 dataset over the
    same rows); the links between groups, sharing the row index, number
    (number_of_groups choose 2). A flat frame is treated as a single L2 table
    with no links.
    """
    internal = 0
    n_links = 0

    if isinstance(data, nx.Graph):
        for _, attrs in data.nodes(data=True):
            payload = None
            for key in ("df", "data", "table"):
                if key in attrs and isinstance(attrs[key], pd.DataFrame):
                    payload = attrs[key]
                    break
            if payload is not None:
                n, m = _df_shape(payload)
                internal += _c_level2(n, m)
        n_links = data.number_of_edges()
        return internal, n_links

    if isinstance(data, pd.DataFrame):
        cols = data.columns
        if isinstance(cols, pd.MultiIndex) and cols.nlevels >= 2:
            groups = list(dict.fromkeys(cols.get_level_values(0)))
            n_rows = int(data.shape[0])
            for g in groups:
                block = data.loc[:, [c for c in cols if c[0] == g]]
                m = int(block.shape[1])
                internal += _c_level2(n_rows, m)
            n_links = comb(len(groups), 2)
            return internal, n_links
        # Flat frame: a single constituent table, no cross-dataset links.
        n, m = _df_shape(data)
        return _c_level2(n, m), 0

    raise TypeError(
        f"Level 3 payload must be a networkx.Graph or pandas.DataFrame, "
        f"got {type(data).__name__}"
    )


def _level4_components(data: Mapping[str, object]) -> int:
    """Sum of constituent complexities for a Level 4 collection (Prop. 4.13).

    Each value is a raw source. DataFrames contribute their L2 complexity;
    Series contribute L1 complexity; anything else contributes 0. No links
    exist at Level 4, so there is no C_L term.
    """
    total = 0
    for source in data.values():
        if isinstance(source, pd.DataFrame):
            n, m = _df_shape(source)
            total += _c_level2(n, m)
        elif isinstance(source, pd.Series):
            total += _c_level1(len(source))
    return total


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def complexity(dataset) -> int:
    """Compute C(D), the structural complexity of a level-typed dataset.

    Accepts any instance of the ``Dataset`` hierarchy in
    ``intuitiveness.complexity`` (Level0Dataset ... Level4Dataset). Returns the
    number of extractable atomic relationships (Definition 4.8) according to the
    measure proven for that level in Section 4.

    The function dispatches on the dataset's ``complexity_level`` rather than on
    its Python class, so any object exposing that property and ``get_data()``
    works.

    Examples
    --------
    >>> import pandas as pd
    >>> from intuitiveness.complexity import Level2Dataset
    >>> df = pd.DataFrame({"w": [45, 60], "h": [150, 178]})
    >>> complexity(Level2Dataset(df))
    5
    """
    level = dataset.complexity_level.value
    data = dataset.get_data()

    if level == 0:
        return 0

    if level == 1:
        return _c_level1(len(data))

    if level == 2:
        n, m = _df_shape(data)
        return _c_level2(n, m)

    if level == 3:
        internal, n_links = _level3_components(data)
        return internal + n_links

    if level == 4:
        return _level4_components(data)

    raise ValueError(f"Unknown complexity level: {level}")


def linking_complexity(dataset) -> int:
    """Return only the C_L term of a Level 3 dataset (Proposition 4.12).

    This is the count of discovered cross-dataset links, i.e. the quantity
    reported as 40,279 in the case study after L4->L3 graph construction. Raises
    if the dataset is not Level 3.
    """
    if dataset.complexity_level.value != 3:
        raise ValueError("linking_complexity is defined only for Level 3 datasets")
    _, n_links = _level3_components(dataset.get_data())
    return n_links


def reduction_ratio(source, target) -> float:
    """Realized complexity reduction for a descent transition (Definition 4.15).

    Returns Delta C = 1 - C(target) / C(source), the share of atomic
    relationships removed by descending from ``source`` to the lower-level
    ``target``. The target level must be strictly below the source level, and
    the source must have positive complexity.

    For the worked examples in the paper this returns 1.0 for L1->L0, and at
    least 0.8 and 0.5454... respectively for the minimal L2->L1 and L3->L2
    transitions.
    """
    src_level = source.complexity_level.value
    tgt_level = target.complexity_level.value
    if tgt_level >= src_level:
        raise ValueError(
            f"reduction_ratio expects a descent: target level {tgt_level} "
            f"must be below source level {src_level}"
        )
    c_source = complexity(source)
    if c_source == 0:
        raise ZeroDivisionError(
            "source complexity is 0; reduction ratio is undefined"
        )
    c_target = complexity(target)
    return 1.0 - c_target / c_source


def complexity_report(datasets: Sequence) -> "pd.DataFrame":
    """Tabulate C(D) and per-step reductions over an ordered descent trail.

    ``datasets`` is a sequence ordered from higher to lower abstraction level
    (for example the accumulated outputs of a NavigationSession descent). Returns
    a DataFrame with one row per visited level: its level number, C(D), and the
    reduction ratio relative to the previous (higher) level. The first row has no
    previous level, so its reduction is NaN.
    """
    rows = []
    prev = None
    for d in datasets:
        c = complexity(d)
        if prev is None:
            red = float("nan")
        else:
            c_prev = complexity(prev)
            red = float("nan") if c_prev == 0 else 1.0 - c / c_prev
        rows.append(
            {
                "level": d.complexity_level.value,
                "complexity": c,
                "reduction_vs_previous": red,
            }
        )
        prev = d
    return pd.DataFrame(rows)
