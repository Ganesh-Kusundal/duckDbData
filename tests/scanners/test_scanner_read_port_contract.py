"""
Contract tests for ScannerReadPort adapter conformance.

These tests ensure all ScannerReadPort implementations (DuckDB and future adapters)
satisfy the same contract and return consistent data structures.
"""

import pytest
from datetime import date, time
from typing import Dict, List, Any, Protocol
from abc import ABC, abstractmethod

from src.application.ports.scanner_read_port import ScannerReadPort
from src.infrastructure.adapters.scanner_read_adapter import DuckDBScannerReadAdapter


class FakeScannerReadAdapter(ScannerReadPort):
    """Fake implementation for testing contract compliance."""

    def get_crp_candidates(
        self,
        scan_date: date,
        cutoff_time: time,
        config: Dict[str, Any],
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Fake CRP candidates implementation."""
        fake_data = [
            {
                'symbol': 'TEST1',
                'crp_price': 100.0,
                'open_price': 98.0,
                'current_high': 102.0,
                'current_low': 97.0,
                'current_volume': 100000,
                'current_range_pct': 5.0,
                'close_score': 0.4,
                'range_score': 0.3,
                'volume_score': 0.2,
                'momentum_score': 0.1,
                'crp_probability_score': 85.0,
                'close_position': 'Near High'
            },
            {
                'symbol': 'TEST2',
                'crp_price': 200.0,
                'open_price': 195.0,
                'current_high': 205.0,
                'current_low': 194.0,
                'current_volume': 150000,
                'current_range_pct': 5.5,
                'close_score': 0.4,
                'range_score': 0.3,
                'volume_score': 0.15,
                'momentum_score': 0.05,
                'crp_probability_score': 75.0,
                'close_position': 'Near Low'
            }
        ]
        return fake_data[:max_results] if max_results > 0 else []

    def get_end_of_day_prices(
        self,
        symbols: List[str],
        scan_date: date,
        end_time: time,
    ) -> Dict[str, Dict[str, Any]]:
        """Fake end-of-day prices implementation."""
        result = {}
        for symbol in symbols:
            result[symbol] = {
                'eod_price': 105.0 if symbol == 'TEST1' else 210.0,
                'eod_high': 107.0 if symbol == 'TEST1' else 212.0,
                'eod_low': 103.0 if symbol == 'TEST1' else 208.0,
                'eod_volume': 120000 if symbol == 'TEST1' else 180000,
            }
        return result

    def get_breakout_candidates(
        self,
        scan_date: date,
        cutoff_time: time,
        config: Dict[str, Any],
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Fake breakout candidates implementation."""
        fake_data = [
            {
                'symbol': 'TEST1',
                'breakout_price': 100.0,
                'open_price': 98.0,
                'current_high': 103.0,
                'current_low': 97.0,
                'current_volume': 150000,
                'breakout_above_resistance': 3.0,
                'breakout_pct': 3.0,
                'volume_ratio': 2.5,
                'probability_score': 85.0
            }
        ]
        return fake_data[:max_results] if max_results > 0 else []


class TestScannerReadPortContract:
    """Test suite for ScannerReadPort contract compliance."""

    @pytest.fixture(params=[
        pytest.param(DuckDBScannerReadAdapter, id="DuckDBAdapter"),
        pytest.param(FakeScannerReadAdapter, id="FakeAdapter")
    ])
    def adapter_factory(self, request):
        """Factory for creating adapters."""
        adapter_class = request.param
        return adapter_class

    def test_get_crp_candidates_signature(self, adapter_factory):
        """Test get_crp_candidates method signature and basic contract."""
        adapter = adapter_factory()

        # Test method exists and is callable
        assert hasattr(adapter, 'get_crp_candidates')
        assert callable(getattr(adapter, 'get_crp_candidates'))

        # Test with valid parameters
        scan_date = date.today()
        cutoff_time = time(9, 50)
        config = {
            'close_threshold_pct': 2.0,
            'range_threshold_pct': 3.0,
            'min_price': 50,
            'max_price': 2000,
            'min_volume': 50000,
            'max_volume': 5000000
        }
        max_results = 5

        result = adapter.get_crp_candidates(scan_date, cutoff_time, config, max_results)

        # Verify return type
        assert isinstance(result, list)

        # Verify result structure if not empty
        if result:
            for item in result:
                assert isinstance(item, dict)
                # Check required CRP candidate fields
                required_fields = [
                    'symbol', 'crp_price', 'open_price', 'current_high', 'current_low',
                    'current_volume', 'current_range_pct', 'close_score', 'range_score',
                    'volume_score', 'momentum_score', 'crp_probability_score', 'close_position'
                ]
                for field in required_fields:
                    assert field in item, f"Missing required field: {field}"
                    assert isinstance(item[field], (int, float, str)), f"Invalid type for {field}"

    def test_get_end_of_day_prices_signature(self, adapter_factory):
        """Test get_end_of_day_prices method signature and contract."""
        adapter = adapter_factory()

        # Test method exists and is callable
        assert hasattr(adapter, 'get_end_of_day_prices')
        assert callable(getattr(adapter, 'get_end_of_day_prices'))

        # Test with valid parameters
        symbols = ['TEST1', 'TEST2']
        scan_date = date.today()
        end_time = time(15, 15)

        result = adapter.get_end_of_day_prices(symbols, scan_date, end_time)

        # Verify return type
        assert isinstance(result, dict)

        # Verify result structure
        for symbol in symbols:
            if symbol in result:
                eod_data = result[symbol]
                assert isinstance(eod_data, dict)
                # Check required EOD price fields
                required_fields = ['eod_price', 'eod_high', 'eod_low', 'eod_volume']
                for field in required_fields:
                    assert field in eod_data, f"Missing required field: {field}"
                    assert isinstance(eod_data[field], (int, float)), f"Invalid type for {field}"

    def test_get_breakout_candidates_signature(self, adapter_factory):
        """Test get_breakout_candidates method signature and contract."""
        adapter = adapter_factory()

        # Test method exists and is callable
        assert hasattr(adapter, 'get_breakout_candidates')
        assert callable(getattr(adapter, 'get_breakout_candidates'))

        # Test with valid parameters
        scan_date = date.today()
        cutoff_time = time(9, 50)
        config = {
            'min_price': 50,
            'max_price': 2000,
        }
        max_results = 5

        result = adapter.get_breakout_candidates(scan_date, cutoff_time, config, max_results)

        # Verify return type
        assert isinstance(result, list)

        # Verify result structure if not empty
        if result:
            for item in result:
                assert isinstance(item, dict)
                # Check required breakout candidate fields
                required_fields = [
                    'symbol', 'breakout_price', 'open_price', 'current_high', 'current_low',
                    'current_volume', 'breakout_above_resistance', 'breakout_pct',
                    'volume_ratio', 'probability_score'
                ]
                for field in required_fields:
                    assert field in item, f"Missing required field: {field}"
                    assert isinstance(item[field], (int, float, str)), f"Invalid type for {field}"

    def test_edge_cases(self, adapter_factory):
        """Test edge cases and error handling."""
        adapter = adapter_factory()

        # Test empty symbols list
        result = adapter.get_end_of_day_prices([], date.today(), time(15, 15))
        assert isinstance(result, dict)
        assert len(result) == 0

        # Test max_results = 0
        result = adapter.get_crp_candidates(
            date.today(), time(9, 50), {'close_threshold_pct': 2.0, 'range_threshold_pct': 3.0,
                                       'min_price': 50, 'max_price': 2000, 'min_volume': 50000,
                                       'max_volume': 5000000}, 0
        )
        assert isinstance(result, list)
        assert len(result) == 0

    def test_contract_consistency(self, adapter_factory):
        """Test that contract is consistent across different adapter implementations."""
        adapter1 = adapter_factory()
        adapter2 = adapter_factory()

        # Both adapters should have the same methods
        methods = ['get_crp_candidates', 'get_end_of_day_prices', 'get_breakout_candidates']
        for method in methods:
            assert hasattr(adapter1, method)
            assert hasattr(adapter2, method)
            assert callable(getattr(adapter1, method))
            assert callable(getattr(adapter2, method))

    def test_config_validation(self, adapter_factory):
        """Test that adapters handle config parameters appropriately."""
        adapter = adapter_factory()

        # Skip config validation for DuckDBAdapter as it has specific requirements
        if adapter_factory.__name__ == 'DuckDBScannerReadAdapter':
            pytest.skip("DuckDBAdapter requires specific config parameters, skipping minimal config test")

        # Test with minimal config (only for FakeAdapter)
        minimal_config = {'close_threshold_pct': 2.0}
        result = adapter.get_crp_candidates(date.today(), time(9, 50), minimal_config, 5)
        assert isinstance(result, list)

        # Test with extended config
        extended_config = {
            'close_threshold_pct': 2.0,
            'range_threshold_pct': 3.0,
            'min_price': 50,
            'max_price': 2000,
            'min_volume': 50000,
            'max_volume': 5000000,
            'custom_param': 'value'
        }
        result = adapter.get_crp_candidates(date.today(), time(9, 50), extended_config, 5)
        assert isinstance(result, list)


def test_adapter_interface_compliance():
    """Test that adapters properly implement the ScannerReadPort interface."""
    from typing import get_type_hints

    # Get the protocol methods
    protocol_methods = [method for method in dir(ScannerReadPort) if not method.startswith('_')]

    # Test DuckDB adapter
    duckdb_adapter = DuckDBScannerReadAdapter()
    for method in protocol_methods:
        assert hasattr(duckdb_adapter, method), f"DuckDBAdapter missing method: {method}"
        assert callable(getattr(duckdb_adapter, method)), f"DuckDBAdapter method not callable: {method}"

    # Test fake adapter
    fake_adapter = FakeScannerReadAdapter()
    for method in protocol_methods:
        assert hasattr(fake_adapter, method), f"FakeAdapter missing method: {method}"
        assert callable(getattr(fake_adapter, method)), f"FakeAdapter method not callable: {method}"
