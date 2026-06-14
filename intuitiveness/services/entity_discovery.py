"""
Three-Tier Entity Discovery (spec 5.3.2)
==========================================

Progressive relationship discovery between L4 source DataFrames:

  Tier 1 — Name heuristics (~5ms): column name pattern matching
  Tier 2 — Value overlap (~100ms): Jaccard similarity on sampled values
  Tier 3 — Semantic embeddings (~2s): LLM-powered conceptual matching

Each tier produces scored relationship candidates. Results are merged,
deduplicated, and ranked by combined confidence before presentation.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ColumnRelationship:
    """A discovered relationship between two columns across sources."""
    source_a: str
    column_a: str
    source_b: str
    column_b: str
    concept: str
    description: str
    confidence: float  # 0.0–1.0
    tier: int  # which tier discovered it (1, 2, or 3)
    method: str  # e.g. "name_exact", "jaccard", "embedding"
    details: str = ""


@dataclass
class DiscoveryResult:
    """Combined output from all three tiers."""
    relationships: List[ColumnRelationship] = field(default_factory=list)
    catalog: List[dict] = field(default_factory=list)
    explanation: str = ""
    tier_timings: Dict[str, float] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Tier 1 — Name Heuristics (~5ms)
# ─────────────────────────────────────────────────────────────────────────────

_ID_PATTERNS = re.compile(r"(?:^id$|_id$|^id_|_key$|_code$|_num$|_no$)", re.IGNORECASE)
_TEMPORAL_NAMES = {"year", "date", "annee", "année", "month", "mois", "period", "time",
                   "timestamp", "created_at", "updated_at", "jour", "day"}
_GEO_NAMES = {"country", "pays", "region", "département", "departement", "commune",
              "ville", "city", "state", "province", "code_postal", "zip", "lat",
              "lon", "longitude", "latitude", "territoire", "zone", "area"}
_ENTITY_NAMES = {"name", "nom", "label", "title", "titre", "description",
                 "etablissement", "organisation", "organization", "company",
                 "institution", "school", "college", "lycee"}

_CONCEPT_SETS = {
    "Temporal": _TEMPORAL_NAMES,
    "Geographic": _GEO_NAMES,
    "Entity ID": _ENTITY_NAMES,
}

# Measurement columns: same name ≠ same data. "value" in GDP ≠ "value" in
# life expectancy. These must NOT be proposed as join keys by name alone;
# only Tier 2 (value overlap) or Tier 3 (LLM) may promote them.
_MEASUREMENT_NAMES = {
    "value", "valeur", "values", "amount", "montant", "count", "nombre",
    "total", "sum", "score", "rate", "taux", "ratio", "percent",
    "percentage", "mean", "average", "median", "min", "max", "std",
    "quantity", "quantite", "result", "resultat", "measure", "mesure",
    "indicator", "indicateur", "observation", "data", "donnee",
    "unit", "unite", "units", "currency", "devise",
}


def _normalize_col(name: str) -> str:
    """Normalize a column name for comparison."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _col_concept(name: str) -> Optional[str]:
    """Detect which concept family a column belongs to."""
    norm = name.lower().strip()
    for concept, names in _CONCEPT_SETS.items():
        if norm in names or any(n in norm for n in names):
            return concept
    if _ID_PATTERNS.search(norm):
        return "Entity ID"
    return None


def tier1_name_heuristics(
    sources: Dict[str, pd.DataFrame],
) -> List[ColumnRelationship]:
    """Match columns by name patterns across sources."""
    results: List[ColumnRelationship] = []
    source_names = list(sources.keys())

    for i, src_a in enumerate(source_names):
        cols_a = list(sources[src_a].columns)
        for src_b in source_names[i + 1:]:
            cols_b = list(sources[src_b].columns)

            for ca in cols_a:
                norm_a = _normalize_col(ca)
                concept_a = _col_concept(ca)

                for cb in cols_b:
                    norm_b = _normalize_col(cb)
                    concept_b = _col_concept(cb)

                    # Exact name match — but skip measurement columns
                    if norm_a == norm_b and norm_a:
                        if norm_a in _MEASUREMENT_NAMES:
                            continue
                        results.append(ColumnRelationship(
                            source_a=src_a, column_a=ca,
                            source_b=src_b, column_b=cb,
                            concept=ca, description=f"Same column name in both sources",
                            confidence=0.95, tier=1, method="name_exact",
                        ))
                        continue

                    # Same concept family
                    if concept_a and concept_a == concept_b:
                        results.append(ColumnRelationship(
                            source_a=src_a, column_a=ca,
                            source_b=src_b, column_b=cb,
                            concept=concept_a,
                            description=f"Both columns relate to {concept_a.lower()} information",
                            confidence=0.7, tier=1, method="name_concept",
                        ))

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Tier 2 — Value Overlap (~100ms)
# ─────────────────────────────────────────────────────────────────────────────

_SAMPLE_SIZE = 200


def _sample_unique(series: pd.Series, n: int = _SAMPLE_SIZE) -> Set[str]:
    """Get a stratified sample of unique string values."""
    vals = series.dropna().unique()
    if len(vals) > n:
        idx = np.linspace(0, len(vals) - 1, n, dtype=int)
        vals = vals[idx]
    return {str(v).strip().lower() for v in vals if str(v).strip()}


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union > 0 else 0.0


def _dtype_compatible(a: pd.Series, b: pd.Series) -> bool:
    """Check if two columns have compatible data types."""
    a_numeric = pd.api.types.is_numeric_dtype(a)
    b_numeric = pd.api.types.is_numeric_dtype(b)
    if a_numeric and b_numeric:
        return True
    a_str = pd.api.types.is_string_dtype(a) or pd.api.types.is_object_dtype(a)
    b_str = pd.api.types.is_string_dtype(b) or pd.api.types.is_object_dtype(b)
    if a_str and b_str:
        return True
    return False


def tier2_value_overlap(
    sources: Dict[str, pd.DataFrame],
    min_jaccard: float = 0.05,
) -> List[ColumnRelationship]:
    """Find column pairs with overlapping values via Jaccard similarity."""
    results: List[ColumnRelationship] = []
    source_names = list(sources.keys())

    # Pre-sample all columns
    samples: Dict[Tuple[str, str], Set[str]] = {}
    for src in source_names:
        for col in sources[src].columns:
            samples[(src, col)] = _sample_unique(sources[src][col])

    for i, src_a in enumerate(source_names):
        for src_b in source_names[i + 1:]:
            for ca in sources[src_a].columns:
                sa = samples[(src_a, ca)]
                if not sa:
                    continue

                for cb in sources[src_b].columns:
                    sb = samples[(src_b, cb)]
                    if not sb:
                        continue

                    # Skip if types are incompatible
                    if not _dtype_compatible(sources[src_a][ca], sources[src_b][cb]):
                        continue

                    jaccard = _jaccard(sa, sb)
                    if jaccard >= min_jaccard:
                        overlap_count = len(sa & sb)
                        confidence = min(0.95, jaccard * 1.2 + 0.1)
                        results.append(ColumnRelationship(
                            source_a=src_a, column_a=ca,
                            source_b=src_b, column_b=cb,
                            concept=f"{ca}/{cb}",
                            description=f"{overlap_count} shared values ({jaccard:.0%} overlap)",
                            confidence=confidence, tier=2, method="jaccard",
                            details=f"jaccard={jaccard:.3f}, overlap={overlap_count}",
                        ))

    # Sort by confidence, keep top matches
    results.sort(key=lambda r: r.confidence, reverse=True)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Tier 3 — Semantic Embeddings / LLM (~2s)
# ─────────────────────────────────────────────────────────────────────────────

def tier3_semantic(
    sources: Dict[str, pd.DataFrame],
    existing: List[ColumnRelationship],
) -> Tuple[List[ColumnRelationship], List[dict], str]:
    """Use LLM to find conceptually related columns and build a catalog.

    Skips column pairs already found by tiers 1-2 to avoid redundant work.
    Returns (new_relationships, catalog, explanation).
    """
    from intuitiveness.services.entity_matcher import (
        match_entities,
        _build_source_profile,
    )

    # Build the relationships list from existing tier 1-2 discoveries
    # so the LLM can focus on what's NOT yet found
    known_pairs = {
        (r.source_a, r.column_a, r.source_b, r.column_b) for r in existing
    } | {
        (r.source_b, r.column_b, r.source_a, r.column_a) for r in existing
    }

    # Pass existing relationships to the LLM so it can augment, not repeat
    hint_relationships = [
        {
            "source_a": r.source_a, "column_a": r.column_a,
            "source_b": r.source_b, "column_b": r.column_b,
        }
        for r in existing
    ]

    result = match_entities(sources, hint_relationships)

    if result.get("error"):
        logger.warning("Tier 3 (LLM) failed: %s", result["error"])
        return [], [], ""

    new_rels: List[ColumnRelationship] = []
    catalog = result.get("catalog", [])

    for entry in catalog:
        concept = entry.get("concept", "")
        description = entry.get("description", "")
        mappings = entry.get("mappings", [])

        for i, m_a in enumerate(mappings):
            for m_b in mappings[i + 1:]:
                pair = (m_a["source"], m_a["column"], m_b["source"], m_b["column"])
                if pair not in known_pairs:
                    new_rels.append(ColumnRelationship(
                        source_a=m_a["source"], column_a=m_a["column"],
                        source_b=m_b["source"], column_b=m_b["column"],
                        concept=concept, description=description,
                        confidence=0.6, tier=3, method="llm",
                    ))

    explanation = result.get("explanation", "")
    return new_rels, catalog, explanation


# ─────────────────────────────────────────────────────────────────────────────
# Combined Discovery
# ─────────────────────────────────────────────────────────────────────────────

def discover_entities(
    sources: Dict[str, pd.DataFrame],
    use_llm: bool = True,
) -> DiscoveryResult:
    """Run all three tiers and merge results into a unified catalog.

    Args:
        sources: {filename: DataFrame} — the L4 source data
        use_llm: whether to run Tier 3 (slower but finds semantic matches)

    Returns:
        DiscoveryResult with merged relationships and catalog
    """
    import time

    all_rels: List[ColumnRelationship] = []

    # Tier 1
    t0 = time.monotonic()
    tier1 = tier1_name_heuristics(sources)
    t1_time = time.monotonic() - t0
    all_rels.extend(tier1)
    logger.info("Tier 1 (name heuristics): %d relationships in %.1fms", len(tier1), t1_time * 1000)

    # Tier 2
    t0 = time.monotonic()
    tier2 = tier2_value_overlap(sources)
    t2_time = time.monotonic() - t0
    all_rels.extend(tier2)
    logger.info("Tier 2 (value overlap): %d relationships in %.1fms", len(tier2), t2_time * 1000)

    # Tier 3 (optional)
    catalog: List[dict] = []
    explanation = ""
    t3_time = 0.0
    if use_llm:
        t0 = time.monotonic()
        tier3_rels, catalog, explanation = tier3_semantic(sources, all_rels)
        t3_time = time.monotonic() - t0
        all_rels.extend(tier3_rels)
        logger.info("Tier 3 (LLM semantic): %d new relationships in %.1fs", len(tier3_rels), t3_time)

    # Deduplicate: keep the highest-confidence version of each column pair
    seen: Dict[Tuple[str, str, str, str], ColumnRelationship] = {}
    for r in all_rels:
        key = tuple(sorted([(r.source_a, r.column_a), (r.source_b, r.column_b)]))
        flat_key = (key[0][0], key[0][1], key[1][0], key[1][1])
        if flat_key not in seen or r.confidence > seen[flat_key].confidence:
            seen[flat_key] = r
    deduped = sorted(seen.values(), key=lambda r: r.confidence, reverse=True)

    # Build catalog from relationships if LLM didn't provide one
    if not catalog:
        catalog = _build_catalog_from_relationships(deduped)

    # Build explanation if not provided
    if not explanation:
        tier_counts = {}
        for r in deduped:
            tier_counts[r.tier] = tier_counts.get(r.tier, 0) + 1
        parts = []
        if tier_counts.get(1):
            parts.append(f"{tier_counts[1]} by column name patterns")
        if tier_counts.get(2):
            parts.append(f"{tier_counts[2]} by value overlap")
        if tier_counts.get(3):
            parts.append(f"{tier_counts[3]} by semantic analysis")
        explanation = f"Found {len(deduped)} relationships: {', '.join(parts)}."

    return DiscoveryResult(
        relationships=deduped,
        catalog=catalog,
        explanation=explanation,
        tier_timings={
            "tier1_ms": round(t1_time * 1000, 1),
            "tier2_ms": round(t2_time * 1000, 1),
            "tier3_s": round(t3_time, 2),
        },
    )


def _build_catalog_from_relationships(
    rels: List[ColumnRelationship],
) -> List[dict]:
    """Group relationships by concept into a catalog structure."""
    concepts: Dict[str, dict] = {}
    for r in rels:
        if r.concept not in concepts:
            concepts[r.concept] = {
                "concept": r.concept,
                "description": r.description,
                "mappings": [],
            }
        entry = concepts[r.concept]
        for src, col in [(r.source_a, r.column_a), (r.source_b, r.column_b)]:
            if not any(m["source"] == src and m["column"] == col for m in entry["mappings"]):
                entry["mappings"].append({
                    "source": src,
                    "column": col,
                    "notes": f"tier {r.tier}, {r.method} (confidence: {r.confidence:.0%})",
                })
    return list(concepts.values())


__all__ = [
    "discover_entities",
    "tier1_name_heuristics",
    "tier2_value_overlap",
    "tier3_semantic",
    "ColumnRelationship",
    "DiscoveryResult",
]
