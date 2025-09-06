"""
Visualization Utilities
======================

Helper functions for creating charts and plots for analytics.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class AnalyticsVisualizer:
    """Utility class for creating analytics visualizations."""

    @staticmethod
    def create_breakout_heatmap(df: pd.DataFrame,
                              time_column: str = 'timestamp',
                              value_column: str = 'breakout_up_pct') -> go.Figure:
        """Create a heatmap of breakout patterns by time."""
        if df.empty:
            return go.Figure()

        # Prepare data for heatmap
        df = df.copy()
        df['date'] = pd.to_datetime(df[time_column]).dt.date
        df['hour'] = pd.to_datetime(df[time_column]).dt.hour
        df['minute'] = pd.to_datetime(df[time_column]).dt.minute

        # Create pivot table for heatmap
        heatmap_data = df.pivot_table(
            values=value_column,
            index='hour',
            columns='date',
            aggfunc='mean'
        ).fillna(0)

        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=heatmap_data.index,
            colorscale='RdYlGn',
            hoverongaps=False
        ))

        fig.update_layout(
            title="Breakout Pattern Heatmap",
            xaxis_title="Date",
            yaxis_title="Hour of Day",
            height=600
        )

        return fig

    @staticmethod
    def create_volume_price_scatter(df: pd.DataFrame) -> go.Figure:
        """Create scatter plot of volume vs price movement."""
        if df.empty or 'volume_spike' not in df.columns or 'breakout_up_pct' not in df.columns:
            return go.Figure()

        fig = px.scatter(
            df,
            x='volume_spike',
            y='breakout_up_pct',
            color='is_volume_spike',
            title="Volume Multiplier vs Price Movement",
            labels={
                'volume_spike': 'Volume Multiplier',
                'breakout_up_pct': 'Price Movement (%)'
            }
        )

        fig.update_layout(height=600)
        return fig

    @staticmethod
    def create_time_window_analysis(df: pd.DataFrame) -> go.Figure:
        """Create bar chart of pattern success by time window."""
        if df.empty:
            return go.Figure()

        # Group by time windows
        df = df.copy()
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        df['time_window'] = pd.cut(df['hour'],
                                 bins=[9, 10, 11, 12, 13, 14, 15, 16],
                                 labels=['9-10', '10-11', '11-12', '12-13', '13-14', '14-15', '15-16'])

        window_stats = df.groupby('time_window').agg({
            'breakout_up': 'sum',
            'is_volume_spike': 'sum',
            'breakout_up_pct': 'mean'
        }).reset_index()

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Bar chart for pattern count
        fig.add_trace(
            go.Bar(
                x=window_stats['time_window'],
                y=window_stats['breakout_up'],
                name="Breakout Patterns",
                marker_color='lightblue'
            ),
            secondary_y=False
        )

        # Line chart for success rate
        success_rate = window_stats['breakout_up'] / window_stats['is_volume_spike'].replace(0, 1)
        fig.add_trace(
            go.Scatter(
                x=window_stats['time_window'],
                y=success_rate,
                name="Success Rate",
                mode='lines+markers',
                marker_color='red'
            ),
            secondary_y=True
        )

        fig.update_layout(
            title="Pattern Analysis by Time Window",
            xaxis_title="Time Window",
            height=600
        )

        fig.update_yaxes(title_text="Pattern Count", secondary_y=False)
        fig.update_yaxes(title_text="Success Rate", secondary_y=True)

        return fig

    @staticmethod
    def create_pattern_distribution_chart(df: pd.DataFrame) -> go.Figure:
        """Create pie chart of pattern type distribution."""
        if df.empty:
            return go.Figure()

        # Count pattern types
        pattern_counts = df['pattern_type'].value_counts() if 'pattern_type' in df.columns else pd.Series()

        if pattern_counts.empty:
            # Fallback to breakout types
            breakout_up = (df['breakout_up'] == True).sum()
            breakout_down = (df['breakout_down'] == True).sum()
            pattern_counts = pd.Series({
                'Breakout Up': breakout_up,
                'Breakout Down': breakout_down
            })

        fig = px.pie(
            values=pattern_counts.values,
            names=pattern_counts.index,
            title="Pattern Type Distribution"
        )

        fig.update_layout(height=500)
        return fig

    @staticmethod
    def create_performance_metrics_chart(metrics: Dict[str, Any]) -> go.Figure:
        """Create dashboard-style metrics visualization."""
        if not metrics:
            return go.Figure()

        # Create subplots for key metrics
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("Pattern Statistics", "Success Rates", "Volume Analysis", "Time Distribution"),
            specs=[[{"type": "domain"}, {"type": "domain"}],
                   [{"type": "domain"}, {"type": "domain"}]]
        )

        # Pattern Statistics Pie
        pattern_stats = metrics.get('pattern_statistics', {})
        fig.add_trace(
            go.Pie(
                labels=list(pattern_stats.keys()),
                values=list(pattern_stats.values()),
                name="Patterns"
            ),
            row=1, col=1
        )

        # Success Rates (mock data if not available)
        success_data = {
            'Successful Breakouts': pattern_stats.get('breakouts_up', 0),
            'Failed Attempts': pattern_stats.get('volume_spikes', 0) - pattern_stats.get('breakouts_up', 0)
        }
        fig.add_trace(
            go.Pie(
                labels=list(success_data.keys()),
                values=list(success_data.values()),
                name="Success Rate"
            ),
            row=1, col=2
        )

        # Volume Analysis (mock data)
        volume_data = {
            'High Volume': pattern_stats.get('volume_spikes', 0),
            'Normal Volume': max(0, metrics.get('total_records', 0) - pattern_stats.get('volume_spikes', 0))
        }
        fig.add_trace(
            go.Pie(
                labels=list(volume_data.keys()),
                values=list(volume_data.values()),
                name="Volume Analysis"
            ),
            row=2, col=1
        )

        # Time Distribution (mock data)
        time_data = {
            'Morning (9-11)': 60,
            'Afternoon (11-15)': 30,
            'Other': 10
        }
        fig.add_trace(
            go.Pie(
                labels=list(time_data.keys()),
                values=list(time_data.values()),
                name="Time Distribution"
            ),
            row=2, col=2
        )

        fig.update_layout(height=800, title_text="Analytics Dashboard Overview")
        return fig

    @staticmethod
    def create_intraday_pattern_chart(df: pd.DataFrame) -> go.Figure:
        """Create intraday pattern visualization."""
        if df.empty or 'timestamp' not in df.columns:
            return go.Figure()

        df = df.copy()
        df['time'] = pd.to_datetime(df['timestamp']).dt.time
        df['hour_minute'] = df['time'].apply(lambda x: f"{x.hour:02d}:{x.minute:02d}")

        # Group by time and count patterns
        time_patterns = df.groupby('hour_minute').agg({
            'breakout_up': 'sum',
            'volume_spike': 'mean'
        }).reset_index()

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Pattern count bars
        fig.add_trace(
            go.Bar(
                x=time_patterns['hour_minute'],
                y=time_patterns['breakout_up'],
                name="Breakout Patterns",
                marker_color='lightgreen'
            ),
            secondary_y=False
        )

        # Volume spike line
        fig.add_trace(
            go.Scatter(
                x=time_patterns['hour_minute'],
                y=time_patterns['volume_spike'],
                name="Avg Volume Multiplier",
                mode='lines+markers',
                marker_color='red'
            ),
            secondary_y=True
        )

        fig.update_layout(
            title="Intraday Pattern Analysis",
            xaxis_title="Time",
            height=600
        )

        fig.update_yaxes(title_text="Pattern Count", secondary_y=False)
        fig.update_yaxes(title_text="Volume Multiplier", secondary_y=True)

        return fig

    @staticmethod
    def export_chart_to_html(fig: go.Figure, filename: str = "chart.html") -> None:
        """Export chart to HTML file."""
        fig.write_html(filename)
        logger.info(f"Exported chart to {filename}")

    @staticmethod
    def create_summary_dashboard(df: pd.DataFrame) -> Dict[str, go.Figure]:
        """Create a complete dashboard with multiple charts."""
        if df.empty:
            return {}

        charts = {}

        # Main pattern heatmap
        charts['heatmap'] = AnalyticsVisualizer.create_breakout_heatmap(df)

        # Volume-price scatter
        charts['scatter'] = AnalyticsVisualizer.create_volume_price_scatter(df)

        # Time window analysis
        charts['time_windows'] = AnalyticsVisualizer.create_time_window_analysis(df)

        # Pattern distribution
        charts['distribution'] = AnalyticsVisualizer.create_pattern_distribution_chart(df)

        # Intraday analysis
        charts['intraday'] = AnalyticsVisualizer.create_intraday_pattern_chart(df)

        logger.info(f"Created {len(charts)} dashboard charts")
        return charts
