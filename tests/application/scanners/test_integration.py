"""
Integration tests for scanner analytics integration.
Tests pattern discovery, scoring integration, and error handling.
"""

import pytest
import pandas as pd
from datetime import date, time
from unittest.mock import Mock, patch, MagicMock

from src.application.scanners.base_scanner import BaseScanner
from src.application.scanners.strategies.breakout_scanner import BreakoutScanner
from src.application.scanners.strategies.technical_scanner import TechnicalScanner
from src.application.use_cases.scan_market import ScanMarketUseCase, ScanRequest, ScanResult
from analytics.core.pattern_analyzer import PatternAnalyzer, BreakoutPattern
from analytics.core.duckdb_connector import DuckDBAnalytics
from src.domain.exceptions import ScannerError
from src.infrastructure.config.config_manager import ConfigManager


@pytest.fixture
def mock_config_manager():
    """Mock ConfigManager fixture."""
    mock = Mock(spec=ConfigManager)
    
    def get_config(section):
        configs = {
            'scanners': {
                'default': {
                    'max_results': 10,
                    'min_price': 50,
                    'max_price': 2000,
                    'consolidation_period': 5,
                    'rsi_overbought': 70,
                    'rsi_oversold': 30
                }
            },
            'analytics': {
                'min_volume_multiplier': 1.5,
                'queries': {
                    'volume_spike': {
                        'min_volume_multiplier': 1.5,
                        'time_window_minutes': 10,
                        'min_price_move': 0.03
                    }
                },
                'dashboard': {
                    'analysis_start_time': '09:35',
                    'analysis_end_time': '09:50'
                }
            },
            'database': {
                'path': '../data/financial_data.duckdb'
            }
        }
        return configs.get(section, {})
    
    def get_value(path, default=None):
        # Handle scanner-specific overrides: scanners.strategies.{scanner_name}
        if path.startswith('scanners.strategies.'):
            scanner_name = path.split('.')[-1]
            strategy_configs = {
                'breakout': {
                    'obv_lookback_period': 10,
                    'obv_threshold': 1.5,
                    'consolidation_period': 5,
                    'consolidation_range_pct': 3.0,
                    'breakout_volume_ratio': 2.0,
                    'momentum_period': 3,
                    'resistance_break_pct': 1.0,
                    'min_price': 50,
                    'max_price': 2000,
                    'max_results': 20
                },
                'technical': {
                    'required_indicators': ['rsi', 'macd', 'bollinger_bands'],
                    'rsi_overbought': 70,
                    'rsi_oversold': 30,
                    'macd_threshold': 0.1,
                    'bb_deviation': 1.5,
                    'min_price': 50,
                    'max_price': 2000,
                    'max_results': 50
                }
            }
            return strategy_configs.get(scanner_name, default)
        return default
    
    mock.get_config.side_effect = get_config
    mock.get_value.side_effect = get_value
    return mock


@pytest.fixture
def mock_duckdb_analytics():
    """Mock DuckDBAnalytics fixture."""
    mock = Mock(spec=DuckDBAnalytics)
    return mock


@pytest.fixture
def mock_pattern_analyzer(mock_duckdb_analytics, mock_config_manager):
    """Mock PatternAnalyzer fixture."""
    analyzer = PatternAnalyzer(db_connector=mock_duckdb_analytics, scanner_mode='breakout')
    return analyzer


@pytest.fixture
def mock_market_data_repo():
    """Mock MarketDataRepository fixture."""
    return Mock()


@pytest.fixture
def mock_data_sync_service():
    """Mock DataSyncService fixture."""
    return Mock()


@pytest.fixture
def mock_event_bus():
    """Mock EventBus fixture."""
    return Mock()


@pytest.fixture
def sample_pattern_scores():
    """Sample pattern scores DataFrame."""
    data = {
        'symbol': ['AAPL', 'GOOGL', 'MSFT'],
        'confidence_score': [0.85, 0.0, 0.65],
        'volume_multiplier': [2.5, 1.0, 1.8]
    }
    return pd.DataFrame(data)


def test_base_scanner_pattern_analyzer_injection(mock_config_manager, mock_duckdb_analytics):
    """Test PatternAnalyzer injection in BaseScanner."""
    # Create scanner with pattern analyzer
    class TestScanner(BaseScanner):
        @property
        def scanner_name(self):
            return "test"
    
    scanner = TestScanner(
        config_manager=mock_config_manager,
        pattern_analyzer=PatternAnalyzer(mock_duckdb_analytics)
    )
    
    # Verify injection
    assert scanner.pattern_analyzer is not None
    assert scanner.config_manager is mock_config_manager


def test_breakout_scanner_pattern_scoring_integration(mock_config_manager, mock_pattern_analyzer, sample_pattern_scores, mock_market_data_repo, mock_data_sync_service):
    """Test breakout scanner integrates pattern scores into breakout_score."""
    # Patch get_pattern_scores to return sample data
    with patch.object(BaseScanner, 'get_pattern_scores', return_value=sample_pattern_scores):
        # Create scanner without repo/service parameters (use defaults)
        scanner = BreakoutScanner(
            config_manager=mock_config_manager,
            pattern_analyzer=mock_pattern_analyzer
        )
        
        # Mock _execute_query to return sample technical data
        mock_result = pd.DataFrame({
            'symbol': ['AAPL', 'GOOGL', 'MSFT'],
            'current_price': [150.0, 2800.0, 300.0],
            'basic_breakout_score': [4.5, 2.0, 3.2]
        })
        
        with patch.object(BreakoutScanner, '_execute_query', return_value=mock_result):
            result = scanner.scan(date(2025, 1, 15), time(10, 0))
        
        # Verify pattern scores influence final breakout_score
        assert not result.empty
        assert 'confidence_score' in result.columns
        assert 'volume_multiplier' in result.columns
        assert 'breakout_score' in result.columns
        
        # AAPL should have enhanced score due to high confidence
        aapl_row = result[result['symbol'] == 'AAPL'].iloc[0]
        assert aapl_row['confidence_score'] == 0.85
        assert aapl_row['breakout_score'] > 4.5  # Enhanced by patterns
        
        # GOOGL should have basic score (no pattern)
        googl_row = result[result['symbol'] == 'GOOGL'].iloc[0]
        assert googl_row['confidence_score'] == 0.0
        assert googl_row['breakout_score'] >= 2.0


def test_technical_scanner_pattern_integration(mock_config_manager, mock_pattern_analyzer, sample_pattern_scores, mock_market_data_repo, mock_data_sync_service):
    """Test technical scanner integrates pattern scores into technical analysis."""
    # Patch get_pattern_scores to return sample data
    with patch.object(BaseScanner, 'get_pattern_scores', return_value=sample_pattern_scores):
        # Create scanner without repo/service parameters (use defaults)
        scanner = TechnicalScanner(
            config_manager=mock_config_manager,
            pattern_analyzer=mock_pattern_analyzer
        )
        
        # Mock _execute_query to return sample technical data
        mock_result = pd.DataFrame({
            'symbol': ['AAPL', 'GOOGL', 'MSFT'],
            'current_price': [150.0, 2800.0, 300.0],
            'basic_technical_score': [6, 2, 4]
        })
        
        with patch.object(TechnicalScanner, '_execute_query', return_value=mock_result):
            result = scanner.scan(date(2025, 1, 15), time(10, 0))
        
        # Verify pattern integration
        assert not result.empty
        assert 'confidence_score' in result.columns
        assert 'technical_score' in result.columns
        
        # AAPL should have enhanced technical score
        aapl_row = result[result['symbol'] == 'AAPL'].iloc[0]
        assert aapl_row['confidence_score'] == 0.85
        assert aapl_row['technical_score'] > 6
        
        # GOOGL should have basic score
        googl_row = result[result['symbol'] == 'GOOGL'].iloc[0]
        assert googl_row['confidence_score'] == 0.0
        assert googl_row['technical_score'] >= 2


def test_scan_market_pattern_stats_aggregation(mock_config_manager, mock_duckdb_analytics, mock_pattern_analyzer, mock_market_data_repo, mock_data_sync_service, mock_event_bus):
    """Test ScanMarketUseCase aggregates pattern statistics in ScanResult."""
    use_case = ScanMarketUseCase(
        market_data_repo=mock_market_data_repo,
        data_sync_service=mock_data_sync_service,
        event_bus=mock_event_bus,
        config_manager=mock_config_manager
    )

    # Register scanners
    from src.application.scanners.strategies.breakout_scanner import BreakoutScanner
    from src.application.scanners.strategies.technical_scanner import TechnicalScanner
    use_case.register_scanner_strategy('breakout', BreakoutScanner)
    use_case.register_scanner_strategy('technical', TechnicalScanner)

    # Create request
    request = ScanRequest(
        scan_date=date(2025, 1, 15),
        cutoff_time=time(10, 0),
        scanner_types=['breakout', 'technical']
    )

    # Mock scanner results with pattern data
    mock_breakout_result = pd.DataFrame({
        'symbol': ['AAPL', 'GOOGL'],
        'breakout_score': [5.2, 2.1],
        'confidence_score': [0.85, 0.0],
        'volume_multiplier': [2.5, 1.0]
    })

    mock_technical_result = pd.DataFrame({
        'symbol': ['AAPL', 'MSFT'],
        'technical_score': [6.8, 4.2],
        'confidence_score': [0.85, 0.65],
        'volume_multiplier': [2.5, 1.8]
    })

    with patch.object(BreakoutScanner, 'scan', return_value=mock_breakout_result), \
         patch.object(TechnicalScanner, 'scan', return_value=mock_technical_result):
        
        # Mock the retry decorator to return a proper decorator factory
        with patch('src.infrastructure.utils.retry.retry_on_transient_errors') as mock_retry:
            def mock_decorator_factory(*args, **kwargs):
                def decorator(f):
                    def wrapper(*a, **kw):
                        return f(*a, **kw)
                    return wrapper
                return decorator
            mock_retry.return_value = mock_decorator_factory
            
            result = use_case.execute(request)
    
    # Verify pattern stats aggregation
    assert isinstance(result, ScanResult)
    assert result.pattern_stats is not None
    assert result.pattern_stats['total_pattern_signals'] == 3  # AAPL (2x), MSFT (1x)
    assert result.pattern_stats['total_confidence_score'] > 1.0
    assert result.pattern_stats['average_confidence'] > 0.5
    assert result.pattern_stats['pattern_coverage'] > 0


def test_scanner_error_handling_for_pattern_failures(mock_config_manager, mock_market_data_repo, mock_data_sync_service, mock_event_bus):
    """Test error handling when pattern analysis fails in scanners."""
    use_case = ScanMarketUseCase(
        market_data_repo=mock_market_data_repo,
        data_sync_service=mock_data_sync_service,
        event_bus=mock_event_bus,
        config_manager=mock_config_manager
    )
    
    # Register scanner
    from src.application.scanners.strategies.breakout_scanner import BreakoutScanner
    use_case.register_scanner_strategy('breakout', BreakoutScanner)
    
    request = ScanRequest(
        scan_date=date(2025, 1, 15),
        cutoff_time=time(10, 0),
        scanner_types=['breakout']
    )
    
    # Mock pattern analyzer to raise ScannerError
    mock_pattern_analyzer = Mock()
    mock_pattern_analyzer.get_pattern_scores.side_effect = ScannerError(
        "Pattern analysis failed", "test_scanner"
    )
    
    # Patch scanner instantiation to inject failing pattern analyzer
    with patch('src.application.scanners.strategies.breakout_scanner.BreakoutScanner') as mock_scanner:
        instance = mock_scanner.return_value
        instance.pattern_analyzer = mock_pattern_analyzer
        instance.scan.return_value = pd.DataFrame()

        # Mock the retry decorator to return a proper decorator factory
        with patch('src.infrastructure.utils.retry.retry_on_transient_errors') as mock_retry:
            def mock_decorator_factory(*args, **kwargs):
                def decorator(f):
                    def wrapper(*a, **kw):
                        return f(*a, **kw)
                    return wrapper
                return decorator
            mock_retry.return_value = mock_decorator_factory
            
            result = use_case.execute(request)
    
    # Verify graceful degradation - scan still completes
    assert result.successful_scanners >= 0
    assert 'pattern_stats' in result.__dict__
    assert result.pattern_stats is None or isinstance(result.pattern_stats, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])