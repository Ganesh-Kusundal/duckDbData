"""
DuckDB Repository Adapter
=======================

Implements RepositoryPort for persisting trade artifacts,
analytics, and telemetry data to DuckDB.
"""

import duckdb
from typing import List, Dict, Any, Optional
from datetime import date, datetime
from decimal import Decimal
import os
import uuid

from ..domain.models import Bar, Signal, Order, Fill, Position, Score, RunMetadata
from ..ports.repository import RepositoryPort


class DuckDBRepository(RepositoryPort):
    """DuckDB-based repository implementation"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = None
        self._ensure_connection()
        self.initialize_tables()

    def _ensure_connection(self):
        """Ensure database connection exists"""
        if self._conn is None:
            self._conn = duckdb.connect(self.db_path)
            self._conn.execute("SET memory_limit='2GB'")
            self._conn.execute("SET threads=2")

    def initialize_tables(self) -> bool:
        """Initialize database tables for trade engine"""
        try:
            # Signals table
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id VARCHAR PRIMARY KEY,
                    symbol VARCHAR,
                    signal_type VARCHAR,
                    timestamp TIMESTAMP,
                    price DECIMAL(10,2),
                    quantity INTEGER,
                    reason VARCHAR,
                    confidence_score FLOAT,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Orders table
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id VARCHAR PRIMARY KEY,
                    broker_order_id VARCHAR,
                    symbol VARCHAR,
                    side VARCHAR,
                    quantity INTEGER,
                    filled_quantity INTEGER DEFAULT 0,
                    order_type VARCHAR,
                    status VARCHAR,
                    price DECIMAL(10,2),
                    stop_price DECIMAL(10,2),
                    avg_fill_price DECIMAL(10,2),
                    timestamp TIMESTAMP,
                    fills JSON
                )
            """)

            # Positions table
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    symbol VARCHAR PRIMARY KEY,
                    quantity INTEGER,
                    avg_cost DECIMAL(10,2),
                    current_price DECIMAL(10,2),
                    unrealized_pnl DECIMAL(10,2),
                    realized_pnl DECIMAL(10,2),
                    entry_timestamp TIMESTAMP,
                    stops JSON,
                    ladder_stage INTEGER,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Scores table
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS scores (
                    symbol VARCHAR,
                    date DATE,
                    ret_0915_0950 FLOAT,
                    vspike_10m FLOAT,
                    obv_delta_35m FLOAT,
                    sector_strength FLOAT,
                    range_compression FLOAT,
                    spread_penalty FLOAT,
                    illiq_penalty FLOAT,
                    total_score FLOAT,
                    components_json JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (symbol, date)
                )
            """)

            # Runs table
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id VARCHAR PRIMARY KEY,
                    mode VARCHAR,
                    start_date DATE,
                    end_date DATE,
                    start_time TIME,
                    end_time TIME,
                    config_snapshot JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            return True

        except Exception as e:
            print(f"Error initializing tables: {e}")
            return False

    def save_signals(self, signals: List[Signal]) -> bool:
        """Save trading signals"""
        try:
            for signal in signals:
                self._conn.execute("""
                    INSERT OR REPLACE INTO signals
                    (id, symbol, signal_type, timestamp, price, quantity, reason, confidence_score, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    signal.id,
                    signal.symbol,
                    signal.signal_type.value,
                    signal.timestamp,
                    float(signal.price),
                    signal.quantity,
                    signal.reason,
                    signal.confidence_score,
                    str(signal.metadata) if signal.metadata else None
                ])
            return True
        except Exception as e:
            print(f"Error saving signals: {e}")
            return False

    def save_orders(self, orders: List[Order]) -> bool:
        """Save order information"""
        try:
            for order in orders:
                fills_json = str([{
                    'timestamp': f.timestamp.isoformat(),
                    'quantity': f.quantity,
                    'price': float(f.price),
                    'fee': float(f.fee)
                } for f in order.fills]) if order.fills else None

                self._conn.execute("""
                    INSERT OR REPLACE INTO orders
                    (id, broker_order_id, symbol, side, quantity, filled_quantity,
                     order_type, status, price, stop_price, avg_fill_price, timestamp, fills)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    order.id,
                    order.broker_order_id,
                    order.symbol,
                    order.side.value,
                    order.quantity,
                    order.filled_quantity,
                    order.order_type.value,
                    order.status.value,
                    float(order.price) if order.price else None,
                    float(order.stop_price) if order.stop_price else None,
                    float(order.avg_fill_price) if order.avg_fill_price else None,
                    order.timestamp,
                    fills_json
                ])
            return True
        except Exception as e:
            print(f"Error saving orders: {e}")
            return False

    def save_positions(self, positions: List[Position]) -> bool:
        """Save position snapshots"""
        try:
            for position in positions:
                stops_json = str([{
                    'stop_price': float(s.stop_price),
                    'tsl_mode': s.tsl_mode.value,
                    'k_atr': s.k_atr
                } for s in position.stops]) if position.stops else None

                self._conn.execute("""
                    INSERT OR REPLACE INTO positions
                    (symbol, quantity, avg_cost, current_price, unrealized_pnl,
                     realized_pnl, entry_timestamp, stops, ladder_stage)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    position.symbol,
                    position.quantity,
                    float(position.avg_cost),
                    float(position.current_price) if position.current_price else None,
                    float(position.unrealized_pnl),
                    float(position.realized_pnl),
                    position.entry_timestamp,
                    stops_json,
                    position.ladder_stage
                ])
            return True
        except Exception as e:
            print(f"Error saving positions: {e}")
            return False

    def save_scores(self, scores: List[Score]) -> bool:
        """Save scoring data"""
        try:
            for score in scores:
                self._conn.execute("""
                    INSERT OR REPLACE INTO scores
                    (symbol, date, ret_0915_0950, vspike_10m, obv_delta_35m,
                     sector_strength, range_compression, spread_penalty, illiq_penalty,
                     total_score, components_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    score.symbol,
                    score.date,
                    score.ret_0915_0950,
                    score.vspike_10m,
                    score.obv_delta_35m,
                    score.sector_strength,
                    score.range_compression,
                    score.spread_penalty,
                    score.illiq_penalty,
                    score.total_score,
                    str(score.components_json)
                ])
            return True
        except Exception as e:
            print(f"Error saving scores: {e}")
            return False

    def save_run_metadata(self, metadata: RunMetadata) -> bool:
        """Save run metadata"""
        try:
            self._conn.execute("""
                INSERT OR REPLACE INTO runs
                (run_id, mode, start_date, end_date, start_time, end_time, config_snapshot)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                metadata.run_id,
                metadata.mode,
                metadata.start_date,
                metadata.end_date,
                metadata.start_time,
                metadata.end_time,
                str(metadata.config_snapshot)
            ])
            return True
        except Exception as e:
            print(f"Error saving run metadata: {e}")
            return False

    # Placeholder implementations for other methods
    def save_bars(self, bars: List[Bar]) -> bool:
        """Save market data bars - placeholder"""
        return True

    def save_fills(self, fills: List[Fill]) -> bool:
        """Save order fills - handled in orders"""
        return True

    def load_bars(self, symbol: str, start_date: date, end_date: date,
                  timeframe: str = "1m") -> List[Bar]:
        """Load historical bars - placeholder"""
        return []

    def load_signals(self, run_id: str, symbol: Optional[str] = None) -> List[Signal]:
        """Load trading signals - placeholder"""
        return []

    def get_pnl_series(self, run_id: str, symbol: Optional[str] = None) -> Dict[datetime, Decimal]:
        """Get P&L time series - placeholder"""
        return {}

    def get_run_metrics(self, run_id: str) -> Dict[str, Any]:
        """Get run performance metrics - placeholder"""
        return {}

    def __del__(self):
        """Cleanup connection"""
        if self._conn:
            self._conn.close()
