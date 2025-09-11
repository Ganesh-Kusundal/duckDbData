"""
DuckDB Database Infrastructure for Financial Data
Provides connection and schema management for parquet-based financial data.
"""

import duckdb
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime, date, timedelta
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DuckDBManager:
    """
    Manages DuckDB database connections and operations for financial data.
    
    This class handles:
    - Database connection management
    - Schema creation and management
    - Data loading from parquet files
    - Query execution with optimized performance
    """
    
    def __init__(self, db_path: str = None, data_root: str = None):
        """
        Initialize DuckDB manager.
        
        Args:
            db_path: Path to DuckDB database file
            data_root: Root directory containing parquet files
        """
        from src.infrastructure.config.settings import get_settings
        settings = get_settings()
        self.db_path = db_path or settings.database.path
        # Prefer configured data_root if provided; otherwise default to project data dir
        default_data_root = Path("data")
        self.data_root = Path(data_root) if data_root else default_data_root
        self.connection: Optional[duckdb.DuckDBPyConnection] = None
        
        # Validate data root exists
        if not self.data_root.exists():
            raise ValueError(f"Data root directory does not exist: {data_root}")
        
        logger.info(f"Initialized DuckDB manager with database: {db_path}")
    
    def connect(self) -> duckdb.DuckDBPyConnection:
        """
        Establish connection to DuckDB database.
        
        Returns:
            DuckDB connection object
        """
        if self.connection is None:
            try:
                self.connection = duckdb.connect(self.db_path)
                logger.info(f"Connected to DuckDB database: {self.db_path}")
                
                # Configure DuckDB for optimal performance
                self.connection.execute("SET memory_limit='4GB'")
                self.connection.execute("SET threads=4")
            except Exception as e:
                # If there's a lock conflict, wait a moment and retry
                import time
                time.sleep(0.5)
                try:
                    self.connection = duckdb.connect(self.db_path)
                    logger.info(f"Connected to DuckDB database (retry): {self.db_path}")
                    
                    # Configure DuckDB for optimal performance
                    self.connection.execute("SET memory_limit='4GB'")
                    self.connection.execute("SET threads=4")
                except:
                    raise e
            
        return self.connection
    
    def close(self):
        """Close database connection."""
        if self.connection:
            try:
                if not self.connection.closed:
                    self.connection.close()
                self.connection = None
                logger.info("Closed DuckDB connection")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
                self.connection = None
    
    def create_schema(self):
        """
        Create the database schema for financial data.
        
        Creates tables:
        - market_data: Main table for OHLCV data with symbol and timestamp
        - symbols: Reference table for symbol metadata
        """
        conn = self.connect()
        
        # Create market_data table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                symbol VARCHAR NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                open DOUBLE NOT NULL,
                high DOUBLE NOT NULL,
                low DOUBLE NOT NULL,
                close DOUBLE NOT NULL,
                volume BIGINT NOT NULL,
                date_partition DATE NOT NULL,
                PRIMARY KEY (symbol, timestamp)
            )
        """)
        
        # Create symbols reference table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS symbols (
                symbol VARCHAR PRIMARY KEY,
                name VARCHAR,
                sector VARCHAR,
                industry VARCHAR,
                first_date DATE,
                last_date DATE,
                total_records BIGINT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Create indexes for optimal query performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_market_data_date ON market_data(date_partition)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_market_data_symbol_date ON market_data(symbol, date_partition)")
        
        logger.info("Created database schema with tables: market_data, symbols")
    
    def get_available_symbols(self) -> List[str]:
        """
        Get list of available symbols from the file system.
        
        Returns:
            List of symbol names found in parquet files
        """
        symbols = set()
        
        # Scan through year directories
        for year_dir in self.data_root.iterdir():
            if year_dir.is_dir() and year_dir.name.isdigit():
                # Scan through month directories
                for month_dir in year_dir.iterdir():
                    if month_dir.is_dir():
                        # Scan through day directories
                        for day_dir in month_dir.iterdir():
                            if day_dir.is_dir():
                                # Extract symbols from parquet filenames
                                for parquet_file in day_dir.glob("*.parquet"):
                                    # Extract symbol from filename pattern: SYMBOL_minute_YYYY-MM-DD.parquet
                                    filename = parquet_file.stem
                                    if "_minute_" in filename:
                                        symbol = filename.split("_minute_")[0]
                                        symbols.add(symbol)
        
        return sorted(list(symbols))
    
    def get_date_range(self) -> tuple[date, date]:
        """
        Get the available date range from the file system.
        
        Returns:
            Tuple of (start_date, end_date)
        """
        dates = []
        
        # Scan through year directories
        for year_dir in self.data_root.iterdir():
            if year_dir.is_dir() and year_dir.name.isdigit():
                year = int(year_dir.name)
                # Scan through month directories
                for month_dir in year_dir.iterdir():
                    if month_dir.is_dir() and month_dir.name.isdigit():
                        month = int(month_dir.name)
                        # Scan through day directories
                        for day_dir in month_dir.iterdir():
                            if day_dir.is_dir() and day_dir.name.isdigit():
                                day = int(day_dir.name)
                                try:
                                    dates.append(date(year, month, day))
                                except ValueError:
                                    continue
        
        if not dates:
            raise ValueError("No valid dates found in data directory")
        
        return min(dates), max(dates)
    
    def load_symbol_data(self, symbol: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> int:
        """
        Load data for a specific symbol into the database.
        
        Args:
            symbol: Symbol to load (e.g., 'RELIANCE')
            start_date: Start date for loading (optional)
            end_date: End date for loading (optional)
            
        Returns:
            Number of records loaded
        """
        conn = self.connect()
        records_loaded = 0
        
        # Get date range if not specified
        if start_date is None or end_date is None:
            available_start, available_end = self.get_date_range()
            start_date = start_date or available_start
            end_date = end_date or available_end
        
        logger.info(f"Loading data for {symbol} from {start_date} to {end_date}")
        
        # Iterate through date range
        current_date = start_date
        while current_date <= end_date:
            year = current_date.year
            month = current_date.month
            day = current_date.day
            
            # Construct file path
            file_path = self.data_root / str(year) / f"{month:02d}" / f"{day:02d}" / f"{symbol}_minute_{current_date}.parquet"
            
            if file_path.exists():
                try:
                    # Read parquet file
                    df = pd.read_parquet(file_path)
                    
                    if not df.empty:
                        # Add metadata columns
                        df['symbol'] = symbol
                        df['date_partition'] = current_date
                        
                        # Create timestamp from index (assuming index represents minutes from market open)
                        # Reset index to ensure we have a clean integer sequence
                        df = df.reset_index(drop=True)
                        market_open = pd.to_datetime(f"{current_date} 09:15:00")
                        df['timestamp'] = market_open + pd.to_timedelta(df.index, unit='m')
                        
                        # Reorder columns
                        df = df[['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'date_partition']]
                        
                        # Insert into database using DuckDB's efficient bulk insert
                        conn.execute("INSERT INTO market_data SELECT * FROM df")
                        records_loaded += len(df)
                        
                        logger.debug(f"Loaded {len(df)} records for {symbol} on {current_date}")
                
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {e}")
            
            # Move to next day using safe arithmetic
            current_date = current_date + timedelta(days=1)
        
        # Update symbols table
        self._update_symbol_metadata(symbol)
        
        logger.info(f"Loaded {records_loaded} records for {symbol}")
        return records_loaded
    
    def _update_symbol_metadata(self, symbol: str):
        """Update metadata for a symbol in the symbols table."""
        conn = self.connect()
        
        # Get symbol statistics
        result = conn.execute("""
            SELECT 
                MIN(date_partition) as first_date,
                MAX(date_partition) as last_date,
                COUNT(*) as total_records
            FROM market_data 
            WHERE symbol = ?
        """, [symbol]).fetchone()
        
        if result:
            first_date, last_date, total_records = result
            
            # Upsert symbol metadata
            conn.execute("""
                INSERT INTO symbols (symbol, first_date, last_date, total_records, updated_at)
                VALUES (?, ?, ?, ?, NOW())
                ON CONFLICT (symbol) DO UPDATE SET
                    first_date = EXCLUDED.first_date,
                    last_date = EXCLUDED.last_date,
                    total_records = EXCLUDED.total_records,
                    updated_at = NOW()
            """, [symbol, first_date, last_date, total_records])
    
    def query_market_data(self, 
                         symbol: Optional[str] = None,
                         start_date: Optional[date] = None,
                         end_date: Optional[date] = None,
                         start_time: Optional[str] = None,
                         end_time: Optional[str] = None,
                         limit: Optional[int] = None) -> pd.DataFrame:
        """
        Query market data with flexible filtering.
        
        Args:
            symbol: Symbol to filter by (optional)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            start_time: Start time filter in HH:MM format (optional)
            end_time: End time filter in HH:MM format (optional)
            limit: Maximum number of records to return (optional)
            
        Returns:
            DataFrame with filtered market data
        """
        conn = self.connect()
        
        # Build query
        where_clauses = []
        params = []
        
        if symbol:
            where_clauses.append("symbol = ?")
            params.append(symbol)
        
        if start_date:
            where_clauses.append("date_partition >= ?")
            params.append(start_date)
        
        if end_date:
            where_clauses.append("date_partition <= ?")
            params.append(end_date)
        
        if start_time:
            where_clauses.append("TIME(timestamp) >= ?")
            params.append(start_time)
        
        if end_time:
            where_clauses.append("TIME(timestamp) <= ?")
            params.append(end_time)
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        query = f"""
            SELECT symbol, timestamp, open, high, low, close, volume, date_partition
            FROM market_data
            WHERE {where_clause}
            ORDER BY symbol, timestamp
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        return conn.execute(query, params).df()
    
    def get_symbols_info(self) -> pd.DataFrame:
        """
        Get information about all symbols in the database.
        
        Returns:
            DataFrame with symbol metadata
        """
        conn = self.connect()
        return conn.execute("SELECT * FROM symbols ORDER BY symbol").df()
    
    def insert_market_data(self, df: pd.DataFrame) -> int:
        """
        Insert market data DataFrame into the database.
        
        Args:
            df: DataFrame with columns: symbol, timestamp, open, high, low, close, volume
            
        Returns:
            Number of records inserted
        """
        if df.empty:
            return 0
        
        conn = self.connect()
        
        # Ensure required columns are present
        required_columns = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Add date_partition column if not present
        if 'date_partition' not in df.columns:
            df = df.copy()
            df['date_partition'] = pd.to_datetime(df['timestamp']).dt.date
        
        # Select and order columns for insertion
        df_insert = df[['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'date_partition']].copy()
        
        # Convert timestamp to proper format if needed
        df_insert['timestamp'] = pd.to_datetime(df_insert['timestamp'])
        
        try:
            # Use DuckDB's efficient bulk insert with ON CONFLICT handling
            conn.execute("""
                INSERT INTO market_data (symbol, timestamp, open, high, low, close, volume, date_partition)
                SELECT * FROM df_insert
                ON CONFLICT (symbol, timestamp) DO NOTHING
            """)
            
            # Get count of records that were actually inserted
            # Since we use ON CONFLICT DO NOTHING, we need to check what was actually inserted
            records_inserted = len(df_insert)
            
            logger.info(f"Inserted {records_inserted} records into market_data table")
            return records_inserted
            
        except Exception as e:
            logger.error(f"Error inserting market data: {e}")
            raise
    
    def execute_custom_query(self, query: str, params: Optional[List] = None) -> pd.DataFrame:
        """
        Execute a custom SQL query.
        
        Args:
            query: SQL query string
            params: Query parameters (optional)
            
        Returns:
            DataFrame with query results
        """
        conn = self.connect()
        return conn.execute(query, params or []).df()
