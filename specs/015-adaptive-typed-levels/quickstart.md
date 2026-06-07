# Quickstart: Adaptive Typed Levels & Unified Redesign Engine

End-to-end walkthrough of the target behavior. Doubles as the acceptance script for the E2E regression (SC-011) and the new branch/export scenario.

## 1. Self-describing artifacts at every level (US1)

```python
from intuitiveness.complexity import Level4Dataset, ComplexityLevel
from intuitiveness.navigation.session import NavigationSession
from intuitiveness.redesign.params import L4toL3Params, L3toL2Params, L2toL1Params, L1toL0Params

session = NavigationSession(Level4Dataset({"scores.csv": df_scores, "schools.csv": df_schools}))

session.descend(L4toL3Params(model=data_model))     # L4→L3
session.descend(L3toL2Params(domains=["country side", "down town"]))  # L3→L2

art = session.current_dataset
assert art.complexity_level == ComplexityLevel.LEVEL_2
print(art.summary())                 # {level:2, level_name:'LEVEL_2', type:'dataframe', row_count:.., columns:[...]}
for step in art.lineage.get_history():
    print(step["operation_type"], step["parameters"])   # L4→L3, L3→L2 — full chain from raw origin
```

**Expected**: `summary()` returns the table shape with no external type-switch; `lineage` lists every step back to the raw files (FR-001/FR-003, SC-001/SC-002).

## 2. Descend to the atomic metric (US1, constitution II)

```python
session.descend(L2toL1Params(column="score"))       # L2→L1
session.descend(L1toL0Params(aggregation="mean"))   # L1→L0
print(session.current_dataset.summary())            # {level:0, type:'datum', value: <avg score>}
```

## 3. Branch + time-travel safely (US2)

```python
# Time-travel back to the L2 decision point, then take a DIFFERENT domain split → sibling branch
l2_node_id = [n.id for n in session._tree.nodes_at_level(ComplexityLevel.LEVEL_2)][0]
before = session._tree.restore(l2_node_id)
before_hist = list(before.lineage.get_history())     # snapshot for equality check

session.branch_from(l2_node_id, L3toL2Params(domains=["urban", "rural"]))  # sibling trajectory

after = session._tree.restore(l2_node_id)
assert list(after.lineage.get_history()) == before_hist   # ORIGINAL unchanged (SC-005)
assert len(session._tree.branches()) == 2                 # two coherent trajectories
```

**Expected**: the original branch's artifact + history are byte-for-byte unchanged after branching (FR-013, SC-005); branching needed no flag to enable (SC-006).

## 4. Compare trajectories (US2 / SC-012)

```python
a, b = (br[-1].id for br in session._tree.branches())
print(session._tree.divergence_point(a, b).id)   # the L2 node where they split
```

## 5. Export as a self-contained, versioned record (US3)

```python
record = session.save()             # full-fidelity SessionExportRecord
assert record["schema_version"]
# shared ancestors stored once:
assert len(record["nodes"]) == number_of_unique_nodes  # no per-branch duplication (SC-009)
```

## 6. Consume the export WITHOUT importing intuitiveness (US3 / SC-008)

A downstream service (e.g. synthetic generation) reads the record using only the documented decode rules — no package import:

```python
import json, base64, zlib, io, pandas as pd, networkx as nx

rec = json.load(open("session.json"))
assert rec["schema_version"].startswith("1.")     # fail-closed on unknown major

for node_id, node in rec["nodes"].items():
    kind = node["payload_kind"]
    if kind == "dataframe":
        raw = zlib.decompress(base64.b64decode(node["payload"]))
        data = pd.read_csv(io.BytesIO(raw))
    elif kind == "graph":
        data = nx.node_link_graph(json.loads(node["payload"]))
    elif kind == "value":
        data = node["payload"]
    # ... full lineage available at node["lineage"], decision at node["edge_decision"]
```

**Expected**: every node's payload + lineage reconstructable from the record alone (FR-024/FR-025, SC-007/SC-008).

## 7. localStorage holds only the index (US3 / SC-010)

```python
# Browser index entry is a pointer, not payloads:
# { "id": "...", "title": "School Scores redesign", "backend_location": "blob://sessions/abc.json" }
```

**Expected**: index stays within ≈5 MB irrespective of session size; full payloads live in the durable backend (FR-027/SC-010).

---

## Regression checklist (run before merge)

- [ ] All three reference datasets complete full descent→ascent via the new engine (SC-011).
- [ ] `grep -rn "LevelNDataset(" intuitiveness/ | grep -v redesign/engine.py` → **no matches** (SC-003).
- [ ] No `AscentOperation`, `NavigationHistory`, `use_tree`, or `redesign_legacy` references remain (R2/R6/R9).
- [ ] Export→reload round-trips tables, graphs, vectors, scalars with full fidelity (SC-007).
- [ ] Playwright UI E2E (`tests/e2e/`) green (no user-facing regression).
