"""SessionService — the stateless load → transition → save core (spec 017 R1).

No session state is held between calls. Each method:
  1. loads the session record from the durable store (Postgres on Railway, files
     locally — `get_durable_backend()`),
  2. rebuilds the `NavigationSession` tree (`import_session` + `_from_tree`),
  3. runs ONE engine transition / tree operation through the existing core,
  4. saves the updated tree back (`export_session` → store).

So restarting the backend mid-session loses nothing, and it scales horizontally.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from intuitiveness.navigation.session import NavigationSession
from intuitiveness.navigation.exceptions import NavigationError, SessionNotFoundError
from intuitiveness.persistence.durable_backend import get_durable_backend
from intuitiveness.persistence.session_export import export_session, import_session

from .builders import resolve_builder
from .demo import load_demo


def _json_safe(value: Any) -> Any:
    """Coerce numpy/pandas scalars to plain JSON-serializable values."""
    if hasattr(value, "item"):           # numpy scalar
        try:
            return value.item()
        except Exception:
            return str(value)
    return value


class SessionService:
    """Stateless façade over the navigation engine + durable store."""

    def __init__(self, backend=None):
        # Injected backend (tests pass a temp FileDurableBackend); else the
        # configured one (Postgres when DATABASE_URL is set, else files).
        self._backend = backend or get_durable_backend()

    # ------------------------------------------------------------------ #
    # Load / save (the stateless boundary)
    # ------------------------------------------------------------------ #
    def _load(self, session_id: str) -> NavigationSession:
        try:
            record = self._backend.load_record(session_id)
        except FileNotFoundError:
            raise SessionNotFoundError(f"Session '{session_id}' not found.")
        tree = import_session(record)
        return NavigationSession._from_tree(tree, record.get("metadata", {}))

    def _title_of(self, session: NavigationSession) -> str:
        root = session.navigation_tree.nodes[session.navigation_tree.root_id]
        data = root.dataset_snapshot.get_data()
        if isinstance(data, dict) and data:
            return next(iter(data.keys()))
        return session.session_id

    def _save(self, session: NavigationSession) -> None:
        record = export_session(session.navigation_tree, metadata={
            "session_id": session.session_id,
            "state": session.state.value,
            "title": self._title_of(session),
        })
        self._backend.save_record(session.session_id, record)

    # ------------------------------------------------------------------ #
    # State projection (what the API returns)
    # ------------------------------------------------------------------ #
    def state_of(self, session: NavigationSession) -> Dict[str, Any]:
        return {
            "session_id": session.session_id,
            "current_level": session.current_level.value,
            "current_node_id": session.navigation_tree.current_id,
            "summary": self._summary(session),
            "available_moves": session.get_available_moves(),
        }

    def _summary(self, session: NavigationSession) -> Dict[str, Any]:
        ds = session.current_dataset
        snapshot = ds.summary() if hasattr(ds, "summary") else {}
        snapshot = {k: _json_safe(v) for k, v in dict(snapshot).items()}
        # Surface the scalar at L0 explicitly for clients.
        if session.current_level.value == 0:
            snapshot["value"] = _json_safe(ds.get_data())
        return snapshot

    # ------------------------------------------------------------------ #
    # Session lifecycle
    # ------------------------------------------------------------------ #
    def create(self, source: str) -> Dict[str, Any]:
        l4 = load_demo(source)
        session = NavigationSession(l4)
        self._save(session)
        return self.state_of(session)

    def get(self, session_id: str) -> Dict[str, Any]:
        return self.state_of(self._load(session_id))

    def list_sessions(self) -> List[Dict[str, str]]:
        out = []
        for sid, title in self._backend.list_sessions():
            out.append({"session_id": sid, "title": title})
        return out

    def delete(self, session_id: str) -> bool:
        return self._backend.delete(session_id)

    # ------------------------------------------------------------------ #
    # Transitions (engine)
    # ------------------------------------------------------------------ #
    def descend(self, session_id: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        session = self._load(session_id)
        kwargs = dict(params or {})
        if session.current_level.value == 4:
            # L4→L3 needs a graph builder callable; default to rows_as_nodes.
            builder_name = kwargs.pop("builder", "rows_as_nodes")
            config = kwargs.pop("config", {}) or {}
            kwargs["builder_func"] = resolve_builder(builder_name, config)
        # L3→L2 (domains), L2→L1 (column/filter_query), L1→L0 (aggregation)
        # pass straight through to the session's param adapter.
        session.descend(**kwargs)
        self._save(session)
        return self.state_of(session)

    def ascend(self, session_id: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        session = self._load(session_id)
        session.ascend(**(params or {}))
        self._save(session)
        return self.state_of(session)

    # ------------------------------------------------------------------ #
    # Navigation tree (branching / time-travel) — spec 015
    # ------------------------------------------------------------------ #
    def tree(self, session_id: str) -> Dict[str, Any]:
        session = self._load(session_id)
        return session.navigation_tree.export_to_json()

    def time_travel(self, session_id: str, node_id: str) -> Dict[str, Any]:
        session = self._load(session_id)
        session.time_travel(node_id)
        self._save(session)
        return self.state_of(session)

    def branch_from(self, session_id: str, node_id: str, action: str,
                    params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        session = self._load(session_id)
        kwargs = dict(params or {})
        # If branching a descent off L4, resolve the builder like descend() does.
        if action == "descend":
            target_node = session.navigation_tree.nodes[node_id]
            if target_node.level.value == 4:
                builder_name = kwargs.pop("builder", "rows_as_nodes")
                kwargs["builder_func"] = resolve_builder(builder_name, kwargs.pop("config", {}) or {})
        session.branch_from(node_id, action=action, **kwargs)
        self._save(session)
        return self.state_of(session)

    def prune(self, session_id: str, node_id: str) -> int:
        session = self._load(session_id)
        removed = session.prune(node_id)
        self._save(session)
        return removed

    def archive(self, session_id: str, node_id: str) -> int:
        session = self._load(session_id)
        marked = session.archive(node_id)
        self._save(session)
        return marked

    # ------------------------------------------------------------------ #
    # Export / import (spec-015 cross-service contract)
    # ------------------------------------------------------------------ #
    def export(self, session_id: str) -> Dict[str, Any]:
        session = self._load(session_id)
        return export_session(session.navigation_tree, metadata={
            "session_id": session.session_id,
            "state": session.state.value,
            "title": self._title_of(session),
        })

    def import_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        tree = import_session(record)
        session = NavigationSession._from_tree(tree, record.get("metadata", {}))
        self._save(session)
        return self.state_of(session)
