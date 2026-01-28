"""
UI Components for Data Redesign Method

This package contains UI components for:
- Decision-tree navigation and drag-and-drop relationship builder (002-ascent-functionality)
- Level-specific display components (003-level-dataviz-display)
- Ascent UI forms for L0→L1, L1→L2, L2→L3 transitions (004-ascent-precision)

Features: 002-ascent-functionality, 003-level-dataviz-display, 004-ascent-precision
"""

from .drag_drop import DragDropRelationshipBuilder, get_entities_from_dataframe
from .decision_tree import DecisionTreeComponent, render_simple_tree
from .json_visualizer import JsonVisualizer, render_navigation_export

# Level-specific display components (003-level-dataviz-display)
# Updated for Spec 011: Extracted to ui/levels/ package
from .levels import (
    render_l0_datum,
    render_l1_vector,
    render_l2_domain_table,
    render_l3_graph_with_tabs,
    render_l4_file_list,
)

# Legacy imports for backward compatibility (TODO: Remove in future)
try:
    from .level_displays import (
        NavigationDirection,
        DisplayType,
        LevelDisplayConfig,
        LEVEL_DISPLAY_MAPPING,
        get_display_level,
        render_navigation_direction_indicator,
    )
except ImportError:
    # level_displays.py deleted - these are legacy
    NavigationDirection = None
    DisplayType = None
    LevelDisplayConfig = None
    LEVEL_DISPLAY_MAPPING = None
    get_display_level = None
    render_navigation_direction_indicator = None

# Entity/relationship tab components (003-level-dataviz-display)
from .entity_tabs import (
    EntityTabData,
    RelationshipTabData,
    CombinedTabData,
    extract_entity_tabs,
    extract_relationship_tabs,
    render_entity_relationship_tabs,
    create_combined_all_table,
    create_combined_entity_table,
    create_combined_relationship_table,
    get_graph_summary,
)

# Recovery banner (005-session-persistence)
from .recovery_banner import (
    RecoveryAction,
    render_recovery_banner,
    render_start_fresh_button,
    render_start_fresh_confirmation,
    format_time_ago,
)

# Internationalization (006-playwright-mcp-e2e)
from .i18n import (
    t,
    get_language,
    set_language,
    render_language_toggle,
    render_language_toggle_compact,
    TRANSLATIONS,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    SESSION_KEY_LANGUAGE,
)

# Metric card component (007-streamlit-design-makeup)
from .metric_card import (
    render_metric_card,
    render_metric_card_row,
)

# Custom alert component (007-streamlit-design-makeup)
from .alert import (
    render_alert,
    info as alert_info,
    success as alert_success,
    warning as alert_warning,
    error as alert_error,
    tip as alert_tip,
)

# Custom button component (007-streamlit-design-makeup)
from .button import (
    render_button,
    render_button_row,
    primary_button,
    secondary_button,
    ghost_button,
    danger_button,
)

# Custom accordion component (007-streamlit-design-makeup)
from .accordion import (
    render_accordion,
    render_accordion_group,
)

# SaaS-style header component (007-streamlit-design-makeup)
from .header import (
    render_page_header,
    render_section_header,
    render_card_header,
)

# Layout helpers (007-streamlit-design-makeup)
from .layout import (
    card,
    render_card,
    separator,
    spacer,
    two_column_layout,
)

# Data.gouv.fr search interface (008-datagouv-search)
from .datagouv_search import (
    render_search_interface,
    render_search_bar,
    render_dataset_grid,
    render_resource_selector,
    render_basket_sidebar,
)

# Sarazin & Mourey tutorial (007-streamlit-design-makeup, Phase 9)
from .tutorial import (
    render_tutorial,
    render_tutorial_replay_button,
    is_tutorial_completed,
    mark_tutorial_completed,
    skip_tutorial,
    reset_tutorial,
    SESSION_KEY_TUTORIAL_COMPLETED,
    SESSION_KEY_TUTORIAL_STEP,
    TUTORIAL_STEPS,
)

# Quality Data Platform (009-quality-data-platform)
from .quality_dashboard import render_quality_dashboard
from .catalog_browser import render_catalog_browser

# Ascent UI forms (004-ascent-precision)
# Updated for Spec 011: Extracted to ui/ascent/ package
from .ascent import (
    # Form renderers
    render_l0_to_l1_unfold_form,
    render_l1_to_l2_domain_form,
    render_l2_to_l3_entity_form,
    # Constants
    DEFAULT_SIMILARITY_THRESHOLD,
    DEFAULT_DOMAINS,
)

# Discovery wizard components (still in ascent_forms.py)
from .ascent_forms import (
    # Shared components
    _render_domain_categorization_inputs,
    _parse_domains,
    _apply_domain_categorization,
    DEFAULT_UNMATCHED_LABEL,
    # Discovery wizard components (Step 2 simplification)
    render_wizard_step_1_columns,
    render_wizard_step_1_entities,
    render_wizard_step_2_connections,
    render_wizard_step_2_relationships,
    render_wizard_step_3_confirm,
    convert_suggestions_to_mappings,
    _get_wizard_step,
    _set_wizard_step,
    SESSION_KEY_WIZARD_STEP,
    SESSION_KEY_DISCOVERY_RESULTS,
    # Step 3 join helpers
    _build_semantic_mapping,
    _perform_table_join,
)

__all__ = [
    # Drag-and-drop relationship builder (L2→L3)
    'DragDropRelationshipBuilder',
    'get_entities_from_dataframe',
    # Decision tree sidebar component
    'DecisionTreeComponent',
    'render_simple_tree',
    # JSON visualization
    'JsonVisualizer',
    'render_navigation_export',
    # Level-specific displays (003-level-dataviz-display)
    'NavigationDirection',
    'DisplayType',
    'LevelDisplayConfig',
    'LEVEL_DISPLAY_MAPPING',
    'get_display_level',
    'render_l4_file_list',
    'render_l2_domain_table',
    'render_l1_vector',
    'render_l0_datum',
    'render_navigation_direction_indicator',
    # Entity/relationship tabs (003-level-dataviz-display)
    'EntityTabData',
    'RelationshipTabData',
    'CombinedTabData',
    'extract_entity_tabs',
    'extract_relationship_tabs',
    'render_entity_relationship_tabs',
    'create_combined_all_table',
    'create_combined_entity_table',
    'create_combined_relationship_table',
    'get_graph_summary',
    # Ascent UI forms (004-ascent-precision)
    'render_l0_to_l1_unfold_form',
    'render_l1_to_l2_domain_form',
    'render_l2_to_l3_entity_form',
    '_render_domain_categorization_inputs',
    '_parse_domains',
    '_apply_domain_categorization',
    'DEFAULT_SIMILARITY_THRESHOLD',
    'DEFAULT_UNMATCHED_LABEL',
    'DEFAULT_DOMAINS',
    # Discovery wizard components (Step 2 simplification)
    'render_wizard_step_1_columns',
    'render_wizard_step_1_entities',
    'render_wizard_step_2_connections',
    'render_wizard_step_2_relationships',
    'render_wizard_step_3_confirm',
    'convert_suggestions_to_mappings',
    '_get_wizard_step',
    '_set_wizard_step',
    'SESSION_KEY_WIZARD_STEP',
    'SESSION_KEY_DISCOVERY_RESULTS',
    # Step 3 join helpers
    '_build_semantic_mapping',
    '_perform_table_join',
    # Recovery banner (005-session-persistence)
    'RecoveryAction',
    'render_recovery_banner',
    'render_start_fresh_button',
    'render_start_fresh_confirmation',
    'format_time_ago',
    # Internationalization (006-playwright-mcp-e2e)
    't',
    'get_language',
    'set_language',
    'render_language_toggle',
    'render_language_toggle_compact',
    'TRANSLATIONS',
    'SUPPORTED_LANGUAGES',
    'DEFAULT_LANGUAGE',
    'SESSION_KEY_LANGUAGE',
    # Metric card component (007-streamlit-design-makeup)
    'render_metric_card',
    'render_metric_card_row',
    # Custom alert component (007-streamlit-design-makeup)
    'render_alert',
    'alert_info',
    'alert_success',
    'alert_warning',
    'alert_error',
    'alert_tip',
    # Custom button component (007-streamlit-design-makeup)
    'render_button',
    'render_button_row',
    'primary_button',
    'secondary_button',
    'ghost_button',
    'danger_button',
    # Custom accordion component (007-streamlit-design-makeup)
    'render_accordion',
    'render_accordion_group',
    # SaaS-style header component (007-streamlit-design-makeup)
    'render_page_header',
    'render_section_header',
    'render_card_header',
    # Layout helpers (007-streamlit-design-makeup)
    'card',
    'render_card',
    'separator',
    'spacer',
    'two_column_layout',
    # Data.gouv.fr search interface (008-datagouv-search)
    'render_search_interface',
    'render_search_bar',
    'render_dataset_grid',
    'render_resource_selector',
    'render_basket_sidebar',
    # Sarazin & Mourey tutorial (007-streamlit-design-makeup, Phase 9)
    'render_tutorial',
    'render_tutorial_replay_button',
    'is_tutorial_completed',
    'mark_tutorial_completed',
    'skip_tutorial',
    'reset_tutorial',
    'SESSION_KEY_TUTORIAL_COMPLETED',
    'SESSION_KEY_TUTORIAL_STEP',
    'TUTORIAL_STEPS',
    # Quality Data Platform (009-quality-data-platform)
    'render_quality_dashboard',
    'render_catalog_browser',
]
