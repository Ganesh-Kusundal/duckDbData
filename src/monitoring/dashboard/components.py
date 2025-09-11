"""
Reusable Dashboard Components
==============================

This module contains reusable UI components for the monitoring dashboard,
including cards, charts, tables, and status indicators.
"""

from typing import Dict, Any, List, Optional, Union, Callable, Tuple
from datetime import datetime
import json

import panel as pn
import param

from .themes import monitoring_theme
from ..logging import get_logger

logger = get_logger(__name__)


class MetricCard(pn.Column):
    """A card displaying a metric value with label and optional change indicator."""

    def __init__(self, title: str, value: Union[str, float, int], unit: str = "",
                 change: Optional[str] = None, change_description: str = "",
                 color: Optional[str] = None, **params):
        self.title = title
        self.value = value
        self.unit = unit
        self.change = change
        self.change_description = change_description
        self.color = color or monitoring_theme.COLORS['primary']

        # Create the card content
        content = self._create_content()

        super().__init__(content, css_classes=['metric-card'], **params)

    def _create_content(self) -> pn.Column:
        """Create the card content."""
        value_display = f"{self.value}{self.unit}"

        change_html = ""
        if self.change:
            change_class = "metric-change-neutral"
            if self.change.startswith('+'):
                change_class = "metric-change-positive"
            elif self.change.startswith('-'):
                change_class = "metric-change-negative"

            change_html = f"""
            <div class="metric-change {change_class}">
                {self.change}
                {f'<span class="change-description">{self.change_description}</span>' if self.change_description else ''}
            </div>
            """

        html = f"""
        <div class="metric-card-content">
            <div class="metric-title">{self.title}</div>
            <div class="metric-value" style="color: {self.color};">{value_display}</div>
            {change_html}
        </div>
        """

        return pn.Column(
            pn.pane.HTML(html, sizing_mode='stretch_width'),
            sizing_mode='stretch_width'
        )


class StatusIndicator(pn.Row):
    """A status indicator with colored dot and text."""

    def __init__(self, status: str, text: Optional[str] = None, **params):
        self.status = status.lower()
        self.text = text or status.title()

        # Get color from theme
        color = monitoring_theme.STATUS_COLORS.get(self.status, monitoring_theme.COLORS['text_muted'])

        # Create indicator
        indicator = pn.pane.HTML(f"""
            <div class="status-indicator" style="background-color: {color};"></div>
        """, width=20, height=20)

        # Create text
        text_pane = pn.pane.HTML(f"""
            <span style="color: {monitoring_theme.COLORS['text']}; font-size: 14px;">{self.text}</span>
        """)

        super().__init__(indicator, text_pane, **params)


class ProgressBar(pn.Column):
    """A progress bar with percentage display."""

    def __init__(self, value: float, max_value: float = 100, label: str = "",
                 color: Optional[str] = None, show_percentage: bool = True, **params):
        self.value = value
        self.max_value = max_value
        self.label = label
        self.show_percentage = show_percentage
        self.color = color or monitoring_theme.COLORS['primary']

        percentage = min(100, max(0, (value / max_value) * 100))

        # Determine color based on percentage
        if percentage > 90:
            bar_color = monitoring_theme.COLORS['error']
        elif percentage > 75:
            bar_color = monitoring_theme.COLORS['warning']
        else:
            bar_color = self.color

        # Create progress bar HTML
        percentage_html = f"""
        <div style="text-align: center; font-size: 12px; color: {monitoring_theme.COLORS['text_secondary']}; margin-top: 4px;">
            {percentage:.1f}%
        </div>
        """ if show_percentage else ""

        html = f"""
        <div class="progress-bar">
            <div class="progress-fill" style="width: {percentage}%; background-color: {bar_color};"></div>
        </div>
        {percentage_html}
        """

        content = []
        if self.label:
            content.append(pn.pane.HTML(f"<div class='progress-label'>{self.label}</div>"))

        content.append(pn.pane.HTML(html, height=40 if show_percentage else 20))

        super().__init__(*content, **params)


class AlertCard(pn.Column):
    """A card displaying alert information."""

    def __init__(self, alert: Dict[str, Any], **params):
        self.alert = alert

        severity = alert.get('severity', 'low').lower()
        title = alert.get('title', 'Alert')
        message = alert.get('message', '')
        timestamp = alert.get('created_at', datetime.now())

        if hasattr(timestamp, 'strftime'):
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        else:
            timestamp_str = str(timestamp)

        # Get severity color
        severity_color = monitoring_theme.SEVERITY_COLORS.get(severity, monitoring_theme.COLORS['warning'])

        html = f"""
        <div class="alert-card alert-{severity}" style="border-left-color: {severity_color};">
            <div class="alert-title" style="color: {monitoring_theme.COLORS['text']};">{title}</div>
            <div class="alert-message" style="color: {monitoring_theme.COLORS['text_secondary']};">{message}</div>
            <div class="alert-timestamp" style="color: {monitoring_theme.COLORS['text_muted']}; font-size: 12px;">
                {timestamp_str}
            </div>
        </div>
        """

        super().__init__(
            pn.pane.HTML(html, sizing_mode='stretch_width'),
            css_classes=['alert-card-container'],
            **params
        )


class DataTable(pn.Column):
    """Enhanced data table with filtering and sorting."""

    def __init__(self, data: List[Dict[str, Any]], columns: Optional[List[str]] = None,
                 title: str = "", height: int = 400, **params):

        self.data = data or []
        self.columns = columns
        self.title = title

        # Determine columns if not specified
        if not self.columns and self.data:
            self.columns = list(self.data[0].keys())

        # Create table content
        table_html = self._create_table_html()

        content = []
        if self.title:
            content.append(pn.pane.HTML(f"<h3>{self.title}</h3>"))

        content.append(pn.pane.HTML(table_html, height=height, sizing_mode='stretch_width'))

        super().__init__(*content, css_classes=['data-table'], **params)

    def _create_table_html(self) -> str:
        """Create HTML table from data."""
        if not self.data or not self.columns:
            return "<p>No data available</p>"

        # Create table header
        header_html = "".join(f"<th>{col.title()}</th>" for col in self.columns)
        header_row = f"<tr>{header_html}</tr>"

        # Create table rows
        rows_html = ""
        for i, row in enumerate(self.data):
            row_class = "even" if i % 2 == 0 else "odd"
            cells_html = ""

            for col in self.columns:
                value = row.get(col, '')
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, indent=2)
                elif hasattr(value, 'strftime'):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                cells_html += f"<td>{value}</td>"

            rows_html += f"<tr class='{row_class}'>{cells_html}</tr>"

        table_html = f"""
        <div class="table-container" style="overflow-x: auto; height: 100%;">
            <table class="data-table-content">
                <thead>{header_row}</thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
        """

        return table_html


class ChartCard(pn.Column):
    """A card containing a chart with title and controls."""

    def __init__(self, chart: pn.pane.Plotly, title: str = "", controls: Optional[List[pn.widgets.Widget]] = None, **params):
        self.chart = chart
        self.title = title
        self.controls = controls or []

        content = []

        # Add title if provided
        if self.title:
            content.append(pn.pane.HTML(f"<h3 class='chart-title'>{self.title}</h3>"))

        # Add controls if provided
        if self.controls:
            content.append(pn.Row(*self.controls, sizing_mode='stretch_width'))

        # Add chart
        content.append(self.chart)

        super().__init__(*content, css_classes=['chart-card'], **params)


class LoadingSpinner(pn.Row):
    """A loading spinner with optional text."""

    def __init__(self, text: str = "Loading...", **params):
        spinner = pn.pane.HTML("""
            <div class="loading-spinner"></div>
        """, width=20, height=20)

        text_pane = pn.pane.HTML(f"""
            <span style="color: {monitoring_theme.COLORS['text_secondary']}; margin-left: 8px;">
                {text}
            </span>
        """)

        super().__init__(spinner, text_pane, **params)


class StatusBadge(pn.pane.HTML):
    """A status badge with color coding."""

    def __init__(self, status: str, **params):
        status_lower = status.lower()
        color = monitoring_theme.STATUS_COLORS.get(status_lower, monitoring_theme.COLORS['text_muted'])

        html = f"""
        <span class="status-badge" style="
            background-color: {color};
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
            text-transform: uppercase;
        ">
            {status}
        </span>
        """

        super().__init__(html, **params)


class NotificationPanel(pn.Column):
    """A panel for displaying notifications and messages."""

    def __init__(self, **params):
        self.notifications: List[Dict[str, Any]] = []

        self.content = pn.Column(sizing_mode='stretch_width')
        self._update_content()

        super().__init__(self.content, css_classes=['notification-panel'], **params)

    def add_notification(self, message: str, type: str = "info", duration: int = 5000) -> None:
        """Add a notification."""
        notification_id = len(self.notifications)

        notification = {
            'id': notification_id,
            'message': message,
            'type': type,
            'timestamp': datetime.now(),
            'duration': duration
        }

        self.notifications.append(notification)
        self._update_content()

        # Auto-remove after duration
        if duration > 0:
            import threading
            import time

            def remove_notification():
                time.sleep(duration / 1000)
                if notification in self.notifications:
                    self.notifications.remove(notification)
                    self._update_content()

            thread = threading.Thread(target=remove_notification, daemon=True)
            thread.start()

    def clear_notifications(self) -> None:
        """Clear all notifications."""
        self.notifications.clear()
        self._update_content()

    def _update_content(self) -> None:
        """Update the panel content."""
        if not self.notifications:
            self.content.objects = [pn.pane.HTML("<p style='color: #636e72;'>No notifications</p>")]
            return

        notification_elements = []

        for notification in self.notifications[-5:]:  # Show last 5 notifications
            color = {
                'info': monitoring_theme.COLORS['info'],
                'success': monitoring_theme.COLORS['success'],
                'warning': monitoring_theme.COLORS['warning'],
                'error': monitoring_theme.COLORS['error']
            }.get(notification['type'], monitoring_theme.COLORS['info'])

            html = f"""
            <div class="notification-item" style="
                background-color: rgba(45, 45, 45, 0.8);
                border-left: 4px solid {color};
                padding: 8px 12px;
                margin: 4px 0;
                border-radius: 4px;
            ">
                <div style="color: {monitoring_theme.COLORS['text']}; font-size: 14px;">
                    {notification['message']}
                </div>
                <div style="color: {monitoring_theme.COLORS['text_muted']}; font-size: 12px;">
                    {notification['timestamp'].strftime('%H:%M:%S')}
                </div>
            </div>
            """

            notification_elements.append(pn.pane.HTML(html, sizing_mode='stretch_width'))

        self.content.objects = notification_elements


class FilterPanel(pn.Column):
    """A panel with filtering controls."""

    def __init__(self, filters: Dict[str, pn.widgets.Widget], on_filter_change: Optional[Callable] = None, **params):
        self.filters = filters
        self.on_filter_change = on_filter_change

        # Create filter controls
        filter_controls = []
        for name, widget in self.filters.items():
            if self.on_filter_change:
                widget.param.watch(self._on_filter_change, 'value')

            filter_controls.append(pn.Row(
                pn.pane.HTML(f"<label style='color: {monitoring_theme.COLORS['text']};'>{name.title()}:</label>", width=100),
                widget,
                sizing_mode='stretch_width'
            ))

        # Add clear filters button
        clear_button = pn.widgets.Button(name="Clear Filters", button_type="light")
        clear_button.on_click(self._clear_filters)

        filter_controls.append(pn.Row(clear_button, sizing_mode='stretch_width'))

        super().__init__(
            pn.pane.HTML("<h4>Filters</h4>"),
            *filter_controls,
            css_classes=['filter-panel'],
            **params
        )

    def _on_filter_change(self, event) -> None:
        """Handle filter change."""
        if self.on_filter_change:
            self.on_filter_change(self.get_filter_values())

    def _clear_filters(self, event) -> None:
        """Clear all filters."""
        for widget in self.filters.values():
            if hasattr(widget, 'value'):
                if isinstance(widget, pn.widgets.Select):
                    widget.value = widget.options[0] if widget.options else None
                elif isinstance(widget, pn.widgets.MultiSelect):
                    widget.value = []
                elif isinstance(widget, pn.widgets.TextInput):
                    widget.value = ""
                elif isinstance(widget, pn.widgets.DatePicker):
                    widget.value = None

        if self.on_filter_change:
            self.on_filter_change(self.get_filter_values())

    def get_filter_values(self) -> Dict[str, Any]:
        """Get current filter values."""
        return {name: widget.value for name, widget in self.filters.items()}


# Utility functions for creating common components

def create_metric_grid(metrics: List[Dict[str, Any]], columns: int = 3) -> pn.GridBox:
    """Create a grid of metric cards."""
    cards = []

    for metric in metrics:
        card = MetricCard(
            title=metric.get('title', ''),
            value=metric.get('value', 0),
            unit=metric.get('unit', ''),
            change=metric.get('change'),
            change_description=metric.get('change_description', ''),
            color=metric.get('color')
        )
        cards.append(card)

    return pn.GridBox(*cards, ncols=columns, sizing_mode='stretch_width')


def create_status_summary(statuses: Dict[str, int]) -> pn.Row:
    """Create a row of status indicators with counts."""
    indicators = []

    for status, count in statuses.items():
        if count > 0:
            indicator = StatusIndicator(status, f"{status.title()}: {count}")
            indicators.append(indicator)

    return pn.Row(*indicators, sizing_mode='stretch_width')


def create_quick_actions(actions: List[Dict[str, Any]]) -> pn.Column:
    """Create a panel with quick action buttons."""
    buttons = []

    for action in actions:
        button = pn.widgets.Button(
            name=action.get('name', ''),
            button_type=action.get('type', 'primary'),
            width=200
        )

        if 'callback' in action:
            button.on_click(action['callback'])

        buttons.append(button)

    return pn.Column(
        pn.pane.HTML("<h4>Quick Actions</h4>"),
        pn.Row(*buttons, sizing_mode='stretch_width'),
        css_classes=['quick-actions-panel']
    )
