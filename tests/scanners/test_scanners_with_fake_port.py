from datetime import date, time

from src.application.scanners.strategies.crp_scanner import CRPScanner
from src.application.scanners.strategies.breakout_scanner import BreakoutScanner


class FakeScannerReadPort:
    def get_crp_candidates(self, scan_date, cutoff_time, config, max_results):
        return [
            {
                'symbol': 'FAKE', 'crp_price': 100.0, 'open_price': 99.0,
                'current_high': 101.0, 'current_low': 98.5, 'current_volume': 50000,
                'current_range_pct': 2.5, 'close_score': 0.4, 'range_score': 0.3,
                'volume_score': 0.2, 'momentum_score': 0.1, 'crp_probability_score': 70.0,
                'close_position': 'Near High'
            }
        ]

    def get_breakout_candidates(self, scan_date, cutoff_time, config, max_results):
        return [
            {
                'symbol': 'BRK', 'breakout_price': 50.0, 'open_price': 49.0,
                'current_high': 50.5, 'current_low': 48.8, 'current_volume': 20000,
                'breakout_above_resistance': 0.5, 'breakout_pct': 1.0,
                'volume_ratio': 1.2, 'probability_score': 55.0,
            }
        ]

    def get_end_of_day_prices(self, symbols, scan_date, end_time):
        return {s: {'eod_price': 101.2, 'eod_high': 102.0, 'eod_low': 98.0, 'eod_volume': 120000} for s in symbols}


def test_crp_scanner_with_fake_port():
    port = FakeScannerReadPort()
    scanner = CRPScanner(scanner_read_port=port)
    df = scanner.scan(date.today(), time(9, 50))
    assert hasattr(df, 'empty') and not df.empty
    row = df.iloc[0]
    assert row['symbol'] == 'FAKE'
    assert 'crp_probability_score' in row


def test_breakout_scanner_with_fake_port():
    port = FakeScannerReadPort()
    scanner = BreakoutScanner(scanner_read_port=port)
    df = scanner.scan(date.today(), time(9, 50))
    assert hasattr(df, 'empty') and not df.empty
    row = df.iloc[0]
    assert row['symbol'] == 'BRK'
    assert 'probability_score' in row

