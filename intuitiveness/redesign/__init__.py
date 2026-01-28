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

# TODO (Spec 001: FR-018-024): Refactor Redesigner into redesign/core.py
# For now, import from legacy redesign_legacy.py module for backward compatibility
from intuitiveness.redesign_legacy import Redesigner

__all__ = [
    "Redesigner",  # Legacy import from intuitiveness.redesign_legacy
    "DataLineage",
    "SourceReference",
]
