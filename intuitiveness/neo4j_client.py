"""
Neo4j Client Module - Direct Python Driver Connection

Provides a simple client for Neo4j operations using the official Python driver.
This is a simplified alternative to the MCP subprocess approach.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

try:
    from neo4j import GraphDatabase
    from neo4j.exceptions import ServiceUnavailable, AuthError
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("[Neo4j Client] Warning: neo4j package not installed. Run: pip install neo4j")


@dataclass
class Neo4jResult:
    """Result from a Neo4j operation."""
    success: bool
    data: Any
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error
        }


def get_graph_db_credentials() -> Dict[str, Optional[str]]:
    """Read graph-database (Memgraph/Neo4j, Bolt-compatible) connection details.

    Resolution order, per key: Streamlit ``st.secrets`` first, then environment
    variables. Looks up ``MEMGRAPH_*`` names first, then ``NEO4J_*`` aliases for
    backward compatibility. There are NO hardcoded host or password defaults —
    a missing value resolves to ``None`` so an unconfigured deployment fails
    gracefully (the graph feature is optional) and no secrets live in source.

    Returns a dict with keys: uri, user, password, database (any may be None).
    """
    import os

    def _lookup(*names):
        try:
            import streamlit as st
            for n in names:
                try:
                    if n in st.secrets:
                        return st.secrets[n]
                except Exception:
                    pass
        except Exception:
            pass
        for n in names:
            v = os.getenv(n)
            if v:
                return v
        return None

    return {
        "uri": _lookup("MEMGRAPH_URI", "NEO4J_URI"),
        "user": _lookup("MEMGRAPH_USER", "NEO4J_USER"),
        "password": _lookup("MEMGRAPH_PASSWORD", "NEO4J_PASSWORD"),
        "database": _lookup("MEMGRAPH_DATABASE", "NEO4J_DATABASE"),
    }


class Neo4jClient:
    """
    Bolt-protocol graph-database client (Memgraph or Neo4j) using the official
    neo4j Python driver.

    Connection details come from secrets/env via ``get_graph_db_credentials()``
    (keys ``MEMGRAPH_URI``/``MEMGRAPH_USER``/``MEMGRAPH_PASSWORD``/
    ``MEMGRAPH_DATABASE``); no credentials are hardcoded.

    Usage:
        client = Neo4jClient()  # reads MEMGRAPH_* from st.secrets / env

        # Connect
        client.connect()

        # Get schema
        schema = client.get_schema()

        # Run queries
        result = client.run_cypher("MATCH (n:Indicator) RETURN n LIMIT 5")

        # Close connection
        client.close()
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None
    ):
        """
        Initialize the graph-database client.

        Any argument left as None is read from secrets/env via
        ``get_graph_db_credentials()``. No connection details are hardcoded.

        Args:
            uri: Bolt connection URI (e.g. bolt+s://host:port). None → secrets/env.
            user: username. None → secrets/env (may be empty for no-auth Memgraph).
            password: password. None → secrets/env.
            database: database name. None → secrets/env, then "memgraph".
        """
        if not NEO4J_AVAILABLE:
            raise ImportError("Neo4j package not available. Install with: pip install neo4j")

        creds = get_graph_db_credentials()
        self._uri = uri if uri is not None else creds["uri"]
        self._user = user if user is not None else creds["user"]
        self._password = password if password is not None else creds["password"]
        self._database = database or creds["database"] or "memgraph"
        self._driver = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected and self._driver is not None

    def connect(self) -> bool:
        """
        Establish connection to Neo4j.

        Returns:
            True if connection successful
        """
        if not self._uri:
            print("[Graph DB Client] No connection URI configured "
                  "(set MEMGRAPH_URI in st.secrets or env). Skipping connection.")
            self._connected = False
            return False
        try:
            print(f"[Graph DB Client] Connecting to {self._uri}...")
            print(f"[Graph DB Client] Database: {self._database}")

            # Memgraph may run without auth — pass auth=None when no user is set.
            auth = (self._user, self._password) if self._user else None
            self._driver = GraphDatabase.driver(self._uri, auth=auth)

            # Verify connection
            self._driver.verify_connectivity()
            self._connected = True

            print(f"[Neo4j Client] Connected successfully!")
            return True

        except ServiceUnavailable as e:
            print(f"[Neo4j Client] Connection failed - service unavailable: {e}")
            self._connected = False
            return False

        except AuthError as e:
            print(f"[Neo4j Client] Connection failed - auth error: {e}")
            self._connected = False
            return False

        except Exception as e:
            print(f"[Neo4j Client] Connection failed: {e}")
            self._connected = False
            return False

    def close(self):
        """Close the connection."""
        if self._driver:
            self._driver.close()
            self._driver = None
        self._connected = False
        print("[Neo4j Client] Connection closed")

    def get_schema(self) -> Neo4jResult:
        """
        Get database schema (labels and relationship types).

        Returns:
            Neo4jResult with schema information
        """
        if not self.is_connected:
            return Neo4jResult(
                success=False,
                data=None,
                error="Not connected. Call connect() first."
            )

        try:
            with self._driver.session(database=self._database) as session:
                # Get node labels
                labels_result = session.run("CALL db.labels()").data()
                labels = [r['label'] for r in labels_result]

                # Get relationship types
                rels_result = session.run("CALL db.relationshipTypes()").data()
                relationships = [r['relationshipType'] for r in rels_result]

                # Get node counts per label
                node_counts = {}
                for label in labels:
                    count_result = session.run(
                        f"MATCH (n:`{label}`) RETURN count(n) as count"
                    ).single()
                    node_counts[label] = count_result['count'] if count_result else 0

                schema = {
                    "labels": labels,
                    "relationships": relationships,
                    "node_counts": node_counts
                }

                print(f"[Neo4j Client] Schema retrieved: {len(labels)} labels, {len(relationships)} relationship types")
                return Neo4jResult(success=True, data=schema)

        except Exception as e:
            error_msg = str(e)
            print(f"[Neo4j Client] Get schema error: {error_msg}")
            return Neo4jResult(success=False, data=None, error=error_msg)

    def run_cypher(self, query: str, params: Dict = None) -> Neo4jResult:
        """
        Execute a Cypher query.

        Args:
            query: Cypher query string
            params: Query parameters

        Returns:
            Neo4jResult with query results
        """
        if not self.is_connected:
            return Neo4jResult(
                success=False,
                data=None,
                error="Not connected. Call connect() first."
            )

        try:
            print(f"[Neo4j Client] Executing query: {query[:100]}...")

            with self._driver.session(database=self._database) as session:
                result = session.run(query, params or {})
                data = result.data()

                print(f"[Neo4j Client] Query returned {len(data)} records")
                return Neo4jResult(success=True, data=data)

        except Exception as e:
            error_msg = str(e)
            print(f"[Neo4j Client] Query error: {error_msg}")
            return Neo4jResult(success=False, data=None, error=error_msg)

    def write_cypher(self, query: str, params: Dict = None) -> Neo4jResult:
        """
        Execute a write Cypher query.

        Args:
            query: Cypher query string
            params: Query parameters

        Returns:
            Neo4jResult with execution summary
        """
        if not self.is_connected:
            return Neo4jResult(
                success=False,
                data=None,
                error="Not connected. Call connect() first."
            )

        try:
            print(f"[Neo4j Client] Executing write query: {query[:100]}...")

            with self._driver.session(database=self._database) as session:
                result = session.run(query, params or {})
                summary = result.consume()

                data = {
                    "nodes_created": summary.counters.nodes_created,
                    "nodes_deleted": summary.counters.nodes_deleted,
                    "relationships_created": summary.counters.relationships_created,
                    "relationships_deleted": summary.counters.relationships_deleted,
                    "properties_set": summary.counters.properties_set
                }

                print(f"[Neo4j Client] Write completed: {data}")
                return Neo4jResult(success=True, data=data)

        except Exception as e:
            error_msg = str(e)
            print(f"[Neo4j Client] Write error: {error_msg}")
            return Neo4jResult(success=False, data=None, error=error_msg)

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Convenience function for testing
def test_neo4j_connection():
    """Test Neo4j connection."""
    with Neo4jClient() as client:
        print("\n--- Testing get_schema ---")
        schema = client.get_schema()
        print(f"Schema: {schema.data}")

        print("\n--- Testing run_cypher ---")
        result = client.run_cypher(
            "MATCH (n) RETURN labels(n) as labels, count(*) as count LIMIT 5"
        )
        print(f"Result: {result.data}")


if __name__ == "__main__":
    test_neo4j_connection()
