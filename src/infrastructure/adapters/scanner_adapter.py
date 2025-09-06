"""Adapter to integrate existing scanners with the new DDD architecture."""

from typing import List, Dict, Any, Optional
from datetime import date, time
from abc import ABC, abstractmethod
import pandas as pd

from ...domain.entities.market_data import MarketData
from ...domain.entities.scanner import ScannerResult, TradingSignal, SignalType, SignalStrength
from ...domain.repositories.market_data_repo import MarketDataRepository
from ...infrastructure.repositories.duckdb_market_repo import DuckDBMarketDataRepository


class ScannerAdapter(ABC):
    """Abstract adapter for integrating scanners with DDD architecture."""

    def __init__(self, market_data_repo: Optional[MarketDataRepository] = None):
        """Initialize scanner adapter."""
        self.market_data_repo = market_data_repo or DuckDBMarketDataRepository()

    @abstractmethod
    def get_scanner_name(self) -> str:
        """Get scanner name."""
        pass

    @abstractmethod
    def execute_scan(self, scan_date: date, cutoff_time: time = time(9, 50)) -> List[ScannerResult]:
        """Execute scanner logic and return domain entities."""
        pass

    def get_market_data_for_symbols(self,
                                  symbols: List[str],
                                  start_date: date,
                                  end_date: date,
                                  timeframe: str = '1D') -> List[MarketData]:
        """Get market data for symbols using domain repository."""
        all_data = []
        for symbol in symbols:
            data = self.market_data_repo.find_by_symbol_and_date_range(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                timeframe=timeframe
            )
            all_data.extend(data)
        return all_data

    def convert_dataframe_to_scanner_results(self,
                                           df: pd.DataFrame,
                                           scanner_name: str) -> List[ScannerResult]:
        """Convert pandas DataFrame to ScannerResult domain entities."""
        from datetime import datetime
        from decimal import Decimal

        results = []
        for _, row in df.iterrows():
            # Create trading signals from the row data
            signals = []
            if row.get('signal_type'):
                signal_type = SignalType.BUY if 'BUY' in str(row.get('signal_type', '')).upper() else SignalType.SELL
                signal = TradingSignal(
                    symbol=row.get('symbol', ''),
                    signal_type=signal_type,
                    strength=SignalStrength.STRONG,
                    timestamp=datetime.now(),
                    price=Decimal(str(row.get('close', 0))),
                    confidence=float(row.get('signal_strength', 0.5)),
                    scanner_name=scanner_name,
                    metadata={}
                )
                signals.append(signal)

            result = ScannerResult(
                scanner_name=scanner_name,
                symbol=row.get('symbol', ''),
                timestamp=datetime.now(),
                signals=signals,
                metadata={
                    'price_change_pct': row.get('price_change_pct'),
                    'current_volume': row.get('current_volume'),
                    'avg_volume': row.get('avg_volume'),
                    'signal_type': row.get('signal_type'),
                    'trading_bias': row.get('trading_bias'),
                    'momentum_class': row.get('momentum_class'),
                    'technical_setup': row.get('technical_setup'),
                },
                execution_time_ms=0.0
            )
            results.append(result)
        return results


class LegacyScannerAdapter(ScannerAdapter):
    """Adapter for existing scanner implementations."""

    def __init__(self, legacy_scanner, market_data_repo: Optional[MarketDataRepository] = None):
        """Initialize with existing scanner instance."""
        super().__init__(market_data_repo)
        self.legacy_scanner = legacy_scanner

    def get_scanner_name(self) -> str:
        """Get scanner name from legacy scanner."""
        return self.legacy_scanner.scanner_name

    def execute_scan(self, scan_date: date, cutoff_time: time = time(9, 50)) -> List[ScannerResult]:
        """Execute legacy scanner and convert results."""
        # Execute legacy scanner
        df_results = self.legacy_scanner.scan(scan_date, cutoff_time)

        # Convert to domain entities
        return self.convert_dataframe_to_scanner_results(df_results, self.get_scanner_name())


class ScannerService:
    """Service for managing scanner operations."""

    def __init__(self, market_data_repo: Optional[MarketDataRepository] = None):
        """Initialize scanner service."""
        self.market_data_repo = market_data_repo or DuckDBMarketDataRepository()
        self.adapters: Dict[str, ScannerAdapter] = {}

    def register_scanner(self, name: str, adapter: ScannerAdapter):
        """Register a scanner adapter."""
        self.adapters[name] = adapter

    def execute_scanner(self, name: str, scan_date: date, cutoff_time: time = time(9, 50)) -> List[ScannerResult]:
        """Execute a registered scanner."""
        if name not in self.adapters:
            raise ValueError(f"Scanner '{name}' not registered")

        return self.adapters[name].execute_scan(scan_date, cutoff_time)

    def get_available_scanners(self) -> List[str]:
        """Get list of available scanners."""
        return list(self.adapters.keys())

    def execute_all_scanners(self, scan_date: date, cutoff_time: time = time(9, 50)) -> Dict[str, List[ScannerResult]]:
        """Execute all registered scanners."""
        results = {}
        for name, adapter in self.adapters.items():
            try:
                results[name] = adapter.execute_scan(scan_date, cutoff_time)
            except Exception as e:
                print(f"Error executing scanner {name}: {e}")
                results[name] = []
        return results
