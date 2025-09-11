#!/usr/bin/env python3
"""
Performance Dashboard - Real-time Performance Visualization

This module provides a comprehensive dashboard for visualizing performance
metrics, system health, and trading analytics in real-time.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import threading
import logging
from pathlib import Path

# Import our monitoring components
from .performance_monitor import PerformanceMonitor, RuleExecutionMetric
from .alert_system import AlertManager, AlertConfig


@dataclass
class DashboardConfig:
    """Configuration for the performance dashboard."""
    update_interval: int = 5  # seconds
    history_hours: int = 24
    max_chart_points: int = 100
    enable_real_time: bool = True
    theme: str = "dark"  # light, dark, auto


class PerformanceDashboard:
    """Real-time performance dashboard."""

    def __init__(self, monitor: PerformanceMonitor, alert_manager: Optional[AlertManager] = None):
        self.monitor = monitor
        self.alert_manager = alert_manager
        self.config = DashboardConfig()
        self._dashboard_active = False
        self._dashboard_thread = None

        # Dashboard data cache
        self.cached_data = {
            'system_metrics': {},
            'rule_performance': {},
            'alerts': [],
            'last_update': None
        }

        self.logger = logging.getLogger(__name__)

    def start_dashboard(self):
        """Start the dashboard update loop."""
        if self._dashboard_active:
            return

        self._dashboard_active = True
        self._dashboard_thread = threading.Thread(target=self._dashboard_loop, daemon=True)
        self._dashboard_thread.start()

        self.logger.info("Performance dashboard started")

    def stop_dashboard(self):
        """Stop the dashboard."""
        self._dashboard_active = False
        if self._dashboard_thread:
            self._dashboard_thread.join(timeout=5)

        self.logger.info("Performance dashboard stopped")

    def _dashboard_loop(self):
        """Main dashboard update loop."""
        while self._dashboard_active:
            try:
                self._update_dashboard_data()
                time.sleep(self.config.update_interval)
            except Exception as e:
                self.logger.error(f"Dashboard update error: {e}")
                time.sleep(10)

    def _update_dashboard_data(self):
        """Update cached dashboard data."""
        try:
            # Get system performance
            system_perf = self.monitor.get_system_performance_summary(self.config.history_hours)

            # Get rule performance for all rules (this would need to be implemented)
            rule_perf = self._get_all_rules_performance()

            # Get recent alerts
            alerts = []
            if self.alert_manager:
                alerts = self.alert_manager.get_alert_history(20)

            # Update cache
            self.cached_data.update({
                'system_metrics': system_perf,
                'rule_performance': rule_perf,
                'alerts': alerts,
                'last_update': datetime.now()
            })

        except Exception as e:
            self.logger.error(f"Failed to update dashboard data: {e}")

    def _get_all_rules_performance(self) -> Dict[str, Any]:
        """Get performance data for all rules."""
        # This would query the database for all unique rule IDs and their performance
        # For now, return mock data
        return {
            'breakout-standard': {
                'total_executions': 45,
                'success_rate': 0.711,
                'avg_execution_time': 1.2,
                'avg_signals_per_execution': 2.3,
                'total_signals': 103
            },
            'crp-standard': {
                'total_executions': 38,
                'success_rate': 0.737,
                'avg_execution_time': 1.8,
                'avg_signals_per_execution': 1.9,
                'total_signals': 72
            }
        }

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data."""
        return self.cached_data.copy()

    def generate_html_dashboard(self) -> str:
        """Generate HTML dashboard."""
        data = self.get_dashboard_data()

        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Trading System Performance Dashboard</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{
                    background-color: #1a1a1a;
                    color: #ffffff;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                }}
                .card {{
                    background-color: #2d2d2d;
                    border: 1px solid #404040;
                    border-radius: 10px;
                    margin-bottom: 20px;
                }}
                .card-header {{
                    background-color: #404040;
                    border-bottom: 1px solid #555;
                    color: #ffffff;
                }}
                .metric-value {{
                    font-size: 2rem;
                    font-weight: bold;
                    color: #00ff88;
                }}
                .alert-critical {{ background-color: #dc3545; color: white; }}
                .alert-warning {{ background-color: #ffc107; color: black; }}
                .alert-info {{ background-color: #0dcaf0; color: black; }}
            </style>
        </head>
        <body>
            <div class="container-fluid p-4">
                <div class="row mb-4">
                    <div class="col-12">
                        <h1 class="text-center mb-4">
                            🚀 Trading System Performance Dashboard
                        </h1>
                        <p class="text-center text-muted">
                            Real-time monitoring of system health and rule performance
                        </p>
                    </div>
                </div>

                <!-- System Health Overview -->
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title">CPU Usage</h5>
                                <div class="metric-value">{data['system_metrics'].get('avg_cpu_percent', 0):.1f}%</div>
                                <small class="text-muted">Average (24h)</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title">Memory Usage</h5>
                                <div class="metric-value">{data['system_metrics'].get('avg_memory_percent', 0):.1f}%</div>
                                <small class="text-muted">Peak: {data['system_metrics'].get('peak_memory_mb', 0):.0f} MB</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title">Active Threads</h5>
                                <div class="metric-value">{data['system_metrics'].get('avg_active_threads', 0):.0f}</div>
                                <small class="text-muted">Current average</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title">Network Conn.</h5>
                                <div class="metric-value">{data['system_metrics'].get('avg_network_connections', 0):.0f}</div>
                                <small class="text-muted">Active connections</small>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Rule Performance -->
                <div class="row mb-4">
                    <div class="col-md-8">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="fas fa-chart-bar"></i> Rule Performance Summary</h5>
                            </div>
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-dark">
                                        <thead>
                                            <tr>
                                                <th>Rule ID</th>
                                                <th>Executions</th>
                                                <th>Success Rate</th>
                                                <th>Avg Time</th>
                                                <th>Signals</th>
                                                <th>Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
        """

        # Add rule performance rows
        for rule_id, perf in data['rule_performance'].items():
            success_rate = perf.get('success_rate', 0) * 100
            status_class = "success" if success_rate > 70 else "warning" if success_rate > 50 else "danger"

            html += f"""
                                            <tr>
                                                <td><code>{rule_id}</code></td>
                                                <td>{perf.get('total_executions', 0)}</td>
                                                <td><span class="badge bg-{status_class}">{success_rate:.1f}%</span></td>
                                                <td>{perf.get('avg_execution_time', 0):.2f}s</td>
                                                <td>{perf.get('total_signals', 0)}</td>
                                                <td><span class="badge bg-success">Active</span></td>
                                            </tr>
            """

        html += """
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="fas fa-exclamation-triangle"></i> Recent Alerts</h5>
                            </div>
                            <div class="card-body">
        """

        # Add recent alerts
        alerts = data.get('alerts', [])
        if alerts:
            for alert in alerts[:5]:  # Show last 5 alerts
                severity_class = f"alert-{alert.get('severity', 'info')}"
                html += f"""
                                <div class="alert {severity_class} alert-dismissible fade show" role="alert">
                                    <strong>{alert.get('severity', 'info').upper()}:</strong> {alert.get('message', '')}
                                    <small class="text-muted d-block">{alert.get('timestamp', '')[:19]}</small>
                                </div>
                """
        else:
            html += """
                                <div class="text-center text-muted py-3">
                                    <i class="fas fa-check-circle fa-2x mb-2"></i>
                                    <p>No recent alerts</p>
                                </div>
            """

        html += """
                            </div>
                        </div>

                        <div class="card mt-3">
                            <div class="card-header">
                                <h5><i class="fas fa-clock"></i> Dashboard Status</h5>
                            </div>
                            <div class="card-body">
                                <div class="mb-2">
                                    <strong>Last Update:</strong>
                                    <span id="lastUpdate">{data.get('last_update', datetime.now()).strftime('%H:%M:%S')}</span>
                                </div>
                                <div class="mb-2">
                                    <strong>Update Interval:</strong> {self.config.update_interval}s
                                </div>
                                <div class="mb-2">
                                    <strong>Monitoring:</strong>
                                    <span class="badge bg-success">Active</span>
                                </div>
                                <div class="progress mt-3">
                                    <div class="progress-bar bg-success" style="width: 85%"></div>
                                </div>
                                <small class="text-muted">System Health: Good</small>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Charts Section -->
                <div class="row mb-4">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="fas fa-chart-line"></i> CPU Usage Trend</h5>
                            </div>
                            <div class="card-body">
                                <canvas id="cpuChart" width="400" height="200"></canvas>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="fas fa-chart-line"></i> Memory Usage Trend</h5>
                            </div>
                            <div class="card-body">
                                <canvas id="memoryChart" width="400" height="200"></canvas>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <div class="row">
                    <div class="col-12 text-center text-muted">
                        <small>
                            Trading System Performance Dashboard |
                            Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        </small>
                    </div>
                </div>
            </div>

            <script>
                // Auto-refresh dashboard
                setTimeout(function() {
                    location.reload();
                }, {self.config.update_interval * 1000});

                // Sample charts (would be populated with real data)
                document.addEventListener('DOMContentLoaded', function() {
                    // CPU Chart
                    const cpuCtx = document.getElementById('cpuChart').getContext('2d');
                    new Chart(cpuCtx, {
                        type: 'line',
                        data: {
                            labels: ['-24h', '-18h', '-12h', '-6h', 'Now'],
                            datasets: [{
                                label: 'CPU Usage %',
                                data: [45, 52, 48, 61, {data['system_metrics'].get('avg_cpu_percent', 50)}],
                                borderColor: '#00ff88',
                                backgroundColor: 'rgba(0, 255, 136, 0.1)',
                                tension: 0.4
                            }]
                        },
                        options: {
                            responsive: true,
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    max: 100
                                }
                            }
                        }
                    });

                    // Memory Chart
                    const memoryCtx = document.getElementById('memoryChart').getContext('2d');
                    new Chart(memoryCtx, {
                        type: 'line',
                        data: {
                            labels: ['-24h', '-18h', '-12h', '-6h', 'Now'],
                            datasets: [{
                                label: 'Memory Usage %',
                                data: [62, 68, 65, 72, {data['system_metrics'].get('avg_memory_percent', 70)}],
                                borderColor: '#0088ff',
                                backgroundColor: 'rgba(0, 136, 255, 0.1)',
                                tension: 0.4
                            }]
                        },
                        options: {
                            responsive: true,
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    max: 100
                                }
                            }
                        }
                    });
                });
            </script>
        </body>
        </html>
        """

        return html

    def save_dashboard_html(self, output_file: str) -> bool:
        """Save the dashboard as an HTML file."""
        try:
            html_content = self.generate_html_dashboard()

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            self.logger.info(f"Dashboard HTML saved to {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save dashboard HTML: {e}")
            return False

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate a comprehensive performance report."""
        data = self.get_dashboard_data()

        report = {
            'generated_at': datetime.now().isoformat(),
            'period_hours': self.config.history_hours,
            'system_health': {
                'cpu_usage_percent': data['system_metrics'].get('avg_cpu_percent', 0),
                'memory_usage_percent': data['system_metrics'].get('avg_memory_percent', 0),
                'peak_memory_mb': data['system_metrics'].get('peak_memory_mb', 0),
                'active_threads': data['system_metrics'].get('avg_active_threads', 0),
                'network_connections': data['system_metrics'].get('avg_network_connections', 0)
            },
            'rule_performance': data['rule_performance'],
            'alert_summary': self._calculate_alert_summary(data['alerts']),
            'recommendations': self._generate_recommendations(data)
        }

        return report

    def _calculate_alert_summary(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate alert summary statistics."""
        if not alerts:
            return {
                'total_alerts': 0,
                'critical_count': 0,
                'warning_count': 0,
                'error_count': 0,
                'most_common_type': None
            }

        severity_counts = {'critical': 0, 'warning': 0, 'error': 0, 'info': 0}
        type_counts = {}

        for alert in alerts:
            severity = alert.get('severity', 'info')
            alert_type = alert.get('type', 'unknown')

            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            type_counts[alert_type] = type_counts.get(alert_type, 0) + 1

        most_common_type = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else None

        return {
            'total_alerts': len(alerts),
            'critical_count': severity_counts['critical'],
            'warning_count': severity_counts['warning'],
            'error_count': severity_counts['error'],
            'most_common_type': most_common_type
        }

    def _generate_recommendations(self, data: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations."""
        recommendations = []

        # System health recommendations
        system_metrics = data.get('system_metrics', {})
        if system_metrics.get('avg_cpu_percent', 0) > 70:
            recommendations.append("Consider optimizing CPU-intensive operations or scaling resources")

        if system_metrics.get('avg_memory_percent', 0) > 80:
            recommendations.append("Monitor memory usage and consider memory optimization techniques")

        # Rule performance recommendations
        rule_performance = data.get('rule_performance', {})
        for rule_id, perf in rule_performance.items():
            if perf.get('success_rate', 0) < 0.7:
                recommendations.append(f"Review and optimize rule '{rule_id}' (success rate: {perf['success_rate']:.1f}%)")

            if perf.get('avg_execution_time', 0) > 3.0:
                recommendations.append(f"Optimize execution time for rule '{rule_id}' ({perf['avg_execution_time']:.2f}s)")

        # Alert-based recommendations
        alerts = data.get('alerts', [])
        recent_critical = [a for a in alerts if a.get('severity') == 'critical']
        if len(recent_critical) > 2:
            recommendations.append("Address critical system alerts immediately")

        if not recommendations:
            recommendations.append("System performance is optimal - continue monitoring")

        return recommendations
