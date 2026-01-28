"""
Data Lineage Tracking Module

Implements Spec 001: FR-013-015 (Data Lineage Tracking)

Provides comprehensive transformation history tracking with <1s retrieval
for 100K rows. Enables complete provenance from L4 to L0 and back.

Classes:
--------
- SourceReference: Single transformation operation reference
- DataLineage: Complete transformation history for a dataset

Example:
--------
>>> lineage = DataLineage()
>>> lineage.add_operation(
...     operation_type="L4→L3",
...     input_level=ComplexityLevel.LEVEL_4,
...     output_level=ComplexityLevel.LEVEL_3,
...     parameters={"builder": "semantic_join"},
...     timestamp=datetime.now()
... )
>>> lineage.export("trace.json")
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
import json
from pathlib import Path

from intuitiveness.complexity import ComplexityLevel


@dataclass
class SourceReference:
    """
    Single transformation operation reference.

    Tracks provenance for one transition between complexity levels.

    Attributes:
    -----------
    operation_type : str
        Type of operation (e.g., "L4→L3", "L2→L1", "L0→L1")
    input_level : ComplexityLevel
        Source complexity level
    output_level : ComplexityLevel
        Target complexity level
    timestamp : datetime
        When the operation was performed
    parameters : Dict[str, Any]
        Operation-specific parameters (e.g., column name, aggregation method)
    duration_ms : float
        Operation execution time in milliseconds
    row_count_before : Optional[int]
        Number of rows before operation (if applicable)
    row_count_after : Optional[int]
        Number of rows after operation (if applicable)
    """
    operation_type: str
    input_level: ComplexityLevel
    output_level: ComplexityLevel
    timestamp: datetime
    parameters: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    row_count_before: Optional[int] = None
    row_count_after: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "operation_type": self.operation_type,
            "input_level": self.input_level.name,
            "output_level": self.output_level.name,
            "timestamp": self.timestamp.isoformat(),
            "parameters": self.parameters,
            "duration_ms": self.duration_ms,
            "row_count_before": self.row_count_before,
            "row_count_after": self.row_count_after,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceReference":
        """Create from dictionary."""
        return cls(
            operation_type=data["operation_type"],
            input_level=ComplexityLevel[data["input_level"]],
            output_level=ComplexityLevel[data["output_level"]],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            parameters=data.get("parameters", {}),
            duration_ms=data.get("duration_ms", 0.0),
            row_count_before=data.get("row_count_before"),
            row_count_after=data.get("row_count_after"),
        )


class DataLineage:
    """
    Complete transformation history for a dataset.

    Tracks all operations from initial L4 entry through descent and ascent
    phases. Enables <1s retrieval for 100K rows.

    Implements Spec 001: FR-013-015 (Data Lineage Tracking)

    Attributes:
    -----------
    operations : List[SourceReference]
        Ordered list of transformation operations
    metadata : Dict[str, Any]
        Additional lineage metadata (user, session_id, etc.)

    Example:
    --------
    >>> lineage = DataLineage(metadata={"session_id": "abc123"})
    >>> lineage.add_operation(
    ...     operation_type="L4→L3",
    ...     input_level=ComplexityLevel.LEVEL_4,
    ...     output_level=ComplexityLevel.LEVEL_3,
    ...     parameters={"files": ["file1.csv", "file2.csv"]},
    ...     duration_ms=1250.5
    ... )
    >>> history = lineage.get_history()
    >>> lineage.export("lineage.json")
    """

    def __init__(self, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize empty lineage tracker.

        Parameters:
        -----------
        metadata : Optional[Dict[str, Any]]
            Additional metadata (session_id, user, etc.)
        """
        self.operations: List[SourceReference] = []
        self.metadata: Dict[str, Any] = metadata or {}
        self._created_at = datetime.now()

    def add_operation(
        self,
        operation_type: str,
        input_level: ComplexityLevel,
        output_level: ComplexityLevel,
        parameters: Optional[Dict[str, Any]] = None,
        duration_ms: float = 0.0,
        row_count_before: Optional[int] = None,
        row_count_after: Optional[int] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Add a transformation operation to the lineage.

        Parameters:
        -----------
        operation_type : str
            Type of operation (e.g., "L4→L3")
        input_level : ComplexityLevel
            Source complexity level
        output_level : ComplexityLevel
            Target complexity level
        parameters : Optional[Dict[str, Any]]
            Operation-specific parameters
        duration_ms : float
            Execution time in milliseconds
        row_count_before : Optional[int]
            Rows before operation
        row_count_after : Optional[int]
            Rows after operation
        timestamp : Optional[datetime]
            Operation timestamp (defaults to now)
        """
        ref = SourceReference(
            operation_type=operation_type,
            input_level=input_level,
            output_level=output_level,
            timestamp=timestamp or datetime.now(),
            parameters=parameters or {},
            duration_ms=duration_ms,
            row_count_before=row_count_before,
            row_count_after=row_count_after,
        )
        self.operations.append(ref)

    def get_history(self) -> List[Dict[str, Any]]:
        """
        Get complete transformation history.

        Returns:
        --------
        List[Dict[str, Any]]
            List of operation dictionaries with all metadata

        Performance:
        ------------
        Guaranteed <1s retrieval for 100K rows (Spec 001: FR-014)
        """
        return [op.to_dict() for op in self.operations]

    def get_operations_by_level(
        self, level: ComplexityLevel
    ) -> List[SourceReference]:
        """
        Get all operations involving a specific level.

        Parameters:
        -----------
        level : ComplexityLevel
            Target complexity level

        Returns:
        --------
        List[SourceReference]
            Operations with level as input or output
        """
        return [
            op for op in self.operations
            if op.input_level == level or op.output_level == level
        ]

    def get_total_duration(self) -> float:
        """
        Get total execution time for all operations.

        Returns:
        --------
        float
            Total duration in milliseconds
        """
        return sum(op.duration_ms for op in self.operations)

    def export(self, filepath: str) -> None:
        """
        Export lineage to JSON file.

        Parameters:
        -----------
        filepath : str
            Path to output JSON file

        Example:
        --------
        >>> lineage.export("lineage_trace.json")
        """
        path = Path(filepath)

        export_data = {
            "metadata": self.metadata,
            "created_at": self._created_at.isoformat(),
            "total_operations": len(self.operations),
            "total_duration_ms": self.get_total_duration(),
            "operations": self.get_history(),
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, filepath: str) -> "DataLineage":
        """
        Load lineage from JSON file.

        Parameters:
        -----------
        filepath : str
            Path to lineage JSON file

        Returns:
        --------
        DataLineage
            Restored lineage object

        Example:
        --------
        >>> lineage = DataLineage.load("lineage_trace.json")
        """
        path = Path(filepath)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        lineage = cls(metadata=data.get("metadata", {}))
        lineage._created_at = datetime.fromisoformat(data["created_at"])

        for op_data in data.get("operations", []):
            lineage.operations.append(SourceReference.from_dict(op_data))

        return lineage

    def __repr__(self) -> str:
        """String representation of lineage."""
        return (
            f"DataLineage(operations={len(self.operations)}, "
            f"duration={self.get_total_duration():.2f}ms)"
        )
