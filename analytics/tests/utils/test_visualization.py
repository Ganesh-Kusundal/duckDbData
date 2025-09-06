#!/usr/bin/env python3
"""
Tests for Visualization Utilities
=================================

Comprehensive tests for the visualization component.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from analytics.utils.visualization import AnalyticsVisualizer


class TestAnalyticsVisualizer:
    """Test suite for AnalyticsVisualizer class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.visualizer = AnalyticsVisualizer()

    def test_initialization(self):
        """Test AnalyticsVisualizer initialization."""
        visualizer = AnalyticsVisualizer()
        assert visualizer is not None
        assert hasattr(visualizer, 'create_breakout_heatmap')

    def test_create_breakout_heatmap(self):
        """Test breakout heatmap creation."""
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5),
            'pattern_type': ['volume_spike', 'time_window', 'volume_spike', 'breakout', 'time_window'],
            'confidence': [0.8, 0.7, 0.9, 0.6, 0.75],
            'symbol': ['AAPL', 'GOOGL', 'AAPL', 'MSFT', 'GOOGL']
        })

        result = self.visualizer.create_breakout_heatmap(data)

        assert result is not None
        assert hasattr(result, 'data')  # Plotly figure

    @patch('plotly.graph_objects.Figure')
    def test_create_heatmap(self, mock_figure):
        """Test heatmap creation."""
        mock_fig = MagicMock()
        mock_figure.return_value = mock_fig

        data = pd.DataFrame({
            '09:30': [1.2, 1.5, 0.8],
            '10:00': [1.8, 2.1, 1.3],
            '10:30': [1.5, 1.9, 1.1]
        })

        result = self.visualizer.create_breakout_heatmap(data)

        assert result is not None
        mock_figure.assert_called()

    @patch('plotly.graph_objects.Figure')
    def test_create_scatter_plot(self, mock_figure):
        """Test scatter plot creation."""
        mock_fig = MagicMock()
        mock_figure.return_value = mock_fig

        data = pd.DataFrame({
            'volume_ratio': [1.2, 1.5, 2.1, 0.8, 1.9],
            'price_change': [1.5, 2.2, 3.1, 0.9, 2.8],
            'symbol': ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
        })

        result = self.visualizer.create_volume_price_scatter(data)

        assert result is not None
        mock_figure.assert_called()

    def test_create_time_window_analysis(self):
        """Test time window analysis chart creation."""
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01 09:30', periods=6, freq='15min'),
            'pattern_type': ['volume_spike', 'breakout', 'time_window', 'volume_spike', 'breakout', 'time_window'],
            'confidence': [0.8, 0.7, 0.9, 0.6, 0.85, 0.75]
        })

        result = self.visualizer.create_time_window_analysis(data)

        assert result is not None
        assert hasattr(result, 'data')  # Plotly figure

    def test_create_summary_dashboard(self):
        """Test summary dashboard creation."""
        # Create DataFrame with pattern data for dashboard
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10),
            'pattern_type': ['volume_spike'] * 5 + ['time_window'] * 5,
            'confidence': [0.8, 0.7, 0.9, 0.6, 0.85, 0.75, 0.8, 0.65, 0.9, 0.7],
            'symbol': ['AAPL'] * 10
        })

        result = self.visualizer.create_summary_dashboard(data)

        assert result is not None
        assert isinstance(result, dict)


class TestAnalyticsVisualizerEdgeCases:
    """Test edge cases for AnalyticsVisualizer."""

    def setup_method(self):
        """Setup test fixtures."""
        self.visualizer = AnalyticsVisualizer()

    @patch('plotly.graph_objects.Figure')
    def test_empty_dataframe_handling(self, mock_figure):
        """Test handling empty dataframes."""
        mock_fig = MagicMock()
        mock_figure.return_value = mock_fig

        empty_df = pd.DataFrame()

        result = self.visualizer.create_ohlcv_chart(empty_df)

        assert result is not None
        mock_figure.assert_called()

    @patch('plotly.graph_objects.Figure')
    def test_missing_columns_handling(self, mock_figure):
        """Test handling missing required columns."""
        mock_fig = MagicMock()
        mock_figure.return_value = mock_fig

        incomplete_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=3),
            'close': [100, 102, 104]
            # Missing open, high, low, volume
        })

        result = self.visualizer.create_ohlcv_chart(incomplete_data)

        assert result is not None
        mock_figure.assert_called()

    @patch('plotly.graph_objects.Figure')
    def test_create_heatmap_with_nan_values(self, mock_figure):
        """Test heatmap creation with NaN values."""
        mock_fig = MagicMock()
        mock_figure.return_value = mock_fig

        data = pd.DataFrame({
            '09:30': [1.2, np.nan, 0.8],
            '10:00': [1.8, 2.1, np.nan],
            '10:30': [np.nan, 1.9, 1.1]
        })

        result = self.visualizer.create_heatmap(data)

        assert result is not None
        mock_figure.assert_called()

    @patch('plotly.graph_objects.Figure')
    def test_single_data_point_handling(self, mock_figure):
        """Test handling single data point."""
        mock_fig = MagicMock()
        mock_figure.return_value = mock_fig

        single_point_data = pd.DataFrame({
            'timestamp': [pd.Timestamp('2024-01-01')],
            'open': [100],
            'high': [105],
            'low': [95],
            'close': [102],
            'volume': [1000]
        })

        result = self.visualizer.create_ohlcv_chart(single_point_data)

        assert result is not None
        mock_figure.assert_called()


class TestAnalyticsVisualizerIntegration:
    """Integration tests for AnalyticsVisualizer."""

    def setup_method(self):
        """Setup test fixtures."""
        self.visualizer = AnalyticsVisualizer()

    @patch('plotly.graph_objects.Figure')
    def test_complete_visualization_workflow(self, mock_figure):
        """Test complete visualization workflow."""
        mock_fig = MagicMock()
        mock_figure.return_value = mock_fig

        # Create comprehensive test data
        ohlcv_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='H'),
            'open': np.random.uniform(100, 110, 10),
            'high': np.random.uniform(105, 115, 10),
            'low': np.random.uniform(95, 105, 10),
            'close': np.random.uniform(100, 110, 10),
            'volume': np.random.randint(1000, 2000, 10)
        })

        heatmap_data = pd.DataFrame({
            '09:30': np.random.uniform(1, 3, 5),
            '10:00': np.random.uniform(1, 3, 5),
            '10:30': np.random.uniform(1, 3, 5)
        })

        scatter_data = pd.DataFrame({
            'volume_ratio': np.random.uniform(1, 3, 20),
            'price_change': np.random.uniform(0.5, 4, 20),
            'symbol': ['AAPL'] * 10 + ['GOOGL'] * 10
        })

        # Generate all visualizations
        ohlcv_chart = self.visualizer.create_ohlcv_chart(ohlcv_data)
        heatmap = self.visualizer.create_heatmap(heatmap_data)
        scatter = self.visualizer.create_scatter_plot(
            scatter_data, 'volume_ratio', 'price_change'
        )

        assert ohlcv_chart is not None
        assert heatmap is not None
        assert scatter is not None

        # Verify Figure was called for each chart
        assert mock_figure.call_count == 3

    @patch('plotly.graph_objects.Figure')
    def test_pattern_analysis_visualization_suite(self, mock_figure):
        """Test pattern analysis visualization suite."""
        mock_fig = MagicMock()
        mock_figure.return_value = mock_fig

        # Simulate pattern analysis results
        pattern_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-15 09:30', periods=20, freq='15min'),
            'pattern_strength': np.random.uniform(0.5, 1.0, 20),
            'volume_ratio': np.random.uniform(1, 4, 20),
            'price_change': np.random.uniform(0.5, 3.5, 20),
            'symbol': np.random.choice(['AAPL', 'GOOGL', 'MSFT'], 20)
        })

        time_distribution = pd.Series([
            '09:30', '09:45', '10:00', '10:15', '10:30', '10:45'
        ] * 5)

        # Create visualization suite
        time_dist_chart = self.visualizer.create_time_distribution_chart(time_distribution)
        pattern_scatter = self.visualizer.create_scatter_plot(
            pattern_data, 'volume_ratio', 'price_change',
            color_col='symbol', title="Pattern Analysis"
        )

        # Create summary stats
        summary_stats = {
            'total_patterns': len(pattern_data),
            'avg_volume_ratio': pattern_data['volume_ratio'].mean(),
            'avg_price_change': pattern_data['price_change'].mean(),
            'success_rate': 0.75
        }

        summary_dashboard = self.visualizer.create_summary_dashboard(summary_stats)

        assert time_dist_chart is not None
        assert pattern_scatter is not None
        assert summary_dashboard is not None

        # Verify all visualizations were created
        assert mock_figure.call_count == 3


class TestAnalyticsVisualizerStyling:
    """Test visualization styling and customization."""

    def setup_method(self):
        """Setup test fixtures."""
        self.visualizer = AnalyticsVisualizer()

    @patch('plotly.graph_objects.Figure')
    def test_chart_customization(self, mock_figure):
        """Test chart customization options."""
        mock_fig = MagicMock()
        mock_figure.return_value = mock_fig

        data = pd.DataFrame({
            'volume_ratio': [1.2, 1.5, 2.1],
            'price_change': [1.5, 2.2, 3.1]
        })

        # Test with custom styling
        result = self.visualizer.create_scatter_plot(
            data,
            x_col='volume_ratio',
            y_col='price_change',
            title="Custom Styled Chart",
            width=800,
            height=600
        )

        assert result is not None
        mock_figure.assert_called()

    @patch('plotly.graph_objects.Figure')
    def test_color_scheme_customization(self, mock_figure):
        """Test color scheme customization."""
        mock_fig = MagicMock()
        mock_figure.return_value = mock_fig

        data = pd.DataFrame({
            'category': ['A', 'B', 'C'],
            'value': [10, 20, 30]
        })

        # Test with custom colors
        result = self.visualizer.create_heatmap(
            data,
            title="Custom Colors",
            colorscale='Viridis'
        )

        assert result is not None
        mock_figure.assert_called()
