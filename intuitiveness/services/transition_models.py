"""Pydantic output models for each complexity level transition.

Each model defines the exact shape the LLM must produce when suggesting
how to perform a transition. These models serve three roles:
  1. JSON schema sent to the LLM API (structured output constraint)
  2. Validation layer when parsing the response
  3. Contract between services and router endpoints

Descent: L4→L3 (entity), L3→L2 (domain), L2→L1 (column), L1→L0 (aggregation)
Ascent:  L0→L1 (enrichment), L1→L2 (dimension), L2→L3 (linkage)
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# L3 → L2: Domain categorization (descent)
# --------------------------------------------------------------------------- #

class DomainSuggestion(BaseModel):
    """LLM output for L3→L2 domain categorization.

    The LLM analyzes a dataset and proposes how to split it into
    meaningful domain categories (e.g. "urban"/"rural", "high"/"low").
    """
    proposed_column: str = Field(
        description="The column chosen for categorization."
    )
    proposed_domains: List[str] = Field(
        description="2-4 meaningful category names (e.g. ['urban', 'rural'])."
    )
    code: str = Field(
        description="Python code that creates df['category']. Must end with .fillna('uncategorized').astype(str)."
    )
    explanation: str = Field(
        description="2-3 sentences explaining why these thresholds are meaningful."
    )


# --------------------------------------------------------------------------- #
# L2 → L1: Column extraction (descent)
# --------------------------------------------------------------------------- #

class ColumnSuggestion(BaseModel):
    """LLM output for L2→L1 column extraction.

    The LLM analyzes an L2 table and proposes which column to extract
    as an L1 vector, plus optional filtering code.
    """
    proposed_column: str = Field(
        description="The column chosen for extraction."
    )
    proposed_filter: Optional[str] = Field(
        default=None,
        description="Optional filter condition to apply before extraction."
    )
    code: str = Field(
        description="Python code that extracts the column from the DataFrame, applying any filter if provided."
    )
    explanation: str = Field(
        description="2-3 sentences explaining why this column is meaningful and how the filter (if any) improves the extraction."
    )


# --------------------------------------------------------------------------- #
# L1 → L0: Aggregation (descent)
# --------------------------------------------------------------------------- #

class AggregationSuggestion(BaseModel):
    """LLM output for L1→L0 aggregation.

    The LLM analyzes an L1 vector and proposes how to compress it
    to a single L0 datum (e.g. mean, median, sum).
    """
    proposed_aggregation: str = Field(
        description="The aggregation method (e.g. 'mean', 'median', 'sum')."
    )
    code: str = Field(
        description="Python code that computes the scalar value from a pandas Series called 'series'."
    )
    explanation: str = Field(
        description="Why this aggregation is appropriate for this data."
    )
    preview_value: Optional[float] = Field(
        default=None,
        description="Preview of the aggregated value on sample data."
    )


# --------------------------------------------------------------------------- #
# L0 → L1: Enrichment (ascent)
# --------------------------------------------------------------------------- #

class EnrichmentSuggestion(BaseModel):
    """LLM output for L0→L1 enrichment.

    The LLM writes code to reconstruct an L1 vector from an L0 datum,
    using the parent series as context.
    """
    code: str = Field(
        description="Python code that builds a pandas Series from 'scalar' and 'parent_series'."
    )
    explanation: str = Field(
        description="How the enrichment reconstructs the vector."
    )
    preview_description: str = Field(
        default="",
        description="Short description of what the resulting vector represents."
    )


# --------------------------------------------------------------------------- #
# L1 → L2: Dimension analysis (ascent)
# --------------------------------------------------------------------------- #

class DimensionSuggestion(BaseModel):
    """LLM output for L1→L2 dimension analysis.

    The LLM writes code to add analytical dimensions to an L1 vector,
    producing an L2 table with new columns.
    """
    code: str = Field(
        description="Python code that adds columns to a DataFrame built from 'series'. Must produce a DataFrame."
    )
    proposed_columns: List[str] = Field(
        description="Names of the new columns the code will add."
    )
    explanation: str = Field(
        description="What analytical dimensions are being added and why."
    )


# --------------------------------------------------------------------------- #
# L2 → L3: Linkage (ascent)
# --------------------------------------------------------------------------- #

class LinkageSuggestion(BaseModel):
    """LLM output for L2→L3 linkage.

    The LLM writes code to add relationship/linkage columns to an L2
    table, producing an L3-ready structure with richer connections.
    """
    code: str = Field(
        description="Python code that adds linkage columns to 'df'. Must return a DataFrame."
    )
    proposed_columns: List[str] = Field(
        description="Names of the new linkage columns."
    )
    explanation: str = Field(
        description="What relationships are being captured."
    )
    graph_description: str = Field(
        default="",
        description="How the resulting structure could be interpreted as a graph."
    )


# --------------------------------------------------------------------------- #
# L0: Intent suggestion (at the bottom of descent)
# --------------------------------------------------------------------------- #

class IntentSuggestion(BaseModel):
    """LLM output for suggesting analytical intents at L0.

    After reaching L0, the LLM suggests what questions the user could
    explore during the ascent phase.
    """
    intents: List[dict] = Field(
        description="List of intent objects, each with 'short' (title) and 'long' (description) keys."
    )


# --------------------------------------------------------------------------- #
# L0: Datum description (plain language summary)
# --------------------------------------------------------------------------- #

class DatumDescription(BaseModel):
    """LLM output for describing an L0 datum in plain language."""
    title: str = Field(
        description="Short title for the datum (e.g. 'Average school score')."
    )
    description: str = Field(
        description="1-2 sentence plain-language description of what this value means."
    )


# --------------------------------------------------------------------------- #
# L4 → L3: Entity matching
# --------------------------------------------------------------------------- #

class EntityCatalogMapping(BaseModel):
    source: str = Field(description="Source filename.")
    column: str = Field(description="Column name in that source.")
    notes: str = Field(default="", description="How the column maps to the concept.")

class EntityCatalogEntry(BaseModel):
    concept: str = Field(description="The real-world concept (e.g. 'Time Period').")
    description: str = Field(default="", description="What this concept represents.")
    mappings: List[EntityCatalogMapping] = Field(description="Which source columns map to this concept.")

class EntityMatchSuggestion(BaseModel):
    """LLM output for L4→L3 entity matching.

    The LLM analyzes multiple data sources and identifies shared concepts
    (entities) that can be used to join them into a knowledge graph.
    """
    catalog: List[EntityCatalogEntry] = Field(
        description="Entity catalog: concepts shared across sources with their column mappings."
    )
    join_plan: dict = Field(
        default_factory=dict,
        description="Join strategy with join_key, join_type, and confidence."
    )
    column_transforms: dict = Field(
        default_factory=dict,
        description="Per-column transforms needed before joining (e.g. extract_year)."
    )
    explanation: str = Field(
        default="",
        description="How the sources are related and why these join keys were chosen."
    )
