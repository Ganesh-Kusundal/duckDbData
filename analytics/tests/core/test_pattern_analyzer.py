#!/usr/bin/env python3
"""
Tests for Pattern Analyzer
==========================

Comprehensive tests for the pattern analysis component.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from analytics.core.pattern_analyzer import PatternAnalyzer


class TestPatternAnalyzer:
    """Test suite for PatternAnalyzer class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_connector = MagicMock()
        # Mock the required methods
        mock_df = pd.DataFrame({
            'symbol': ['HDFCBANK'],
            'spike_time': [pd.Timestamp('2024-01-15 10:00:00')],
            'volume_multiplier': [2.0],
            'price_move_pct': [3.0],
            'confidence_score': [0.85]
        })
        self.mock_connector.get_volume_spike_patterns.return_value = mock_df
        self.mock_connector.execute_analytics_query.return_value = mock_df
        self.analyzer = PatternAnalyzer(self.mock_connector)

    def test_initialization(self):
        """Test PatternAnalyzer initialization."""
        assert self.analyzer is not None
        assert self.analyzer.db is not None
        assert hasattr(self.analyzer, 'discovered_patterns')

    def test_discover_volume_spike_patterns(self):
        """Test volume spike pattern discovery."""
        # Mock the database query result using NIFTY-500 stocks
        mock_df = pd.DataFrame({
            'symbol': ['HDFCBANK', 'RELIANCE'],
            'spike_time': [pd.Timestamp('2024-01-15 10:00:00'), pd.Timestamp('2024-01-15 11:00:00')],
            'volume_multiplier': [2.0, 1.8],
            'price_move_pct': [3.0, 2.5],
            'entry_price': [152.50, 2850.00],
            'max_high_next_60min': [157.25, 2921.25]
        })
        self.mock_connector.get_volume_spike_patterns.return_value = mock_df

        result = self.analyzer.discover_volume_spike_patterns(
            min_volume_multiplier=1.5,
            time_window_minutes=60
        )

        assert result is not None
        assert len(result) == 2
        assert result[0].symbol == 'HDFCBANK'
        assert result[0].pattern_type == 'volume_spike'
        self.mock_connector.get_volume_spike_patterns.assert_called_once()

    def test_discover_time_window_patterns(self):
        """Test time window pattern discovery."""
        mock_df = pd.DataFrame({
            'time_window': ['09:30', '10:00'],
            'pattern_count': [10, 8],
            'avg_return': [75.5, 82.3]
        })
        self.mock_connector.execute_analytics_query.return_value = mock_df

        result = self.analyzer.discover_time_window_patterns(
            start_time='09:30',
            end_time='11:00'
        )

        assert result is not None

    def test_get_pattern_summary_table(self):
        """Test pattern summary table generation."""
        from analytics.core.pattern_analyzer import BreakoutPattern
        from datetime import datetime

        # Create mock patterns
        patterns = [
            BreakoutPattern(
                pattern_type="volume_spike",
                symbol="HDFCBANK",
                trigger_time=datetime.now(),
                volume_multiplier=2.0,
                price_move_pct=3.0,
                confidence_score=0.85,
                technical_indicators={}
            ),
            BreakoutPattern(
                pattern_type="time_window",
                symbol="GOOGL",
                trigger_time=datetime.now(),
                volume_multiplier=1.5,
                price_move_pct=2.0,
                confidence_score=0.78,
                technical_indicators={}
            )
        ]

        result = self.analyzer.get_pattern_summary_table(patterns)

        assert result is not None
        assert len(result) == 2

    def test_analyze_pattern_success_rates(self):
        """Test pattern success rate analysis."""
        from analytics.core.pattern_analyzer import BreakoutPattern
        from datetime import datetime

        # Create mock patterns
        patterns = [
            BreakoutPattern(
                pattern_type="volume_spike",
                symbol="HDFCBANK",
                trigger_time=datetime.now(),
                volume_multiplier=2.0,
                price_move_pct=3.0,
                confidence_score=0.85,
                technical_indicators={}
            )
        ]

        result = self.analyzer.analyze_pattern_success_rates(patterns)

        assert result is not None
        assert hasattr(result, 'total_occurrences')

    def test_analyze_pattern_success_rates_detailed(self):
        """Test detailed pattern success rate analysis."""
        from analytics.core.pattern_analyzer import BreakoutPattern
        from datetime import datetime

        # Create multiple mock patterns
        patterns = [
            BreakoutPattern(
                pattern_type="volume_spike",
                symbol="HDFCBANK",
                trigger_time=datetime.now(),
                volume_multiplier=2.0,
                price_move_pct=3.0,
                confidence_score=0.85,
                technical_indicators={}
            ),
            BreakoutPattern(
                pattern_type="time_window",
                symbol="GOOGL",
                trigger_time=datetime.now(),
                volume_multiplier=1.5,
                price_move_pct=2.0,
                confidence_score=0.78,
                technical_indicators={}
            )
        ]

        result = self.analyzer.analyze_pattern_success_rates(patterns)

        assert result is not None
        assert hasattr(result, 'total_occurrences')
        assert result.total_occurrences == 2


class TestPatternAnalyzerEdgeCases:
    """Test edge cases for PatternAnalyzer."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_connector = MagicMock()
        # Mock the required methods
        mock_df = pd.DataFrame({
            'symbol': ['HDFCBANK'],
            'spike_time': [pd.Timestamp('2024-01-15 10:00:00')],
            'volume_multiplier': [2.0],
            'price_move_pct': [3.0],
            'confidence_score': [0.85]
        })
        self.mock_connector.get_volume_spike_patterns.return_value = mock_df
        self.mock_connector.execute_analytics_query.return_value = mock_df
        self.analyzer = PatternAnalyzer(self.mock_connector)

    def test_empty_results_handling(self):
        """Test handling empty query results."""
        # Override the setup mock with empty DataFrame
        self.mock_connector.get_volume_spike_patterns.return_value = pd.DataFrame()

        result = self.analyzer.discover_volume_spike_patterns()

        assert result == []

    def test_database_connection_error(self):
        """Test handling database connection errors."""
        self.mock_connector.execute_analytics_query.side_effect = Exception("DB Error")

        # The method should handle the exception gracefully
        result = self.analyzer.discover_volume_spike_patterns()
        assert result == []  # Should return empty list on error

    def test_invalid_parameters(self):
        """Test handling invalid parameters."""
        # Mock successful response
        mock_df = pd.DataFrame({
            'symbol': ['HDFCBANK'],
            'timestamp': ['2024-01-15 10:00:00'],
            'volume': [1000000],
            'close': [152.50]
        })
        self.mock_connector.execute_analytics_query.return_value = mock_df

        # Test with invalid volume multiplier
        result = self.analyzer.discover_volume_spike_patterns(min_volume_multiplier=0)

        # Should still work
        assert result is not None
        self.mock_connector.execute_analytics_query.assert_called()


class TestPatternAnalyzerIntegration:
    """Integration tests for PatternAnalyzer."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_connector = MagicMock()
        # Mock the required methods
        mock_df = pd.DataFrame({
            'symbol': ['HDFCBANK'],
            'spike_time': [pd.Timestamp('2024-01-15 10:00:00')],
            'volume_multiplier': [2.0],
            'price_move_pct': [3.0],
            'confidence_score': [0.85]
        })
        self.mock_connector.get_volume_spike_patterns.return_value = mock_df
        self.mock_connector.execute_analytics_query.return_value = mock_df
        self.analyzer = PatternAnalyzer(self.mock_connector)

    def test_full_analysis_workflow(self):
        """Test complete analysis workflow."""
        from analytics.core.pattern_analyzer import BreakoutPattern
        from datetime import datetime

        # Mock database response for volume spike discovery
        mock_volume_df = pd.DataFrame({
            'symbol': ['HDFCBANK'],
            'timestamp': ['2024-01-15 10:00:00'],
            'volume': [1000000],
            'close': [152.50]
        })
        self.mock_connector.execute_analytics_query.return_value = mock_volume_df

        # Run volume spike discovery
        volume_patterns = self.analyzer.discover_volume_spike_patterns()

        # Create patterns for success rate analysis
        patterns = [
            BreakoutPattern(
                pattern_type="volume_spike",
                symbol="HDFCBANK",
                trigger_time=datetime.now(),
                volume_multiplier=2.0,
                price_move_pct=3.0,
                confidence_score=0.85,
                technical_indicators={}
            )
        ]

        # Run success rate analysis
        success_stats = self.analyzer.analyze_pattern_success_rates(patterns)

        assert volume_patterns is not None
        assert success_stats is not None
        assert self.mock_connector.execute_analytics_query.call_count >= 1
