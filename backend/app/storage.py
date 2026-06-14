"""Hybrid PostgreSQL + Memgraph storage for session data (spec 017).

When ``USE_DB_STORAGE=1`` is set, heavy operations offload to the databases:
  - DataFrames stored column-wise in PostgreSQL (``session_dataframes``)
  - Graph structures stored in Memgraph via Cypher
  - SQL JOINs replace pandas merge for L4->L3 entity matching
  - NavigationTree nodes persisted in PostgreSQL (``session_tree_nodes``)

Toggle: ``USE_DB_STORAGE`` env var (default off). When off, the existing
in-memory + durable-backend path is unchanged.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

import networkx as nx
import pandas as pd

from intuitiveness.neo4j_client import Neo4jClient, get_graph_db_credentials

logger = logging.getLogger(__name__)


def is_db_storage_enabled() -> bool:
    """Check whether hybrid DB storage is toggled on."""
    return os.getenv("USE_DB_STORAGE", "").strip() in ("1", "true", "yes")


# --------------------------------------------------------------------------- #
# SQL DDL
# --------------------------------------------------------------------------- #

_CREATE_DATAFRAMES_TABLE = """
CREATE TABLE IF NOT EXISTS session_dataframes (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id     TEXT NOT NULL,
    node_id        TEXT NOT NULL,
    level          INTEGER NOT NULL,
    table_name     TEXT NOT NULL DEFAULT '',
    data           JSONB NOT NULL,
    row_count      INTEGER NOT NULL DEFAULT 0,
    col_count      INTEGER NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (session_id, node_id, table_name)
);
CREATE INDEX IF NOT EXISTS idx_sdf_session ON session_dataframes (session_id);
"""

_CREATE_TREE_TABLE = """
CREATE TABLE IF NOT EXISTS session_tree_nodes (
    node_id        TEXT NOT NULL,
    session_id     TEXT NOT NULL,
    parent_id      TEXT,
    level          INTEGER NOT NULL,
    action         TEXT,
    params         JSONB,
    decision_desc  TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, node_id)
);
CREATE INDEX IF NOT EXISTS idx_stn_session ON session_tree_nodes (session_id);
"""


# --------------------------------------------------------------------------- #
# Postgres helpers
# --------------------------------------------------------------------------- #

def _get_pg_driver():
    """Import psycopg3 or psycopg2; return (connect_func, Json_class) or raise."""
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
        raise RuntimeError("No PostgreSQL driver found. Install psycopg2-binary or psycopg.")


# --------------------------------------------------------------------------- #
# DatabaseStorage
# --------------------------------------------------------------------------- #

class DatabaseStorage:
    """Hybrid PostgreSQL + Memgraph storage for session data.

    Designed to sit alongside the existing durable backend (which stores the
    full navigation tree as a single JSONB blob). This class handles the
    *granular* storage that enables:
      - SQL joins instead of pandas merges
      - Graph queries in Memgraph instead of NetworkX
      - Per-node DataFrame retrieval without loading the whole session
    """

    def __init__(self, pg_url: str, memgraph_url: Optional[str] = None):
        connect, self._Json = _get_pg_driver()
        self._pg_url = pg_url
        self._connect = connect
        self._memgraph_client: Optional[Neo4jClient] = None

        # Memgraph (optional — graph storage degrades to no-op if unavailable)
        if memgraph_url:
            try:
                creds = get_graph_db_credentials()
                self._memgraph_client = Neo4jClient(
                    uri=memgraph_url,
                    user=creds.get("user"),
                    password=creds.get("password"),
                )
                self._memgraph_client.connect()
                logger.info("DatabaseStorage: Memgraph connected at %s", memgraph_url)
            except Exception as exc:
                logger.warning("DatabaseStorage: Memgraph unavailable (%s); graph storage disabled.", exc)
                self._memgraph_client = None

        self._ensure_tables()

    # -- connection helpers ------------------------------------------------- #

    def _conn(self):
        return self._connect(self._pg_url)

    def _ensure_tables(self) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(_CREATE_DATAFRAMES_TABLE)
                cur.execute(_CREATE_TREE_TABLE)
            conn.commit()
        logger.info("DatabaseStorage: PostgreSQL tables ensured.")

    # ------------------------------------------------------------------ #
    # DataFrame storage (PostgreSQL)
    # ------------------------------------------------------------------ #

    def store_dataframe(
        self,
        session_id: str,
        node_id: str,
        level: int,
        df: pd.DataFrame,
        table_name: str = "",
    ) -> None:
        """Persist a DataFrame schema + 100-row sample in PostgreSQL.

        Only the schema and first 100 rows are stored — enough for LLM
        analysis, previews, and schema inference. Full data lives in the
        session blob for the duration of the request.
        """
        sample = df.head(100)
        records = json.loads(sample.to_json(orient="records", date_format="iso"))
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO session_dataframes
                        (session_id, node_id, level, table_name, data, row_count, col_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (session_id, node_id, table_name) DO UPDATE SET
                        level = EXCLUDED.level,
                        data = EXCLUDED.data,
                        row_count = EXCLUDED.row_count,
                        col_count = EXCLUDED.col_count,
                        created_at = now()
                    """,
                    (
                        session_id, node_id, level, table_name,
                        self._Json(records),
                        len(df), len(df.columns),
                    ),
                )
            conn.commit()

    def load_dataframe(self, session_id: str, node_id: str, table_name: str = "") -> pd.DataFrame:
        """Retrieve a stored DataFrame from PostgreSQL."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT data FROM session_dataframes "
                    "WHERE session_id = %s AND node_id = %s AND table_name = %s",
                    (session_id, node_id, table_name),
                )
                row = cur.fetchone()
        if row is None:
            raise FileNotFoundError(
                f"No dataframe for session={session_id}, node={node_id}, table={table_name}"
            )
        data = row[0] if isinstance(row[0], list) else json.loads(row[0])
        return pd.DataFrame(data)

    # ------------------------------------------------------------------ #
    # SQL join (replaces pandas merge)
    # ------------------------------------------------------------------ #

    def join_sources(
        self,
        session_id: str,
        left_node: str,
        right_node: str,
        join_keys: List[str],
        join_type: str = "inner",
        left_table: str = "",
        right_table: str = "",
    ) -> pd.DataFrame:
        """Join two stored DataFrames using PostgreSQL instead of pandas.

        This pushes the join down to the database, which is more efficient for
        large tables and avoids loading both frames into Python memory.
        """
        valid_types = {"inner", "left", "right", "full"}
        if join_type not in valid_types:
            raise ValueError(f"join_type must be one of {valid_types}")

        with self._conn() as conn:
            with conn.cursor() as cur:
                # Create temp tables, load the JSONB rows, then join in SQL.
                cur.execute("""
                    WITH left_data AS (
                        SELECT jsonb_array_elements(data) AS row
                        FROM session_dataframes
                        WHERE session_id = %s AND node_id = %s AND table_name = %s
                    ),
                    right_data AS (
                        SELECT jsonb_array_elements(data) AS row
                        FROM session_dataframes
                        WHERE session_id = %s AND node_id = %s AND table_name = %s
                    )
                    SELECT l.row || r.row AS merged
                    FROM left_data l
                    """ + join_type.upper() + """ JOIN right_data r
                    ON """ + " AND ".join(
                        f"l.row->>'{k}' = r.row->>'{k}'" for k in join_keys
                    ),
                    (session_id, left_node, left_table,
                     session_id, right_node, right_table),
                )
                rows = cur.fetchall()

        if not rows:
            return pd.DataFrame()

        merged_records = [
            r[0] if isinstance(r[0], dict) else json.loads(r[0])
            for r in rows
        ]
        return pd.DataFrame(merged_records)

    # ------------------------------------------------------------------ #
    # Graph storage (Memgraph)
    # ------------------------------------------------------------------ #

    def store_graph(self, session_id: str, node_id: str, graph: nx.Graph) -> None:
        """Store a NetworkX graph in Memgraph, tagged by session_id + node_id."""
        node_count = graph.number_of_nodes() if hasattr(graph, 'number_of_nodes') else 0
        if node_count > 100:
            logger.warning("Graph too large for Memgraph schema store (%d nodes, max 100), skipping.", node_count)
            return
        if self._memgraph_client is None or not self._memgraph_client.is_connected:
            logger.debug("Memgraph not available; skipping graph storage.")
            return
        try:
            self._memgraph_client.write_cypher("RETURN 1", {})
        except Exception as e:
            logger.warning("Memgraph auth/connectivity check failed, skipping graph storage: %s", e)
            return

        # Clear any previous graph for this session+node
        self._memgraph_client.write_cypher(
            "MATCH (n {session_id: $sid, node_id: $nid}) DETACH DELETE n",
            {"sid": session_id, "nid": node_id},
        )

        # Store nodes
        for n, attrs in graph.nodes(data=True):
            props = {k: _cypher_safe(v) for k, v in attrs.items()}
            props["_graph_node_key"] = str(n)
            props["session_id"] = session_id
            props["node_id"] = node_id
            label = props.pop("node_type", "Entity")
            self._memgraph_client.write_cypher(
                f"CREATE (n:`{label}` $props)",
                {"props": props},
            )

        # Store edges
        for u, v, attrs in graph.edges(data=True):
            props = {k: _cypher_safe(val) for k, val in attrs.items()}
            rel_type = props.pop("relationship", props.pop("type", "RELATES_TO"))
            self._memgraph_client.write_cypher(
                f"""
                MATCH (a {{session_id: $sid, node_id: $nid, _graph_node_key: $u}})
                MATCH (b {{session_id: $sid, node_id: $nid, _graph_node_key: $v}})
                CREATE (a)-[:`{rel_type}` $props]->(b)
                """,
                {"sid": session_id, "nid": node_id, "u": str(u), "v": str(v), "props": props},
            )

    def load_graph(self, session_id: str, node_id: str) -> nx.Graph:
        """Reconstruct a NetworkX graph from Memgraph."""
        if self._memgraph_client is None or not self._memgraph_client.is_connected:
            raise RuntimeError("Memgraph not available; cannot load graph.")

        g = nx.DiGraph()

        # Load nodes
        result = self._memgraph_client.run_cypher(
            "MATCH (n {session_id: $sid, node_id: $nid}) "
            "RETURN n, labels(n) AS labels",
            {"sid": session_id, "nid": node_id},
        )
        if result.success and result.data:
            for record in result.data:
                node_props = dict(record["n"])
                key = node_props.pop("_graph_node_key", str(uuid.uuid4()))
                node_props.pop("session_id", None)
                node_props.pop("node_id", None)
                labels = record.get("labels", [])
                if labels:
                    node_props["node_type"] = labels[0]
                g.add_node(key, **node_props)

        # Load edges
        result = self._memgraph_client.run_cypher(
            "MATCH (a {session_id: $sid, node_id: $nid})"
            "-[r]->"
            "(b {session_id: $sid, node_id: $nid}) "
            "RETURN a._graph_node_key AS u, b._graph_node_key AS v, "
            "type(r) AS rel_type, properties(r) AS props",
            {"sid": session_id, "nid": node_id},
        )
        if result.success and result.data:
            for record in result.data:
                props = dict(record.get("props", {}))
                props["relationship"] = record["rel_type"]
                g.add_edge(record["u"], record["v"], **props)

        return g

    # ------------------------------------------------------------------ #
    # Tree persistence (PostgreSQL)
    # ------------------------------------------------------------------ #

    def store_tree_node(
        self,
        session_id: str,
        node_id: str,
        parent_id: Optional[str],
        level: int,
        action: str,
        params: Optional[dict] = None,
        decision_desc: str = "",
    ) -> None:
        """Persist a single NavigationTree node."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO session_tree_nodes
                        (session_id, node_id, parent_id, level, action, params, decision_desc)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (session_id, node_id) DO UPDATE SET
                        parent_id = EXCLUDED.parent_id,
                        level = EXCLUDED.level,
                        action = EXCLUDED.action,
                        params = EXCLUDED.params,
                        decision_desc = EXCLUDED.decision_desc,
                        created_at = now()
                    """,
                    (
                        session_id, node_id, parent_id, level, action,
                        self._Json(params or {}), decision_desc,
                    ),
                )
            conn.commit()

    def load_tree(self, session_id: str) -> List[dict]:
        """Load all tree nodes for a session, ordered by creation time."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT node_id, parent_id, level, action, params, decision_desc, created_at "
                    "FROM session_tree_nodes "
                    "WHERE session_id = %s ORDER BY created_at",
                    (session_id,),
                )
                rows = cur.fetchall()
        return [
            {
                "node_id": r[0],
                "parent_id": r[1],
                "level": r[2],
                "action": r[3],
                "params": r[4] if isinstance(r[4], dict) else json.loads(r[4] or "{}"),
                "decision_desc": r[5],
                "created_at": str(r[6]),
            }
            for r in rows
        ]

    # ------------------------------------------------------------------ #
    # Cleanup
    # ------------------------------------------------------------------ #

    def delete_session(self, session_id: str) -> None:
        """Remove all stored data for a session from both databases."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM session_dataframes WHERE session_id = %s", (session_id,))
                cur.execute("DELETE FROM session_tree_nodes WHERE session_id = %s", (session_id,))
            conn.commit()

        if self._memgraph_client and self._memgraph_client.is_connected:
            self._memgraph_client.write_cypher(
                "MATCH (n {session_id: $sid}) DETACH DELETE n",
                {"sid": session_id},
            )

    # ------------------------------------------------------------------ #
    # Introspection
    # ------------------------------------------------------------------ #

    def list_dataframes(self, session_id: str) -> List[dict]:
        """List stored dataframes for a session (metadata only)."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT node_id, level, table_name, row_count, col_count, created_at "
                    "FROM session_dataframes WHERE session_id = %s ORDER BY created_at",
                    (session_id,),
                )
                return [
                    {
                        "node_id": r[0], "level": r[1], "table_name": r[2],
                        "row_count": r[3], "col_count": r[4], "created_at": str(r[5]),
                    }
                    for r in cur.fetchall()
                ]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _cypher_safe(value: Any) -> Any:
    """Coerce a Python value to something Cypher can store as a property."""
    if value is None:
        return ""
    if isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


# --------------------------------------------------------------------------- #
# Singleton factory
# --------------------------------------------------------------------------- #

_instance: Optional[DatabaseStorage] = None


def get_database_storage() -> Optional[DatabaseStorage]:
    """Return the DatabaseStorage singleton, or None if not enabled.

    Only constructs the instance on first call (lazy). Returns None when
    ``USE_DB_STORAGE`` is not set, so callers can fall through to the
    existing in-memory path.
    """
    global _instance
    if not is_db_storage_enabled():
        return None
    if _instance is not None:
        return _instance

    from intuitiveness.persistence.durable_backend import get_database_url
    pg_url = get_database_url()
    if not pg_url:
        logger.warning("USE_DB_STORAGE=1 but no DATABASE_URL set; disabling DB storage.")
        return None

    creds = get_graph_db_credentials()
    memgraph_url = creds.get("uri")

    try:
        _instance = DatabaseStorage(pg_url, memgraph_url)
        return _instance
    except Exception as exc:
        logger.error("Failed to initialize DatabaseStorage: %s", exc)
        return None
