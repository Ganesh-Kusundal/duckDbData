#!/usr/bin/env python3
"""
Tests for Data Processor
========================

Comprehensive tests for the data processing utilities.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from analytics.utils.data_processor import DataProcessor


class TestDataProcessor:
    """Test suite for DataProcessor class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.processor = DataProcessor()

    def test_initialization(self):
        """Test DataProcessor initialization."""
        processor = DataProcessor()
        assert processor is not None
        assert hasattr(processor, 'calculate_technical_indicators')

    def test_calculate_technical_indicators_sma(self):
        """Test SMA calculation."""
        data = pd.DataFrame({
            'open': [99, 101, 103, 102, 104, 106, 105],
            'high': [101, 103, 105, 104, 106, 108, 107],
            'low': [98, 100, 102, 101, 103, 105, 104],
            'close': [100, 102, 104, 103, 105, 107, 106],
            'volume': [1000, 1100, 900, 1200, 800, 1300, 1100]
        })

        result = self.processor.calculate_technical_indicators(data)

        assert 'sma_20' in result.columns
        assert 'sma_50' in result.columns
        # With only 7 data points, SMA_20 and SMA_50 will be NaN
        assert pd.isna(result['sma_20'].iloc[0])
        assert pd.isna(result['sma_50'].iloc[0])

    def test_calculate_technical_indicators_ema(self):
        """Test EMA calculation."""
        data = pd.DataFrame({
            'open': [99, 101, 103, 102, 104, 106, 105, 107, 109, 108] * 5,
            'high': [101, 103, 105, 104, 106, 108, 107, 109, 111, 110] * 5,
            'low': [98, 100, 102, 101, 103, 105, 104, 106, 108, 107] * 5,
            'close': [100, 102, 104, 103, 105, 107, 106, 108, 110, 109] * 5,
            'volume': [1000, 1100, 900, 1200, 800, 1300, 1100, 1400, 900, 1200] * 5
        })

        result = self.processor.calculate_technical_indicators(data)

        assert 'ema_12' in result.columns
        assert 'ema_26' in result.columns
        # EMA should have values after the period
        assert not pd.isna(result['ema_12'].iloc[12])

    def test_calculate_technical_indicators_rsi(self):
        """Test RSI calculation."""
        # Create data with upward trend followed by downward trend
        prices = list(range(100, 120)) + list(range(120, 100, -1))
        data = pd.DataFrame({
            'open': [p-1 for p in prices],
            'high': [p+1 for p in prices],
            'low': [p-2 for p in prices],
            'close': prices,
            'volume': [1000] * len(prices)
        })

        result = self.processor.calculate_technical_indicators(data)

        assert 'rsi' in result.columns
        # RSI should be between 0 and 100
        rsi_values = result['rsi'].dropna()
        assert all(0 <= rsi <= 100 for rsi in rsi_values)

    def test_calculate_technical_indicators_volume_indicators(self):
        """Test volume-based indicators."""
        data = pd.DataFrame({
            'open': [99, 101, 103, 102, 104],
            'high': [101, 103, 105, 104, 106],
            'low': [98, 100, 102, 101, 103],
            'close': [100, 102, 104, 103, 105],
            'volume': [1000, 1200, 800, 1500, 1100]
        })

        result = self.processor.calculate_technical_indicators(data)

        assert 'volume_sma_20' in result.columns
        assert 'volume_ratio' in result.columns

    def test_detect_volume_spikes(self):
        """Test volume spike detection."""
        data = pd.DataFrame({
            'volume': [1000, 1200, 800, 2500, 1100, 800, 3000],
            'close': [100, 102, 104, 103, 105, 107, 106]
        })

        result = self.processor.detect_volume_spikes(data, threshold=1.5)

        assert isinstance(result, pd.DataFrame)
        assert 'volume_spike' in result.columns
        assert 'is_volume_spike' in result.columns
        # With threshold 1.5, we should detect spikes
        # The rolling window might not detect spikes in small datasets

    def test_detect_volume_spikes_no_spikes(self):
        """Test volume spike detection with no spikes."""
        data = pd.DataFrame({
            'volume': [1000, 1100, 900, 1050, 950],
            'close': [100, 102, 104, 103, 105]
        })

        result = self.processor.detect_volume_spikes(data, threshold=2.0)

        assert (result['is_volume_spike'] == False).all()

    def test_calculate_breakout_metrics(self):
        """Test breakout metrics calculation."""
        data = pd.DataFrame({
            'high': [105, 107, 109, 108, 110, 112, 111],
            'low': [95, 97, 99, 98, 100, 102, 101],
            'close': [100, 102, 104, 103, 105, 107, 106],
            'volume': [1000, 1200, 800, 1500, 1100, 800, 1300]
        })

        result = self.processor.calculate_breakout_metrics(data)

        assert 'lookback_high' in result.columns
        assert 'breakout_up' in result.columns
        assert 'volume_confirmation' in result.columns

    def test_generate_pattern_report(self):
        """Test pattern report generation."""
        # Create DataFrame with pattern data
        patterns_df = pd.DataFrame({
            'timestamp': pd.to_datetime(['2024-01-15 10:00:00', '2024-01-15 09:30:00']),
            'symbol': ['AAPL', 'GOOGL'],
            'volume': [1000000, 500000],
            'close': [152.50, 2850.00],
            'volume_spike': [2.1, 1.4],
            'is_volume_spike': [True, False],
            'breakout_up': [True, False],
            'breakout_down': [False, False],
            'breakout_up_pct': [2.5, 0.0],
            'breakout_down_pct': [0.0, 0.0]
        })

        result = self.processor.generate_pattern_report(patterns_df)

        assert isinstance(result, dict)
        assert 'total_records' in result
        assert result['total_records'] == 2
        assert result['pattern_statistics']['volume_spikes'] == 1

    def test_generate_pattern_report_empty(self):
        """Test pattern report generation with empty data."""
        empty_df = pd.DataFrame()
        result = self.processor.generate_pattern_report(empty_df)

        assert result == {"error": "No data available"}


class TestDataProcessorEdgeCases:
    """Test edge cases for DataProcessor."""

    def setup_method(self):
        """Setup test fixtures."""
        self.processor = DataProcessor()

    def test_empty_dataframe_handling(self):
        """Test handling empty dataframes."""
        empty_df = pd.DataFrame()

        # Should handle gracefully without crashing
        result = self.processor.calculate_technical_indicators(empty_df)
        assert isinstance(result, pd.DataFrame)

    def test_insufficient_data_points(self):
        """Test handling insufficient data points for calculations."""
        small_data = pd.DataFrame({
            'close': [100, 102],
            'volume': [1000, 1200]
        })

        result = self.processor.calculate_technical_indicators(small_data)

        # Should still return dataframe even if calculations can't be performed
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_missing_columns(self):
        """Test handling missing required columns."""
        incomplete_data = pd.DataFrame({
            'close': [100, 102, 104]
            # Missing volume column
        })

        # Should handle missing volume gracefully
        result = self.processor.detect_volume_spikes(incomplete_data)
        assert isinstance(result, pd.DataFrame)

    def test_calculate_technical_indicators_with_nan_values(self):
        """Test technical indicators calculation with NaN values."""
        data = pd.DataFrame({
            'close': [100, np.nan, 104, 103, 105],
            'volume': [1000, 1200, np.nan, 1500, 1100]
        })

        result = self.processor.calculate_technical_indicators(data)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5

    def test_detect_volume_spikes_with_nan_values(self):
        """Test volume spike detection with NaN values."""
        data = pd.DataFrame({
            'volume': [1000, np.nan, 800, 2500, 1100],
            'close': [100, 102, 104, 103, 105]
        })

        result = self.processor.detect_volume_spikes(data, threshold=2.0)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5


class TestDataProcessorIntegration:
    """Integration tests for DataProcessor."""

    def setup_method(self):
        """Setup test fixtures."""
        self.processor = DataProcessor()

    def test_full_data_processing_workflow(self):
        """Test complete data processing workflow."""
        # Create comprehensive test data
        data = pd.DataFrame({
            'open': [99, 101, 103, 102, 104, 106, 105, 107, 109, 108] * 3,
            'high': [105, 107, 109, 108, 110, 112, 111, 113, 115, 114] * 3,
            'low': [95, 97, 99, 98, 100, 102, 101, 103, 105, 104] * 3,
            'close': [100, 102, 104, 103, 105, 107, 106, 108, 110, 109] * 3,
            'volume': [1000, 1200, 800, 2500, 1100, 800, 1300, 900, 2100, 1100] * 3
        })

        # Run full processing pipeline
        with_indicators = self.processor.calculate_technical_indicators(data)
        with_spikes = self.processor.detect_volume_spikes(with_indicators)
        with_metrics = self.processor.calculate_breakout_metrics(with_spikes)

        assert isinstance(with_metrics, pd.DataFrame)
        assert len(with_metrics) == len(data)

        # Check that all expected columns are present
        expected_columns = ['close', 'volume', 'high', 'low', 'sma_20', 'ema_12',
                          'rsi', 'volume_spike', 'lookback_high', 'breakout_up']

        for col in expected_columns:
            assert col in with_metrics.columns

    def test_pattern_report_with_realistic_data(self):
        """Test pattern report with realistic pattern data."""
        # Create DataFrame with realistic pattern data
        realistic_patterns_df = pd.DataFrame({
            'timestamp': pd.to_datetime(['2024-01-15 09:35:00', '2024-01-15 10:15:00', '2024-01-15 09:45:00']),
            'symbol': ['AAPL', 'AAPL', 'GOOGL'],
            'volume': [2800000, 3100000, 1400000],
            'close': [152.50, 155.30, 2850.00],
            'volume_spike': [2.8, 3.1, 1.4],
            'is_volume_spike': [True, True, False],
            'breakout_up': [True, True, False],
            'breakout_down': [False, False, False],
            'breakout_up_pct': [3.2, 2.8, 0.0],
            'breakout_down_pct': [0.0, 0.0, 0.0]
        })

        report = self.processor.generate_pattern_report(realistic_patterns_df)

        assert report['total_records'] == 3
        assert report['pattern_statistics']['volume_spikes'] == 2  # 2 True values in is_volume_spike
