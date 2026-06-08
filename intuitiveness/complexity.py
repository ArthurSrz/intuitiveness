from enum import Enum
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional, Union, TYPE_CHECKING
import pandas as pd
import networkx as nx

if TYPE_CHECKING:  # avoid circular import at runtime (lineage.py imports ComplexityLevel)
    from intuitiveness.redesign.lineage import DataLineage


class ComplexityLevel(Enum):
    LEVEL_0 = 0  # Data Point
    LEVEL_1 = 1  # Variable / Vector
    LEVEL_2 = 2  # Table / Matrix
    LEVEL_3 = 3  # Multi-level Table / Knowledge Graph
    LEVEL_4 = 4  # Unlinkable Tables / Raw Data

class Dataset(ABC):
    """Abstract base class for all datasets.

    Every level is symmetric (spec 015 FR-001/FR-002/FR-003): it carries its
    payload, its full derivation ``lineage`` (denormalized, raw origin → self),
    and can describe itself via ``summary()`` with no external type-switching.
    """

    @property
    @abstractmethod
    def complexity_level(self) -> ComplexityLevel:
        pass

    @abstractmethod
    def get_data(self) -> Any:
        pass

    @abstractmethod
    def summary(self) -> Dict[str, Any]:
        """Return a level-appropriate self-description.

        MUST always include ``level`` and ``level_name``. Implemented by every
        level so that no external component branches on ``complexity_level``.
        """

    @property
    def lineage(self) -> "DataLineage":
        """Full denormalized derivation history (raw origin → this artifact).

        Lazily created (empty) on first access to keep every level
        self-describing without forcing callers to pass a lineage. The import
        is local to avoid a circular dependency with ``redesign.lineage``.
        """
        existing = getattr(self, "_lineage", None)
        if existing is None:
            from intuitiveness.redesign.lineage import DataLineage
            existing = DataLineage()
            self._lineage = existing
        return existing

    @lineage.setter
    def lineage(self, value: "DataLineage") -> None:
        self._lineage = value

    def _base_summary(self) -> Dict[str, Any]:
        return {
            "level": self.complexity_level.value,
            "level_name": self.complexity_level.name,
        }

    def __repr__(self):
        return f"<{self.__class__.__name__} (Level {self.complexity_level.value})>"

class Level4Dataset(Dataset):
    """
    Level 4: Unlinkable Tables / Raw Data.
    Represents a collection of raw data sources that are not yet unified.
    """
    def __init__(self, data_sources: Dict[str, Any], lineage: Optional["DataLineage"] = None):
        self._data = data_sources
        self._lineage = lineage

    @property
    def complexity_level(self) -> ComplexityLevel:
        return ComplexityLevel.LEVEL_4

    def get_data(self) -> Dict[str, Any]:
        return self._data

    def summary(self) -> Dict[str, Any]:
        s = self._base_summary()
        s["type"] = "unlinkable"
        s["source_count"] = len(self._data) if hasattr(self._data, "__len__") else 0
        return s

class Level3Dataset(Dataset):
    """
    Level 3: Multi-level Table / Knowledge Graph.
    Represents data with complex relationships, modeled as a graph or related tables.
    """
    def __init__(self, data: Union[nx.Graph, pd.DataFrame], lineage: Optional["DataLineage"] = None):
        self._data = data
        self._lineage = lineage

    @property
    def complexity_level(self) -> ComplexityLevel:
        return ComplexityLevel.LEVEL_3

    def get_data(self) -> Union[nx.Graph, pd.DataFrame]:
        return self._data

    def summary(self) -> Dict[str, Any]:
        s = self._base_summary()
        s["type"] = "graph"
        data = self._data
        if hasattr(data, "number_of_nodes"):
            s["node_count"] = data.number_of_nodes()
            s["edge_count"] = data.number_of_edges()
        elif hasattr(data, "shape"):
            s["row_count"] = data.shape[0]
        return s

class Level2Dataset(Dataset):
    """
    Level 2: Single Table.
    Represents a flat, tabular dataset (e.g., a pandas DataFrame).
    """
    def __init__(self, df: pd.DataFrame, name: str = "dataset", lineage: Optional["DataLineage"] = None):
        self._df = df
        self.name = name
        self._lineage = lineage

    @property
    def complexity_level(self) -> ComplexityLevel:
        return ComplexityLevel.LEVEL_2

    def get_data(self) -> pd.DataFrame:
        return self._df

    def summary(self) -> Dict[str, Any]:
        s = self._base_summary()
        s["type"] = "dataframe"
        df = self._df
        if hasattr(df, "shape"):
            s["row_count"] = df.shape[0]
            s["columns"] = list(df.columns) if hasattr(df, "columns") else []
        return s

class Level1Dataset(Dataset):
    """
    Level 1: Variable / Vector.
    Represents a single series of values (e.g., a pandas Series or list).
    """
    def __init__(self, series: pd.Series, name: str = "variable", lineage: Optional["DataLineage"] = None):
        self._series = series
        self.name = name
        self._lineage = lineage

    @property
    def complexity_level(self) -> ComplexityLevel:
        return ComplexityLevel.LEVEL_1

    def get_data(self) -> pd.Series:
        return self._series

    def summary(self) -> Dict[str, Any]:
        s = self._base_summary()
        s["type"] = "vector"
        if hasattr(self._series, "__len__"):
            s["length"] = len(self._series)
        return s

class Level0Dataset(Dataset):
    """
    Level 0: Data Point.
    Represents a single scalar value.

    Extended to support ascent by storing parent reference.
    """
    def __init__(
        self,
        value: Any,
        description: str = "value",
        parent_data: Optional[pd.Series] = None,
        aggregation_method: Optional[str] = None,
        lineage: Optional["DataLineage"] = None,
    ):
        self._value = value
        self.description = description
        self._parent_data = parent_data
        self._aggregation_method = aggregation_method
        self._lineage = lineage

    @property
    def complexity_level(self) -> ComplexityLevel:
        return ComplexityLevel.LEVEL_0

    def get_data(self) -> Any:
        return self._value

    def summary(self) -> Dict[str, Any]:
        s = self._base_summary()
        s["type"] = "datum"
        s["value"] = self._value
        return s

    @property
    def has_parent(self) -> bool:
        """Check if parent data is available for ascent."""
        return self._parent_data is not None

    def get_parent_data(self) -> Optional[pd.Series]:
        """Get the parent L1 data that was aggregated to produce this L0."""
        return self._parent_data

    @property
    def aggregation_method(self) -> Optional[str]:
        """Get the aggregation method used to produce this L0."""
        return self._aggregation_method
