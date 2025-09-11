"""
Dashboard Themes and Styling
============================

This module provides dark mode themes and custom styling for the Panel/Bokeh dashboard.
Includes color schemes, CSS styling, and theme configuration.
"""

from typing import Dict, Any
import panel as pn
import param


class MonitoringTheme:
    """Dark mode theme for monitoring dashboard."""

    # Color palette
    COLORS = {
        'background': '#1a1a1a',
        'surface': '#2d2d2d',
        'surface_secondary': '#404040',
        'primary': '#00d4aa',
        'primary_dark': '#00b894',
        'secondary': '#6c5ce7',
        'accent': '#fdcb6e',
        'success': '#00b894',
        'warning': '#fdcb6e',
        'error': '#e17055',
        'info': '#74b9ff',
        'text': '#ffffff',
        'text_secondary': '#b2bec3',
        'text_muted': '#636e72',
        'border': '#404040',
        'border_light': '#555555',
        'shadow': 'rgba(0, 0, 0, 0.3)',
        'grid_lines': '#555555'
    }

    # Status colors
    STATUS_COLORS = {
        'running': '#74b9ff',      # Blue
        'passed': '#00b894',      # Green
        'failed': '#e17055',      # Red
        'skipped': '#fdcb6e',     # Yellow
        'error': '#e17055',       # Red
        'pending': '#636e72',     # Gray
        'timeout': '#a29bfe',     # Purple
        'success': '#00b894',     # Green
        'warning': '#fdcb6e',     # Yellow
        'critical': '#e17055',    # Red
        'info': '#74b9ff'         # Blue
    }

    # Severity colors for alerts
    SEVERITY_COLORS = {
        'low': '#fdcb6e',         # Yellow
        'medium': '#f39c12',      # Orange
        'high': '#e17055',        # Red
        'critical': '#c0392b'     # Dark Red
    }

    @classmethod
    def get_css(cls) -> str:
        """Get custom CSS for dark mode styling."""
        return f"""
        /* Dark mode base styles */
        .monitoring-dashboard {{
            background-color: {cls.COLORS['background']};
            color: {cls.COLORS['text']};
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}

        /* Panel overrides for dark mode */
        .bk {{
            background-color: {cls.COLORS['background']};
            color: {cls.COLORS['text']};
        }}

        .bk-panel {{
            background-color: {cls.COLORS['surface']};
            border: 1px solid {cls.COLORS['border']};
            border-radius: 8px;
        }}

        .bk-tabs-header .bk-tab {{
            background-color: {cls.COLORS['surface_secondary']};
            color: {cls.COLORS['text_secondary']};
            border: 1px solid {cls.COLORS['border']};
            border-bottom: none;
            border-radius: 4px 4px 0 0;
            margin-right: 2px;
            padding: 8px 16px;
        }}

        .bk-tabs-header .bk-tab.bk-active {{
            background-color: {cls.COLORS['surface']};
            color: {cls.COLORS['primary']};
            border-color: {cls.COLORS['primary']};
        }}

        /* Button styling */
        .bk-btn {{
            background-color: {cls.COLORS['surface_secondary']};
            color: {cls.COLORS['text']};
            border: 1px solid {cls.COLORS['border_light']};
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 14px;
            transition: all 0.2s ease;
        }}

        .bk-btn:hover {{
            background-color: {cls.COLORS['surface']};
            border-color: {cls.COLORS['primary']};
            color: {cls.COLORS['primary']};
        }}

        .bk-btn.bk-btn-primary {{
            background-color: {cls.COLORS['primary']};
            color: white;
            border-color: {cls.COLORS['primary']};
        }}

        .bk-btn.bk-btn-primary:hover {{
            background-color: {cls.COLORS['primary_dark']};
            border-color: {cls.COLORS['primary_dark']};
        }}

        /* Input styling */
        .bk-input {{
            background-color: {cls.COLORS['surface']};
            color: {cls.COLORS['text']};
            border: 1px solid {cls.COLORS['border_light']};
            border-radius: 4px;
            padding: 8px 12px;
        }}

        .bk-input:focus {{
            border-color: {cls.COLORS['primary']};
            outline: none;
        }}

        /* Select styling */
        .bk-select {{
            background-color: {cls.COLORS['surface']};
            color: {cls.COLORS['text']};
            border: 1px solid {cls.COLORS['border_light']};
            border-radius: 4px;
        }}

        /* Card styling */
        .monitoring-card {{
            background-color: {cls.COLORS['surface']};
            border: 1px solid {cls.COLORS['border']};
            border-radius: 8px;
            padding: 16px;
            margin: 8px 0;
            box-shadow: 0 2px 4px {cls.COLORS['shadow']};
        }}

        .monitoring-card-header {{
            color: {cls.COLORS['primary']};
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
        }}

        .monitoring-card-header::before {{
            content: '';
            width: 4px;
            height: 20px;
            background-color: {cls.COLORS['primary']};
            margin-right: 8px;
            border-radius: 2px;
        }}

        /* Status indicators */
        .status-indicator {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }}

        .status-running {{ background-color: {cls.STATUS_COLORS['running']}; }}
        .status-passed {{ background-color: {cls.STATUS_COLORS['passed']}; }}
        .status-failed {{ background-color: {cls.STATUS_COLORS['failed']}; }}
        .status-skipped {{ background-color: {cls.STATUS_COLORS['skipped']}; }}
        .status-error {{ background-color: {cls.STATUS_COLORS['error']}; }}
        .status-pending {{ background-color: {cls.STATUS_COLORS['pending']}; }}

        /* Metric displays */
        .metric-value {{
            font-size: 24px;
            font-weight: 700;
            color: {cls.COLORS['primary']};
        }}

        .metric-label {{
            font-size: 12px;
            color: {cls.COLORS['text_secondary']};
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .metric-change {{
            font-size: 14px;
            font-weight: 500;
        }}

        .metric-change-positive {{ color: {cls.COLORS['success']}; }}
        .metric-change-negative {{ color: {cls.COLORS['error']}; }}
        .metric-change-neutral {{ color: {cls.COLORS['text_secondary']}; }}

        /* Alert styling */
        .alert-card {{
            border-left: 4px solid;
            padding: 12px 16px;
            margin: 8px 0;
            border-radius: 4px;
        }}

        .alert-low {{ border-left-color: {cls.SEVERITY_COLORS['low']}; background-color: rgba(253, 203, 110, 0.1); }}
        .alert-medium {{ border-left-color: {cls.SEVERITY_COLORS['medium']}; background-color: rgba(243, 156, 18, 0.1); }}
        .alert-high {{ border-left-color: {cls.SEVERITY_COLORS['high']}; background-color: rgba(225, 112, 85, 0.1); }}
        .alert-critical {{ border-left-color: {cls.SEVERITY_COLORS['critical']}; background-color: rgba(192, 57, 43, 0.1); }}

        .alert-title {{
            font-weight: 600;
            margin-bottom: 4px;
        }}

        .alert-message {{
            font-size: 14px;
            color: {cls.COLORS['text_secondary']};
        }}

        .alert-timestamp {{
            font-size: 12px;
            color: {cls.COLORS['text_muted']};
            margin-top: 4px;
        }}

        /* Progress bars */
        .progress-bar {{
            width: 100%;
            height: 8px;
            background-color: {cls.COLORS['surface_secondary']};
            border-radius: 4px;
            overflow: hidden;
            margin: 8px 0;
        }}

        .progress-fill {{
            height: 100%;
            background-color: {cls.COLORS['primary']};
            transition: width 0.3s ease;
        }}

        /* Loading spinner */
        .loading-spinner {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid {cls.COLORS['border_light']};
            border-radius: 50%;
            border-top-color: {cls.COLORS['primary']};
            animation: spin 1s ease-in-out infinite;
            margin-right: 8px;
        }}

        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}

        /* Table styling */
        .bk-table {{
            background-color: {cls.COLORS['surface']};
            color: {cls.COLORS['text']};
        }}

        .bk-table th {{
            background-color: {cls.COLORS['surface_secondary']};
            color: {cls.COLORS['text']};
            border-bottom: 1px solid {cls.COLORS['border']};
            padding: 12px 8px;
            font-weight: 600;
        }}

        .bk-table td {{
            border-bottom: 1px solid {cls.COLORS['border']};
            padding: 8px;
            color: {cls.COLORS['text_secondary']};
        }}

        .bk-table tr:hover td {{
            background-color: {cls.COLORS['surface_secondary']};
        }}

        /* Sidebar styling */
        .sidebar {{
            background-color: {cls.COLORS['surface']};
            border-right: 1px solid {cls.COLORS['border']};
            padding: 16px;
            min-height: 100vh;
        }}

        .sidebar-header {{
            color: {cls.COLORS['primary']};
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 24px;
        }}

        .sidebar-menu-item {{
            display: block;
            padding: 12px 16px;
            color: {cls.COLORS['text_secondary']};
            text-decoration: none;
            border-radius: 4px;
            margin: 4px 0;
            transition: all 0.2s ease;
        }}

        .sidebar-menu-item:hover {{
            background-color: {cls.COLORS['surface_secondary']};
            color: {cls.COLORS['primary']};
        }}

        .sidebar-menu-item.active {{
            background-color: {cls.COLORS['primary']};
            color: white;
        }}

        /* Responsive design */
        @media (max-width: 768px) {{
            .monitoring-card {{
                margin: 8px;
                padding: 12px;
            }}

            .sidebar {{
                position: fixed;
                top: 0;
                left: -100%;
                width: 280px;
                z-index: 1000;
                transition: left 0.3s ease;
            }}

            .sidebar.open {{
                left: 0;
            }}
        }}
        """

    @classmethod
    def apply_theme(cls) -> None:
        """Apply the dark theme to Panel."""
        # Set Panel theme
        pn.config.theme = 'dark'

        # Add custom CSS
        pn.config.raw_css = [cls.get_css()]

        # Configure global settings
        pn.config.sizing_mode = 'stretch_width'

    @classmethod
    def create_status_indicator(cls, status: str) -> pn.pane.HTML:
        """Create a status indicator HTML element."""
        color = cls.STATUS_COLORS.get(status.lower(), cls.COLORS['text_muted'])
        return pn.pane.HTML(f"""
            <span class="status-indicator status-{status.lower()}"
                  style="background-color: {color};"></span>
            {status.title()}
        """, width=100)

    @classmethod
    def create_metric_display(cls, value: str, label: str, change: str = None) -> pn.Column:
        """Create a metric display card."""
        change_html = ""
        if change:
            change_class = "metric-change-neutral"
            if change.startswith('+'):
                change_class = "metric-change-positive"
            elif change.startswith('-'):
                change_class = "metric-change-negative"
            change_html = f'<div class="metric-change {change_class}">{change}</div>'

        html = f"""
        <div class="metric-display">
            <div class="metric-value">{value}</div>
            <div class="metric-label">{label}</div>
            {change_html}
        </div>
        """

        return pn.Column(
            pn.pane.HTML(html, sizing_mode='stretch_width'),
            sizing_mode='stretch_width',
            css_classes=['metric-card']
        )

    @classmethod
    def create_alert_card(cls, alert: Dict[str, Any]) -> pn.Column:
        """Create an alert card."""
        severity = alert.get('severity', 'low').lower()
        title = alert.get('title', 'Alert')
        message = alert.get('message', '')
        timestamp = alert.get('created_at', '')

        if hasattr(timestamp, 'strftime'):
            timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')

        html = f"""
        <div class="alert-card alert-{severity}">
            <div class="alert-title">{title}</div>
            <div class="alert-message">{message}</div>
            <div class="alert-timestamp">{timestamp}</div>
        </div>
        """

        return pn.Column(
            pn.pane.HTML(html, sizing_mode='stretch_width'),
            sizing_mode='stretch_width'
        )

    @classmethod
    def create_progress_bar(cls, value: float, max_value: float = 100) -> pn.pane.HTML:
        """Create a progress bar."""
        percentage = min(100, max(0, (value / max_value) * 100))
        color = cls.COLORS['primary']

        if percentage > 90:
            color = cls.COLORS['error']
        elif percentage > 75:
            color = cls.COLORS['warning']

        html = f"""
        <div class="progress-bar">
            <div class="progress-fill" style="width: {percentage}%; background-color: {color};"></div>
        </div>
        <div style="text-align: center; font-size: 12px; color: {cls.COLORS['text_secondary']}; margin-top: 4px;">
            {percentage:.1f}%
        </div>
        """

        return pn.pane.HTML(html, height=40)


# Global theme instance
monitoring_theme = MonitoringTheme()
