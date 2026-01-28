"""
Data Sources Module
====================

External data source integrations for the Data Redesign Method.

Feature: 008-datagouv-mcp
"""

from intuitiveness.data_sources.mcp_client import MCPClient
from intuitiveness.data_sources.datagouv import DataGouvClient
from intuitiveness.data_sources.nl_query import NLQueryEngine, NLQueryResult, parse_french_query

# Quality-aware filtering (Spec 008: extends Spec 009)
from intuitiveness.data_sources.quality_filter import (
    DatasetQualityScore,
    quick_assess_dataset,
    filter_by_quality,
    get_quality_cache_key,
    should_show_quality_indicator,
)

__all__ = [
    'MCPClient',
    'DataGouvClient',
    'NLQueryEngine',
    'NLQueryResult',
    'parse_french_query',
    # Quality filtering
    'DatasetQualityScore',
    'quick_assess_dataset',
    'filter_by_quality',
    'get_quality_cache_key',
    'should_show_quality_indicator',
]
