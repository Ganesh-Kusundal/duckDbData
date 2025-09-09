from datetime import date, datetime, time
import pandas as pd

from src.application.scanners.strategies.two_phase_runner import TwoPhaseIntradayRunner
from src.application.scanners.strategies.advanced_two_phase_runner import AdvancedTwoPhaseRunner


class FakeMarketReadPort:
    def get_symbols_for_date(self, trading_date):
        return ["SYM1", "SYM2"]

    def get_minute_data(self, symbol, trading_date, start, end):
        # Minimal DataFrame with required columns
        times = pd.date_range(start=start, end=end, freq="1min")[:40]
        df = pd.DataFrame({
            'timestamp': times,
            'open': [100.0]*len(times),
            'high': [101.0]*len(times),
            'low': [99.0]*len(times),
            'close': [100.5]*len(times),
            'volume': [200000]*len(times),
        })
        return df


def test_two_phase_runner_initialization_and_scan_symbol():
    runner = TwoPhaseIntradayRunner()
    runner.initialize_database(FakeMarketReadPort())
    symbols = runner.get_available_symbols()
    assert symbols, "Expected symbols from fake port"
    res = runner.scan_symbol(symbols[0])
    # res may be None based on simple rules; ensure no exceptions
    assert res is None or isinstance(res, dict)


def test_advanced_two_phase_runner_initialization():
    runner = AdvancedTwoPhaseRunner()
    runner.initialize_database(FakeMarketReadPort())
    symbols = runner.get_available_symbols()
    assert symbols, "Expected symbols from fake port"
