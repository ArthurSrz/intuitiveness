"""
Level-Specific Display Components Package

Implements Spec 003: Level Visualizations (FR-001-015)
Extracted from ui/level_displays.py (314 → 5 focused modules)

This package provides reusable display functions for each abstraction level:
- l4_display: File list (L4 raw data)
- l3_display: Graph with entity/relationship tabs (L3 knowledge graph)
- l2_display: Domain-categorized table (L2 structured table)
- l1_display: Vector visualization (L1 series)
- l0_display: Atomic metric card (L0 datum)

Each level has its own focused module (<150 lines) for maintainability.

Usage:
    from intuitiveness.ui.levels import (
        render_l0_datum,
        render_l1_vector,
        render_l2_domain_table,
        render_l3_graph_with_tabs,
        render_l4_file_list,
    )
"""

from intuitiveness.ui.levels.l0_display import render_l0_datum
from intuitiveness.ui.levels.l1_display import render_l1_vector
from intuitiveness.ui.levels.l2_display import render_l2_domain_table
from intuitiveness.ui.levels.l3_display import render_l3_graph_with_tabs
from intuitiveness.ui.levels.l4_display import render_l4_file_list

__all__ = [
    "render_l0_datum",
    "render_l1_vector",
    "render_l2_domain_table",
    "render_l3_graph_with_tabs",
    "render_l4_file_list",
]
