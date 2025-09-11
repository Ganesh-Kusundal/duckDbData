"""
Main Dashboard Application
==========================

This module contains the main Panel/Bokeh dashboard application with dark mode,
real-time updates, and comprehensive monitoring capabilities.
"""

import asyncio
from typing import Dict, Any, Optional, List
import threading
import time
from datetime import datetime, timedelta

import panel as pn
import param

from ..config.settings import config
from .themes import monitoring_theme
from ..logging import get_logger
from ..test_monitor import test_monitor
from ..metrics import metrics_collector, alert_manager
from ..logging import log_aggregator

logger = get_logger(__name__)


class DashboardApp(param.Parameterized):
    """Main monitoring dashboard application."""

    # Parameters for reactive updates
    refresh_trigger = param.Integer(default=0)
    selected_tab = param.String(default='overview')

    def __init__(self, **params):
        super().__init__(**params)

        # Apply dark theme
        monitoring_theme.apply_theme()

        # Initialize dashboard components
        self.sidebar = self._create_sidebar()
        self.main_content = pn.Column(sizing_mode='stretch_both')

        # Create main layout
        self.layout = pn.Row(
            self.sidebar,
            pn.Column(
                self._create_header(),
                self.main_content,
                sizing_mode='stretch_both'
            ),
            sizing_mode='stretch_both',
            css_classes=['monitoring-dashboard']
        )

        # Initialize with overview tab
        self._update_main_content()

        # Start background refresh thread
        self._refresh_thread = threading.Thread(target=self._background_refresh, daemon=True)
        self._refresh_thread.start()

        logger.info("Dashboard application initialized")

    def _create_sidebar(self) -> pn.Column:
        """Create the sidebar navigation."""
        menu_items = [
            ('overview', '📊 Overview', 'System overview and key metrics'),
            ('tests', '🧪 Tests', 'Test execution and monitoring'),
            ('logs', '📝 Logs', 'System logs and analysis'),
            ('metrics', '📈 Metrics', 'Performance metrics'),
            ('alerts', '🚨 Alerts', 'System alerts and notifications'),
            ('settings', '⚙️ Settings', 'Dashboard configuration')
        ]

        menu_buttons = []
        for tab_id, title, description in menu_items:
            button = pn.widgets.Button(
                name=title,
                button_type='light',
                width=250,
                css_classes=['sidebar-menu-item']
            )
            button.on_click(lambda event, tid=tab_id: self._switch_tab(tid))
            menu_buttons.append(button)

        return pn.Column(
            pn.pane.HTML("<h2 class='sidebar-header'>🖥️ Monitor</h2>", width=250),
            *menu_buttons,
            pn.Spacer(height=50),
            pn.pane.HTML("""
                <div style='padding: 16px; font-size: 12px; color: #636e72;'>
                    <strong>DuckDB Financial Infra</strong><br>
                    Monitoring Dashboard v1.0
                </div>
            """, width=250),
            width=250,
            css_classes=['sidebar']
        )

    def _create_header(self) -> pn.Row:
        """Create the dashboard header."""
        title = pn.pane.HTML("""
            <h1 style='color: #00d4aa; margin: 0; font-size: 24px;'>
                🖥️ DuckDB Financial Infrastructure Monitor
            </h1>
        """)

        status_indicator = pn.pane.HTML("""
            <div style='display: flex; align-items: center; gap: 8px;'>
                <div class='status-indicator status-running'></div>
                <span style='color: #74b9ff; font-size: 14px;'>System Online</span>
            </div>
        """)

        refresh_button = pn.widgets.Button(
            name='🔄 Refresh',
            button_type='primary',
            width=100
        )
        refresh_button.on_click(self._manual_refresh)

        return pn.Row(
            title,
            pn.Spacer(),
            status_indicator,
            refresh_button,
            sizing_mode='stretch_width',
            css_classes=['dashboard-header']
        )

    def _switch_tab(self, tab_id: str) -> None:
        """Switch to a different tab."""
        self.selected_tab = tab_id
        self._update_main_content()
        logger.info("Switched to tab", extra={'tab': tab_id})

    def _update_main_content(self) -> None:
        """Update the main content area based on selected tab."""
        if self.selected_tab == 'overview':
            self.main_content.objects = [self._create_overview_tab()]
        elif self.selected_tab == 'tests':
            self.main_content.objects = [self._create_tests_tab()]
        elif self.selected_tab == 'logs':
            self.main_content.objects = [self._create_logs_tab()]
        elif self.selected_tab == 'metrics':
            self.main_content.objects = [self._create_metrics_tab()]
        elif self.selected_tab == 'alerts':
            self.main_content.objects = [self._create_alerts_tab()]
        elif self.selected_tab == 'settings':
            self.main_content.objects = [self._create_settings_tab()]
        else:
            self.main_content.objects = [pn.pane.HTML("<h2>Tab not implemented</h2>")]

    def _create_overview_tab(self) -> pn.Column:
        """Create the overview dashboard tab."""
        # Key metrics cards
        system_metrics = self._get_system_metrics_display()
        test_status = self._get_test_status_display()
        recent_alerts = self._get_recent_alerts_display()

        # Charts row
        charts_row = pn.Row(
            self._create_cpu_chart(),
            self._create_memory_chart(),
            self._create_test_trends_chart(),
            sizing_mode='stretch_width'
        )

        return pn.Column(
            pn.pane.HTML("<h2>System Overview</h2>"),
            pn.Row(system_metrics, test_status, recent_alerts, sizing_mode='stretch_width'),
            pn.pane.HTML("<h3>Performance Trends</h3>"),
            charts_row,
            sizing_mode='stretch_both'
        )

    def _create_tests_tab(self) -> pn.Column:
        """Create the tests monitoring tab."""
        # Test control panel
        test_controls = self._create_test_controls()

        # Test execution overview
        test_overview = self._create_test_execution_overview()

        # Test results and trends
        test_results_section = self._create_test_results_section()

        return pn.Column(
            pn.pane.HTML("<h2>Test Monitoring</h2>"),
            test_controls,
            test_overview,
            test_results_section,
            sizing_mode='stretch_both'
        )

    def _create_logs_tab(self) -> pn.Column:
        """Create the logs analysis tab."""
        # Log filters and controls
        log_controls = self._create_log_controls()

        # Log analysis overview
        log_overview = self._create_log_overview()

        # Log viewer and details
        log_details = self._create_log_details_section()

        return pn.Column(
            pn.pane.HTML("<h2>System Logs</h2>"),
            log_controls,
            log_overview,
            log_details,
            sizing_mode='stretch_both'
        )

    def _create_metrics_tab(self) -> pn.Column:
        """Create the metrics monitoring tab."""
        # System metrics
        system_metrics = self._create_system_metrics_panel()

        # Database metrics
        db_metrics = self._create_database_metrics_panel()

        # Custom metrics
        custom_metrics = self._create_custom_metrics_panel()

        return pn.Column(
            pn.pane.HTML("<h2>Performance Metrics</h2>"),
            pn.Row(system_metrics, db_metrics, sizing_mode='stretch_width'),
            custom_metrics,
            sizing_mode='stretch_both'
        )

    def _create_alerts_tab(self) -> pn.Column:
        """Create the alerts monitoring tab."""
        # Active alerts
        active_alerts = self._get_active_alerts()

        # Alert history
        alert_history = self._get_alert_history()

        # Alert configuration
        alert_config = self._create_alert_configuration()

        return pn.Column(
            pn.pane.HTML("<h2>System Alerts</h2>"),
            pn.Row(active_alerts, alert_history, sizing_mode='stretch_width'),
            alert_config,
            sizing_mode='stretch_both'
        )

    def _create_settings_tab(self) -> pn.Column:
        """Create the settings tab."""
        return pn.Column(
            pn.pane.HTML("<h2>Dashboard Settings</h2>"),
            pn.pane.HTML("<p>Settings panel - Coming soon!</p>"),
            sizing_mode='stretch_both'
        )

    def _get_system_metrics_display(self) -> pn.Column:
        """Get system metrics display cards."""
        try:
            metrics = metrics_collector.get_metric_summary()

            cpu_card = monitoring_theme.create_metric_display(
                f"{metrics['cpu']['avg_percent']:.1f}%",
                "CPU Usage",
                f"{metrics['cpu']['max_percent']:.1f}% max"
            )

            memory_card = monitoring_theme.create_metric_display(
                f"{metrics['memory']['avg_percent']:.1f}%",
                "Memory Usage",
                f"{metrics['memory']['max_percent']:.1f}% max"
            )

            return pn.Column(
                pn.pane.HTML("<h3>System Metrics</h3>"),
                pn.Row(cpu_card, memory_card, sizing_mode='stretch_width'),
                css_classes=['monitoring-card']
            )
        except Exception as e:
            logger.error("Failed to get system metrics", extra={'error': str(e)})
            return pn.Column(
                pn.pane.HTML("<h3>System Metrics</h3><p>Error loading metrics</p>"),
                css_classes=['monitoring-card']
            )

    def _get_test_status_display(self) -> pn.Column:
        """Get test status overview."""
        try:
            status = test_monitor.get_current_status()

            summary = status.get('summary', {})

            passed_card = monitoring_theme.create_metric_display(
                str(summary.get('passed', 0)),
                "Tests Passed",
                f"{summary.get('success_rate', 0):.1f}% success rate"
            )

            failed_count = summary.get('failed', 0) or 0
            failed_card = monitoring_theme.create_metric_display(
                str(failed_count),
                "Tests Failed",
                "Last 24h" if failed_count > 0 else ""
            )

            return pn.Column(
                pn.pane.HTML("<h3>Test Status</h3>"),
                pn.Row(passed_card, failed_card, sizing_mode='stretch_width'),
                css_classes=['monitoring-card']
            )
        except Exception as e:
            logger.error("Failed to get test status", extra={'error': str(e)})
            return pn.Column(
                pn.pane.HTML("<h3>Test Status</h3><p>Error loading test status</p>"),
                css_classes=['monitoring-card']
            )

    def _get_recent_alerts_display(self) -> pn.Column:
        """Get recent alerts display."""
        try:
            alerts = alert_manager.get_alert_history(days=1)[:5]

            alert_cards = []
            for alert in alerts:
                alert_cards.append(monitoring_theme.create_alert_card(alert))

            if not alert_cards:
                alert_cards = [pn.pane.HTML("<p style='color: #636e72;'>No recent alerts</p>")]

            return pn.Column(
                pn.pane.HTML("<h3>Recent Alerts</h3>"),
                *alert_cards,
                css_classes=['monitoring-card']
            )
        except Exception as e:
            logger.error("Failed to get recent alerts", extra={'error': str(e)})
            return pn.Column(
                pn.pane.HTML("<h3>Recent Alerts</h3><p>Error loading alerts</p>"),
                css_classes=['monitoring-card']
            )

    def _create_cpu_chart(self) -> pn.pane.Plotly:
        """Create CPU usage chart."""
        try:
            # Mock chart data for now - will be replaced with real data
            import plotly.graph_objects as go

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[datetime.now() - timedelta(hours=i) for i in range(24, 0, -1)],
                y=[50 + (i % 10) for i in range(24)],
                mode='lines',
                name='CPU Usage',
                line=dict(color='#00d4aa', width=2)
            ))

            fig.update_layout(
                title='CPU Usage (Last 24h)',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ffffff'),
                margin=dict(l=20, r=20, t=40, b=20)
            )

            return pn.pane.Plotly(fig, height=300, sizing_mode='stretch_width')
        except Exception as e:
            logger.error("Failed to create CPU chart", extra={'error': str(e)})
            return pn.pane.HTML("<p>Error loading CPU chart</p>")

    def _create_memory_chart(self) -> pn.pane.Plotly:
        """Create memory usage chart."""
        try:
            import plotly.graph_objects as go

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[datetime.now() - timedelta(hours=i) for i in range(24, 0, -1)],
                y=[60 + (i % 15) for i in range(24)],
                mode='lines',
                name='Memory Usage',
                line=dict(color='#6c5ce7', width=2)
            ))

            fig.update_layout(
                title='Memory Usage (Last 24h)',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ffffff'),
                margin=dict(l=20, r=20, t=40, b=20)
            )

            return pn.pane.Plotly(fig, height=300, sizing_mode='stretch_width')
        except Exception as e:
            logger.error("Failed to create memory chart", extra={'error': str(e)})
            return pn.pane.HTML("<p>Error loading memory chart</p>")

    def _create_test_trends_chart(self) -> pn.pane.Plotly:
        """Create test trends chart."""
        try:
            import plotly.graph_objects as go

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=['Passed', 'Failed', 'Skipped'],
                y=[85, 5, 10],
                marker_color=['#00b894', '#e17055', '#fdcb6e']
            ))

            fig.update_layout(
                title='Test Results Summary',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ffffff'),
                margin=dict(l=20, r=20, t=40, b=20)
            )

            return pn.pane.Plotly(fig, height=300, sizing_mode='stretch_width')
        except Exception as e:
            logger.error("Failed to create test trends chart", extra={'error': str(e)})
            return pn.pane.HTML("<p>Error loading test trends chart</p>")

    def _create_test_controls(self) -> pn.Column:
        """Create test execution controls."""
        test_suite_select = pn.widgets.Select(
            name='Test Suite',
            options=['unit', 'integration', 'e2e', 'performance', 'all'],
            value='unit'
        )

        run_button = pn.widgets.Button(
            name='▶️ Run Tests',
            button_type='primary'
        )

        @run_button.on_click
        def run_tests(event):
            try:
                suite = test_suite_select.value
                execution_id = test_monitor.run_test_suite(suite)

                # Show success message
                pn.state.notifications.success(f"Started test suite: {suite} (ID: {execution_id})")
                logger.info("Test suite started from dashboard", extra={
                    'suite': suite,
                    'execution_id': execution_id
                })
            except Exception as e:
                pn.state.notifications.error(f"Failed to start tests: {str(e)}")
                logger.error("Failed to start test suite from dashboard", extra={'error': str(e)})

        return pn.Column(
            pn.pane.HTML("<h3>Test Execution</h3>"),
            pn.Row(test_suite_select, run_button, sizing_mode='stretch_width'),
            css_classes=['monitoring-card']
        )

    def _create_test_execution_overview(self) -> pn.Column:
        """Create test execution overview with real-time status."""
        try:
            status = test_monitor.get_current_status()

            # Active executions
            active_executions = status.get('active_executions', [])
            active_count = len(active_executions)

            # Summary metrics
            summary = status.get('summary', {})
            total_tests = summary.get('total_tests', 0)
            passed_tests = summary.get('passed', 0)
            failed_tests = summary.get('failed', 0)
            success_rate = summary.get('success_rate', 0)

            # Create metrics cards
            active_card = monitoring_theme.create_metric_display(
                str(active_count),
                "Active Executions",
                "Running now"
            )

            total_card = monitoring_theme.create_metric_display(
                str(total_tests),
                "Total Tests",
                f"{success_rate:.1f}% success rate" if total_tests > 0 else "No tests yet"
            )

            passed_card = monitoring_theme.create_metric_display(
                str(passed_tests),
                "Tests Passed",
                f"{(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else ""
            )

            failed_card = monitoring_theme.create_metric_display(
                str(failed_tests),
                "Tests Failed",
                f"{(failed_tests/total_tests*100):.1f}%" if total_tests > 0 else ""
            )

            # Active execution details
            if active_executions:
                active_details = []
                for execution in active_executions[:3]:  # Show first 3
                    status_indicator = monitoring_theme.create_status_indicator(execution.get('status', 'unknown'))
                    execution_info = pn.Row(
                        status_indicator,
                        pn.pane.HTML(f"""
                            <div style="margin-left: 8px;">
                                <strong>{execution.get('suite', 'Unknown')}</strong><br>
                                <small>ID: {execution.get('execution_id', 'N/A')[:8]}</small>
                            </div>
                        """)
                    )
                    active_details.append(execution_info)

                active_section = pn.Column(
                    pn.pane.HTML("<h4>Active Test Executions</h4>"),
                    *active_details,
                    css_classes=['monitoring-card']
                )
            else:
                active_section = pn.Column(
                    pn.pane.HTML("<h4>Active Test Executions</h4>"),
                    pn.pane.HTML("<p style='color: #636e72;'>No active test executions</p>"),
                    css_classes=['monitoring-card']
                )

            return pn.Column(
                pn.Row(active_card, total_card, passed_card, failed_card, sizing_mode='stretch_width'),
                active_section,
                sizing_mode='stretch_width'
            )

        except Exception as e:
            logger.error("Failed to create test execution overview", extra={'error': str(e)})
            return pn.Column(
                pn.pane.HTML("<h3>Test Execution Overview</h3>"),
                pn.pane.HTML("<p>Error loading test execution data</p>"),
                css_classes=['monitoring-card']
            )

    def _create_test_results_section(self) -> pn.Column:
        """Create comprehensive test results section with charts and trends."""
        try:
            # Get test history for trends
            test_history = test_monitor.get_test_history(days=7)

            # Test results chart
            results_chart = self._create_test_results_chart(test_history)

            # Test performance chart
            performance_chart = self._create_test_performance_chart(test_history)

            # Recent test results table
            recent_results_table = self._create_recent_test_results_table(test_history)

            return pn.Column(
                pn.pane.HTML("<h3>Test Results & Trends</h3>"),
                pn.Row(results_chart, performance_chart, sizing_mode='stretch_width'),
                recent_results_table,
                sizing_mode='stretch_width'
            )

        except Exception as e:
            logger.error("Failed to create test results section", extra={'error': str(e)})
            return pn.Column(
                pn.pane.HTML("<h3>Test Results & Trends</h3>"),
                pn.pane.HTML("<p>Error loading test results data</p>"),
                css_classes=['monitoring-card']
            )

    def _create_log_controls(self) -> pn.Column:
        """Create log filtering and control panel."""
        try:
            # Level filter
            level_select = pn.widgets.MultiSelect(
                name='Log Levels',
                options=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                value=['INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                width=200
            )

            # Component filter
            components = log_aggregator.get_components()[:10]  # Limit to first 10
            component_select = pn.widgets.MultiSelect(
                name='Components',
                options=components,
                value=[],
                width=200
            )

            # Time range
            time_range = pn.widgets.Select(
                name='Time Range',
                options=['Last Hour', 'Last 6 Hours', 'Last 24 Hours', 'Last 7 Days'],
                value='Last 24 Hours',
                width=150
            )

            # Search input
            search_input = pn.widgets.TextInput(
                name='Search',
                placeholder='Search logs...',
                width=250
            )

            # Refresh button
            refresh_button = pn.widgets.Button(
                name='🔄 Refresh',
                button_type='primary',
                width=100
            )

            # Export button
            export_button = pn.widgets.Button(
                name='📥 Export',
                button_type='light',
                width=100
            )

            # Create filter row
            filters_row = pn.Row(
                pn.Column(
                    pn.pane.HTML("<strong>Filters:</strong>"),
                    pn.Row(level_select, component_select, time_range),
                    pn.Row(search_input, refresh_button, export_button)
                ),
                sizing_mode='stretch_width'
            )

            # Store filter widgets for access
            self._log_filters = {
                'levels': level_select,
                'components': component_select,
                'time_range': time_range,
                'search': search_input
            }

            # Bind refresh action
            refresh_button.on_click(self._refresh_logs)

            return pn.Column(
                pn.pane.HTML("<h3>Log Controls</h3>"),
                filters_row,
                css_classes=['monitoring-card']
            )

        except Exception as e:
            logger.error("Failed to create log controls", extra={'error': str(e)})
            return pn.Column(
                pn.pane.HTML("<h3>Log Controls</h3>"),
                pn.pane.HTML("<p>Error loading log controls</p>"),
                css_classes=['monitoring-card']
            )

    def _create_log_overview(self) -> pn.Column:
        """Create log analysis overview with statistics."""
        try:
            # Get log statistics
            stats = log_aggregator.get_log_stats()

            # Create metric cards
            total_logs_card = monitoring_theme.create_metric_display(
                str(stats['total_entries']),
                "Total Logs",
                f"Last {stats['time_range']}"
            )

            error_rate_card = monitoring_theme.create_metric_display(
                ".1f",
                "Error Rate",
                "Percentage of error logs"
            )

            unique_correlation_card = monitoring_theme.create_metric_display(
                str(stats['unique_correlation_ids']),
                "Active Traces",
                "Unique correlation IDs"
            )

            # Top error types
            top_errors = stats.get('most_common_errors', [])
            if top_errors:
                error_list = []
                for error_msg, count in top_errors[:5]:
                    error_list.append(f"• {error_msg[:50]}... ({count})" if len(error_msg) > 50 else f"• {error_msg} ({count})")

                top_errors_html = "<br>".join(error_list)
            else:
                top_errors_html = "<em>No errors found</em>"

            # Logs by level breakdown
            level_breakdown = stats.get('entries_by_level', {})
            level_stats = []
            for level, count in level_breakdown.items():
                level_stats.append(f"{level}: {count}")

            level_stats_html = " | ".join(level_stats) if level_stats else "No logs found"

            return pn.Column(
                pn.Row(total_logs_card, error_rate_card, unique_correlation_card, sizing_mode='stretch_width'),
                pn.Column(
                    pn.pane.HTML("<h4>Log Statistics</h4>"),
                    pn.pane.HTML(f"<p><strong>By Level:</strong> {level_stats_html}</p>"),
                    pn.pane.HTML(f"<p><strong>Top Errors:</strong><br>{top_errors_html}</p>"),
                    css_classes=['monitoring-card']
                ),
                sizing_mode='stretch_width'
            )

        except Exception as e:
            logger.error("Failed to create log overview", extra={'error': str(e)})
            return pn.Column(
                pn.pane.HTML("<h3>Log Overview</h3>"),
                pn.pane.HTML("<p>Error loading log statistics</p>"),
                css_classes=['monitoring-card']
            )

    def _create_log_details_section(self) -> pn.Column:
        """Create log details section with viewer and charts."""
        try:
            # Log timeline chart
            log_timeline = self._create_log_timeline_chart()

            # Log entries table
            log_table = self._create_log_entries_table()

            return pn.Column(
                pn.pane.HTML("<h3>Log Details</h3>"),
                log_timeline,
                log_table,
                sizing_mode='stretch_width'
            )

        except Exception as e:
            logger.error("Failed to create log details section", extra={'error': str(e)})
            return pn.Column(
                pn.pane.HTML("<h3>Log Details</h3>"),
                pn.pane.HTML("<p>Error loading log details</p>"),
                css_classes=['monitoring-card']
            )

    def _refresh_logs(self, event=None) -> None:
        """Refresh log data based on current filters."""
        try:
            # Get current filter values
            filters = self._log_filters
            levels = filters['levels'].value
            components = filters['components'].value
            time_range = filters['time_range'].value
            search_text = filters['search'].value

            # Parse time range
            from datetime import datetime, timedelta
            now = datetime.now()

            if time_range == 'Last Hour':
                start_time = now - timedelta(hours=1)
            elif time_range == 'Last 6 Hours':
                start_time = now - timedelta(hours=6)
            elif time_range == 'Last 7 Days':
                start_time = now - timedelta(days=7)
            else:  # Last 24 Hours
                start_time = now - timedelta(hours=24)

            # Apply filters to log aggregator
            from ..logging.aggregator import LogFilter
            log_filter = LogFilter(
                start_time=start_time,
                end_time=datetime.now(),
                levels=levels if levels else None,
                components=components if components else None,
                message_contains=search_text if search_text else None,
                limit=100
            )

            # Get filtered logs
            filtered_logs = log_aggregator.get_logs(log_filter)

            # Update displays (this would trigger reactive updates)
            self.refresh_trigger += 1

            logger.info("Logs refreshed with filters", extra={
                'levels': levels,
                'components': components,
                'time_range': time_range,
                'search': search_text,
                'result_count': len(filtered_logs)
            })

        except Exception as e:
            logger.error("Failed to refresh logs", extra={'error': str(e)})

    def _create_log_timeline_chart(self) -> pn.pane.Plotly:
        """Create log timeline chart showing log volume over time."""
        try:
            import plotly.graph_objects as go
            from datetime import datetime, timedelta

            # Get recent log data (mock data for now)
            hours = 24
            time_points = []
            log_counts = {'DEBUG': [], 'INFO': [], 'WARNING': [], 'ERROR': [], 'CRITICAL': []}

            for i in range(hours):
                time_point = datetime.now() - timedelta(hours=hours-i-1)
                time_points.append(time_point.strftime('%H:%M'))

                # Mock data - in real implementation, get from log_aggregator
                base_count = 50 + (i % 20)
                log_counts['DEBUG'].append(base_count)
                log_counts['INFO'].append(base_count * 2)
                log_counts['WARNING'].append(base_count // 4)
                log_counts['ERROR'].append(base_count // 8)
                log_counts['CRITICAL'].append(base_count // 20)

            # Create stacked area chart
            fig = go.Figure()

            colors = {
                'DEBUG': '#636e72',
                'INFO': '#74b9ff',
                'WARNING': '#fdcb6e',
                'ERROR': '#e17055',
                'CRITICAL': '#c0392b'
            }

            for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
                fig.add_trace(go.Scatter(
                    x=time_points,
                    y=log_counts[level],
                    mode='lines',
                    name=level,
                    stackgroup='one',
                    line=dict(width=0.5),
                    fillcolor=colors[level],
                    hovertemplate=f'{level}: %{{y}}<extra></extra>'
                ))

            fig.update_layout(
                title='Log Volume Over Time (Last 24 Hours)',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ffffff'),
                showlegend=True,
                xaxis=dict(
                    title="Time",
                    gridcolor='#555555'
                ),
                yaxis=dict(
                    title="Log Count",
                    gridcolor='#555555'
                ),
                margin=dict(l=60, r=20, t=60, b=40)
            )

            return pn.pane.Plotly(fig, height=300, sizing_mode='stretch_width')

        except Exception as e:
            logger.error("Failed to create log timeline chart", extra={'error': str(e)})
            return pn.pane.HTML("<p>Error loading log timeline</p>")

    def _create_log_entries_table(self) -> pn.Column:
        """Create log entries table with recent logs."""
        try:
            # Get recent logs
            from ..logging.aggregator import LogFilter
            log_filter = LogFilter(limit=50)
            recent_logs = log_aggregator.get_logs(log_filter)

            if not recent_logs:
                return pn.Column(
                    pn.pane.HTML("<h4>Recent Log Entries</h4>"),
                    pn.pane.HTML("<p style='color: #636e72;'>No logs available</p>"),
                    css_classes=['monitoring-card']
                )

            # Create table data
            table_data = []
            for log in recent_logs[:20]:  # Show first 20
                timestamp = log.get('timestamp', '')
                if hasattr(timestamp, 'strftime'):
                    timestamp = timestamp.strftime('%H:%M:%S')
                elif isinstance(timestamp, str) and 'T' in timestamp:
                    timestamp = timestamp.split('T')[1][:8] if len(timestamp.split('T')) > 1 else timestamp

                table_data.append({
                    'Time': timestamp,
                    'Level': log.get('level', 'UNKNOWN'),
                    'Component': log.get('component', 'UNKNOWN')[:20],
                    'Message': log.get('message', '')[:80] + '...' if len(log.get('message', '')) > 80 else log.get('message', ''),
                    'Correlation': log.get('correlation_id', '')[:8] if log.get('correlation_id') else ''
                })

            # Create simple HTML table
            if table_data:
                table_rows = ""
                for row in table_data:
                    level_class = f"status-{row['Level'].lower()}"
                    table_rows += f"""
                    <tr>
                        <td>{row['Time']}</td>
                        <td><span class="status-indicator {level_class}"></span>{row['Level']}</td>
                        <td>{row['Component']}</td>
                        <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis;">{row['Message']}</td>
                        <td>{row['Correlation']}</td>
                    </tr>
                    """

                table_html = f"""
                <div class="table-container" style="max-height: 400px; overflow-y: auto;">
                    <table class="data-table-content" style="width: 100%; border-collapse: collapse; font-size: 12px;">
                        <thead>
                            <tr style="background-color: #2d2d2d; color: #ffffff;">
                                <th style="padding: 6px; border: 1px solid #404040;">Time</th>
                                <th style="padding: 6px; border: 1px solid #404040;">Level</th>
                                <th style="padding: 6px; border: 1px solid #404040;">Component</th>
                                <th style="padding: 6px; border: 1px solid #404040;">Message</th>
                                <th style="padding: 6px; border: 1px solid #404040;">Correlation</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
                """
            else:
                table_html = "<p>No log entries available</p>"

            return pn.Column(
                pn.pane.HTML(f"<h4>Recent Log Entries</h4>{table_html}"),
                css_classes=['monitoring-card']
            )

        except Exception as e:
            logger.error("Failed to create log entries table", extra={'error': str(e)})
            return pn.Column(
                pn.pane.HTML("<h4>Recent Log Entries</h4>"),
                pn.pane.HTML("<p>Error loading log entries</p>"),
                css_classes=['monitoring-card']
            )

    def _create_system_metrics_panel(self) -> pn.Column:
        """Create system metrics panel."""
        return pn.Column(
            pn.pane.HTML("<h3>System Metrics</h3>"),
            pn.pane.HTML("<p>Detailed system performance metrics</p>"),
            css_classes=['monitoring-card']
        )

    def _create_database_metrics_panel(self) -> pn.Column:
        """Create database metrics panel."""
        return pn.Column(
            pn.pane.HTML("<h3>Database Metrics</h3>"),
            pn.pane.HTML("<p>Database performance and usage metrics</p>"),
            css_classes=['monitoring-card']
        )

    def _create_custom_metrics_panel(self) -> pn.Column:
        """Create custom metrics panel."""
        return pn.Column(
            pn.pane.HTML("<h3>Custom Metrics</h3>"),
            pn.pane.HTML("<p>Custom application metrics</p>"),
            css_classes=['monitoring-card']
        )

    def _get_active_alerts(self) -> pn.Column:
        """Get active alerts panel."""
        return pn.Column(
            pn.pane.HTML("<h3>Active Alerts</h3>"),
            pn.pane.HTML("<p>Currently active system alerts</p>"),
            css_classes=['monitoring-card']
        )

    def _get_alert_history(self) -> pn.Column:
        """Get alert history panel."""
        return pn.Column(
            pn.pane.HTML("<h3>Alert History</h3>"),
            pn.pane.HTML("<p>Historical alert data</p>"),
            css_classes=['monitoring-card']
        )

    def _create_alert_configuration(self) -> pn.Column:
        """Create alert configuration panel."""
        return pn.Column(
            pn.pane.HTML("<h3>Alert Configuration</h3>"),
            pn.pane.HTML("<p>Configure alert rules and thresholds</p>"),
            css_classes=['monitoring-card']
        )

    def _manual_refresh(self, event) -> None:
        """Manual refresh triggered by user."""
        self.refresh_trigger += 1
        pn.state.notifications.info("Dashboard refreshed")
        logger.info("Manual dashboard refresh triggered")

    def _background_refresh(self) -> None:
        """Background refresh thread."""
        while True:
            try:
                time.sleep(config.dashboard.refresh_interval)
                # Trigger reactive update
                self.refresh_trigger += 1
            except Exception as e:
                logger.error("Background refresh failed", extra={'error': str(e)})
                time.sleep(5)  # Wait before retry

    def get_app(self) -> pn.Column:
        """Get the main dashboard application."""
        return self.layout


def create_dashboard_app() -> pn.Column:
    """Create and return the dashboard application."""
    app = DashboardApp()
    return app.get_app()


# Main entry point for running the dashboard
def run_dashboard(port: int = None, host: str = None) -> None:
    """Run the monitoring dashboard."""
    if port is None:
        port = config.dashboard.port
    if host is None:
        host = config.dashboard.host

    # Initialize monitoring systems
    try:
        # Setup database schema
        from ..config.database import monitoring_db
        monitoring_db.setup_schema()

        # Start metrics collection
        metrics_collector.start_collection()

        logger.info("Starting monitoring dashboard", extra={
            'port': port,
            'host': host
        })

        # Create and serve the dashboard
        dashboard = create_dashboard_app()

        pn.serve(
            dashboard,
            port=port,
            host=host,
            title="DuckDB Financial Infrastructure Monitor",
            show=False,
            autoreload=True
        )

    except Exception as e:
        logger.error("Failed to start dashboard", extra={'error': str(e)})
        raise


    def _create_test_results_chart(self, test_history) -> pn.pane.Plotly:
        """Create test results trend chart."""
        try:
            import plotly.graph_objects as go
            from collections import defaultdict
            from datetime import datetime, timedelta

            # Process test history data
            daily_stats = defaultdict(lambda: {'passed': 0, 'failed': 0, 'skipped': 0, 'total': 0})

            for test in test_history:
                date = test.get('executed_at')
                if isinstance(date, str):
                    date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                elif hasattr(date, 'date'):
                    date = date.date()
                else:
                    continue

                date_str = date.strftime('%Y-%m-%d')
                status = test.get('status', '').lower()

                daily_stats[date_str]['total'] += 1
                if status == 'passed':
                    daily_stats[date_str]['passed'] += 1
                elif status == 'failed':
                    daily_stats[date_str]['failed'] += 1
                elif status == 'skipped':
                    daily_stats[date_str]['skipped'] += 1

            # Get last 7 days
            dates = []
            passed = []
            failed = []
            skipped = []

            for i in range(6, -1, -1):
                date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                stats = daily_stats[date]
                dates.append(date[-5:])  # Show MM-DD format
                passed.append(stats['passed'])
                failed.append(stats['failed'])
                skipped.append(stats['skipped'])

            # Create stacked bar chart
            fig = go.Figure()

            fig.add_trace(go.Bar(
                name='Passed',
                x=dates,
                y=passed,
                marker_color='#00b894',
                hovertemplate='Passed: %{y}<extra></extra>'
            ))

            fig.add_trace(go.Bar(
                name='Failed',
                x=dates,
                y=failed,
                marker_color='#e17055',
                hovertemplate='Failed: %{y}<extra></extra>'
            ))

            fig.add_trace(go.Bar(
                name='Skipped',
                x=dates,
                y=skipped,
                marker_color='#fdcb6e',
                hovertemplate='Skipped: %{y}<extra></extra>'
            ))

            fig.update_layout(
                title='Daily Test Results (Last 7 Days)',
                barmode='stack',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ffffff'),
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                margin=dict(l=20, r=20, t=60, b=20)
            )

            return pn.pane.Plotly(fig, height=350, sizing_mode='stretch_width')

        except Exception as e:
            logger.error("Failed to create test results chart", extra={'error': str(e)})
            return pn.pane.HTML("<p>Error loading test results chart</p>")

    def _create_test_performance_chart(self, test_history) -> pn.pane.Plotly:
        """Create test performance chart showing duration trends."""
        try:
            import plotly.graph_objects as go
            from collections import defaultdict

            # Process duration data by suite
            suite_durations = defaultdict(list)

            for test in test_history:
                suite = test.get('suite_name', 'unknown')
                duration = test.get('duration', 0)
                if duration and duration > 0:
                    suite_durations[suite].append(duration)

            # Calculate average durations
            suites = []
            avg_durations = []

            for suite, durations in suite_durations.items():
                if durations:
                    suites.append(suite.title())
                    avg_durations.append(sum(durations) / len(durations))

            # Sort by duration
            sorted_data = sorted(zip(avg_durations, suites), reverse=True)
            avg_durations, suites = zip(*sorted_data) if sorted_data else ([], [])

            # Create horizontal bar chart
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=avg_durations,
                y=suites,
                orientation='h',
                marker=dict(
                    color='#6c5ce7',
                    line=dict(color='#a29bfe', width=1)
                ),
                hovertemplate='Avg Duration: %{x:.2f}s<extra></extra>'
            ))

            fig.update_layout(
                title='Average Test Duration by Suite',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ffffff'),
                xaxis=dict(
                    title="Duration (seconds)",
                    gridcolor='#555555'
                ),
                yaxis=dict(
                    title="Test Suite",
                    autorange="reversed"
                ),
                margin=dict(l=100, r=20, t=60, b=20)
            )

            return pn.pane.Plotly(fig, height=350, sizing_mode='stretch_width')

        except Exception as e:
            logger.error("Failed to create test performance chart", extra={'error': str(e)})
            return pn.pane.HTML("<p>Error loading test performance chart</p>")

    def _create_recent_test_results_table(self, test_history) -> pn.Column:
        """Create recent test results table."""
        try:
            # Take most recent 10 results
            recent_tests = test_history[:10] if test_history else []

            if not recent_tests:
                return pn.Column(
                    pn.pane.HTML("<h4>Recent Test Results</h4>"),
                    pn.pane.HTML("<p style='color: #636e72;'>No test results available</p>"),
                    css_classes=['monitoring-card']
                )

            # Create table data
            table_data = []
            for test in recent_tests:
                executed_at = test.get('executed_at', '')
                if hasattr(executed_at, 'strftime'):
                    executed_at = executed_at.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(executed_at, str) and len(executed_at) > 19:
                    executed_at = executed_at[:19]  # Truncate if too long

                table_data.append({
                    'Suite': test.get('suite_name', 'N/A'),
                    'Test': test.get('test_name', 'N/A')[:50] + '...' if len(test.get('test_name', '')) > 50 else test.get('test_name', 'N/A'),
                    'Status': test.get('status', 'unknown').title(),
                    'Duration': '.2f' if test.get('duration') else 'N/A',
                    'Executed': executed_at
                })

            # Create simple HTML table
            if table_data:
                table_rows = ""
                for row in table_data:
                    status_class = f"status-{row['Status'].lower()}"
                    table_rows += f"""
                    <tr>
                        <td>{row['Suite']}</td>
                        <td>{row['Test']}</td>
                        <td><span class="status-indicator {status_class}"></span>{row['Status']}</td>
                        <td>{row['Duration']}</td>
                        <td>{row['Executed']}</td>
                    </tr>
                    """

                table_html = f"""
                <div class="table-container" style="max-height: 300px; overflow-y: auto;">
                    <table class="data-table-content" style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background-color: #2d2d2d; color: #ffffff;">
                                <th style="padding: 8px; border: 1px solid #404040;">Suite</th>
                                <th style="padding: 8px; border: 1px solid #404040;">Test</th>
                                <th style="padding: 8px; border: 1px solid #404040;">Status</th>
                                <th style="padding: 8px; border: 1px solid #404040;">Duration</th>
                                <th style="padding: 8px; border: 1px solid #404040;">Executed</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
                """
            else:
                table_html = "<p>No test results available</p>"

            return pn.Column(
                pn.pane.HTML(f"<h4>Recent Test Results</h4>{table_html}"),
                css_classes=['monitoring-card']
            )

        except Exception as e:
            logger.error("Failed to create test results table", extra={'error': str(e)})
            return pn.Column(
                pn.pane.HTML("<h4>Recent Test Results</h4>"),
                pn.pane.HTML("<p>Error loading test results table</p>"),
                css_classes=['monitoring-card']
            )


if __name__ == "__main__":
    run_dashboard()
