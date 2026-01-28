from typing import Callable, Any, Dict, Optional, List
import pandas as pd
import networkx as nx
from .complexity import (
    Dataset, ComplexityLevel, 
    Level4Dataset, Level3Dataset, Level2Dataset, Level1Dataset, Level0Dataset
)

class Redesigner:
    """
    Handles the transition between complexity levels.
    """

    @staticmethod
    def reduce_complexity(dataset: Dataset, target_level: ComplexityLevel, **kwargs) -> Dataset:
        """
        Reduces the complexity of a dataset to the target level.
        """
        current_level = dataset.complexity_level
        
        if current_level.value <= target_level.value:
            raise ValueError(f"Cannot reduce complexity from {current_level} to {target_level}. Target must be lower.")

        # Dispatch to specific reduction methods
        if current_level == ComplexityLevel.LEVEL_4 and target_level == ComplexityLevel.LEVEL_3:
            return Redesigner._reduce_4_to_3(dataset, **kwargs)
        elif current_level == ComplexityLevel.LEVEL_3 and target_level == ComplexityLevel.LEVEL_2:
            return Redesigner._reduce_3_to_2(dataset, **kwargs)
        elif current_level == ComplexityLevel.LEVEL_2 and target_level == ComplexityLevel.LEVEL_1:
            return Redesigner._reduce_2_to_1(dataset, **kwargs)
        elif current_level == ComplexityLevel.LEVEL_1 and target_level == ComplexityLevel.LEVEL_0:
            return Redesigner._reduce_1_to_0(dataset, **kwargs)
        else:
            # Recursive reduction for multi-step jumps
            intermediate_level = ComplexityLevel(current_level.value - 1)
            intermediate_dataset = Redesigner.reduce_complexity(dataset, intermediate_level, **kwargs)
            return Redesigner.reduce_complexity(intermediate_dataset, target_level, **kwargs)

    @staticmethod
    def _reduce_4_to_3(dataset: Level4Dataset, builder_func: Callable[[Dict[str, Any]], nx.Graph], **kwargs) -> Level3Dataset:
        """
        L4 -> L3: Unlinkable to Graph.
        Requires a builder function that knows how to connect the raw sources.
        """
        graph = builder_func(dataset.get_data())
        return Level3Dataset(graph)

    @staticmethod
    def _reduce_3_to_2(dataset: Level3Dataset, query_func: Callable[[nx.Graph], pd.DataFrame], **kwargs) -> Level2Dataset:
        """
        L3 -> L2: Graph to Table.
        Requires a query function (e.g., Cypher-like or NetworkX traversal) to extract a table.
        """
        df = query_func(dataset.get_data())
        return Level2Dataset(df)

    @staticmethod
    def _reduce_2_to_1(dataset: Level2Dataset, column: str = None, filter_query: str = None, **kwargs) -> Level1Dataset:
        """
        L2 -> L1: Table to Vector.
        Selects a column, optionally filtering rows.
        """
        df = dataset.get_data()
        if filter_query:
            df = df.query(filter_query)
        
        if column:
            if column not in df.columns:
                raise ValueError(f"Column '{column}' not found in dataset.")
            series = df[column]
        else:
            # If no column specified, and only one column exists, use it.
            if len(df.columns) == 1:
                series = df.iloc[:, 0]
            else:
                raise ValueError("Must specify 'column' to extract from Level 2 dataset.")
        
        return Level1Dataset(series, name=column)

    @staticmethod
    def _reduce_1_to_0(dataset: Level1Dataset, aggregation: str = "sum", **kwargs) -> Level0Dataset:
        """
        L1 -> L0: Vector to Scalar.
        Applies an aggregation function (sum, mean, count, min, max).
        Stores parent data reference for potential ascent.
        """
        series = dataset.get_data()
        aggregation_name = aggregation if isinstance(aggregation, str) else "custom"

        if aggregation == "sum":
            val = series.sum()
        elif aggregation == "mean":
            val = series.mean()
        elif aggregation == "count":
            val = series.count()
        elif aggregation == "min":
            val = series.min()
        elif aggregation == "max":
            val = series.max()
        elif callable(aggregation):
            val = aggregation(series)
        else:
            raise ValueError(f"Unknown aggregation method: {aggregation}")

        # Store parent data for potential ascent (FR-005: data integrity)
        return Level0Dataset(
            val,
            description=f"{aggregation_name} of {dataset.name}",
            parent_data=series.copy(),
            aggregation_method=aggregation_name
        )

    @staticmethod
    def increase_complexity(dataset: Dataset, target_level: ComplexityLevel, **kwargs) -> Dataset:
        """
        Increases complexity (Ascent).
        Re-augments data by adding context and dimensions.

        Dispatches to specific methods:
        - L0 → L1: _increase_0_to_1
        - L1 → L2: _increase_1_to_2
        - L2 → L3: _increase_2_to_3

        Args:
            dataset: Source dataset
            target_level: Target level (must be source + 1, max L3)
            **kwargs: Additional parameters for enrichment

        Raises:
            ValueError: If target is not source + 1 or is L4
        """
        current_level = dataset.complexity_level

        if current_level.value >= target_level.value:
            raise ValueError(
                f"Cannot increase complexity from {current_level} to {target_level}. "
                f"Target must be higher."
            )

        if target_level == ComplexityLevel.LEVEL_4:
            raise ValueError("L4 is entry-only, cannot ascend to L4")

        if target_level.value != current_level.value + 1:
            raise ValueError(
                f"Ascent must be to adjacent level. "
                f"Got source={current_level.name}, target={target_level.name}"
            )

        # Dispatch to specific methods
        if current_level == ComplexityLevel.LEVEL_0 and target_level == ComplexityLevel.LEVEL_1:
            return Redesigner._increase_0_to_1(dataset, **kwargs)
        elif current_level == ComplexityLevel.LEVEL_1 and target_level == ComplexityLevel.LEVEL_2:
            return Redesigner._increase_1_to_2(dataset, **kwargs)
        elif current_level == ComplexityLevel.LEVEL_2 and target_level == ComplexityLevel.LEVEL_3:
            return Redesigner._increase_2_to_3(dataset, **kwargs)
        else:
            raise NotImplementedError(f"Ascent from {current_level} to {target_level} is not supported.")

    @staticmethod
    def _increase_0_to_1(dataset: Level0Dataset, **kwargs) -> Level1Dataset:
        """
        L0 -> L1: Datum to Vector.
        Enriches a scalar back to a vector using enrichment functions.

        Args:
            dataset: Level0Dataset with optional parent_data
            enrichment_func: Name of enrichment function or EnrichmentFunction object
            **kwargs: Additional parameters

        Returns:
            Level1Dataset with enriched vector

        Raises:
            ValueError: If no enrichment possible
        """
        from .ascent.enrichment import EnrichmentRegistry

        registry = EnrichmentRegistry.get_instance()
        enrichment_func = kwargs.get('enrichment_func')

        # Get enrichment function
        if enrichment_func is None:
            # Use default: source_expansion if parent data available
            if dataset.has_parent:
                enrichment_func = 'source_expansion'
            else:
                defaults = registry.get_defaults(
                    ComplexityLevel.LEVEL_0, ComplexityLevel.LEVEL_1
                )
                if not defaults:
                    raise ValueError(
                        "No enrichment function provided and no defaults available. "
                        "Provide 'enrichment_func' parameter."
                    )
                enrichment_func = defaults[0].name

        # Resolve function name to EnrichmentFunction
        if isinstance(enrichment_func, str):
            func = registry.get(enrichment_func)
        else:
            func = enrichment_func

        # Execute enrichment
        data = dataset.get_data()
        context = dataset.get_parent_data() if func.requires_context else None

        if func.requires_context and context is None:
            raise ValueError(
                f"Enrichment function '{func.name}' requires parent data context, "
                f"but none is available. This L0 dataset may not have been created "
                f"by descent from L1."
            )

        result = func(data, context)

        # Validate output is Series (FR-010)
        if not isinstance(result, pd.Series):
            if hasattr(result, '__iter__') and not isinstance(result, (str, dict)):
                result = pd.Series(list(result))
            else:
                raise TypeError(
                    f"Enrichment function must return pd.Series. "
                    f"Got {type(result).__name__}"
                )

        # Handle edge case: enrichment produces no data
        if len(result) == 0:
            raise ValueError(
                f"Enrichment function '{func.name}' produced no data. "
                f"Cannot ascend to L1 with empty vector."
            )

        # FR-005: Data integrity check - row counts should match
        # For source_expansion, the result should have same count as original
        if context is not None and len(result) != len(context):
            import warnings
            warnings.warn(
                f"Data integrity warning: Enriched vector has {len(result)} items, "
                f"but original context had {len(context)} items. "
                f"This may affect data traceability.",
                UserWarning
            )

        return Level1Dataset(result, name=f"enriched_{dataset.description}")

    @staticmethod
    def _increase_1_to_2(dataset: Level1Dataset, **kwargs) -> Level2Dataset:
        """
        L1 -> L2: Vector to Table.
        Adds categorical dimensions to create a table.

        Args:
            dataset: Level1Dataset
            dimensions: List of dimension names or DimensionDefinition objects
            enrichment_func: Alternative enrichment function
            **kwargs: Additional parameters

        Returns:
            Level2Dataset with dimension columns
        """
        from .ascent.dimensions import DimensionRegistry, DimensionDefinition

        registry = DimensionRegistry.get_instance()
        series = dataset.get_data()

        # Start with the vector as a DataFrame
        df = pd.DataFrame({'value': series})

        # Get dimensions to apply
        dimensions = kwargs.get('dimensions', [])

        if not dimensions:
            # Use defaults if no dimensions specified
            defaults = registry.get_defaults(
                ComplexityLevel.LEVEL_1, ComplexityLevel.LEVEL_2
            )
            if defaults:
                dimensions = [d.name for d in defaults]

        # Apply each dimension
        for dim in dimensions:
            if isinstance(dim, str):
                dim_def = registry.get(dim)
            elif isinstance(dim, DimensionDefinition):
                dim_def = dim
            else:
                raise TypeError(f"Expected dimension name or DimensionDefinition, got {type(dim)}")

            df = dim_def.apply_to_dataframe(df, source_column='value')

        # Validate output is DataFrame (FR-010)
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"Expected pd.DataFrame, got {type(df).__name__}")

        return Level2Dataset(df, name=f"table_{dataset.name}")

    @staticmethod
    def _increase_2_to_3(dataset: Level2Dataset, **kwargs) -> Level3Dataset:
        """
        L2 -> L3: Table to Linkable.
        Adds hierarchical/analytic dimensions for multi-level grouping.

        Args:
            dataset: Level2Dataset
            dimensions: List of dimension names or DimensionDefinition objects
            relationships: List of RelationshipDefinition objects for graph creation
            **kwargs: Additional parameters

        Returns:
            Level3Dataset with analytic dimensions and optional graph structure
        """
        from .ascent.dimensions import (
            DimensionRegistry, DimensionDefinition, RelationshipDefinition,
            apply_relationships_to_dataframe, create_graph_from_relationships
        )

        registry = DimensionRegistry.get_instance()
        df = dataset.get_data().copy()

        # Get dimensions to apply
        dimensions = kwargs.get('dimensions', [])
        relationships = kwargs.get('relationships', [])

        if not dimensions and not relationships:
            # Use defaults if nothing specified
            defaults = registry.get_defaults(
                ComplexityLevel.LEVEL_2, ComplexityLevel.LEVEL_3
            )
            if defaults:
                dimensions = [d.name for d in defaults]

        # Store initial row count for integrity check (FR-005)
        initial_row_count = len(df)

        # Apply each dimension
        source_column = kwargs.get('source_column')
        if source_column is None and 'value' in df.columns:
            source_column = 'value'
        elif source_column is None and len(df.columns) > 0:
            source_column = df.columns[0]

        for dim in dimensions:
            if isinstance(dim, str):
                dim_def = registry.get(dim)
            elif isinstance(dim, DimensionDefinition):
                dim_def = dim
            else:
                raise TypeError(f"Expected dimension name or DimensionDefinition, got {type(dim)}")

            df = dim_def.apply_to_dataframe(df, source_column=source_column)

        # Apply relationship definitions (T037: drag-and-drop support)
        if relationships:
            # Convert dict relationships to RelationshipDefinition if needed
            rel_defs = []
            for rel in relationships:
                if isinstance(rel, RelationshipDefinition):
                    rel_defs.append(rel)
                elif isinstance(rel, dict):
                    rel_defs.append(RelationshipDefinition.from_dict(rel))
                else:
                    raise TypeError(f"Expected RelationshipDefinition or dict, got {type(rel)}")

            df = apply_relationships_to_dataframe(df, rel_defs, source_column)

        # Validate row count preserved (FR-005)
        if len(df) != initial_row_count:
            raise ValueError(
                f"Data integrity error: row count changed during ascent. "
                f"Before: {initial_row_count}, After: {len(df)}"
            )

        return Level3Dataset(df)
