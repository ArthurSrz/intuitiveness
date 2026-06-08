# Contract: Redesigner Engine API

The single transition chokepoint (`redesign/engine.py`). Sole constructor of level artifacts; sole lineage-stamper. Stateless. Realizes FR-007..FR-014, FR-016.

## Public surface

```text
class Redesigner:
    # Descent (L4→L3→L2→L1→L0)
    reduce_complexity(dataset: Dataset, target_level: ComplexityLevel, params: TransitionParams) -> Dataset

    # Ascent (L0→L1→L2→L3)
    increase_complexity(dataset: Dataset, target_level: ComplexityLevel, params: TransitionParams) -> Dataset
```

`params` is the typed dataclass matching the (current_level → target_level) edge. No `**kwargs`. No injected callables.

## Typed params (`redesign/params.py`)

| Edge | Param dataclass | Fields |
|------|-----------------|--------|
| L4→L3 | `L4toL3Params` | `model` (graph-build spec / data model) |
| L3→L2 | `L3toL2Params` | `domains: list[str]` |
| L2→L1 | `L2toL1Params` | `column: str`, `filter_query: str \| None = None` |
| L1→L0 | `L1toL0Params` | `aggregation: str` |
| L0→L1 | `L0toL1Params` | `enrichment_function: str`, … |
| L1→L2 | `L1toL2Params` | `dimensions: list[str]` |
| L2→L3 | `L2toL3Params` | dimension/link spec |

## Behavioral guarantees (test these)

| ID | Guarantee | Maps to |
|----|-----------|---------|
| RD-1 | Returns a NEW `Dataset` of `target_level`; never mutates input. | FR-008, R1 |
| RD-2 | Output `.lineage` == deepcopy(input `.lineage`) + exactly one appended `SourceReference`. | FR-012 |
| RD-3 | Output lineage is independent: mutating input afterward does not change output (and vice-versa). | FR-013 |
| RD-4 | Rejects non-adjacent transitions with a clear adjacency error. | FR-014 |
| RD-5 | No method exists whose target is L4 on ascent (structurally unreachable). | FR-014 |
| RD-6 | Ascent rejects any step where `row_count_after != row_count_before`. | FR-014 |
| RD-7 | Calls the payload-pure transform in `descent/`/`ascent/`; engine itself contains NO transform logic, only wrap+stamp+validate. | FR-010, R4 |
| RD-8 | Engine is the ONLY code in the package constructing a `LevelNDataset(...)`. | FR-008, SC-003 |
| RD-9 | Same inputs from guided workflow vs direct call produce indistinguishable artifact+lineage. | US5, SC |

## Error modes

- `ValueError` on non-adjacent levels (RD-4).
- `ValueError` on ascent row-count violation (RD-6).
- `TypeError`/validation error on mismatched `params` type for the edge.
