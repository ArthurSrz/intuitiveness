"""
Ascent Test Configurations.

Implements Spec 006: Test fixtures for ascent automation

Provides expected values and configurations for each dataset's
ascent phase (L0→L1→L2→L3).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any
from pathlib import Path


TEST_DATA_DIR = Path(__file__).parent.parent.parent.parent / "test_data"


@dataclass
class AscentConfig:
    """Configuration for a single dataset's ascent test."""

    test_name: str
    files: List[str]

    # Expected L0 datum
    l0_value: float
    l0_aggregation: str = "mean"  # or "sum"

    # Expected L1 vector
    l1_vector_length: int = 0
    l1_column_name: str = ""

    # L1→L2 domain enrichment
    l2_domains: List[str] = field(default_factory=list)
    l2_use_semantic: bool = False
    l2_threshold: float = 0.7

    # L2→L3 graph building
    l3_linkage_key: str = ""
    l3_entity_type: str = "Entity"
    l3_relationship_type: str = "RELATES_TO"
    l3_expected_columns: int = 0

    # Performance expectations
    max_ascent_time_seconds: float = 20.0


# =============================================================================
# DATASET CONFIGURATIONS
# =============================================================================

SCHOOLS_CONFIG = AscentConfig(
    test_name="test0_schools",
    files=[
        str(TEST_DATA_DIR / "test0" / "fr-en-college-effectifs-niveau-sexe-lv.csv"),
        str(TEST_DATA_DIR / "test0" / "fr-en-indicateurs-valeur-ajoutee-colleges.csv")
    ],

    # L0 datum: mean success rate
    l0_value=88.2537,
    l0_aggregation="mean",

    # L1 vector: all school success rates
    l1_vector_length=410,
    l1_column_name="Taux de réussite G",

    # L1→L2: categorize by performance
    l2_domains=["high_score", "low_score"],
    l2_use_semantic=False,  # Keyword matching is faster
    l2_threshold=0.7,

    # L2→L3: linkage key for future demographic joins
    l3_linkage_key="Commune",
    l3_entity_type="School",
    l3_relationship_type="LOCATED_IN",
    l3_expected_columns=0,  # TBD based on implementation

    max_ascent_time_seconds=20.0
)


ADEME_CONFIG = AscentConfig(
    test_name="test1_ademe",
    files=[
        str(TEST_DATA_DIR / "test1" / "ECS.csv"),
        str(TEST_DATA_DIR / "test1" / "Les aides financieres ADEME.csv")
    ],

    # L0 datum: total funding amount
    l0_value=69586180.93,
    l0_aggregation="sum",

    # L1 vector: all individual funding amounts
    l1_vector_length=450,
    l1_column_name="montant",

    # L1→L2: categorize by funding size
    l2_domains=["above_10k", "below_10k"],
    l2_use_semantic=False,
    l2_threshold=0.7,

    # L2→L3: linkage key for project type
    l3_linkage_key="objet",
    l3_entity_type="Project",
    l3_relationship_type="FUNDED_FOR",
    l3_expected_columns=48,

    max_ascent_time_seconds=20.0
)


ENERGY_CONFIG = AscentConfig(
    test_name="test2_energy",
    files=[
        str(TEST_DATA_DIR / "test2" / "Niveaux_prix_TRVG.csv"),
        str(TEST_DATA_DIR / "test2" / "imports-exports-commerciaux.csv")
    ],

    # L0 datum: TBD based on implementation
    l0_value=0.0,
    l0_aggregation="sum",

    # L1 vector: energy prices
    l1_vector_length=0,  # TBD
    l1_column_name="",  # TBD

    # L1→L2: categorize by price level
    l2_domains=["high_price", "low_price"],
    l2_use_semantic=False,
    l2_threshold=0.7,

    # L2→L3: linkage key for energy type
    l3_linkage_key="",  # TBD
    l3_entity_type="EnergyPrice",
    l3_relationship_type="HAS_PRICE",
    l3_expected_columns=0,

    max_ascent_time_seconds=20.0
)


# Configuration registry
ALL_CONFIGS = {
    "test0_schools": SCHOOLS_CONFIG,
    "test1_ademe": ADEME_CONFIG,
    "test2_energy": ENERGY_CONFIG,
}


def get_config(test_name: str) -> AscentConfig:
    """
    Get ascent configuration for a test by name.

    Args:
        test_name: One of "test0_schools", "test1_ademe", "test2_energy"

    Returns:
        AscentConfig for the test

    Raises:
        KeyError: If test_name not found
    """
    if test_name not in ALL_CONFIGS:
        raise KeyError(
            f"Unknown test: {test_name}. "
            f"Available: {list(ALL_CONFIGS.keys())}"
        )
    return ALL_CONFIGS[test_name]


def get_all_configs() -> List[AscentConfig]:
    """Get all ascent configurations."""
    return list(ALL_CONFIGS.values())
