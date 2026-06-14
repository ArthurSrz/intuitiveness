"""PostgreSQL primary backend — normalized storage for sessions, tree nodes, and payloads.

Replaces the single JSONB blob with 3 tables:
  - sessions: metadata (id, title, root_id, current_id, state, schema_version)
  - tree_nodes: navigation tree structure (one row per node)
  - node_payloads: dataset payloads per node (kind + encoded data)

Graph payloads (L3) are stored in Memgraph when available, with a
PostgreSQL fallback for the encoded payload.

This backend implements the same interface as FileDurableBackend /
PostgresDurableBackend — it accepts the export_session record format
on save and returns it on load, so service.py doesn't need to change.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# DDL — the 3 normalized tables
# --------------------------------------------------------------------------- #

_CREATE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id       TEXT PRIMARY KEY,
    title            TEXT NOT NULL DEFAULT '',
    root_id          TEXT NOT NULL,
    current_id       TEXT NOT NULL,
    state            TEXT NOT NULL DEFAULT 'exploring',
    schema_version   TEXT NOT NULL DEFAULT '1.1.0',
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

_CREATE_TREE_NODES = """
CREATE TABLE IF NOT EXISTS tree_nodes (
    session_id       TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    node_id          TEXT NOT NULL,
    parent_id        TEXT,
    children_ids     JSONB NOT NULL DEFAULT '[]',
    level            INTEGER NOT NULL,
    edge_decision    JSONB NOT NULL DEFAULT '{}',
    lineage          JSONB NOT NULL DEFAULT '[]',
    l0_parent        TEXT,
    l0_aggregation   TEXT,
    PRIMARY KEY (session_id, node_id)
);
"""

_CREATE_PAYLOADS = """
CREATE TABLE IF NOT EXISTS node_payloads (
    session_id       TEXT NOT NULL,
    node_id          TEXT NOT NULL,
    payload_kind     TEXT NOT NULL,
    payload          TEXT NOT NULL,
    PRIMARY KEY (session_id, node_id),
    FOREIGN KEY (session_id, node_id) REFERENCES tree_nodes(session_id, node_id) ON DELETE CASCADE
);
"""


def _cypher_safe(value: Any) -> Any:
    """Coerce a Python value to something Cypher can store as a property."""
    if value is None:
        return ""
    if isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _import_psycopg():
    try:
        import psycopg
        from psycopg.types.json import Json
        return psycopg.connect, Json
    except Exception:
        pass
    try:
        import psycopg2
        from psycopg2.extras import Json
        return psycopg2.connect, Json
    except Exception:
        return None


class PgPrimaryBackend:
    """Normalized PostgreSQL + Memgraph storage for sessions.

    Decomposes the export_session record into 3 PostgreSQL tables on save,
    recomposes it on load. L3 graph payloads are additionally stored in
    Memgraph as native nodes/edges for Cypher querying.
    """

    def __init__(self, database_url: str, memgraph_url: Optional[str] = None):
        driver = _import_psycopg()
        if driver is None:
            raise RuntimeError("PostgreSQL driver not installed (psycopg2-binary or psycopg).")
        self._connect, self._Json = driver
        self._database_url = database_url
        self._memgraph = None
        if memgraph_url:
            try:
                from intuitiveness.neo4j_client import Neo4jClient
                self._memgraph = Neo4jClient(uri=memgraph_url)
                self._memgraph.connect()
                logger.info("PgPrimaryBackend: Memgraph connected at %s", memgraph_url)
            except Exception as e:
                logger.warning("PgPrimaryBackend: Memgraph unavailable (%s), L3 graphs stored in PG only.", e)
                self._memgraph = None
        self._ensure_tables()

    def _conn(self):
        return self._connect(self._database_url)

    def _ensure_tables(self):
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(_CREATE_SESSIONS)
                cur.execute(_CREATE_TREE_NODES)
                # Drop and recreate node_payloads if payload column is JSONB (migration)
                cur.execute("""
                    SELECT data_type FROM information_schema.columns
                    WHERE table_name = 'node_payloads' AND column_name = 'payload'
                """)
                row = cur.fetchone()
                if row and row[0] == 'jsonb':
                    cur.execute("DROP TABLE IF EXISTS node_payloads")
                cur.execute(_CREATE_PAYLOADS)
            conn.commit()

    # ------------------------------------------------------------------ #
    # save_record: decompose the export dict into 3 tables
    # ------------------------------------------------------------------ #

    def save_record(self, session_id: str, record: Dict[str, Any]) -> str:
        """Decompose an export_session record into normalized tables."""
        meta = record.get("metadata", {})
        nodes = record.get("nodes", {})

        with self._conn() as conn:
            with conn.cursor() as cur:
                # 1. Upsert session metadata
                cur.execute("""
                    INSERT INTO sessions (session_id, title, root_id, current_id, state, schema_version, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (session_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        root_id = EXCLUDED.root_id,
                        current_id = EXCLUDED.current_id,
                        state = EXCLUDED.state,
                        schema_version = EXCLUDED.schema_version,
                        updated_at = now()
                """, (
                    session_id,
                    meta.get("title", session_id),
                    meta.get("root_id", ""),
                    meta.get("current_id", ""),
                    meta.get("state", "exploring"),
                    record.get("schema_version", "1.1.0"),
                ))

                # 2. Clear old nodes + payloads (cascade deletes payloads)
                cur.execute("DELETE FROM tree_nodes WHERE session_id = %s", (session_id,))

                # 3. Insert each node
                for node_id, node in nodes.items():
                    cur.execute("""
                        INSERT INTO tree_nodes
                            (session_id, node_id, parent_id, children_ids, level,
                             edge_decision, lineage, l0_parent, l0_aggregation)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        session_id,
                        node_id,
                        node.get("parent_id"),
                        self._Json(node.get("children_ids", [])),
                        node["level"],
                        self._Json(node.get("edge_decision", {})),
                        self._Json(node.get("lineage", [])),
                        node.get("l0_parent"),
                        node.get("l0_aggregation"),
                    ))

                    # 4. Insert payload separately (as JSON text — payloads can be
                    #    dicts, strings, or base64 blobs depending on payload_kind)
                    raw_payload = node.get("payload", {})
                    payload_text = json.dumps(raw_payload, default=str) if not isinstance(raw_payload, str) else raw_payload
                    cur.execute("""
                        INSERT INTO node_payloads (session_id, node_id, payload_kind, payload)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        session_id,
                        node_id,
                        node.get("payload_kind", "unknown"),
                        payload_text,
                    ))

            conn.commit()

        # 5. Store L3 graph payloads in Memgraph for native Cypher queries
        if self._memgraph:
            for node_id, node in nodes.items():
                if node.get("payload_kind") == "graph" and node.get("level") == 3:
                    self._store_graph_in_memgraph(session_id, node_id, node.get("payload", {}))

        return f"pg://{session_id}"

    # ------------------------------------------------------------------ #
    # load_record: recompose the export dict from 3 tables
    # TODO(human): implement this method
    # ------------------------------------------------------------------ #

    def load_record(self, session_id: str) -> Dict[str, Any]:
        """Recompose an export_session-compatible record from the normalized tables.

        Must return the same dict shape that export_session() produces:
        {
            "schema_version": "1.1.0",
            "metadata": {"root_id": ..., "current_id": ..., "title": ..., ...},
            "nodes": {
                "node-id-1": {
                    "id": ..., "level": ..., "parent_id": ..., "children_ids": [...],
                    "edge_decision": {...}, "lineage": [...],
                    "payload_kind": ..., "payload": ...,
                    "l0_parent": ... (optional), "l0_aggregation": ... (optional),
                },
                ...
            }
        }

        Steps:
          1. SELECT from sessions WHERE session_id = %s → metadata
          2. SELECT from tree_nodes WHERE session_id = %s → node structure
          3. SELECT from node_payloads WHERE session_id = %s → payloads
          4. JOIN nodes + payloads by node_id into the export format
          5. Return the recomposed record
        """
        with self._conn() as conn:
            with conn.cursor() as cur:
                # 1. Session metadata
                cur.execute("""
                    SELECT title, root_id, current_id, state, schema_version
                    FROM sessions WHERE session_id = %s
                """, (session_id,))
                row = cur.fetchone()
                if row is None:
                    raise FileNotFoundError(f"No session '{session_id}' in database.")
                title, root_id, current_id, state, schema_version = row

                # 2. Tree nodes
                cur.execute("""
                    SELECT node_id, parent_id, children_ids, level,
                           edge_decision, lineage, l0_parent, l0_aggregation
                    FROM tree_nodes WHERE session_id = %s
                """, (session_id,))
                node_rows = cur.fetchall()

                # 3. Payloads
                cur.execute("""
                    SELECT node_id, payload_kind, payload
                    FROM node_payloads WHERE session_id = %s
                """, (session_id,))
                payload_rows = cur.fetchall()

        # 4. Index payloads by node_id — deserialize TEXT back to original form
        payloads = {}
        for node_id, kind, payload_text in payload_rows:
            try:
                payload = json.loads(payload_text) if payload_text else {}
            except (json.JSONDecodeError, TypeError):
                payload = payload_text  # base64 strings stay as-is
            payloads[node_id] = (kind, payload)

        # 5. Assemble nodes dict
        nodes = {}
        for node_id, parent_id, children_ids, level, edge_decision, lineage, l0_parent, l0_aggregation in node_rows:
            entry = {
                "id": node_id,
                "level": level,
                "parent_id": parent_id,
                "children_ids": children_ids if isinstance(children_ids, list) else json.loads(children_ids),
                "edge_decision": edge_decision if isinstance(edge_decision, dict) else json.loads(edge_decision),
                "lineage": lineage if isinstance(lineage, list) else json.loads(lineage),
            }
            if node_id in payloads:
                entry["payload_kind"] = payloads[node_id][0]
                entry["payload"] = payloads[node_id][1]
            if l0_parent is not None:
                entry["l0_parent"] = l0_parent
            if l0_aggregation is not None:
                entry["l0_aggregation"] = l0_aggregation
            nodes[node_id] = entry

        return {
            "schema_version": schema_version,
            "metadata": {
                "session_id": session_id,
                "root_id": root_id,
                "current_id": current_id,
                "state": state,
                "title": title,
            },
            "nodes": nodes,
        }

    # ------------------------------------------------------------------ #
    # Memgraph: store and retrieve L3 graphs natively
    # ------------------------------------------------------------------ #

    def _store_graph_in_memgraph(self, session_id: str, node_id: str, serialized_payload) -> None:
        """Write a serialized graph payload to Memgraph as native nodes/edges."""
        if not self._memgraph:
            return
        try:
            from intuitiveness.persistence.serializers import deserialize_graph
            graph = deserialize_graph(serialized_payload)
        except Exception as e:
            logger.warning("Cannot deserialize graph for Memgraph storage: %s", e)
            return

        try:
            # Clear previous version
            self._memgraph.write_cypher(
                "MATCH (n {session_id: $sid, tree_node: $nid}) DETACH DELETE n",
                {"sid": session_id, "nid": node_id},
            )
            # Store each graph node
            for n, attrs in graph.nodes(data=True):
                props = {k: _cypher_safe(v) for k, v in attrs.items()}
                props["_key"] = str(n)
                props["session_id"] = session_id
                props["tree_node"] = node_id
                label = props.pop("node_type", "Entity")
                self._memgraph.write_cypher(
                    f"CREATE (n:`{label}` $props)", {"props": props},
                )
            # Store each edge
            for u, v, attrs in graph.edges(data=True):
                props = {k: _cypher_safe(val) for k, val in attrs.items()}
                rel_type = props.pop("relationship", props.pop("type", "RELATES_TO"))
                self._memgraph.write_cypher(
                    f"MATCH (a {{session_id: $sid, tree_node: $nid, _key: $u}}) "
                    f"MATCH (b {{session_id: $sid, tree_node: $nid, _key: $v}}) "
                    f"CREATE (a)-[:`{rel_type}` $props]->(b)",
                    {"sid": session_id, "nid": node_id, "u": str(u), "v": str(v), "props": props},
                )
            logger.info("Memgraph: stored L3 graph (%d nodes, %d edges) for %s/%s",
                        graph.number_of_nodes(), graph.number_of_edges(), session_id, node_id)
        except Exception as e:
            logger.warning("Memgraph write failed (non-fatal): %s", e)

    def query_graph(self, session_id: str, node_id: str, cypher: str, params: Optional[dict] = None) -> Any:
        """Run a Cypher query scoped to a specific session's L3 graph.

        The query runs against the Memgraph graph for the given session/node.
        Use this to query graph structure without loading it into memory.

        Example:
            backend.query_graph(sid, nid,
                "MATCH (n {session_id: $sid, tree_node: $nid}) RETURN count(n) AS total",
                {"sid": sid, "nid": nid})
        """
        if not self._memgraph:
            raise RuntimeError("Memgraph is not configured.")
        full_params = {"sid": session_id, "nid": node_id}
        if params:
            full_params.update(params)
        return self._memgraph.run_cypher(cypher, full_params)

    # ------------------------------------------------------------------ #
    # Cleanup: also remove from Memgraph
    # ------------------------------------------------------------------ #

    def delete(self, session_id: str) -> bool:
        # Clean Memgraph first
        if self._memgraph:
            try:
                self._memgraph.write_cypher(
                    "MATCH (n {session_id: $sid}) DETACH DELETE n",
                    {"sid": session_id},
                )
            except Exception as e:
                logger.warning("Memgraph cleanup failed: %s", e)
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))
                deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    # ------------------------------------------------------------------ #
    # Other interface methods
    # ------------------------------------------------------------------ #

    def exists(self, session_id: str) -> bool:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM sessions WHERE session_id = %s", (session_id,))
                return cur.fetchone() is not None

    def list_session_ids(self) -> List[str]:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT session_id FROM sessions ORDER BY updated_at DESC")
                return [r[0] for r in cur.fetchall()]

    def list_sessions(self) -> List[Tuple[str, str]]:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT session_id, title FROM sessions ORDER BY updated_at DESC")
                return [(r[0], r[1]) for r in cur.fetchall()]
