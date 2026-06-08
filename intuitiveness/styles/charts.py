"""
Chart Styling Module - Klein Blue Palette
==========================================

Professional, minimalist chart styling following DataGyver principles:
- Consistent Klein Blue color palette
- Clean, grid-free designs
- Plotly for interactivity
- Native Streamlit functions preferred

Feature: 007-streamlit-design-makeup
"""

try:
    import streamlit as st  # optional: only needed with the "app" extra
except ImportError:
    st = None
import pandas as pd
from typing import List, Dict, Any, Optional, Union
import plotly.express as px
import plotly.graph_objects as go


# =============================================================================
# Klein Blue Color Palette
# =============================================================================

# Primary Klein Blue palette (from darkest to lightest)
KLEIN_BLUE = {
    'primary': '#002fa7',      # Original Klein Blue
    'dark': '#001d6c',         # Darker variant
    'medium': '#0041d1',       # Medium blue
    'light': '#3b82f6',        # Light blue
    'lighter': '#60a5fa',      # Lighter blue
    'lightest': '#93c5fd',     # Very light blue
    'pale': '#dbeafe',         # Pale blue (backgrounds)
}

# Complementary accent colors (for multi-series charts)
ACCENT_COLORS = {
    'amber': '#f59e0b',        # Warm accent
    'emerald': '#10b981',      # Success/positive
    'rose': '#f43f5e',         # Alert/negative
    'violet': '#8b5cf6',       # Alternative accent
    'slate': '#64748b',        # Neutral
}

# Semantic color mapping
SEMANTIC_COLORS = {
    'positive': '#10b981',
    'negative': '#f43f5e',
    'neutral': '#64748b',
    'highlight': '#002fa7',
}

# Default chart color sequence (Klein Blue focused)
CHART_COLORS = [
    '#002fa7',  # Klein Blue primary
    '#3b82f6',  # Light blue
    '#60a5fa',  # Lighter blue
    '#93c5fd',  # Very light blue
    '#f59e0b',  # Amber accent (contrast)
    '#10b981',  # Emerald accent
    '#8b5cf6',  # Violet accent
]


# =============================================================================
# Plotly Layout Defaults
# =============================================================================

def get_default_layout() -> Dict[str, Any]:
    """
    Get default Plotly layout configuration for consistent styling.

    Following DataGyver principles:
    - Minimal grid lines
    - Clean typography
    - Generous whitespace
    - No chart junk
    """
    return {
        'font': {
            'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
            'size': 13,
            'color': '#0f172a'
        },
        'title': {
            'font': {
                'size': 16,
                'color': '#0f172a',
                'family': 'Inter, sans-serif'
            },
            'x': 0,
            'xanchor': 'left',
            'y': 0.98,
        },
        'paper_bgcolor': 'rgba(0,0,0,0)',  # Transparent
        'plot_bgcolor': 'rgba(0,0,0,0)',   # Transparent
        'margin': {'l': 40, 'r': 20, 't': 50, 'b': 40},
        'xaxis': {
            'showgrid': False,
            'showline': True,
            'linewidth': 1,
            'linecolor': '#e2e8f0',
            'tickfont': {'size': 11, 'color': '#64748b'},
        },
        'yaxis': {
            'showgrid': True,
            'gridwidth': 1,
            'gridcolor': '#f1f5f9',
            'showline': False,
            'tickfont': {'size': 11, 'color': '#64748b'},
            'zeroline': False,
        },
        'hoverlabel': {
            'bgcolor': '#0f172a',
            'font_size': 12,
            'font_family': 'Inter, sans-serif',
            'font_color': 'white',
        },
        'showlegend': True,
        'legend': {
            'orientation': 'h',
            'yanchor': 'bottom',
            'y': -0.2,
            'xanchor': 'center',
            'x': 0.5,
            'font': {'size': 11},
            'bgcolor': 'rgba(0,0,0,0)',
        },
    }


# =============================================================================
# Chart Components
# =============================================================================

def styled_bar_chart(
    data: Union[pd.DataFrame, Dict[str, float]],
    x: Optional[str] = None,
    y: Optional[str] = None,
    title: Optional[str] = None,
    orientation: str = 'v',
    color_discrete_sequence: Optional[List[str]] = None,
    show_values: bool = True,
    height: int = 350,
) -> go.Figure:
    """
    Create a stylish bar chart with Klein Blue palette.

    Args:
        data: DataFrame or dict of {label: value}
        x: Column name for x-axis (if DataFrame)
        y: Column name for y-axis (if DataFrame)
        title: Chart title
        orientation: 'v' for vertical, 'h' for horizontal
        color_discrete_sequence: Custom colors (defaults to CHART_COLORS)
        show_values: Display values on bars
        height: Chart height in pixels

    Returns:
        Plotly figure object
    """
    colors = color_discrete_sequence or CHART_COLORS

    # Convert dict to DataFrame if needed
    if isinstance(data, dict):
        df = pd.DataFrame({
            'category': list(data.keys()),
            'value': list(data.values())
        })
        x = 'category'
        y = 'value'
    else:
        df = data

    fig = px.bar(
        df,
        x=x if orientation == 'v' else y,
        y=y if orientation == 'v' else x,
        orientation=orientation,
        color_discrete_sequence=colors,
    )

    # Apply default layout
    fig.update_layout(**get_default_layout())
    fig.update_layout(height=height, showlegend=False)

    if title:
        fig.update_layout(title_text=title)

    # Style bars
    fig.update_traces(
        marker_line_width=0,
        marker_cornerradius=4,
        hovertemplate='<b>%{x}</b><br>Value: %{y:,.0f}<extra></extra>' if orientation == 'v'
                      else '<b>%{y}</b><br>Value: %{x:,.0f}<extra></extra>'
    )

    # Add value labels
    if show_values:
        fig.update_traces(
            texttemplate='%{y:,.0f}' if orientation == 'v' else '%{x:,.0f}',
            textposition='outside',
            textfont={'size': 11, 'color': '#0f172a', 'family': 'Inter, sans-serif'}
        )

    return fig


def styled_metric_card(
    label: str,
    value: Union[int, float, str],
    delta: Optional[Union[int, float]] = None,
    delta_color: str = 'normal',
    icon: Optional[str] = None,
) -> None:
    """
    Render a stylish metric card using CSS injection.

    Args:
        label: Metric label
        value: Metric value
        delta: Change value (optional)
        delta_color: 'normal', 'inverse', or 'off'
        icon: Optional emoji icon
    """
    # Format value
    if isinstance(value, float):
        formatted_value = f"{value:,.1f}"
    elif isinstance(value, int):
        formatted_value = f"{value:,}"
    else:
        formatted_value = str(value)

    # Delta display
    delta_html = ""
    if delta is not None:
        if delta_color == 'normal':
            color = SEMANTIC_COLORS['positive'] if delta >= 0 else SEMANTIC_COLORS['negative']
            arrow = "↑" if delta >= 0 else "↓"
        elif delta_color == 'inverse':
            color = SEMANTIC_COLORS['negative'] if delta >= 0 else SEMANTIC_COLORS['positive']
            arrow = "↑" if delta >= 0 else "↓"
        else:
            color = SEMANTIC_COLORS['neutral']
            arrow = ""

        delta_html = f'''
            <div style="font-size: 0.85rem; color: {color}; margin-top: 4px;">
                {arrow} {abs(delta):,.1f}
            </div>
        '''

    # Icon display
    icon_html = f'<span style="margin-right: 8px;">{icon}</span>' if icon else ''

    # Render card
    st.markdown(f'''
        <div style="
            background: linear-gradient(135deg, {KLEIN_BLUE['pale']} 0%, white 100%);
            border: 1px solid {KLEIN_BLUE['lightest']};
            border-radius: 12px;
            padding: 1.25rem;
            text-align: center;
        ">
            <div style="
                font-size: 0.85rem;
                color: #64748b;
                margin-bottom: 4px;
                font-weight: 500;
            ">
                {icon_html}{label}
            </div>
            <div style="
                font-size: 1.75rem;
                font-weight: 700;
                color: {KLEIN_BLUE['primary']};
            ">
                {formatted_value}
            </div>
            {delta_html}
        </div>
    ''', unsafe_allow_html=True)


def styled_donut_chart(
    data: Dict[str, float],
    title: Optional[str] = None,
    height: int = 300,
    hole_size: float = 0.5,
    show_legend: bool = True,
) -> go.Figure:
    """
    Create a stylish donut chart.

    Args:
        data: Dict of {label: value}
        title: Chart title
        height: Chart height
        hole_size: Size of center hole (0-1)
        show_legend: Show legend

    Returns:
        Plotly figure object
    """
    labels = list(data.keys())
    values = list(data.values())

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=hole_size,
        marker_colors=CHART_COLORS[:len(labels)],
        textinfo='percent+label',
        textposition='outside',
        textfont={'size': 11, 'color': '#0f172a'},
        hovertemplate='<b>%{label}</b><br>Value: %{value:,.0f}<br>Share: %{percent}<extra></extra>',
    )])

    layout = get_default_layout()
    layout['height'] = height
    layout['showlegend'] = show_legend

    if title:
        layout['title_text'] = title

    fig.update_layout(**layout)

    return fig


def styled_line_chart(
    data: pd.DataFrame,
    x: str,
    y: Union[str, List[str]],
    title: Optional[str] = None,
    height: int = 350,
    smooth: bool = True,
) -> go.Figure:
    """
    Create a stylish line chart.

    Args:
        data: DataFrame with data
        x: Column for x-axis
        y: Column(s) for y-axis
        title: Chart title
        height: Chart height
        smooth: Apply line smoothing

    Returns:
        Plotly figure object
    """
    y_cols = [y] if isinstance(y, str) else y

    fig = go.Figure()

    for i, col in enumerate(y_cols):
        fig.add_trace(go.Scatter(
            x=data[x],
            y=data[col],
            name=col,
            mode='lines+markers',
            line={
                'color': CHART_COLORS[i % len(CHART_COLORS)],
                'width': 2.5,
                'shape': 'spline' if smooth else 'linear',
            },
            marker={
                'size': 6,
                'color': CHART_COLORS[i % len(CHART_COLORS)],
            },
            hovertemplate=f'<b>{col}</b><br>%{{x}}: %{{y:,.0f}}<extra></extra>',
        ))

    layout = get_default_layout()
    layout['height'] = height

    if title:
        layout['title_text'] = title

    fig.update_layout(**layout)

    return fig


# =============================================================================
# Streamlit Native Wrappers
# =============================================================================

def render_plotly_chart(
    fig: go.Figure,
    use_container_width: bool = True,
    key: Optional[str] = None,
    on_select: str = "ignore",
) -> Optional[Dict]:
    """
    Render a Plotly chart with consistent configuration.

    Following DataGyver's recommendation for `on_select="rerun"` interactivity.

    Args:
        fig: Plotly figure
        use_container_width: Expand to container width
        key: Unique key for the chart
        on_select: Selection behavior ("ignore", "rerun", or callback)

    Returns:
        Selection data if on_select is enabled
    """
    return st.plotly_chart(
        fig,
        use_container_width=use_container_width,
        key=key,
        on_select=on_select,
        config={
            'displayModeBar': False,  # Hide toolbar for cleaner look
            'responsive': True,
        }
    )


def render_metrics_row(metrics: List[Dict[str, Any]], columns: int = 4) -> None:
    """
    Render a row of styled metric cards.

    Args:
        metrics: List of metric configs, each with 'label', 'value',
                 optional 'delta', 'delta_color', 'icon'
        columns: Number of columns
    """
    cols = st.columns(columns)
    for i, metric in enumerate(metrics):
        with cols[i % columns]:
            styled_metric_card(
                label=metric.get('label', ''),
                value=metric.get('value', 0),
                delta=metric.get('delta'),
                delta_color=metric.get('delta_color', 'normal'),
                icon=metric.get('icon'),
            )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Colors
    'KLEIN_BLUE',
    'ACCENT_COLORS',
    'SEMANTIC_COLORS',
    'CHART_COLORS',
    # Layout
    'get_default_layout',
    # Charts
    'styled_bar_chart',
    'styled_metric_card',
    'styled_donut_chart',
    'styled_line_chart',
    # Renderers
    'render_plotly_chart',
    'render_metrics_row',
]
