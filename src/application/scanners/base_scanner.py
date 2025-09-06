"""
Base scanner class for intraday stock selection using DuckDB.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, date, time
import pandas as pd
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.infrastructure.core.database import DuckDBManager
from src.infrastructure.core.query_api import QueryAPI


class BaseScanner(ABC):
    """Abstract base class for all scanner implementations."""

    def __init__(self, db_manager: DuckDBManager = None, config: Dict[str, Any] = None):
        """
        Initialize scanner with database manager.

        Args:
            db_manager: DuckDB manager instance (will create if None)
            config: Scanner configuration parameters
        """
        self.db_manager = db_manager or DuckDBManager()
        self.query_api = QueryAPI(self.db_manager)
        self.config = config or self._get_default_config()

    @property
    @abstractmethod
    def scanner_name(self) -> str:
        """Get scanner name."""
        pass

    @abstractmethod
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for scanner."""
        pass

    @abstractmethod
    def scan(self, scan_date: date, cutoff_time: time = time(9, 50)) -> pd.DataFrame:
        """
        Execute scanner logic for given date and time.

        Args:
            scan_date: Date to scan
            cutoff_time: Time cutoff for scanning

        Returns:
            DataFrame with scan results
        """
        pass

    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols from database."""
        return self.db_manager.get_available_symbols()

    def get_market_data(self,
                       symbols: List[str],
                       start_date: Union[str, date],
                       end_date: Union[str, date],
                       timeframe: str = '1m') -> pd.DataFrame:
        """
        Get historical market data for symbols.

        Args:
            symbols: List of symbols to get data for
            start_date: Start date for data
            end_date: End date for data
            timeframe: Data timeframe ('1m', '5m', '1D', etc.)

        Returns:
            DataFrame with market data
        """
        return self.query_api.get_market_data(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe
        )

    def get_technical_indicators(self,
                               symbols: List[str],
                               indicators: List[str],
                               start_date: Union[str, date] = None) -> pd.DataFrame:
        """
        Get technical indicators for symbols.

        Args:
            symbols: List of symbols
            indicators: List of technical indicator names
            start_date: Start date for indicators (default: 30 days ago)

        Returns:
            DataFrame with technical indicators
        """
        if start_date is None:
            start_date = date.today()

        return self.query_api.get_technical_indicators(
            symbols=symbols,
            indicators=indicators,
            start_date=start_date
        )

    def _execute_query(self, query: str, params: Dict = None) -> pd.DataFrame:
        """
        Execute custom SQL query.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query results as DataFrame
        """
        return self.db_manager.execute_custom_query(query, params)

    def _filter_by_liquidity(self,
                           symbols: List[str],
                           min_volume: int = 100000) -> List[str]:
        """
        Filter symbols by minimum average volume.

        Args:
            symbols: List of symbols to filter
            min_volume: Minimum average daily volume

        Returns:
            Filtered list of symbols
        """
        if not symbols:
            return []

        # Get average volumes for the past 20 trading days
        volume_query = """
        SELECT symbol,
               AVG(daily_volume) as avg_volume
        FROM (
            SELECT symbol,
                   date_partition,
                   SUM(volume) as daily_volume
            FROM market_data
            WHERE date_partition BETWEEN ? AND ?
            GROUP BY symbol, date_partition
        ) daily_totals
        WHERE symbol IN ({})
        GROUP BY symbol
        HAVING COUNT(*) >= 5  -- At least 5 trading days
        """.format(','.join(['?'] * len(symbols)))

        return []

    def _market_open_status(self) -> bool:
        """
        Check if market is currently open.

        Returns:
            True if market is open, False otherwise
        """
        now = datetime.now().time()
        market_open = time(9, 15)
        market_close = time(15, 30)

        return market_open <= now <= market_close

    def save_results(self,
                   results: pd.DataFrame,
                   output_dir: str = "scanners/results") -> str:
        """
        Save scan results to CSV file.

        Args:
            results: DataFrame with scan results
            output_dir: Output directory

        Returns:
            Path to saved file
        """
        if results.empty:
            return ""

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.scanner_name}_{timestamp}.csv"
        filepath = output_path / filename

        results.to_csv(filepath, index=False)
        print(f"📁 Results saved to: {filepath}")

        return str(filepath)

    def get_summary(self, results: pd.DataFrame) -> Dict[str, Any]:
        """
        Get summary statistics for scan results.

        Args:
            results: Scan results DataFrame

        Returns:
            Dictionary with summary statistics
        """
        if results.empty:
            return {
                'scanner': self.scanner_name,
                'symbols_found': 0,
                'status': 'No results'
            }

        return {
            'scanner': self.scanner_name,
            'symbols_found': len(results),
            'columns': list(results.columns),
            'total_volume': results.get('current_volume', pd.Series()).sum(),
            'avg_price_change': results.get('price_change_pct', pd.Series()).mean(),
            'timestamp': datetime.now().isoformat(),
            'status': f"Found {len(results)} symbols"
        }
