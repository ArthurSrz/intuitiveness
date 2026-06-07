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

# Spec 015: the unified Redesigner engine (the single transition chokepoint) is
# available as `intuitiveness.redesign.engine.Redesigner` and re-exported here as
# `Engine`. The package-level name `Redesigner` still resolves to the legacy
# implementation during the migration so existing callers (navigation/session.py)
# keep working; the top-level swap happens in US5/T042 once callers are rewired.
from intuitiveness.redesign_legacy import Redesigner  # legacy (transitional)
from intuitiveness.redesign.engine import Redesigner as Engine, TransitionError
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
    "Redesigner",        # legacy (transitional — retired in US5/T042)
    "Engine",            # spec-015 unified engine
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
