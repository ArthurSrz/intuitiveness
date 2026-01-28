"""
Quality Dashboard Package

Phase 1.3 - Code Simplification (011-code-simplification)
Extracted from quality_dashboard.py (2,211 lines)

Package Structure:
------------------
- utils.py          : Score coloring, session state keys
- state.py          : Report history, score evolution display
- upload.py         : File upload, target selection (US-1 Step 1)
- assessment.py     : Assessment button with progress (US-1 Step 2)
- suggestions.py    : Feature suggestions, apply all (US-1 Step 3, FR-002)
- readiness.py      : Traffic light indicator (US-4, FR-001)

Spec Traceability:
------------------
- 009-quality-data-platform: Quality assessment core
- 010-quality-ds-workflow: DS Co-Pilot features (US-1 through US-4)

Usage:
------
# Import from package (preferred)
from intuitiveness.ui.quality import render_file_upload, render_assessment_button

# Or import full dashboard from original location (backward compatible)
from intuitiveness.ui.quality_dashboard import render_quality_dashboard
"""

# Core utilities
from intuitiveness.ui.quality.utils import (
    # Session state keys
    SESSION_KEY_QUALITY_REPORT,
    SESSION_KEY_QUALITY_DF,
    SESSION_KEY_QUALITY_FILE_NAME,
    SESSION_KEY_ASSESSMENT_PROGRESS,
    SESSION_KEY_APPLIED_SUGGESTIONS,
    SESSION_KEY_TRANSFORMED_DF,
    SESSION_KEY_TRANSFORMATION_LOG,
    SESSION_KEY_BENCHMARK_REPORT,
    SESSION_KEY_EXPORT_FORMAT,
    SESSION_KEY_QUALITY_REPORTS_HISTORY,
    SESSION_KEY_CURRENT_REPORT_INDEX,
    # Functions
    get_score_color,
    get_score_label,
)

# State management
from intuitiveness.ui.quality.state import (
    save_report_to_history,
    get_initial_report,
    get_current_report,
    clear_report_history,
    render_quality_score_evolution,
)

# Upload components (US-1 Step 1)
from intuitiveness.ui.quality.upload import (
    render_file_upload,
    render_target_selection,
)

# Assessment components (US-1 Step 2)
from intuitiveness.ui.quality.assessment import (
    render_assessment_button,
)

# Suggestion components (US-1 Step 3, FR-002)
from intuitiveness.ui.quality.suggestions import (
    render_feature_suggestions,
    render_apply_all_button,
)

# Readiness components (US-4, FR-001)
from intuitiveness.ui.quality.readiness import (
    render_readiness_indicator,
    render_tabpfn_methodology,
)

# Anomaly detection components (Spec 009: FR-003, FR-007)
from intuitiveness.ui.quality.anomaly_ui import (
    render_anomaly_detection,
    render_anomaly_results,
    render_anomaly_export,
)

# 60-second workflow components (Spec 010: FR-001 through FR-005)
from intuitiveness.ui.quality.workflow_ui import (
    render_traffic_light_indicator,
    render_apply_all_button,
    render_transformation_summary,
    render_export_section,
    render_60_second_workflow,
)

# ML Diagnostics (Spec 011: extracted from quality_dashboard.py)
from intuitiveness.ui.quality.ml_diagnostics import (
    render_ml_diagnostics,
)

__all__ = [
    # Session state keys
    'SESSION_KEY_QUALITY_REPORT',
    'SESSION_KEY_QUALITY_DF',
    'SESSION_KEY_QUALITY_FILE_NAME',
    'SESSION_KEY_ASSESSMENT_PROGRESS',
    'SESSION_KEY_APPLIED_SUGGESTIONS',
    'SESSION_KEY_TRANSFORMED_DF',
    'SESSION_KEY_TRANSFORMATION_LOG',
    'SESSION_KEY_BENCHMARK_REPORT',
    'SESSION_KEY_EXPORT_FORMAT',
    'SESSION_KEY_QUALITY_REPORTS_HISTORY',
    'SESSION_KEY_CURRENT_REPORT_INDEX',

    # Utilities
    'get_score_color',
    'get_score_label',

    # State management
    'save_report_to_history',
    'get_initial_report',
    'get_current_report',
    'clear_report_history',
    'render_quality_score_evolution',

    # Upload (US-1 Step 1)
    'render_file_upload',
    'render_target_selection',

    # Assessment (US-1 Step 2)
    'render_assessment_button',

    # Suggestions (US-1 Step 3, FR-002)
    'render_feature_suggestions',
    'render_apply_all_button',

    # Readiness (US-4, FR-001)
    'render_readiness_indicator',
    'render_tabpfn_methodology',

    # Anomaly detection (Spec 009: FR-003, FR-007)
    'render_anomaly_detection',
    'render_anomaly_results',
    'render_anomaly_export',

    # 60-second workflow (Spec 010: FR-001 through FR-005)
    'render_traffic_light_indicator',
    'render_apply_all_button',
    'render_transformation_summary',
    'render_export_section',
    'render_60_second_workflow',

    # ML Diagnostics (Spec 011)
    'render_ml_diagnostics',
]
