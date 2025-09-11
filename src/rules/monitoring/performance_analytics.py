#!/usr/bin/env python3
"""
Performance Analytics - Advanced Performance Analysis and Reporting

This module provides sophisticated analytics for performance data including
trend analysis, predictive insights, comparative analysis, and automated reporting.
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import statistics
import logging
from pathlib import Path
import sqlite3


@dataclass
class PerformanceTrend:
    """Represents a performance trend analysis."""
    metric_name: str
    trend_direction: str  # improving, deteriorating, stable
    trend_strength: float  # 0.0 to 1.0
    change_percentage: float
    time_period: str
    confidence_level: float


@dataclass
class PerformanceInsight:
    """Represents a performance insight or recommendation."""
    insight_type: str  # optimization, warning, critical, info
    title: str
    description: str
    impact_level: str  # high, medium, low
    affected_components: List[str]
    recommended_actions: List[str]


class PerformanceAnalytics:
    """Advanced performance analytics engine."""

    def __init__(self, db_path: str = "performance.db"):
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)

    def analyze_performance_trends(self, days: int = 30) -> Dict[str, List[PerformanceTrend]]:
        """Analyze performance trends over time."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            with sqlite3.connect(self.db_path) as conn:
                # Analyze system metrics trends
                system_trends = self._analyze_system_trends(conn, cutoff_date)

                # Analyze rule performance trends
                rule_trends = self._analyze_rule_trends(conn, cutoff_date)

            return {
                'system_trends': system_trends,
                'rule_trends': rule_trends,
                'analysis_period': f"{days} days",
                'generated_at': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Failed to analyze performance trends: {e}")
            return {}

    def _analyze_system_trends(self, conn: sqlite3.Connection, cutoff_date: datetime) -> List[PerformanceTrend]:
        """Analyze system metrics trends."""
        trends = []

        try:
            # CPU usage trend
            cpu_data = pd.read_sql_query('''
                SELECT timestamp, cpu_percent
                FROM system_metrics
                WHERE timestamp > ?
                ORDER BY timestamp ASC
            ''', conn, params=(cutoff_date.isoformat(),))

            if not cpu_data.empty and len(cpu_data) > 10:
                cpu_trend = self._calculate_trend(cpu_data['cpu_percent'].values)
                trends.append(PerformanceTrend(
                    metric_name='CPU Usage',
                    trend_direction=cpu_trend['direction'],
                    trend_strength=cpu_trend['strength'],
                    change_percentage=cpu_trend['change_percent'],
                    time_period=f"{len(cpu_data)} data points",
                    confidence_level=cpu_trend['confidence']
                ))

            # Memory usage trend
            memory_data = pd.read_sql_query('''
                SELECT timestamp, memory_percent
                FROM system_metrics
                WHERE timestamp > ?
                ORDER BY timestamp ASC
            ''', conn, params=(cutoff_date.isoformat(),))

            if not memory_data.empty and len(memory_data) > 10:
                memory_trend = self._calculate_trend(memory_data['memory_percent'].values)
                trends.append(PerformanceTrend(
                    metric_name='Memory Usage',
                    trend_direction=memory_trend['direction'],
                    trend_strength=memory_trend['strength'],
                    change_percentage=memory_trend['change_percent'],
                    time_period=f"{len(memory_data)} data points",
                    confidence_level=memory_trend['confidence']
                ))

        except Exception as e:
            self.logger.error(f"Failed to analyze system trends: {e}")

        return trends

    def _analyze_rule_trends(self, conn: sqlite3.Connection, cutoff_date: datetime) -> List[PerformanceTrend]:
        """Analyze rule performance trends."""
        trends = []

        try:
            # Get all rule IDs
            rule_ids = pd.read_sql_query('''
                SELECT DISTINCT rule_id
                FROM rule_metrics
                WHERE timestamp > ?
            ''', conn, params=(cutoff_date.isoformat(),))['rule_id'].tolist()

            for rule_id in rule_ids:
                # Success rate trend
                success_data = pd.read_sql_query('''
                    SELECT timestamp, success
                    FROM rule_metrics
                    WHERE rule_id = ? AND timestamp > ?
                    ORDER BY timestamp ASC
                ''', conn, params=(rule_id, cutoff_date.isoformat(),))

                if not success_data.empty and len(success_data) > 10:
                    # Calculate rolling success rate
                    success_data['success_rate'] = success_data['success'].rolling(window=10).mean()
                    success_rates = success_data['success_rate'].dropna().values

                    if len(success_rates) > 5:
                        success_trend = self._calculate_trend(success_rates)
                        trends.append(PerformanceTrend(
                            metric_name=f'{rule_id} Success Rate',
                            trend_direction=success_trend['direction'],
                            trend_strength=success_trend['strength'],
                            change_percentage=success_trend['change_percent'],
                            time_period=f"{len(success_data)} executions",
                            confidence_level=success_trend['confidence']
                        ))

                # Execution time trend
                time_data = pd.read_sql_query('''
                    SELECT timestamp, execution_time
                    FROM rule_metrics
                    WHERE rule_id = ? AND timestamp > ?
                    ORDER BY timestamp ASC
                ''', conn, params=(rule_id, cutoff_date.isoformat(),))

                if not time_data.empty and len(time_data) > 10:
                    time_trend = self._calculate_trend(time_data['execution_time'].values)
                    trends.append(PerformanceTrend(
                        metric_name=f'{rule_id} Execution Time',
                        trend_direction=time_trend['direction'],
                        trend_strength=time_trend['strength'],
                        change_percentage=time_trend['change_percent'],
                        time_period=f"{len(time_data)} executions",
                        confidence_level=time_trend['confidence']
                    ))

        except Exception as e:
            self.logger.error(f"Failed to analyze rule trends: {e}")

        return trends

    def _calculate_trend(self, values: np.ndarray) -> Dict[str, Any]:
        """Calculate trend direction and strength."""
        try:
            if len(values) < 5:
                return {
                    'direction': 'insufficient_data',
                    'strength': 0.0,
                    'change_percent': 0.0,
                    'confidence': 0.0
                }

            # Split data into two halves for comparison
            midpoint = len(values) // 2
            first_half = values[:midpoint]
            second_half = values[midpoint:]

            first_avg = np.mean(first_half)
            second_avg = np.mean(second_half)

            if first_avg == 0:
                change_percent = 0.0
            else:
                change_percent = ((second_avg - first_avg) / first_avg) * 100

            # Determine direction
            if abs(change_percent) < 5:
                direction = 'stable'
            elif change_percent > 0:
                direction = 'increasing'
            else:
                direction = 'decreasing'

            # Calculate trend strength (0.0 to 1.0)
            strength = min(abs(change_percent) / 50.0, 1.0)  # Max strength at 50% change

            # Calculate confidence based on data consistency
            std_dev = np.std(values)
            mean_val = np.mean(values)
            cv = std_dev / mean_val if mean_val != 0 else 0  # Coefficient of variation
            confidence = max(0.0, 1.0 - cv)  # Higher consistency = higher confidence

            return {
                'direction': direction,
                'strength': strength,
                'change_percent': change_percent,
                'confidence': confidence
            }

        except Exception as e:
            self.logger.error(f"Failed to calculate trend: {e}")
            return {
                'direction': 'error',
                'strength': 0.0,
                'change_percent': 0.0,
                'confidence': 0.0
            }

    def generate_performance_insights(self, days: int = 7) -> List[PerformanceInsight]:
        """Generate actionable performance insights."""
        insights = []

        try:
            # Get recent performance data
            trends_analysis = self.analyze_performance_trends(days)

            # Analyze system trends for insights
            system_trends = trends_analysis.get('system_trends', [])
            for trend in system_trends:
                if trend.trend_direction == 'increasing' and trend.trend_strength > 0.3:
                    if 'CPU' in trend.metric_name:
                        insights.append(PerformanceInsight(
                            insight_type='optimization',
                            title='High CPU Usage Trend Detected',
                            description=f'System CPU usage has increased by {trend.change_percentage:.1f}% over the last {days} days',
                            impact_level='medium',
                            affected_components=['system_performance', 'rule_execution'],
                            recommended_actions=[
                                'Review CPU-intensive rule operations',
                                'Consider optimizing database queries',
                                'Monitor for potential memory leaks',
                                'Consider horizontal scaling if trend continues'
                            ]
                        ))
                    elif 'Memory' in trend.metric_name:
                        insights.append(PerformanceInsight(
                            insight_type='critical',
                            title='Memory Usage Escalating',
                            description=f'System memory usage has increased by {trend.change_percentage:.1f}% over the last {days} days',
                            impact_level='high',
                            affected_components=['system_stability', 'performance'],
                            recommended_actions=[
                                'Implement memory profiling',
                                'Review large data processing operations',
                                'Consider memory optimization techniques',
                                'Monitor for potential memory leaks',
                                'Plan for memory capacity increase'
                            ]
                        ))

            # Analyze rule trends for insights
            rule_trends = trends_analysis.get('rule_trends', [])
            for trend in rule_trends:
                if 'Success Rate' in trend.metric_name and trend.trend_direction == 'decreasing':
                    rule_id = trend.metric_name.replace(' Success Rate', '')
                    insights.append(PerformanceInsight(
                        insight_type='warning',
                        title=f'Declining Success Rate: {rule_id}',
                        description=f'Rule {rule_id} success rate has decreased by {abs(trend.change_percentage):.1f}%',
                        impact_level='medium',
                        affected_components=[f'rule_{rule_id}'],
                        recommended_actions=[
                            'Review rule logic and conditions',
                            'Check market data quality',
                            'Analyze recent trading signals',
                            'Consider adjusting rule parameters',
                            f'Monitor {rule_id} performance closely'
                        ]
                    ))

                elif 'Execution Time' in trend.metric_name and trend.trend_direction == 'increasing':
                    rule_id = trend.metric_name.replace(' Execution Time', '')
                    insights.append(PerformanceInsight(
                        insight_type='optimization',
                        title=f'Slow Execution Trend: {rule_id}',
                        description=f'Rule {rule_id} execution time has increased by {trend.change_percentage:.1f}%',
                        impact_level='low',
                        affected_components=[f'rule_{rule_id}', 'system_performance'],
                        recommended_actions=[
                            'Optimize rule query performance',
                            'Review database indexes',
                            'Consider caching strategies',
                            'Profile rule execution bottlenecks'
                        ]
                    ))

            # Generate general insights if no specific trends found
            if not insights:
                insights.append(PerformanceInsight(
                    insight_type='info',
                    title='System Performance Stable',
                    description='No significant performance trends detected in the analyzed period',
                    impact_level='low',
                    affected_components=['system_overall'],
                    recommended_actions=[
                        'Continue regular performance monitoring',
                        'Maintain current optimization practices',
                        'Keep performance baselines updated'
                    ]
                ))

        except Exception as e:
            self.logger.error(f"Failed to generate performance insights: {e}")
            insights.append(PerformanceInsight(
                insight_type='critical',
                title='Analytics Error',
                description='Failed to generate performance insights due to system error',
                impact_level='high',
                affected_components=['analytics_system'],
                recommended_actions=[
                    'Check system logs for errors',
                    'Verify database connectivity',
                    'Restart analytics service if needed'
                ]
            ))

        return insights

    def generate_comparative_analysis(self, baseline_period: int = 30,
                                    comparison_period: int = 7) -> Dict[str, Any]:
        """Generate comparative performance analysis."""
        try:
            # Get baseline performance
            baseline_trends = self.analyze_performance_trends(baseline_period)

            # Get comparison performance
            comparison_trends = self.analyze_performance_trends(comparison_period)

            analysis = {
                'baseline_period': f'{baseline_period} days',
                'comparison_period': f'{comparison_period} days',
                'generated_at': datetime.now().isoformat(),
                'comparisons': {}
            }

            # Compare system metrics
            baseline_system = {t.metric_name: t for t in baseline_trends.get('system_trends', [])}
            comparison_system = {t.metric_name: t for t in comparison_trends.get('system_trends', [])}

            for metric_name in set(baseline_system.keys()) | set(comparison_system.keys()):
                baseline_trend = baseline_system.get(metric_name)
                comparison_trend = comparison_system.get(metric_name)

                if baseline_trend and comparison_trend:
                    analysis['comparisons'][metric_name] = {
                        'baseline_trend': baseline_trend.trend_direction,
                        'comparison_trend': comparison_trend.trend_direction,
                        'baseline_change': baseline_trend.change_percentage,
                        'comparison_change': comparison_trend.change_percentage,
                        'trend_difference': comparison_trend.change_percentage - baseline_trend.change_percentage,
                        'analysis': self._analyze_trend_comparison(baseline_trend, comparison_trend)
                    }

            return analysis

        except Exception as e:
            self.logger.error(f"Failed to generate comparative analysis: {e}")
            return {}

    def _analyze_trend_comparison(self, baseline: PerformanceTrend,
                                comparison: PerformanceTrend) -> str:
        """Analyze the difference between two trends."""
        if comparison.trend_direction == baseline.trend_direction:
            if comparison.trend_strength > baseline.trend_strength:
                return "Trend is strengthening compared to baseline"
            elif comparison.trend_strength < baseline.trend_strength:
                return "Trend is weakening compared to baseline"
            else:
                return "Trend remains consistent with baseline"
        else:
            return f"Trend direction changed from {baseline.trend_direction} to {comparison.trend_direction}"

    def export_analytics_report(self, output_file: str, days: int = 30) -> bool:
        """Export comprehensive analytics report."""
        try:
            report = {
                'generated_at': datetime.now().isoformat(),
                'analysis_period_days': days,
                'performance_trends': self.analyze_performance_trends(days),
                'insights': [insight.__dict__ for insight in self.generate_performance_insights(days)],
                'comparative_analysis': self.generate_comparative_analysis(),
                'summary_statistics': self._calculate_summary_statistics(days)
            }

            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            self.logger.info(f"Analytics report exported to {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export analytics report: {e}")
            return False

    def _calculate_summary_statistics(self, days: int) -> Dict[str, Any]:
        """Calculate summary statistics for the analysis period."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Overall system statistics
                system_stats = pd.read_sql_query('''
                    SELECT
                        AVG(cpu_percent) as avg_cpu,
                        MAX(cpu_percent) as max_cpu,
                        AVG(memory_percent) as avg_memory,
                        MAX(memory_percent) as max_memory,
                        COUNT(*) as data_points
                    FROM system_metrics
                    WHERE timestamp > ?
                ''', conn, params=((datetime.now() - timedelta(days=days)).isoformat(),))

                # Rule performance statistics
                rule_stats = pd.read_sql_query('''
                    SELECT
                        COUNT(DISTINCT rule_id) as unique_rules,
                        COUNT(*) as total_executions,
                        AVG(execution_time) as avg_execution_time,
                        SUM(CASE WHEN success THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as overall_success_rate
                    FROM rule_metrics
                    WHERE timestamp > ?
                ''', conn, params=((datetime.now() - timedelta(days=days)).isoformat(),))

                return {
                    'system_stats': system_stats.to_dict('records')[0] if not system_stats.empty else {},
                    'rule_stats': rule_stats.to_dict('records')[0] if not rule_stats.empty else {},
                    'analysis_period_days': days
                }

        except Exception as e:
            self.logger.error(f"Failed to calculate summary statistics: {e}")
            return {}
