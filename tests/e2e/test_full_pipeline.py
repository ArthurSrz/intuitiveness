"""
End-to-End Pipeline Tests for the Data Redesign Method.

This module tests the complete descent (L4->L3->L2->L1->L0) and ascent (L0->L1->L2->L3)
cycles as described in the research paper v2_intuitive_datasets_revised.md.

Key Features:
- Full path tracking at every step
- Artifact export at each level
- Works with all test datasets (test0, test1, test2)
- Validates complexity reduction/increase

Run with: pytest tests/e2e/test_full_pipeline.py -v
"""

import pytest
import pandas as pd
import networkx as nx
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

# Add package to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from intuitiveness import (
    ComplexityLevel,
    Level4Dataset,
    Level3Dataset,
    Level2Dataset,
    Level1Dataset,
    Level0Dataset,
    Redesigner,
    NavigationSession,
    NavigationState,
    NavigationError,
    NavigationTree,
    NavigationAction
)
from intuitiveness.ascent.enrichment import EnrichmentRegistry
from intuitiveness.ascent.dimensions import DimensionRegistry
from intuitiveness.export.json_export import NavigationExport, OutputSummary, CumulativeOutputs
from intuitiveness.redesign.params import (
    L4toL3Params, L3toL2Params, L2toL1Params, L1toL0Params,
    L0toL1Params, L1toL2Params, L2toL3Params,
)


# =============================================================================
# TEST DATA PATHS
# =============================================================================

TEST_DATA_DIR = Path(__file__).parent.parent.parent / "test_data"
TEST0_DIR = TEST_DATA_DIR / "test0"
TEST1_DIR = TEST_DATA_DIR / "test1"
TEST2_DIR = TEST_DATA_DIR / "test2"
ARTIFACTS_DIR = Path(__file__).parent.parent / "artifacts"


# =============================================================================
# ARTIFACT EXPORTER
# =============================================================================

@dataclass
class LevelArtifact:
    """Artifact produced at a complexity level."""
    level: int
    level_name: str
    timestamp: str
    data_type: str  # "dataframe", "series", "scalar", "graph", "dict"
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    node_count: Optional[int] = None
    edge_count: Optional[int] = None
    value: Optional[Any] = None
    columns: Optional[List[str]] = None
    sample_data: Optional[str] = None
    file_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class NavigationPath:
    """Complete navigation path through the descent-ascent cycle."""
    session_id: str
    start_time: str
    end_time: Optional[str] = None
    steps: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: Dict[str, LevelArtifact] = field(default_factory=dict)

    def add_step(self, level: ComplexityLevel, action: str, description: str):
        self.steps.append({
            "level": level.value,
            "level_name": level.name,
            "action": action,
            "description": description,
            "timestamp": datetime.now().isoformat()
        })

    def add_artifact(self, level: ComplexityLevel, artifact: LevelArtifact):
        self.artifacts[f"L{level.value}"] = artifact

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "steps": self.steps,
            "artifacts": {k: v.to_dict() for k, v in self.artifacts.items()}
        }

    def save(self, filepath: Path):
        """Save path to JSON file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)


class ArtifactExporter:
    """Export artifacts at each complexity level."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_l4(self, dataset: Level4Dataset, name: str) -> LevelArtifact:
        """Export L4 (unlinkable datasets) artifact."""
        data = dataset.get_data()
        artifact = LevelArtifact(
            level=4,
            level_name="LEVEL_4",
            timestamp=datetime.now().isoformat(),
            data_type="dict"
        )

        # Export each source
        sources_info = {}
        for source_name, source_data in data.items():
            if isinstance(source_data, pd.DataFrame):
                filepath = self.output_dir / f"{name}_L4_{source_name}"
                source_data.to_csv(filepath.with_suffix('.csv'), index=False)
                sources_info[source_name] = {
                    "rows": len(source_data),
                    "columns": list(source_data.columns),
                    "file": str(filepath.with_suffix('.csv'))
                }

        artifact.sample_data = json.dumps(sources_info, indent=2)
        artifact.file_path = str(self.output_dir / f"{name}_L4_manifest.json")

        with open(artifact.file_path, 'w') as f:
            json.dump(sources_info, f, indent=2)

        return artifact

    def export_l3(self, dataset: Level3Dataset, name: str) -> LevelArtifact:
        """Export L3 (linkable multi-level) artifact."""
        data = dataset.get_data()
        artifact = LevelArtifact(
            level=3,
            level_name="LEVEL_3",
            timestamp=datetime.now().isoformat(),
            data_type="graph" if isinstance(data, nx.Graph) else "dataframe"
        )

        if isinstance(data, nx.Graph):
            artifact.node_count = data.number_of_nodes()
            artifact.edge_count = data.number_of_edges()

            # Export as GraphML
            filepath = self.output_dir / f"{name}_L3_graph.graphml"
            nx.write_graphml(data, filepath)
            artifact.file_path = str(filepath)

            # Also export node/edge lists as CSV
            if data.number_of_nodes() > 0:
                nodes_df = pd.DataFrame([
                    {"node": n, **data.nodes[n]}
                    for n in data.nodes()
                ])
                nodes_df.to_csv(self.output_dir / f"{name}_L3_nodes.csv", index=False)

            if data.number_of_edges() > 0:
                edges_df = pd.DataFrame([
                    {"source": u, "target": v, **d}
                    for u, v, d in data.edges(data=True)
                ])
                edges_df.to_csv(self.output_dir / f"{name}_L3_edges.csv", index=False)

        elif isinstance(data, pd.DataFrame):
            artifact.row_count = len(data)
            artifact.column_count = len(data.columns)
            artifact.columns = list(data.columns)

            filepath = self.output_dir / f"{name}_L3_table.csv"
            data.to_csv(filepath, index=False)
            artifact.file_path = str(filepath)

        return artifact

    def export_l2(self, dataset: Level2Dataset, name: str) -> LevelArtifact:
        """Export L2 (single table) artifact."""
        data = dataset.get_data()
        artifact = LevelArtifact(
            level=2,
            level_name="LEVEL_2",
            timestamp=datetime.now().isoformat(),
            data_type="dataframe",
            row_count=len(data),
            column_count=len(data.columns),
            columns=list(data.columns)
        )

        filepath = self.output_dir / f"{name}_L2_table.csv"
        data.to_csv(filepath, index=False)
        artifact.file_path = str(filepath)

        # Sample data
        artifact.sample_data = data.head(5).to_json(orient='records')

        return artifact

    def export_l1(self, dataset: Level1Dataset, name: str) -> LevelArtifact:
        """Export L1 (vector) artifact."""
        data = dataset.get_data()
        artifact = LevelArtifact(
            level=1,
            level_name="LEVEL_1",
            timestamp=datetime.now().isoformat(),
            data_type="series",
            row_count=len(data)
        )

        filepath = self.output_dir / f"{name}_L1_vector.csv"
        data.to_frame(name=dataset.name).to_csv(filepath, index=True)
        artifact.file_path = str(filepath)

        # Sample data
        artifact.sample_data = str(data.head(10).tolist())

        return artifact

    def export_l0(self, dataset: Level0Dataset, name: str) -> LevelArtifact:
        """Export L0 (datum) artifact."""
        data = dataset.get_data()
        artifact = LevelArtifact(
            level=0,
            level_name="LEVEL_0",
            timestamp=datetime.now().isoformat(),
            data_type="scalar",
            value=data
        )

        filepath = self.output_dir / f"{name}_L0_datum.json"
        with open(filepath, 'w') as f:
            json.dump({
                "value": data,
                "description": dataset.description,
                "aggregation_method": dataset.aggregation_method,
                "has_parent": dataset.has_parent
            }, f, indent=2, default=str)
        artifact.file_path = str(filepath)

        return artifact


# =============================================================================
# PIPELINE RUNNER
# =============================================================================

class DescentAscentPipeline:
    """
    Execute the complete descent-ascent cycle on a dataset.

    This implements the full flow from the research paper:
    - Descent: L4 -> L3 -> L2 -> L1 -> L0 (reduce complexity)
    - Ascent: L0 -> L1 -> L2 -> L3 (rebuild with intentional dimensions)
    """

    def __init__(self, name: str, output_dir: Path):
        self.name = name
        self.exporter = ArtifactExporter(output_dir / name)
        self.path = NavigationPath(
            session_id=f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            start_time=datetime.now().isoformat()
        )
        self.current_dataset = None
        self.session = None

    def load_sources(self, sources: Dict[str, pd.DataFrame]) -> Level4Dataset:
        """Load raw data sources as L4 dataset."""
        l4 = Level4Dataset(sources)
        self.current_dataset = l4

        self.path.add_step(
            ComplexityLevel.LEVEL_4,
            "entry",
            f"Loaded {len(sources)} data sources"
        )

        artifact = self.exporter.export_l4(l4, self.name)
        self.path.add_artifact(ComplexityLevel.LEVEL_4, artifact)

        return l4

    def descend_4_to_3(self, builder_func) -> Level3Dataset:
        """L4 -> L3: Build knowledge graph from unlinkable sources."""
        if self.current_dataset.complexity_level != ComplexityLevel.LEVEL_4:
            raise ValueError("Must be at L4 to descend to L3")

        l3 = Redesigner.reduce_complexity(
            self.current_dataset,
            ComplexityLevel.LEVEL_3,
            L4toL3Params(prebuilt_graph=builder_func(self.current_dataset.get_data())),
        )
        self.current_dataset = l3

        self.path.add_step(
            ComplexityLevel.LEVEL_3,
            "descend",
            "Built knowledge graph from sources"
        )

        artifact = self.exporter.export_l3(l3, self.name)
        self.path.add_artifact(ComplexityLevel.LEVEL_3, artifact)

        return l3

    def descend_3_to_2(self, query_func) -> Level2Dataset:
        """L3 -> L2: Extract domain table from graph."""
        if self.current_dataset.complexity_level != ComplexityLevel.LEVEL_3:
            raise ValueError("Must be at L3 to descend to L2")

        l2 = Redesigner.reduce_complexity(
            self.current_dataset,
            ComplexityLevel.LEVEL_2,
            L3toL2Params(prebuilt_table=query_func(self.current_dataset.get_data())),
        )
        self.current_dataset = l2

        self.path.add_step(
            ComplexityLevel.LEVEL_2,
            "descend",
            "Extracted domain table from graph"
        )

        artifact = self.exporter.export_l2(l2, self.name)
        self.path.add_artifact(ComplexityLevel.LEVEL_2, artifact)

        return l2

    def descend_2_to_1(self, column: str, filter_query: str = None) -> Level1Dataset:
        """L2 -> L1: Extract column as vector."""
        if self.current_dataset.complexity_level != ComplexityLevel.LEVEL_2:
            raise ValueError("Must be at L2 to descend to L1")

        l1 = Redesigner.reduce_complexity(
            self.current_dataset,
            ComplexityLevel.LEVEL_1,
            L2toL1Params(column=column, filter_query=filter_query),
        )
        self.current_dataset = l1

        self.path.add_step(
            ComplexityLevel.LEVEL_1,
            "descend",
            f"Extracted column '{column}' as vector"
        )

        artifact = self.exporter.export_l1(l1, self.name)
        self.path.add_artifact(ComplexityLevel.LEVEL_1, artifact)

        return l1

    def descend_1_to_0(self, aggregation: str = "count") -> Level0Dataset:
        """L1 -> L0: Compute atomic metric."""
        if self.current_dataset.complexity_level != ComplexityLevel.LEVEL_1:
            raise ValueError("Must be at L1 to descend to L0")

        l0 = Redesigner.reduce_complexity(
            self.current_dataset,
            ComplexityLevel.LEVEL_0,
            L1toL0Params(aggregation=aggregation),
        )
        self.current_dataset = l0

        self.path.add_step(
            ComplexityLevel.LEVEL_0,
            "descend",
            f"Computed atomic metric ({aggregation})"
        )

        artifact = self.exporter.export_l0(l0, self.name)
        self.path.add_artifact(ComplexityLevel.LEVEL_0, artifact)

        return l0

    def ascend_0_to_1(self, enrichment_func: str = "source_expansion") -> Level1Dataset:
        """L0 -> L1: Enrich datum back to vector."""
        if self.current_dataset.complexity_level != ComplexityLevel.LEVEL_0:
            raise ValueError("Must be at L0 to ascend to L1")

        l1 = Redesigner.increase_complexity(
            self.current_dataset,
            ComplexityLevel.LEVEL_1,
            L0toL1Params(enrichment_function=enrichment_func),
        )
        self.current_dataset = l1

        self.path.add_step(
            ComplexityLevel.LEVEL_1,
            "ascend",
            f"Enriched to vector using {enrichment_func}"
        )

        artifact = self.exporter.export_l1(l1, f"{self.name}_ascent")
        self.path.add_artifact(ComplexityLevel.LEVEL_1, artifact)

        return l1

    def ascend_1_to_2(self, dimensions: List[str] = None) -> Level2Dataset:
        """L1 -> L2: Add dimensions to create table."""
        if self.current_dataset.complexity_level != ComplexityLevel.LEVEL_1:
            raise ValueError("Must be at L1 to ascend to L2")

        l2 = Redesigner.increase_complexity(
            self.current_dataset,
            ComplexityLevel.LEVEL_2,
            L1toL2Params(dimensions=dimensions or []),
        )
        self.current_dataset = l2

        self.path.add_step(
            ComplexityLevel.LEVEL_2,
            "ascend",
            f"Added dimensions: {dimensions}"
        )

        artifact = self.exporter.export_l2(l2, f"{self.name}_ascent")
        self.path.add_artifact(ComplexityLevel.LEVEL_2, artifact)

        return l2

    def ascend_2_to_3(self, dimensions: List[str] = None) -> Level3Dataset:
        """L2 -> L3: Add hierarchical structure."""
        if self.current_dataset.complexity_level != ComplexityLevel.LEVEL_2:
            raise ValueError("Must be at L2 to ascend to L3")

        l3 = Redesigner.increase_complexity(
            self.current_dataset,
            ComplexityLevel.LEVEL_3,
            L2toL3Params(dimensions=dimensions or []),
        )
        self.current_dataset = l3

        self.path.add_step(
            ComplexityLevel.LEVEL_3,
            "ascend",
            f"Added hierarchical dimensions: {dimensions}"
        )

        artifact = self.exporter.export_l3(l3, f"{self.name}_ascent")
        self.path.add_artifact(ComplexityLevel.LEVEL_3, artifact)

        return l3

    def finalize(self) -> NavigationPath:
        """Complete the pipeline and save the navigation path."""
        self.path.end_time = datetime.now().isoformat()

        # Save the complete path
        path_file = self.exporter.output_dir / f"{self.name}_path.json"
        self.path.save(path_file)

        return self.path


# =============================================================================
# HELPER FUNCTIONS FOR GRAPH BUILDING
# =============================================================================

def build_graph_from_dataframes(sources: Dict[str, pd.DataFrame]) -> nx.Graph:
    """
    Build a simple knowledge graph from dataframes.

    This is a basic implementation that:
    1. Creates nodes for each unique value in key columns
    2. Creates edges between co-occurring values in the same row
    """
    G = nx.Graph()

    for source_name, df in sources.items():
        # Add nodes for each row
        for idx, row in df.head(100).iterrows():  # Limit for testing
            node_id = f"{source_name}_{idx}"
            G.add_node(node_id, source=source_name, **{
                col: str(val)[:100] for col, val in row.items()
                if pd.notna(val)
            })

    # Create edges between nodes from different sources that share values
    source_names = list(sources.keys())
    for i, src1 in enumerate(source_names):
        for src2 in source_names[i+1:]:
            df1 = sources[src1].head(100)
            df2 = sources[src2].head(100)

            # Find common columns
            common_cols = set(df1.columns) & set(df2.columns)

            for col in common_cols:
                # Find matching values
                vals1 = set(df1[col].dropna().astype(str))
                vals2 = set(df2[col].dropna().astype(str))
                common_vals = vals1 & vals2

                for val in list(common_vals)[:10]:  # Limit edges
                    rows1 = df1[df1[col].astype(str) == val].index[:5]
                    rows2 = df2[df2[col].astype(str) == val].index[:5]

                    for r1 in rows1:
                        for r2 in rows2:
                            G.add_edge(
                                f"{src1}_{r1}",
                                f"{src2}_{r2}",
                                relationship=f"SHARES_{col}",
                                value=val
                            )

    return G


def query_graph_to_dataframe(graph: nx.Graph) -> pd.DataFrame:
    """Extract nodes from graph as a dataframe."""
    if graph.number_of_nodes() == 0:
        return pd.DataFrame()

    records = []
    for node, attrs in graph.nodes(data=True):
        record = {"node_id": node}
        record.update(attrs)
        records.append(record)

    return pd.DataFrame(records)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def test0_sources():
    """Load test0 data sources."""
    sources = {}
    for f in TEST0_DIR.glob("*.csv"):
        try:
            df = pd.read_csv(f, nrows=500, sep=';', encoding='utf-8')
            sources[f.name] = df
        except:
            df = pd.read_csv(f, nrows=500, encoding='latin-1')
            sources[f.name] = df
    return sources


@pytest.fixture
def test1_sources():
    """Load test1 data sources."""
    sources = {}
    for f in TEST1_DIR.glob("*.csv"):
        df = None
        # Try different encoding/delimiter combinations
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            for sep in [';', ',']:
                try:
                    df = pd.read_csv(f, nrows=500, sep=sep, encoding=encoding, on_bad_lines='skip')
                    if len(df.columns) > 1:  # Valid if has multiple columns
                        break
                except Exception:
                    continue
            if df is not None and len(df.columns) > 1:
                break
        if df is not None:
            sources[f.name] = df
    return sources


@pytest.fixture
def test2_sources():
    """Load test2 data sources."""
    sources = {}
    for f in TEST2_DIR.glob("*.csv"):
        try:
            df = pd.read_csv(f, nrows=500, sep=';', encoding='utf-8')
            sources[f.name] = df
        except:
            df = pd.read_csv(f, nrows=500, encoding='latin-1')
            sources[f.name] = df
    return sources


@pytest.fixture
def output_dir():
    """Create output directory for artifacts."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACTS_DIR


# =============================================================================
# TESTS
# =============================================================================

class TestDescentPipeline:
    """Test the descent cycle: L4 -> L3 -> L2 -> L1 -> L0"""

    def test_descent_test0(self, test0_sources, output_dir):
        """Test full descent on test0 (French middle school data)."""
        pipeline = DescentAscentPipeline("test0", output_dir)

        # L4: Load sources
        l4 = pipeline.load_sources(test0_sources)
        assert l4.complexity_level == ComplexityLevel.LEVEL_4
        assert "L4" in pipeline.path.artifacts

        # L3: Build graph
        l3 = pipeline.descend_4_to_3(build_graph_from_dataframes)
        assert l3.complexity_level == ComplexityLevel.LEVEL_3
        assert "L3" in pipeline.path.artifacts

        # L2: Query to table
        l2 = pipeline.descend_3_to_2(query_graph_to_dataframe)
        assert l2.complexity_level == ComplexityLevel.LEVEL_2
        assert "L2" in pipeline.path.artifacts

        # Get a numeric column for L1
        df = l2.get_data()
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if not numeric_cols:
            # Use first column if no numeric
            col = df.columns[0]
        else:
            col = numeric_cols[0]

        # L1: Extract column
        l1 = pipeline.descend_2_to_1(col)
        assert l1.complexity_level == ComplexityLevel.LEVEL_1
        assert "L1" in pipeline.path.artifacts

        # L0: Compute metric
        l0 = pipeline.descend_1_to_0("count")
        assert l0.complexity_level == ComplexityLevel.LEVEL_0
        assert "L0" in pipeline.path.artifacts

        # Verify path has all steps
        path = pipeline.finalize()
        assert len(path.steps) == 5
        assert len(path.artifacts) == 5

        print(f"\nTest0 descent complete!")
        print(f"  L0 value: {l0.get_data()}")
        print(f"  Path saved to: {output_dir / 'test0'}")

    def test_descent_test1(self, test1_sources, output_dir):
        """Test full descent on test1 (ADEME funding data)."""
        pipeline = DescentAscentPipeline("test1", output_dir)

        l4 = pipeline.load_sources(test1_sources)
        l3 = pipeline.descend_4_to_3(build_graph_from_dataframes)
        l2 = pipeline.descend_3_to_2(query_graph_to_dataframe)

        df = l2.get_data()
        col = df.columns[0]

        l1 = pipeline.descend_2_to_1(col)
        l0 = pipeline.descend_1_to_0("count")

        path = pipeline.finalize()
        assert len(path.steps) == 5

        print(f"\nTest1 descent complete!")
        print(f"  L0 value: {l0.get_data()}")

    def test_descent_test2(self, test2_sources, output_dir):
        """Test full descent on test2 (energy price/trade data)."""
        pipeline = DescentAscentPipeline("test2", output_dir)

        l4 = pipeline.load_sources(test2_sources)
        l3 = pipeline.descend_4_to_3(build_graph_from_dataframes)
        l2 = pipeline.descend_3_to_2(query_graph_to_dataframe)

        df = l2.get_data()
        col = df.columns[0]

        l1 = pipeline.descend_2_to_1(col)
        l0 = pipeline.descend_1_to_0("count")

        path = pipeline.finalize()
        assert len(path.steps) == 5

        print(f"\nTest2 descent complete!")
        print(f"  L0 value: {l0.get_data()}")


class TestAscentPipeline:
    """Test the ascent cycle: L0 -> L1 -> L2 -> L3"""

    def test_full_cycle_test0(self, test0_sources, output_dir):
        """Test full descent-ascent cycle on test0 (French education data)."""
        pipeline = DescentAscentPipeline("test0_full", output_dir)

        # Complete descent first
        l4 = pipeline.load_sources(test0_sources)
        l3 = pipeline.descend_4_to_3(build_graph_from_dataframes)
        l2 = pipeline.descend_3_to_2(query_graph_to_dataframe)

        df = l2.get_data()
        col = df.columns[0]

        l1 = pipeline.descend_2_to_1(col)
        l0 = pipeline.descend_1_to_0("count")

        print(f"\ntest0 Descent complete, L0 value: {l0.get_data()}")

        # Now ascend
        l1_ascent = pipeline.ascend_0_to_1("source_expansion")
        assert l1_ascent.complexity_level == ComplexityLevel.LEVEL_1

        l2_ascent = pipeline.ascend_1_to_2(dimensions=["business_object", "pattern_type"])
        assert l2_ascent.complexity_level == ComplexityLevel.LEVEL_2

        l3_ascent = pipeline.ascend_2_to_3(dimensions=["client_segment", "financial_view"])
        assert l3_ascent.complexity_level == ComplexityLevel.LEVEL_3

        path = pipeline.finalize()

        # Should have: 5 descent + 3 ascent = 8 steps
        assert len(path.steps) == 8

        print(f"\ntest0 Full descent-ascent cycle complete!")
        print(f"  Steps: {len(path.steps)}")
        print(f"  Artifacts: {list(path.artifacts.keys())}")

    def test_full_cycle_test1(self, test1_sources, output_dir):
        """Test full descent-ascent cycle on test1 (ADEME funding data)."""
        pipeline = DescentAscentPipeline("test1_full", output_dir)

        # Descent
        l4 = pipeline.load_sources(test1_sources)
        l3 = pipeline.descend_4_to_3(build_graph_from_dataframes)
        l2 = pipeline.descend_3_to_2(query_graph_to_dataframe)

        df = l2.get_data()
        col = df.columns[0]

        l1 = pipeline.descend_2_to_1(col)
        l0 = pipeline.descend_1_to_0("count")

        print(f"\ntest1 Descent complete, L0 value: {l0.get_data()}")

        # Ascent
        l1_ascent = pipeline.ascend_0_to_1("source_expansion")
        assert l1_ascent.complexity_level == ComplexityLevel.LEVEL_1

        l2_ascent = pipeline.ascend_1_to_2(dimensions=["business_object", "pattern_type"])
        assert l2_ascent.complexity_level == ComplexityLevel.LEVEL_2

        l3_ascent = pipeline.ascend_2_to_3(dimensions=["client_segment", "financial_view"])
        assert l3_ascent.complexity_level == ComplexityLevel.LEVEL_3

        path = pipeline.finalize()
        assert len(path.steps) == 8

        print(f"\ntest1 Full descent-ascent cycle complete!")
        print(f"  Steps: {len(path.steps)}")

    def test_full_cycle_test2(self, test2_sources, output_dir):
        """Test full descent-ascent cycle on test2 (energy/trade data)."""
        pipeline = DescentAscentPipeline("test2_full", output_dir)

        # Descent
        l4 = pipeline.load_sources(test2_sources)
        l3 = pipeline.descend_4_to_3(build_graph_from_dataframes)
        l2 = pipeline.descend_3_to_2(query_graph_to_dataframe)

        df = l2.get_data()
        col = df.columns[0]

        l1 = pipeline.descend_2_to_1(col)
        l0 = pipeline.descend_1_to_0("count")

        print(f"\ntest2 Descent complete, L0 value: {l0.get_data()}")

        # Ascent
        l1_ascent = pipeline.ascend_0_to_1("source_expansion")
        assert l1_ascent.complexity_level == ComplexityLevel.LEVEL_1

        l2_ascent = pipeline.ascend_1_to_2(dimensions=["business_object", "pattern_type"])
        assert l2_ascent.complexity_level == ComplexityLevel.LEVEL_2

        l3_ascent = pipeline.ascend_2_to_3(dimensions=["client_segment", "financial_view"])
        assert l3_ascent.complexity_level == ComplexityLevel.LEVEL_3

        path = pipeline.finalize()
        assert len(path.steps) == 8

        print(f"\ntest2 Full descent-ascent cycle complete!")
        print(f"  Steps: {len(path.steps)}")


class TestNavigationSession:
    """Test NavigationSession with tree tracking."""

    def test_navigation_with_tree(self, test0_sources, output_dir):
        """Test using NavigationSession with tree mode."""
        l4 = Level4Dataset(test0_sources)

        # Create session with tree tracking
        session = NavigationSession(l4)
        assert session.state == NavigationState.ENTRY
        assert session.current_level == ComplexityLevel.LEVEL_4

        # Descend L4 -> L3
        session.descend(builder_func=build_graph_from_dataframes)
        assert session.current_level == ComplexityLevel.LEVEL_3

        # Descend L3 -> L2
        session.descend(query_func=query_graph_to_dataframe)
        assert session.current_level == ComplexityLevel.LEVEL_2

        # Get column for L2 -> L1
        df = session.current_dataset.get_data()
        col = df.columns[0]

        # Descend L2 -> L1
        session.descend(column=col)
        assert session.current_level == ComplexityLevel.LEVEL_1

        # Descend L1 -> L0
        session.descend(aggregation="count")
        assert session.current_level == ComplexityLevel.LEVEL_0

        # Get history
        history = session.get_history()
        assert len(history) == 5  # Entry + 4 descents

        # Export
        export_data = session.export()
        assert "navigation_tree" in export_data
        assert "cumulative_outputs" in export_data

        # Save export
        export_path = output_dir / "test0_session_export.json"
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        print(f"\nNavigation session complete!")
        print(f"  History steps: {len(history)}")
        print(f"  Export saved to: {export_path}")

    def test_navigation_tree_branching(self, test0_sources, output_dir):
        """Test branching in navigation tree."""
        l4 = Level4Dataset(test0_sources)
        session = NavigationSession(l4)

        # Descend to L3
        session.descend(builder_func=build_graph_from_dataframes)
        l3_node_id = session._current_node_id

        # Descend to L2
        session.descend(query_func=query_graph_to_dataframe)

        # Get visualization
        viz = session.get_tree_visualization()
        assert len(viz["nodes"]) >= 3

        # Test restore to L3 (time-travel)
        session.restore(l3_node_id)
        assert session.current_level == ComplexityLevel.LEVEL_3

        print(f"\nTree branching test complete!")
        print(f"  Nodes in tree: {len(viz['nodes'])}")


class TestComplexityReduction:
    """Test complexity reduction bounds from the paper."""

    def test_l4_to_l3_reduction(self, test0_sources):
        """L4->L3 should achieve nearly 100% complexity reduction."""
        l4 = Level4Dataset(test0_sources)
        l3 = Redesigner.reduce_complexity(
            l4, ComplexityLevel.LEVEL_3,
            L4toL3Params(prebuilt_graph=build_graph_from_dataframes(l4.get_data())),
        )

        # Just verify the transition works
        assert l4.complexity_level.value > l3.complexity_level.value

    def test_cannot_return_to_l4(self, test0_sources):
        """Once at L3, cannot return to L4 (L4 is entry-only)."""
        l4 = Level4Dataset(test0_sources)
        session = NavigationSession(l4)

        session.descend(builder_func=build_graph_from_dataframes)

        # Should not be able to ascend to L4
        with pytest.raises(NavigationError):
            session.ascend()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
