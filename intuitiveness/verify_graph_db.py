"""Verify the hosted graph database (Memgraph/Neo4j) connection end-to-end.

Run once MEMGRAPH_* (or NEO4J_*) are set in st.secrets or the environment:

    python3 -m intuitiveness.verify_graph_db

Checks: credentials resolve → driver connects → RETURN 1 → create/count/delete a
temp node. Prints PASS/FAIL and exits non-zero on failure. Safe to re-run
(cleans up its temp node). The graph feature is optional, so a missing URI is
reported clearly rather than crashing.
"""

import sys

from intuitiveness.neo4j_client import Neo4jClient, get_graph_db_credentials


def main() -> int:
    creds = get_graph_db_credentials()
    if not creds.get("uri"):
        print("FAIL: no MEMGRAPH_URI / NEO4J_URI configured (st.secrets or env).")
        print("      See intuitiveness/MEMGRAPH_DEPLOYMENT.md to set it up.")
        return 1

    masked_user = creds.get("user") or "(no-auth)"
    print(f"Connecting to {creds['uri']} as {masked_user} (db={creds.get('database')})...")

    client = Neo4jClient()
    try:
        if not client.connect() or not client.is_connected:
            print("FAIL: could not establish a connection. Check URI scheme "
                  "(bolt:// vs bolt+s://), TCP proxy, and credentials.")
            return 1
        print("  ✓ connected")

        r = client.run_cypher("RETURN 1 AS ok")
        if not getattr(r, "success", False):
            print(f"FAIL: read query failed: {getattr(r, 'error', r)}")
            return 1
        print("  ✓ RETURN 1 round-tripped")

        # write → count → cleanup
        client.write_cypher("CREATE (:_HealthCheck {id: 'verify_graph_db'})")
        cnt = client.run_cypher("MATCH (n:_HealthCheck {id:'verify_graph_db'}) RETURN count(n) AS c")
        client.write_cypher("MATCH (n:_HealthCheck {id:'verify_graph_db'}) DELETE n")
        print(f"  ✓ write/count/delete ok ({getattr(cnt, 'data', '?')})")

        print("PASS: graph database is reachable and writable.")
        return 0
    except Exception as e:  # noqa: BLE001 - report any driver error clearly
        print(f"FAIL: {type(e).__name__}: {e}")
        return 1
    finally:
        try:
            client.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
