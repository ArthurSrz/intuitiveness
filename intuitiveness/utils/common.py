"""
Common Utilities Module

Consolidates duplicated patterns across the intuitiveness package to reduce
code duplication and improve maintainability.

Created: 2026-01-09 (Phase 0 - Code Simplification)
Supports: ALL specs (utility layer)
"""

from typing import Optional, Literal
from datetime import datetime
import pandas as pd


# =============================================================================
# ALERT RENDERING UTILITIES
# =============================================================================

def format_alert_message(message: str, title: Optional[str] = None) -> str:
    """
    Format alert message with optional title.

    Consolidates the pattern repeated in ui/alert.py:
    `f"**{title}**\n\n{message}" if title else message`

    Args:
        message: Alert message content
        title: Optional title (prepended as bold text)

    Returns:
        Formatted message string

    Example:
        >>> format_alert_message("Please check your input", "Error")
        '**Error**\\n\\nPlease check your input'
        >>> format_alert_message("Success!")
        'Success!'
    """
    return f"**{title}**\n\n{message}" if title else message


# =============================================================================
# HTML/CSS CARD BUILDERS
# =============================================================================

def build_html_card(
    content: str,
    bg_color: str = "#ffffff",
    border_color: str = "#e2e8f0",
    border_radius: str = "0.5rem",
    padding: str = "1.25rem",
    shadow: str = "0 1px 3px rgba(0,0,0,0.05)",
) -> str:
    """
    Build HTML for a styled card container.

    Consolidates inline HTML patterns from metric_card.py, quality_dashboard.py, etc.

    Args:
        content: Inner HTML content
        bg_color: Background color (hex or CSS color)
        border_color: Border color
        border_radius: Border radius CSS value
        padding: Padding CSS value
        shadow: Box shadow CSS value

    Returns:
        Complete HTML card string

    Example:
        >>> html = build_html_card("<h3>My Card</h3><p>Content here</p>")
        >>> st.markdown(html, unsafe_allow_html=True)
    """
    return f'''<div style="background: {bg_color}; border-radius: {border_radius}; padding: {padding}; border: 1px solid {border_color}; box-shadow: {shadow};">
{content}
</div>'''


def build_html_badge(
    text: str,
    bg_color: str = "#3b82f6",
    text_color: str = "#ffffff",
    font_size: str = "0.75rem",
    padding: str = "0.25rem 0.5rem",
) -> str:
    """
    Build HTML for a styled badge/pill.

    Args:
        text: Badge text
        bg_color: Background color
        text_color: Text color
        font_size: Font size CSS value
        padding: Padding CSS value

    Returns:
        HTML badge string

    Example:
        >>> badge = build_html_badge("NEW", bg_color="#22c55e")
    """
    return f'<span style="background: {bg_color}; color: {text_color}; font-size: {font_size}; padding: {padding}; border-radius: 0.25rem; font-weight: 500;">{text}</span>'


# =============================================================================
# TYPE DETECTION UTILITIES (consolidates from assessor.py, benchmark.py)
# =============================================================================

def detect_task_type(y: pd.Series) -> Literal["classification", "regression"]:
    """
    Auto-detect whether target column is for classification or regression.

    Consolidated from quality/assessor.py (line 51) and quality/benchmark.py.

    Args:
        y: Target column series

    Returns:
        "classification" or "regression"

    Example:
        >>> y = pd.Series([0, 1, 0, 1, 1])  # Binary
        >>> detect_task_type(y)
        'classification'
        >>> y = pd.Series([1.2, 3.4, 5.6, 7.8])  # Continuous
        >>> detect_task_type(y)
        'regression'
    """
    # Check if target is categorical or has few unique values
    if y.dtype == "object" or y.dtype.name == "category":
        return "classification"

    n_unique = y.nunique()
    n_total = len(y)

    # If less than 20 unique values or less than 5% of total, treat as classification
    if n_unique <= 20 or (n_unique / n_total) < 0.05:
        return "classification"

    return "regression"


def detect_feature_type(
    series: pd.Series,
    categorical_threshold: int = 10
) -> Literal["numeric", "categorical", "boolean", "datetime"]:
    """
    Detect the type of a feature column.

    Consolidated from quality/assessor.py (line 75) and quality/benchmark.py.

    Args:
        series: Feature column series
        categorical_threshold: Max unique values to consider numeric as categorical

    Returns:
        Feature type string

    Example:
        >>> s = pd.Series([1, 2, 3, 4, 5])
        >>> detect_feature_type(s)
        'numeric'
        >>> s = pd.Series(['A', 'B', 'A', 'C'])
        >>> detect_feature_type(s)
        'categorical'
    """
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_numeric_dtype(series):
        # Check if it's really categorical (few unique values)
        if series.nunique() <= categorical_threshold:
            return "categorical"
        return "numeric"
    return "categorical"


# =============================================================================
# TEXT FORMATTING UTILITIES (consolidates from datagouv_client.py, etc.)
# =============================================================================

def format_filesize(size_bytes: Optional[int]) -> str:
    """
    Convert bytes to human-readable format.

    Consolidated from services/datagouv_client.py (line 94).

    Args:
        size_bytes: File size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")

    Example:
        >>> format_filesize(1536000)
        '1.5 MB'
        >>> format_filesize(None)
        'Unknown size'
    """
    if size_bytes is None:
        return "Unknown size"

    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def parse_iso_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse ISO datetime string from API responses.

    Consolidated from services/datagouv_client.py (line 106).

    Args:
        date_str: ISO format datetime string

    Returns:
        datetime object or None if parsing fails

    Example:
        >>> parse_iso_datetime("2024-01-15T10:30:00Z")
        datetime.datetime(2024, 1, 15, 10, 30, tzinfo=...)
        >>> parse_iso_datetime(None)
        None
    """
    if not date_str:
        return None
    try:
        # Handle various ISO formats
        if 'T' in date_str:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return datetime.strptime(date_str[:10], '%Y-%m-%d')
    except (ValueError, TypeError):
        return None


def truncate_text(
    text: Optional[str],
    max_length: int = 400,
    clean_whitespace: bool = True
) -> str:
    """
    Truncate text to max_length chars with ellipsis.

    Consolidated from services/datagouv_client.py (line 119).

    Args:
        text: Text to truncate
        max_length: Maximum character length
        clean_whitespace: Whether to normalize whitespace

    Returns:
        Truncated text with "..." if shortened, empty string if None

    Example:
        >>> truncate_text("This is a very long description...", max_length=20)
        'This is a very...'
        >>> truncate_text(None)
        ''
    """
    if not text:
        return ""

    text = text.strip()

    # Clean whitespace if requested
    if clean_whitespace:
        text = text.replace('\n', ' ').replace('\r', ' ')

    if len(text) <= max_length:
        return text

    # Truncate at word boundary
    return text[:max_length - 3].rsplit(' ', 1)[0] + "..."


# =============================================================================
# COLOR UTILITIES (for score-based coloring, repeated patterns)
# =============================================================================

def score_to_color(
    score: float,
    thresholds: tuple = (60, 80),
    colors: tuple = ("#ef4444", "#f59e0b", "#22c55e")
) -> str:
    """
    Map a score (0-100) to a color based on thresholds.

    Consolidates pattern from quality/report.py and quality_dashboard.py.

    Supports both 3-color (default) and 4-color modes:
    - 3-color: thresholds=(60, 80), colors=(red, yellow, green)
    - 4-color: thresholds=(40, 60, 80), colors=(red, orange, yellow, green)

    Args:
        score: Score value (0-100)
        thresholds: Threshold tuple (2 or 3 values)
        colors: Color tuple (must be len(thresholds) + 1)

    Returns:
        Color hex string

    Example:
        >>> score_to_color(45)  # 3-color default: Below 60
        '#ef4444'  # Red
        >>> score_to_color(72)  # 3-color default: Between 60-80
        '#f59e0b'  # Yellow
        >>> score_to_color(92)  # 3-color default: Above 80
        '#22c55e'  # Green
        >>> # 4-color mode for quality dashboard
        >>> score_to_color(35, thresholds=(40, 60, 80),
        ...     colors=("#ef4444", "#f97316", "#eab308", "#22c55e"))
        '#ef4444'  # Red (below 40)
    """
    # Support both 3-color (2 thresholds) and 4-color (3 thresholds) modes
    if len(thresholds) == 2:
        low_threshold, high_threshold = thresholds
        red, yellow, green = colors
        if score < low_threshold:
            return red
        elif score < high_threshold:
            return yellow
        else:
            return green
    elif len(thresholds) == 3:
        # 4-color mode: (poor_threshold, fair_threshold, good_threshold)
        poor_t, fair_t, good_t = thresholds
        red, orange, yellow, green = colors
        if score < poor_t:
            return red
        elif score < fair_t:
            return orange
        elif score < good_t:
            return yellow
        else:
            return green
    else:
        # Fallback - use first color for low, last for high
        return colors[-1] if score >= thresholds[-1] else colors[0]


def delta_to_color(
    delta: float,
    positive_color: str = "#22c55e",
    negative_color: str = "#ef4444",
    neutral_color: str = "#64748b"
) -> str:
    """
    Map a delta value to color (positive=green, negative=red).

    Consolidates pattern from metric_card.py (line 50) and quality_dashboard.py.

    Args:
        delta: Change value (can be positive, negative, or zero)
        positive_color: Color for positive deltas
        negative_color: Color for negative deltas
        neutral_color: Color for zero delta

    Returns:
        Color hex string

    Example:
        >>> delta_to_color(2.5)
        '#22c55e'  # Green
        >>> delta_to_color(-1.3)
        '#ef4444'  # Red
        >>> delta_to_color(0.0)
        '#64748b'  # Neutral
    """
    if delta > 0:
        return positive_color
    elif delta < 0:
        return negative_color
    else:
        return neutral_color


# =============================================================================
# VALIDATION UTILITIES
# =============================================================================

def is_valid_dataframe(
    df: pd.DataFrame,
    min_rows: int = 1,
    min_cols: int = 1,
    check_empty: bool = True
) -> tuple[bool, Optional[str]]:
    """
    Validate DataFrame meets minimum requirements.

    Args:
        df: DataFrame to validate
        min_rows: Minimum required rows
        min_cols: Minimum required columns
        check_empty: Whether to check for completely empty DataFrame

    Returns:
        (is_valid, error_message) tuple

    Example:
        >>> df = pd.DataFrame({'a': [1, 2, 3]})
        >>> is_valid_dataframe(df)
        (True, None)
        >>> df = pd.DataFrame()
        >>> is_valid_dataframe(df)
        (False, 'DataFrame is empty')
    """
    if df is None:
        return False, "DataFrame is None"

    if check_empty and df.empty:
        return False, "DataFrame is empty"

    if len(df) < min_rows:
        return False, f"DataFrame has {len(df)} rows, minimum {min_rows} required"

    if len(df.columns) < min_cols:
        return False, f"DataFrame has {len(df.columns)} columns, minimum {min_cols} required"

    return True, None


# =============================================================================
# CONSTANTS (duplicated thresholds consolidated)
# =============================================================================

# Quality assessment thresholds (from quality/assessor.py)
MIN_ROWS_FOR_ASSESSMENT = 50
MAX_ROWS_FOR_TABPFN = 10000
MAX_FEATURES_FOR_TABPFN = 500
HIGH_CARDINALITY_THRESHOLD = 100

# Traffic light thresholds (from specs/010-quality-ds-workflow)
TRAFFIC_LIGHT_GREEN_THRESHOLD = 80  # Ready for modeling
TRAFFIC_LIGHT_YELLOW_THRESHOLD = 60  # Fixable issues
# Below 60 = Red (Needs work)
