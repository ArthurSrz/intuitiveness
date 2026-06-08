# Contract: Dataset Base API (symmetric, self-describing)

Realizes FR-001, FR-002, FR-003. All five level classes share this surface.

```text
class Dataset(ABC):
    complexity_level: ComplexityLevel        # property (unchanged)
    get_data() -> Any                        # payload accessor (unchanged)
    lineage: DataLineage                     # NEW — full denormalized history, raw origin → self
    summary() -> dict                        # NEW — polymorphic self-description
```

## Behavioral guarantees

| ID | Guarantee | Maps to |
|----|-----------|---------|
| DS-1 | Every level (L0..L4) exposes `lineage` with identical shape; no level lacks it. | FR-001, FR-002, SC-001 |
| DS-2 | `lineage.get_history()` lists every step from raw origin to this artifact. | FR-001 |
| DS-3 | `summary()` returns correct level-appropriate keys (see data-model §1) and always includes `level`+`level_name`. | FR-003, SC-002 |
| DS-4 | No external component switches on `complexity_level` to summarize — callers use `summary()`. | FR-003, SC-002, R5 |
| DS-5 | Instances are immutable post-construction (only the Redesigner produces new ones). | R1 |
| DS-6 | `Level0Dataset.parent_data`/`aggregation_method` removed; last `SourceReference` in `lineage` carries that info. | data-model §1 |

## `summary()` per level (return keys)

| Level | Keys (besides `level`, `level_name`) |
|-------|--------------------------------------|
| L4 | `type:"unlinkable"`, `source_count` |
| L3 | `type:"graph"`, (`node_count`,`edge_count`) or `row_count` |
| L2 | `type:"dataframe"`, `row_count`, `columns` |
| L1 | `type:"vector"`, `length` |
| L0 | `type:"datum"`, `value` |
