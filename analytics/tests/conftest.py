#!/usr/bin/env python3
"""
Test Configuration and Fixtures
===============================

Common test fixtures and configuration for analytics module tests.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from pathlib import Path


@pytest.fixture
def sample_market_data():
    """Provide sample market data for testing."""
    return pd.DataFrame({
        'timestamp': pd.date_range('2024-01-15 09:30', periods=20, freq='5min'),
        'symbol': ['AAPL'] * 20,
        'open': np.random.uniform(150, 160, 20),
        'high': np.random.uniform(155, 165, 20),
        'low': np.random.uniform(145, 155, 20),
        'close': np.random.uniform(150, 160, 20),
        'volume': np.random.randint(10000, 50000, 20)
    })


@pytest.fixture
def sample_pattern_data():
    """Provide sample pattern analysis data."""
    return [
        {
            'symbol': 'AAPL',
            'pattern_type': 'volume_spike_breakout',
            'timestamp': '2024-01-15 10:00:00',
            'confidence': 0.87,
            'price_change': 3.2,
            'volume_ratio': 2.8,
            'time_window': '09:30-11:00'
        },
        {
            'symbol': 'GOOGL',
            'pattern_type': 'time_window_breakout',
            'timestamp': '2024-01-15 09:45:00',
            'confidence': 0.76,
            'price_change': 1.9,
            'volume_ratio': 1.4,
            'time_window': '09:30-11:00'
        },
        {
            'symbol': 'MSFT',
            'pattern_type': 'momentum_breakout',
            'timestamp': '2024-01-15 10:15:00',
            'confidence': 0.82,
            'price_change': 2.5,
            'volume_ratio': 1.9,
            'time_window': '09:30-11:00'
        }
    ]


@pytest.fixture
def mock_duckdb_connector():
    """Provide mocked DuckDB connector."""
    mock_connector = MagicMock()
    mock_connector.execute_query.return_value = [
        ('AAPL', '2024-01-15 10:00:00', 25000, 155.50),
        ('GOOGL', '2024-01-15 10:30:00', 18000, 2850.00)
    ]
    mock_connector.get_available_symbols.return_value = ['AAPL', 'GOOGL', 'MSFT']
    mock_connector.get_date_range.return_value = ('2020-01-01', '2024-12-31')
    return mock_connector


@pytest.fixture
def mock_pattern_analyzer():
    """Provide mocked pattern analyzer."""
    mock_analyzer = MagicMock()
    mock_analyzer.discover_volume_spike_breakouts.return_value = [
        {'symbol': 'AAPL', 'confidence': 0.85, 'volume_ratio': 2.1}
    ]
    mock_analyzer.discover_time_window_patterns.return_value = [
        {'time_window': '09:30-11:00', 'avg_return': 2.3}
    ]
    mock_analyzer.get_pattern_summary_table.return_value = [
        ('Volume Spike', 'AAPL', 10, 85.5)
    ]
    return mock_analyzer


@pytest.fixture
def mock_rule_engine():
    """Provide mocked rule engine."""
    mock_engine = MagicMock()
    mock_engine.evaluate_pattern.return_value = [
        {'rule_name': 'Volume Rule', 'matched': True, 'actions': ['alert']}
    ]
    mock_engine.get_rule_statistics.return_value = {
        'total_rules': 5,
        'enabled_rules': 4,
        'disabled_rules': 1
    }
    return mock_engine


@pytest.fixture
def mock_data_processor():
    """Provide mocked data processor."""
    mock_processor = MagicMock()
    mock_processor.calculate_technical_indicators.return_value = pd.DataFrame({
        'close': [100, 102, 104],
        'SMA_20': [np.nan, np.nan, 102.0],
        'RSI': [np.nan, np.nan, 65.0]
    })
    mock_processor.detect_volume_spikes.return_value = pd.DataFrame({
        'volume': [1000, 2500, 800],
        'volume_spike': [False, True, False]
    })
    return mock_processor


@pytest.fixture
def mock_visualizer():
    """Provide mocked visualizer."""
    mock_viz = MagicMock()
    mock_chart = MagicMock()
    mock_viz.create_ohlcv_chart.return_value = mock_chart
    mock_viz.create_heatmap.return_value = mock_chart
    mock_viz.create_scatter_plot.return_value = mock_chart
    return mock_viz


@pytest.fixture
def analytics_test_data_dir(tmp_path):
    """Provide temporary directory for analytics test data."""
    test_dir = tmp_path / "analytics_test_data"
    test_dir.mkdir()

    # Create sample parquet files
    sample_data = pd.DataFrame({
        'symbol': ['AAPL'] * 100,
        'timestamp': pd.date_range('2024-01-15', periods=100, freq='1min'),
        'open': np.random.uniform(150, 160, 100),
        'high': np.random.uniform(155, 165, 100),
        'low': np.random.uniform(145, 155, 100),
        'close': np.random.uniform(150, 160, 100),
        'volume': np.random.randint(10000, 50000, 100)
    })

    parquet_file = test_dir / "AAPL.parquet"
    sample_data.to_parquet(parquet_file)

    return test_dir


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return {
        'database_path': ':memory:',
        'symbols': ['AAPL', 'GOOGL', 'MSFT'],
        'volume_threshold': 1.5,
        'time_window': '09:30-11:00',
        'lookback_minutes': 60,
        'min_confidence': 0.7,
        'max_patterns': 100
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment for all tests."""
    # Set any global test configuration here
    pass


@pytest.fixture
def large_test_dataset():
    """Provide large test dataset for performance testing."""
    return pd.DataFrame({
        'symbol': np.random.choice(['AAPL', 'GOOGL', 'MSFT', 'TSLA'], 1000),
        'timestamp': pd.date_range('2024-01-15', periods=1000, freq='1min'),
        'open': np.random.uniform(100, 200, 1000),
        'high': np.random.uniform(105, 210, 1000),
        'low': np.random.uniform(95, 190, 1000),
        'close': np.random.uniform(100, 200, 1000),
        'volume': np.random.randint(10000, 100000, 1000),
        'volume_ratio': np.random.uniform(1, 4, 1000),
        'price_change': np.random.uniform(0.5, 5, 1000)
    })


@pytest.fixture
def mock_streamlit():
    """Provide mocked Streamlit components for dashboard testing."""
    with pytest.mock.patch.dict('sys.modules', {
        'streamlit': MagicMock(),
        'streamlit.runtime': MagicMock(),
        'streamlit.runtime.scriptrunner': MagicMock(),
    }):
        import streamlit as st
        # Mock common streamlit functions
        st.set_page_config = MagicMock()
        st.title = MagicMock()
        st.header = MagicMock()
        st.subheader = MagicMock()
        st.write = MagicMock()
        st.markdown = MagicMock()
        st.sidebar = MagicMock()
        st.tabs = MagicMock(return_value=[MagicMock() for _ in range(5)])
        st.columns = MagicMock(return_value=[MagicMock() for _ in range(3)])
        st.selectbox = MagicMock(return_value='AAPL')
        st.slider = MagicMock(return_value=(1.5, 3.0))
        st.number_input = MagicMock(return_value=10)
        st.button = MagicMock(return_value=False)
        st.checkbox = MagicMock(return_value=True)
        st.radio = MagicMock(return_value='option1')
        st.text_input = MagicMock(return_value='test')
        st.text_area = MagicMock(return_value='test area')
        st.file_uploader = MagicMock(return_value=None)
        st.dataframe = MagicMock()
        st.data_editor = MagicMock()
        st.table = MagicMock()
        st.metric = MagicMock()
        st.plotly_chart = MagicMock()
        st.spinner = MagicMock()
        st.progress = MagicMock()
        st.success = MagicMock()
        st.info = MagicMock()
        st.warning = MagicMock()
        st.error = MagicMock()
        st.exception = MagicMock()
        st.cache_data = MagicMock()
        st.cache_resource = MagicMock()
        st.session_state = {}

        yield st


# Test configuration
def pytest_configure(config):
    """Configure pytest for analytics tests."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "dashboard: mark test as dashboard test"
    )


# Test data paths
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_DATA_DIR.mkdir(exist_ok=True)
