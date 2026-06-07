"""
Full-fidelity session export/import — the cross-service contract (spec 015 US3).

Turns a NavigationTree (every branch, every point's data + history) into a single
versioned, self-contained record, and back. A SEPARATE program (e.g. a synthetic
data generator) can read the record using only the documented decode rules in
`contracts/session_export.schema.json` — it does NOT need to import this package.

Design:
- Nodes are stored as a FLAT map keyed by id, with parent_id references, so a
  branch sharing ancestors stores each ancestor once (FR-026).
- Each node's payload is encoded by its actual data TYPE (payload_kind), reusing
  the existing serializers (DataFrame/graph/value -> zlib+base64).
- Lineage (the derivation history) is stored as a list of provenance records.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import pandas as pd
import networkx as nx

from intuitiveness.complexity import (
    ComplexityLevel, Dataset,
    Level0Dataset, Level1Dataset, Level2Dataset, Level3Dataset, Level4Dataset,
)
from intuitiveness.redesign.lineage import DataLineage, SourceReference
from intuitiveness.persistence.serializers import (
    serialize_dataframe, deserialize_dataframe,
    serialize_graph, deserialize_graph,
    serialize_value, deserialize_value,
)

# Bump the MAJOR component only on incompatible changes. Consumers fail-closed
# on an unknown major (see import_session).
SCHEMA_VERSION = "1.0.0"


class SchemaVersionError(ValueError):
    """Raised when an export record's schema version is not understood."""


# --------------------------------------------------------------------------- #
# Payload encode / decode (by actual data type)
# --------------------------------------------------------------------------- #

def _encode_payload(data: Any) -> Tuple[str, Any]:
    """Return (payload_kind, encoded_payload) for any level's data."""
    if isinstance(data, dict):
        # L4: a named collection of raw tables
        return "unlinkable", {name: serialize_dataframe(df) for name, df in data.items()}
    if isinstance(data, nx.Graph):
        return "graph", serialize_graph(data)
    if isinstance(data, pd.DataFrame):
        return "dataframe", serialize_dataframe(data)
    if isinstance(data, pd.Series):
        return "vector", serialize_dataframe(data.to_frame(name=data.name or "value"))
    # L0: a single value
    return "value", serialize_value(data)


def _decode_payload(kind: str, payload: Any) -> Any:
    if kind == "unlinkable":
        return {name: deserialize_dataframe(enc) for name, enc in payload.items()}
    if kind == "graph":
        return deserialize_graph(payload)
    if kind == "dataframe":
        return deserialize_dataframe(payload)
    if kind == "vector":
        df = deserialize_dataframe(payload)
        return df.iloc[:, 0]  # single-column frame back to a Series
    if kind == "value":
        return deserialize_value(payload)
    raise ValueError(f"Unknown payload_kind: {kind!r}")


def _rebuild_dataset(level: int, kind: str, payload: Any, lineage: DataLineage) -> Dataset:
    data = _decode_payload(kind, payload)
    cls = {0: Level0Dataset, 1: Level1Dataset, 2: Level2Dataset,
           3: Level3Dataset, 4: Level4Dataset}[level]
    ds = cls(data)
    ds.lineage = lineage
    return ds


# --------------------------------------------------------------------------- #
# Export / Import
# --------------------------------------------------------------------------- #

def export_session(tree, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Serialize a NavigationTree into a full-fidelity, versioned record."""
    nodes_out: Dict[str, Any] = {}
    for node_id, node in tree.nodes.items():
        ds = node.dataset_snapshot
        kind, payload = _encode_payload(ds.get_data())
        nodes_out[node_id] = {
            "id": node_id,
            "level": node.level.value,
            "parent_id": node.parent_id,
            "children_ids": list(node.children_ids),
            "edge_decision": dict(getattr(node, "edge_decision", {}) or {}),
            "lineage": [ref.to_dict() for ref in ds.lineage.operations],
            "payload_kind": kind,
            "payload": payload,
        }

    meta = dict(metadata or {})
    meta.setdefault("root_id", tree.root_id)
    meta.setdefault("current_id", tree.current_id)
    return {"schema_version": SCHEMA_VERSION, "metadata": meta, "nodes": nodes_out}


def import_session(record: Dict[str, Any]):
    """Rebuild a NavigationTree from a record. Re-links shared ancestors (FR-028).

    Fail-closed on an unknown MAJOR schema version.
    """
    version = record.get("schema_version", "")
    if not version.split(".")[0].isdigit() or version.split(".")[0] != SCHEMA_VERSION.split(".")[0]:
        raise SchemaVersionError(
            f"Cannot read schema_version {version!r}; this build understands "
            f"major {SCHEMA_VERSION.split('.')[0]}.x"
        )

    # Imported lazily to avoid any import cycle at module load.
    from intuitiveness.navigation.tree import NavigationTree, NavigationTreeNode

    nodes_in = record["nodes"]
    meta = record.get("metadata", {})
    root_id = meta["root_id"]

    # Rebuild each node's dataset, then assemble the tree by id (shared ancestors
    # appear once in the map, so links naturally point at the same node).
    rebuilt: Dict[str, NavigationTreeNode] = {}
    for node_id, n in nodes_in.items():
        lineage = DataLineage()
        lineage.operations = [SourceReference.from_dict(r) for r in n.get("lineage", [])]
        ds = _rebuild_dataset(n["level"], n["payload_kind"], n["payload"], lineage)
        rebuilt[node_id] = NavigationTreeNode(
            id=node_id,
            level=ComplexityLevel(n["level"]),
            dataset_snapshot=ds,
            parent_id=n["parent_id"],
            children_ids=list(n["children_ids"]),
            edge_decision=dict(n.get("edge_decision", {})),
        )

    # Build a tree shell on the root dataset, then install the rebuilt nodes.
    tree = NavigationTree(rebuilt[root_id].dataset_snapshot)
    tree._nodes = rebuilt
    tree._root_id = root_id
    tree._current_id = meta.get("current_id", root_id)
    return tree
