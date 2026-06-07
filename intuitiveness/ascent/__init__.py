"""
Ascent subpackage for the Data Redesign Method.

Provides functionality for ascending through abstraction levels (L0→L1→L2→L3).
"""

from .enrichment import EnrichmentFunction, EnrichmentRegistry
from .dimensions import (
    DimensionDefinition,
    DimensionRegistry,
    suggest_dimensions,
    find_duplicates,
    create_dimension_groups,
    get_dimension_hierarchy
)

__all__ = [
    'EnrichmentFunction',
    'EnrichmentRegistry',
    'DimensionDefinition',
    'DimensionRegistry',
    'suggest_dimensions',
    'find_duplicates',
    'create_dimension_groups',
    'get_dimension_hierarchy',
]
