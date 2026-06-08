"""Verify the durable session store (PostgreSQL, e.g. Railway) end-to-end.

Run once SESSION_DATABASE_URL (or DATABASE_URL / POSTGRES_URL) is set in
st.secrets or the environment:

    python3 -m intuitiveness.verify_session_db

Checks: a URL is configured → driver imports → table ensured → save → load →
delete a temp record. Prints PASS/FAIL and exits non-zero on failure. Safe to
re-run (cleans up its temp record). The durable store is optional — when no URL
is set the app persists sessions to local files, so a missing URL is reported
clearly rather than crashing.
"""

import sys

from intuitiveness.persistence.durable_backend import (
    PostgresDurableBackend,
    get_database_url,
)


def main() -> int:
    url = get_database_url()
    if not url:
        print("FAIL: no SESSION_DATABASE_URL / DATABASE_URL / POSTGRES_URL configured.")
        print("      Without it, sessions persist to local files (~/.intuitiveness/sessions/).")
        return 1

    # Mask the password in the printed URL.
    masked = url
    if "@" in url and "//" in url:
        scheme, rest = url.split("//", 1)
        creds, host = rest.split("@", 1) if "@" in rest else ("", rest)
        if ":" in creds:
            user = creds.split(":", 1)[0]
            masked = f"{scheme}//{user}:***@{host}"
    print(f"Connecting to {masked} ...")

    try:
        backend = PostgresDurableBackend(url)  # ensures the table on construct
        print("  ✓ connected and session_records table ensured")

        probe_id = "_verify_session_db"
        record = {"schema_version": "1.0.0",
                  "metadata": {"title": "verify probe", "current_id": "x"},
                  "nodes": {}}
        backend.save_record(probe_id, record)
        print("  ✓ saved a probe record")

        loaded = backend.load_record(probe_id)
        if loaded.get("schema_version") != "1.0.0":
            print(f"FAIL: round-trip mismatch: {loaded!r}")
            return 1
        print("  ✓ loaded it back (round-trip ok)")

        backend.delete(probe_id)
        print("  ✓ deleted the probe record")

        print("PASS: durable session store is reachable and writable.")
        return 0
    except Exception as e:  # noqa: BLE001 - report any driver/DB error clearly
        print(f"FAIL: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
