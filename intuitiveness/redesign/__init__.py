"""
Redesign Package - Data Complexity Transitions

Implements Spec 001: Dataset Redesign Package
FR-013-015: Data Lineage Tracking
FR-018-024: Public API Refinement

This package handles transitions between complexity levels (L0-L4)
with comprehensive lineage tracking and provenance management.

Public API:
-----------
- Redesigner: Main interface for descent/ascent operations
- DataLineage: Transformation history tracking
- SourceReference: Operation provenance tracking

Example:
--------
>>> from intuitiveness.redesign import Redesigner, DataLineage
>>> from intuitiveness.complexity import Level4Dataset, ComplexityLevel
>>>
>>> # Create L4 dataset
>>> l4 = Level4Dataset({"file1": df1, "file2": df2})
>>>
>>> # Descend with lineage tracking
>>> redesigner = Redesigner()
>>> l3, lineage = redesigner.reduce_with_lineage(l4, ComplexityLevel.LEVEL_3)
>>>
>>> # Export lineage trace
>>> lineage.export("lineage_trace.json")
"""

from intuitiveness.redesign.lineage import DataLineage, SourceReference

# Spec 015: the unified Redesigner engine is the single transition chokepoint.
# `Redesigner` (and the alias `Engine`) both resolve to the typed engine; the
# legacy redesign_legacy module has been removed (US5/T042 complete).
from intuitiveness.redesign.engine import Redesigner, TransitionError
Engine = Redesigner  # backwards-compatible alias
from intuitiveness.redesign.params import (
    TransitionParams,
    L4toL3Params,
    L3toL2Params,
    L2toL1Params,
    L1toL0Params,
    L0toL1Params,
    L1toL2Params,
    L2toL3Params,
)

__all__ = [
    "Redesigner",        # spec-015 unified engine
    "Engine",            # alias of Redesigner
    "TransitionError",
    "DataLineage",
    "SourceReference",
    "TransitionParams",
    "L4toL3Params",
    "L3toL2Params",
    "L2toL1Params",
    "L1toL0Params",
    "L0toL1Params",
    "L1toL2Params",
    "L2toL3Params",
]
