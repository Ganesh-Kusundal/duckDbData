"""Data ingestion pipeline for loading market data."""

import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd

from ...domain.entities.market_data import MarketData, MarketDataBatch, OHLCV
from ...domain.entities.symbol import Symbol
from ...domain.events import DataIngestedEvent
from ...infrastructure.messaging.event_bus import publish_event
from ...infrastructure.repositories.duckdb_market_repo import DuckDBMarketDataRepository
from ..logging import get_logger

logger = get_logger(__name__)


class DataIngestionPipeline:
    """Pipeline for ingesting market data from various sources."""

    def __init__(self, repository: Optional[DuckDBMarketDataRepository] = None):
        """Initialize data ingestion pipeline."""
        self.repository = repository or DuckDBMarketDataRepository()
        logger.info("Data ingestion pipeline initialized")

    def ingest_from_parquet_files(
        self,
        data_directory: str,
        symbol_pattern: str = "*.parquet",
        batch_size: int = 1000
    ) -> Dict[str, Any]:
        """Ingest market data from Parquet files."""
        data_path = Path(data_directory)
        if not data_path.exists():
            raise ValueError(f"Data directory does not exist: {data_directory}")

        logger.info("Starting Parquet file ingestion", data_directory=str(data_directory))

        total_files = 0
        total_records = 0
        processed_symbols = []

        # Find all Parquet files
        parquet_files = list(data_path.rglob(symbol_pattern))
        logger.info("Found Parquet files", count=len(parquet_files))

        for file_path in parquet_files:
            try:
                symbol = self._extract_symbol_from_filename(file_path.name)
                if not symbol:
                    logger.warning("Could not extract symbol from filename", filename=file_path.name)
                    continue

                # Read Parquet file
                df = pd.read_parquet(file_path)
                if df.empty:
                    logger.warning("Empty Parquet file", file=str(file_path))
                    continue

                # Process and save data
                records_saved = self._process_dataframe(df, symbol, batch_size)
                total_records += records_saved
                processed_symbols.append(symbol)
                total_files += 1

                logger.info(
                    "Processed Parquet file",
                    file=str(file_path),
                    symbol=symbol,
                    records=records_saved
                )

            except Exception as e:
                logger.error(
                    "Failed to process Parquet file",
                    file=str(file_path),
                    error=str(e)
                )
                continue

        result = {
            'total_files': total_files,
            'total_records': total_records,
            'processed_symbols': processed_symbols,
            'success': True
        }

        logger.info(
            "Parquet ingestion completed",
            total_files=total_files,
            total_records=total_records,
            processed_symbols=len(processed_symbols)
        )

        # Publish event
        publish_event(DataIngestedEvent(
            symbol="BATCH",
            timeframe="MULTIPLE",
            records_count=total_records,
            start_date=date.today(),
            end_date=date.today()
        ))

        return result

    def ingest_from_csv_files(
        self,
        data_directory: str,
        symbol_pattern: str = "*.csv",
        batch_size: int = 1000
    ) -> Dict[str, Any]:
        """Ingest market data from CSV files."""
        data_path = Path(data_directory)
        if not data_path.exists():
            raise ValueError(f"Data directory does not exist: {data_directory}")

        logger.info("Starting CSV file ingestion", data_directory=str(data_directory))

        total_files = 0
        total_records = 0
        processed_symbols = []

        # Find all CSV files
        csv_files = list(data_path.rglob(symbol_pattern))
        logger.info("Found CSV files", count=len(csv_files))

        for file_path in csv_files:
            try:
                symbol = self._extract_symbol_from_filename(file_path.name)
                if not symbol:
                    logger.warning("Could not extract symbol from filename", filename=file_path.name)
                    continue

                # Read CSV file
                df = pd.read_csv(file_path)
                if df.empty:
                    logger.warning("Empty CSV file", file=str(file_path))
                    continue

                # Process and save data
                records_saved = self._process_dataframe(df, symbol, batch_size)
                total_records += records_saved
                processed_symbols.append(symbol)
                total_files += 1

                logger.info(
                    "Processed CSV file",
                    file=str(file_path),
                    symbol=symbol,
                    records=records_saved
                )

            except Exception as e:
                logger.error(
                    "Failed to process CSV file",
                    file=str(file_path),
                    error=str(e)
                )
                continue

        result = {
            'total_files': total_files,
            'total_records': total_records,
            'processed_symbols': processed_symbols,
            'success': True
        }

        logger.info(
            "CSV ingestion completed",
            total_files=total_files,
            total_records=total_records,
            processed_symbols=len(processed_symbols)
        )

        return result

    def ingest_from_dataframe(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str = "1D",
        batch_size: int = 1000
    ) -> int:
        """Ingest market data from a pandas DataFrame."""
        logger.info(
            "Starting DataFrame ingestion",
            symbol=symbol,
            timeframe=timeframe,
            records=len(df)
        )

        records_saved = self._process_dataframe(df, symbol, batch_size, timeframe)

        logger.info(
            "DataFrame ingestion completed",
            symbol=symbol,
            records_saved=records_saved
        )

        # Publish event
        publish_event(DataIngestedEvent(
            symbol=symbol,
            timeframe=timeframe,
            records_count=records_saved,
            start_date=date.today(),
            end_date=date.today()
        ))

        return records_saved

    def _process_dataframe(
        self,
        df: pd.DataFrame,
        symbol: str,
        batch_size: int = 1000,
        timeframe: str = "1D"
    ) -> int:
        """Process DataFrame and save market data."""
        # Normalize column names
        df = self._normalize_columns(df)

        # Validate required columns
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Convert data types
        df = self._convert_data_types(df)

        # Create market data entities
        market_data_list = []
        for _, row in df.iterrows():
            try:
                ohlcv = OHLCV(
                    open=Decimal(str(row['open'])),
                    high=Decimal(str(row['high'])),
                    low=Decimal(str(row['low'])),
                    close=Decimal(str(row['close'])),
                    volume=int(row['volume'])
                )

                market_data = MarketData(
                    symbol=symbol,
                    timestamp=row['timestamp'],
                    timeframe=timeframe,
                    ohlcv=ohlcv,
                    date_partition=row['timestamp'].date()
                )
                market_data_list.append(market_data)

            except Exception as e:
                logger.warning(
                    "Failed to create market data entity",
                    symbol=symbol,
                    timestamp=str(row.get('timestamp')),
                    error=str(e)
                )
                continue

        # Save in batches
        total_saved = 0
        for i in range(0, len(market_data_list), batch_size):
            batch_data = market_data_list[i:i + batch_size]
            batch = MarketDataBatch(
                symbol=symbol,
                timeframe=timeframe,
                data=batch_data,
                start_date=batch_data[0].timestamp.date(),
                end_date=batch_data[-1].timestamp.date()
            )

            try:
                self.repository.save_batch(batch)
                total_saved += len(batch_data)
            except Exception as e:
                logger.error(
                    "Failed to save batch",
                    symbol=symbol,
                    batch_size=len(batch_data),
                    error=str(e)
                )
                continue

        return total_saved

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to standard format."""
        column_mapping = {
            'date': 'timestamp',
            'datetime': 'timestamp',
            'time': 'timestamp',
            'o': 'open',
            'h': 'high',
            'l': 'low',
            'c': 'close',
            'v': 'volume',
            'vol': 'volume',
            'volume': 'volume'
        }

        df = df.copy()
        df.columns = df.columns.str.lower()

        for old_col, new_col in column_mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                df = df.rename(columns={old_col: new_col})

        return df

    def _convert_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert DataFrame columns to appropriate data types."""
        df = df.copy()

        # Convert timestamp
        if 'timestamp' in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Convert numeric columns
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Drop rows with NaN values in critical columns
        critical_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        existing_critical = [col for col in critical_columns if col in df.columns]
        df = df.dropna(subset=existing_critical)

        return df

    def _extract_symbol_from_filename(self, filename: str) -> Optional[str]:
        """Extract symbol from filename."""
        # Common patterns: SYMBOL_minute_YYYY-MM-DD.parquet
        # or SYMBOL.csv
        name = Path(filename).stem

        # Remove common suffixes
        for suffix in ['_minute', '_daily', '_hourly', '_weekly', '_monthly']:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
                break

        # Remove date patterns
        import re
        name = re.sub(r'_\d{4}-\d{2}-\d{2}$', '', name)

        return name.upper() if name else None

    def get_ingestion_stats(self) -> Dict[str, Any]:
        """Get ingestion statistics."""
        try:
            # This would query the repository for stats
            # For now, return basic info
            return {
                'status': 'operational',
                'last_ingestion': datetime.now().isoformat(),
                'supported_formats': ['parquet', 'csv', 'dataframe']
            }
        except Exception as e:
            logger.error("Failed to get ingestion stats", error=str(e))
            return {
                'status': 'error',
                'error': str(e)
            }
