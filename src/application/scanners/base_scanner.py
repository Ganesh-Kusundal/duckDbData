"""
Base scanner class for intraday stock selection using DuckDB.
"""

from abc import abstractmethod
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, date, time
import pandas as pd
from pathlib import Path
import sys
import asyncio
from typing import Union, Awaitable

from analytics.core.pattern_analyzer import PatternAnalyzer
from analytics.core.duckdb_connector import DuckDBAnalytics

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.infrastructure.config.config_manager import ConfigManager
from src.infrastructure.core.query_api import QueryAPI
from src.infrastructure.config.settings import get_settings
from src.infrastructure.core.database import DuckDBManager
from src.domain.exceptions import ScannerError
from src.infrastructure.utils.retry import retry_on_transient_errors, retry_db_operation
from src.infrastructure.logging import get_logger
from src.application.interfaces.base_scanner_interface import IBaseScanner
import duckdb
import os

logger = get_logger(__name__)


class BaseScanner(IBaseScanner):
    """Abstract base class for all scanner implementations that follows SOLID principles."""

    def __init__(
        self,
        db_path: str = None,
        config_manager: Optional[ConfigManager] = None,
        config: Dict[str, Any] = None,
        pattern_analyzer: Optional[PatternAnalyzer] = None,
        query_api: Optional[QueryAPI] = None,
        db_manager: Optional[DuckDBManager] = None,
    ):
        """
        Initialize scanner with database path and configuration.

        Args:
            db_path: Path to DuckDB database file
            config_manager: ConfigManager instance for centralized configuration (optional for backward compatibility)
            config: Scanner configuration parameters (fallback if config_manager not provided)
            pattern_analyzer: Optional PatternAnalyzer instance for analytics integration
        """
        settings = get_settings()
        self.db_path = db_path or settings.database.path
        self._connection = None

        # Prefer injected analytics/query dependencies; otherwise, wire conservatively
        if query_api is not None:
            self.query_api = query_api
        else:
            # Only instantiate a real DB manager if explicitly provided or settings are usable
            self.query_api = None
            try:
                manager = db_manager or DuckDBManager(db_path=self.db_path)
                self.query_api = QueryAPI(manager)
            except Exception:
                # Fall back to lazy, scanner-local SQL via get_connection
                pass
        self.config_manager = config_manager
        self.pattern_analyzer = pattern_analyzer

        # Backward compatible config loading
        if self.config_manager:
            try:
                scanners_config = self.config_manager.get_config('scanners')
                self.config = scanners_config.get('default', {})
            except Exception:
                # Fallback to old method if config loading fails
                self.config = self._get_default_config()
        else:
            self.config = config or self._get_default_config()

    @property
    @abstractmethod
    def scanner_name(self) -> str:
        """Get scanner name."""
        pass

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for scanner (backward compatibility)."""
        # Subclasses should override this for backward compatibility
        # New implementations should use ConfigManager instead
        return {
            'obv_threshold': 100.0,
            'volume_multiplier': 1.5,
            'breakout_period': 20
        }

    @retry_on_transient_errors
    @abstractmethod
    def scan(self, scan_date: date, cutoff_time: time = time(9, 50)) -> pd.DataFrame:
        """
        Execute scanner logic for given date and time.
        
        Args:
            scan_date: Date to scan
            cutoff_time: Time cutoff for scanning
            
        Returns:
            DataFrame with scan results
            
        Raises:
            ScannerError: If scanner execution fails
        """
        pass

    def get_connection(self):
        """Get database connection, creating if necessary."""
        if self._connection is None:
            settings = get_settings()
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(f"Database file not found: {self.db_path}")
            # Configure connection using settings
            config = {
                "access_mode": "READ_ONLY" if getattr(settings.database, "read_only", False) else "READ_WRITE",
            }
            self._connection = duckdb.connect(self.db_path, config=config)
            # Apply runtime settings if available
            if getattr(settings.database, "memory_limit", None):
                self._connection.execute(f"SET memory_limit='{settings.database.memory_limit}'")
            if getattr(settings.database, "threads", None):
                self._connection.execute(f"SET threads={int(settings.database.threads)}")
        return self._connection

    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols from database."""
        try:
            conn = self.get_connection()
            result = conn.execute("SELECT DISTINCT symbol FROM market_data_unified ORDER BY symbol").fetchall()
            return [row[0] for row in result]
        except Exception as e:
            logger.warning(f"Failed to get symbols: {e}")
            return []

    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Execute a query and return results as DataFrame."""
        try:
            conn = self.get_connection()
            if params:
                if isinstance(params, dict):
                    # Handle named parameters
                    formatted_query = query
                    param_values = []
                    for key, value in params.items():
                        placeholder = f":{key}"
                        if placeholder in formatted_query:
                            formatted_query = formatted_query.replace(placeholder, "?")
                            param_values.append(value)
                    result = conn.execute(formatted_query, param_values)
                else:
                    result = conn.execute(query, params)
            else:
                result = conn.execute(query)
            return result.fetchdf()
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    @retry_on_transient_errors
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
            
        Raises:
            ScannerError: If market data retrieval fails
        """
        try:
            return self.query_api.get_market_data(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                timeframe=timeframe
            )
        except Exception as e:
            error_msg = f"Failed to get market data for {len(symbols)} symbols: {str(e)}"
            context = {
                'scanner_name': self.scanner_name,
                'symbols_count': len(symbols),
                'timeframe': timeframe,
                'date_range': f"{start_date} to {end_date}"
            }
            exc = ScannerError(error_msg, self.scanner_name, context=context)
            logger.error("Market data retrieval failed", extra=exc.to_dict())
            raise exc

    async def async_get_market_data(self,
                                   symbols: List[str],
                                   start_date: Union[str, date],
                                   end_date: Union[str, date],
                                   timeframe: str = '1m',
                                   timeout: float = 30.0) -> pd.DataFrame:
        """
        Async version of get_market_data using concurrent processing.
        
        Args:
            symbols: List of symbols to get data for
            start_date: Start date for data
            end_date: End date for data
            timeframe: Data timeframe
            timeout: Overall timeout for all concurrent operations
            
        Returns:
            Combined DataFrame with market data
            
        Raises:
            ScannerError: If async market data retrieval fails
        """
        try:
            # Get timeout from ConfigManager if available
            if self.config_manager:
                try:
                    scanners_config = self.config_manager.get_config('scanners')
                    timeout = scanners_config.get('async_timeout', timeout)
                except Exception:
                    logger.debug("Could not load async timeout from config, using default")
            
            async def fetch_symbol_data(symbol: str) -> pd.DataFrame:
                """Fetch data for single symbol."""
                try:
                    # Run sync query in thread pool
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        None,
                        lambda: self.query_api.get_market_data([symbol], start_date, end_date, timeframe)
                    )
                except Exception as e:
                    logger.warning(f"Failed to fetch data for {symbol}: {e}")
                    return pd.DataFrame()
            
            # Create concurrent tasks for each symbol
            tasks = [fetch_symbol_data(symbol) for symbol in symbols]
            
            # Execute with timeout using asyncio.gather
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )
            
            # Combine results
            combined_data = pd.DataFrame()
            for i, result in enumerate(results):
                if isinstance(result, pd.DataFrame) and not result.empty:
                    # Add symbol column if not present
                    if 'symbol' not in result.columns:
                        result['symbol'] = symbols[i]
                    combined_data = pd.concat([combined_data, result], ignore_index=True)
            
            if combined_data.empty:
                logger.warning(f"No market data retrieved for {len(symbols)} symbols")
                return pd.DataFrame()
            
            logger.info(f"Async fetched market data for {len(symbols)} symbols, got {len(combined_data)} records")
            return combined_data
            
        except asyncio.TimeoutError:
            error_msg = f"Async market data timeout after {timeout}s for {len(symbols)} symbols"
            context = {
                'scanner_name': self.scanner_name,
                'symbols_count': len(symbols),
                'timeout': timeout,
                'timeframe': timeframe
            }
            exc = ScannerError(error_msg, self.scanner_name, context=context)
            logger.error("Async market data timeout", extra=exc.to_dict())
            raise exc
        except Exception as e:
            error_msg = f"Async market data retrieval failed for {len(symbols)} symbols: {str(e)}"
            context = {
                'scanner_name': self.scanner_name,
                'symbols_count': len(symbols),
                'timeframe': timeframe,
                'date_range': f"{start_date} to {end_date}"
            }
            exc = ScannerError(error_msg, self.scanner_name, context=context)
            logger.error("Async market data retrieval failed", extra=exc.to_dict())
            raise exc

    @retry_on_transient_errors
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
            
        Raises:
            ScannerError: If technical indicators retrieval fails
        """
        if start_date is None:
            start_date = date.today()
        
        try:
            return self.query_api.get_technical_indicators(
                symbols=symbols,
                indicators=indicators,
                start_date=start_date
            )
        except Exception as e:
            error_msg = f"Failed to get technical indicators for {len(symbols)} symbols: {str(e)}"
            context = {
                'scanner_name': self.scanner_name,
                'symbols_count': len(symbols),
                'indicators_count': len(indicators),
                'start_date': str(start_date)
            }
            exc = ScannerError(error_msg, self.scanner_name, context=context)
            logger.error("Technical indicators retrieval failed", extra=exc.to_dict())
            raise exc

    async def async_get_technical_indicators(self,
                                            symbols: List[str],
                                            indicators: List[str],
                                            start_date: Union[str, date] = None,
                                            timeout: float = 30.0) -> pd.DataFrame:
        """
        Async version of get_technical_indicators using concurrent processing.
        
        Args:
            symbols: List of symbols
            indicators: List of technical indicator names
            start_date: Start date for indicators
            timeout: Overall timeout for concurrent operations
            
        Returns:
            Combined DataFrame with technical indicators
            
        Raises:
            ScannerError: If async technical indicators retrieval fails
        """
        if start_date is None:
            start_date = date.today()
        
        try:
            # Get timeout from ConfigManager if available
            if self.config_manager:
                try:
                    scanners_config = self.config_manager.get_config('scanners')
                    timeout = scanners_config.get('async_timeout', timeout)
                except Exception:
                    logger.debug("Could not load async timeout from config, using default")
            
            async def fetch_symbol_indicators(symbol: str) -> pd.DataFrame:
                """Fetch indicators for single symbol."""
                try:
                    # Run sync query in thread pool
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        None,
                        lambda: self.query_api.get_technical_indicators([symbol], indicators, start_date)
                    )
                except Exception as e:
                    logger.warning(f"Failed to fetch indicators for {symbol}: {e}")
                    return pd.DataFrame()
            
            # Create concurrent tasks for each symbol
            tasks = [fetch_symbol_indicators(symbol) for symbol in symbols]
            
            # Execute with timeout using asyncio.gather
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )
            
            # Combine results
            combined_data = pd.DataFrame()
            for i, result in enumerate(results):
                if isinstance(result, pd.DataFrame) and not result.empty:
                    # Add symbol column if not present
                    if 'symbol' not in result.columns:
                        result['symbol'] = symbols[i]
                    combined_data = pd.concat([combined_data, result], ignore_index=True)
            
            if combined_data.empty:
                logger.warning(f"No technical indicators retrieved for {len(symbols)} symbols")
                return pd.DataFrame()
            
            logger.info(f"Async fetched technical indicators for {len(symbols)} symbols with {len(indicators)} indicators")
            return combined_data
            
        except asyncio.TimeoutError:
            error_msg = f"Async technical indicators timeout after {timeout}s for {len(symbols)} symbols"
            context = {
                'scanner_name': self.scanner_name,
                'symbols_count': len(symbols),
                'indicators_count': len(indicators),
                'timeout': timeout
            }
            exc = ScannerError(error_msg, self.scanner_name, context=context)
            logger.error("Async technical indicators timeout", extra=exc.to_dict())
            raise exc
        except Exception as e:
            error_msg = f"Async technical indicators retrieval failed for {len(symbols)} symbols: {str(e)}"
            context = {
                'scanner_name': self.scanner_name,
                'symbols_count': len(symbols),
                'indicators_count': len(indicators),
                'start_date': str(start_date)
            }
            exc = ScannerError(error_msg, self.scanner_name, context=context)
            logger.error("Async technical indicators retrieval failed", extra=exc.to_dict())
            raise exc

    @retry_db_operation()
    def _execute_query(self, query: str, params: Dict = None) -> pd.DataFrame:
        """
        Execute custom SQL query.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query results as DataFrame

        Raises:
            ScannerError: If query execution fails
        """
        try:
            return self.execute_query(query, params)
        except Exception as e:
            error_msg = f"Query execution failed in scanner {self.scanner_name}: {str(e)}"
            context = {
                'scanner_name': self.scanner_name,
                'query': query[:100] + '...' if len(query) > 100 else query,
                'params_count': len(params) if params else 0
            }
            exc = ScannerError(error_msg, self.scanner_name, context=context)
            logger.error("Scanner query execution failed", extra=exc.to_dict())
            raise exc

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
            FROM market_data_unified
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

    def get_pattern_scores(self, symbols: List[str]) -> pd.DataFrame:
        """
        Get pattern scores for symbols using PatternAnalyzer.
        
        Args:
            symbols: List of symbols to analyze
            
        Returns:
            DataFrame with pattern scores (confidence_score, volume_multiplier)
            
        Raises:
            ScannerError: If pattern analysis fails
        """
        if not self.pattern_analyzer:
            logger.warning(f"No PatternAnalyzer injected in {self.scanner_name}, skipping pattern analysis")
            return pd.DataFrame(columns=['symbol', 'confidence_score', 'volume_multiplier'])
        
        try:
            # Get analytics config if available
            min_volume_multiplier = 1.5
            if self.config_manager:
                try:
                    analytics_config = self.config_manager.get_config('analytics')
                    min_volume_multiplier = analytics_config.get('min_volume_multiplier', 1.5)
                except Exception:
                    logger.debug("Could not load analytics config, using default min_volume_multiplier=1.5")
            
            # Discover patterns
            volume_patterns = self.pattern_analyzer.discover_volume_spike_patterns(
                min_volume_multiplier=min_volume_multiplier
            )
            time_patterns = self.pattern_analyzer.discover_time_window_patterns()
            
            # Combine and aggregate patterns for requested symbols
            all_patterns = volume_patterns + time_patterns
            symbol_scores = {}
            
            for pattern in all_patterns:
                if pattern.symbol in symbols:
                    if pattern.symbol not in symbol_scores:
                        symbol_scores[pattern.symbol] = {
                            'confidence_score': 0.0,
                            'volume_multiplier': 1.0,
                            'pattern_count': 0
                        }
                    
                    symbol_scores[pattern.symbol]['confidence_score'] += pattern.confidence_score
                    symbol_scores[pattern.symbol]['volume_multiplier'] = max(
                        symbol_scores[pattern.symbol]['volume_multiplier'],
                        pattern.volume_multiplier
                    )
                    symbol_scores[pattern.symbol]['pattern_count'] += 1
            
            # Create results DataFrame
            results_data = []
            for symbol in symbols:
                if symbol in symbol_scores:
                    scores = symbol_scores[symbol]
                    avg_confidence = scores['confidence_score'] / scores['pattern_count']
                    results_data.append({
                        'symbol': symbol,
                        'confidence_score': round(avg_confidence, 3),
                        'volume_multiplier': round(scores['volume_multiplier'], 2)
                    })
                else:
                    results_data.append({
                        'symbol': symbol,
                        'confidence_score': 0.0,
                        'volume_multiplier': 1.0
                    })
            
            result_df = pd.DataFrame(results_data)
            logger.info(f"Generated pattern scores for {len(result_df)} symbols in {self.scanner_name}")
            return result_df
            
        except Exception as e:
            error_msg = f"Pattern analysis failed in scanner {self.scanner_name}: {str(e)}"
            context = {
                'scanner_name': self.scanner_name,
                'symbols_count': len(symbols),
                'error_type': type(e).__name__
            }
            exc = ScannerError(error_msg, self.scanner_name, context=context)
            logger.error("Pattern analysis failed", extra=exc.to_dict())
            raise exc

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
