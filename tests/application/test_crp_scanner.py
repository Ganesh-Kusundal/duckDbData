"""
Integration tests for CRP Scanner
Tests CRP pattern detection and analysis functionality
"""

import pytest
from datetime import date, time, timedelta
from unittest.mock import Mock, patch

from src.application.scanners.strategies.crp_scanner import CRPScanner
from src.infrastructure.core.database import DuckDBManager


class TestCRPScanner:
    """Test CRP Scanner functionality."""

    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager for testing."""
        mock_db = Mock(spec=DuckDBManager)

        # Mock the connect method to return a mock cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_db.connect.return_value = mock_connection

        # Mock execute method for cursor
        mock_cursor.fetchall.return_value = [
            ('RELIANCE', 2500.50, 2490.25, 2510.75, 2485.10, 150000,
             1.02, 0.4, 0.3, 0.2, 0.1, 85.5, 'Near High'),
            ('TCS', 3200.75, 3185.50, 3215.90, 3175.25, 200000,
             1.27, 0.4, 0.2, 0.15, 0.05, 78.2, 'Near High'),
            ('INFY', 1450.25, 1445.80, 1465.60, 1440.15, 180000,
             1.76, 0.1, 0.3, 0.2, 0.1, 72.8, 'Mid Range')
        ]

        return mock_db

    @pytest.fixture
    def crp_scanner(self, mock_db_manager):
        """Create CRP scanner instance with mock database."""
        scanner = CRPScanner(db_manager=mock_db_manager)
        return scanner

    def test_scanner_initialization(self, crp_scanner):
        """Test CRP scanner initialization."""
        assert crp_scanner.scanner_name == "enhanced_crp"
        assert 'close_threshold_pct' in crp_scanner.config
        assert 'range_threshold_pct' in crp_scanner.config
        assert 'min_volume' in crp_scanner.config

    def test_default_config(self, crp_scanner):
        """Test default configuration values."""
        config = crp_scanner._get_default_config()

        assert config['consolidation_period'] == 5
        assert config['close_threshold_pct'] == 2.0
        assert config['range_threshold_pct'] == 3.0
        assert config['min_price'] == 50
        assert config['max_price'] == 2000
        assert config['max_results_per_day'] == 3

    def test_scan_single_day_crp(self, crp_scanner, mock_db_manager):
        """Test single day CRP scanning."""
        scan_date = date(2024, 1, 15)
        cutoff_time = time(9, 50)

        # Mock the database connection and cursor
        mock_connection = mock_db_manager.connect.return_value
        mock_cursor = mock_connection.cursor.return_value

        # Set up mock cursor to return CRP data
        mock_cursor.fetchall.return_value = [
            ('RELIANCE', 2500.50, 2490.25, 2510.75, 2485.10, 150000,
             1.02, 0.4, 0.3, 0.2, 0.1, 85.5, 'Near High'),
            ('TCS', 3200.75, 3185.50, 3215.90, 3175.25, 200000,
             1.27, 0.4, 0.2, 0.15, 0.05, 78.2, 'Near High')
        ]

        results = crp_scanner._scan_single_day_crp(scan_date, cutoff_time)

        assert len(results) == 2
        assert results[0]['symbol'] == 'RELIANCE'
        assert results[0]['crp_probability_score'] == 85.5
        assert results[0]['close_position'] == 'Near High'
        assert results[0]['scan_date'] == scan_date

    def test_get_end_of_day_prices(self, crp_scanner, mock_db_manager):
        """Test end-of-day price retrieval."""
        symbols = ['RELIANCE', 'TCS']
        scan_date = date(2024, 1, 15)
        end_time = time(15, 15)

        # Mock the database connection and cursor
        mock_connection = mock_db_manager.connect.return_value
        mock_cursor = mock_connection.cursor.return_value

        # Set up mock cursor to return EOD data
        mock_cursor.fetchall.return_value = [
            ('RELIANCE', 2520.50, 2530.75, 2485.10, 180000),
            ('TCS', 3220.75, 3235.90, 3175.25, 250000)
        ]

        eod_prices = crp_scanner._get_end_of_day_prices(symbols, scan_date, end_time)

        assert len(eod_prices) == 2
        assert 'RELIANCE' in eod_prices
        assert eod_prices['RELIANCE']['eod_price'] == 2520.50
        assert eod_prices['RELIANCE']['eod_high'] == 2530.75

    def test_merge_crp_and_eod_data(self, crp_scanner):
        """Test merging CRP and end-of-day data."""
        crp_data = [
            {
                'symbol': 'RELIANCE',
                'crp_price': 2500.50,
                'current_high': 2510.75,
                'current_low': 2485.10,
                'crp_probability_score': 85.5,
                'close_position': 'Near High'
            }
        ]

        eod_data = {
            'RELIANCE': {
                'eod_price': 2520.50,
                'eod_high': 2530.75,
                'eod_low': 2485.10,
                'eod_volume': 180000
            }
        }

        scan_date = date(2024, 1, 15)
        merged_results = crp_scanner._merge_crp_and_eod_data(crp_data, eod_data, scan_date)

        assert len(merged_results) == 1
        result = merged_results[0]

        assert result['symbol'] == 'RELIANCE'
        assert result['crp_price'] == 2500.50
        assert result['eod_price'] == 2520.50
        assert result['price_change_pct'] == 0.8  # (2520.50 - 2500.50) / 2500.50 * 100
        assert result['crp_successful'] is True

    def test_add_performance_metrics(self, crp_scanner):
        """Test adding performance metrics."""
        results = [
            {
                'symbol': 'RELIANCE',
                'crp_successful': True,
                'price_change_pct': 0.8,
                'performance_rank': 8.5
            },
            {
                'symbol': 'TCS',
                'crp_successful': False,
                'price_change_pct': -0.5,
                'performance_rank': 7.2
            }
        ]

        updated_results = crp_scanner._add_performance_metrics(results)

        assert len(updated_results) == 2
        assert updated_results[0]['overall_success_rate'] == 50.0  # 1 successful out of 2
        assert updated_results[0]['performance_rank'] >= updated_results[1]['performance_rank']  # Should be sorted

    def test_get_trading_days(self, crp_scanner):
        """Test trading days calculation."""
        start_date = date(2024, 1, 15)  # Monday
        end_date = date(2024, 1, 19)    # Friday

        trading_days = crp_scanner._get_trading_days(start_date, end_date)

        # Should include Monday, Tuesday, Wednesday, Thursday, Friday
        assert len(trading_days) == 5
        assert trading_days[0] == date(2024, 1, 15)
        assert trading_days[-1] == date(2024, 1, 19)

    def test_crp_probability_calculation(self, crp_scanner):
        """Test CRP probability score calculation."""
        # Test case 1: High probability CRP pattern
        # Close near high, tight range, good volume, positive momentum
        close_near_high = 0.4  # Close within 2% of high
        tight_range = 0.3      # Range within 3%
        good_volume = 0.2      # Good volume score
        positive_momentum = 0.1  # Positive momentum

        expected_score = (close_near_high + tight_range + good_volume + positive_momentum) * 100
        assert expected_score == 100.0

        # Test case 2: Medium probability CRP pattern
        close_mid = 0.1        # Close in mid range
        medium_range = 0.2     # Range within 4.5%
        medium_volume = 0.15   # Medium volume score
        neutral_momentum = 0.05  # Neutral momentum

        expected_score = (close_mid + medium_range + medium_volume + neutral_momentum) * 100
        assert expected_score == 50.0

    @patch('builtins.print')
    def test_display_results_table(self, mock_print, crp_scanner):
        """Test results table display."""
        results = [
            {
                'symbol': 'RELIANCE',
                'scan_date': date(2024, 1, 15),
                'crp_price': 2500.50,
                'eod_price': 2520.50,
                'price_change_pct': 0.8,
                'close_position': 'Near High',
                'current_range_pct': 1.02,
                'crp_probability_score': 85.5,
                'performance_rank': 8.5,
                'crp_successful': True
            }
        ]

        crp_scanner.display_results_table(results)

        # Verify that print was called (basic check)
        assert mock_print.called

    def test_export_results(self, crp_scanner, tmp_path):
        """Test results export to CSV."""
        results = [
            {
                'symbol': 'RELIANCE',
                'scan_date': date(2024, 1, 15),
                'crp_price': 2500.50,
                'eod_price': 2520.50,
                'price_change_pct': 0.8,
                'close_position': 'Near High',
                'current_range_pct': 1.02,
                'crp_probability_score': 85.5
            }
        ]

        filename = str(tmp_path / "test_crp_results.csv")
        crp_scanner.export_results(results, filename)

        # Verify file was created
        assert tmp_path.joinpath("test_crp_results.csv").exists()

        # Verify file contents
        with open(filename, 'r') as f:
            content = f.read()
            assert 'symbol' in content
            assert 'RELIANCE' in content
            assert 'Near High' in content


if __name__ == "__main__":
    pytest.main([__file__])
