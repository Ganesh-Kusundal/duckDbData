"""
Market Data Repository Implementation
Implements repository pattern for market data persistence
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

from .base_repository import BaseRepository, RepositoryResult, QueryBuilder
from .duckdb_adapter import get_duckdb_adapter

logger = logging.getLogger(__name__)


@dataclass
class MarketData:
    """Market data entity"""
    symbol: str
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    exchange: str = "NSE"
    instrument_type: str = "EQUITY"

    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))


@dataclass
class MarketDataFilter:
    """Filter criteria for market data queries"""
    symbol: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    exchange: Optional[str] = None
    instrument_type: Optional[str] = None
    min_volume: Optional[int] = None
    max_volume: Optional[int] = None


class MarketDataRepositoryImpl(BaseRepository[MarketData, str]):
    """
    Market Data Repository Implementation
    Provides data access layer for market data operations
    """

    TABLE_NAME = "market_data"
    TABLE_SCHEMA = {
        "symbol": "VARCHAR",
        "timestamp": "TIMESTAMP",
        "open_price": "DOUBLE",
        "high_price": "DOUBLE",
        "low_price": "DOUBLE",
        "close_price": "DOUBLE",
        "volume": "BIGINT",
        "exchange": "VARCHAR",
        "instrument_type": "VARCHAR"
    }

    def __init__(self, database_path: str):
        super().__init__(database_path)
        self.adapter = get_duckdb_adapter(database_path)
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Ensure market data table exists"""
        import asyncio
        try:
            # Run sync in async context
            asyncio.create_task(self.adapter.create_table(self.TABLE_NAME, self.TABLE_SCHEMA))
        except Exception as e:
            logger.warning(f"Could not ensure table exists: {e}")

    async def save(self, entity: MarketData) -> RepositoryResult:
        """Save market data entity"""
        try:
            query_builder = QueryBuilder(self.TABLE_NAME)
            insert_query, params = query_builder.build_insert({
                'symbol': entity.symbol,
                'timestamp': entity.timestamp.isoformat(),
                'open_price': entity.open_price,
                'high_price': entity.high_price,
                'low_price': entity.low_price,
                'close_price': entity.close_price,
                'volume': entity.volume,
                'exchange': entity.exchange,
                'instrument_type': entity.instrument_type
            })

            affected_rows = await self.adapter.execute_update(insert_query, params)

            self._log_operation("save", entity.symbol, {
                'timestamp': entity.timestamp.isoformat(),
                'price': entity.close_price
            })

            return RepositoryResult(
                success=True,
                data={'affected_rows': affected_rows, 'entity_id': entity.symbol}
            )

        except Exception as e:
            return self._handle_error("save", e, entity.symbol)

    async def save_batch(self, entities: List[MarketData]) -> RepositoryResult:
        """Save multiple market data entities efficiently"""
        try:
            if not entities:
                return RepositoryResult(success=True, data={'affected_rows': 0})

            queries = []
            for entity in entities:
                query_builder = QueryBuilder(self.TABLE_NAME)
                insert_query, params = query_builder.build_insert({
                    'symbol': entity.symbol,
                    'timestamp': entity.timestamp.isoformat(),
                    'open_price': entity.open_price,
                    'high_price': entity.high_price,
                    'low_price': entity.low_price,
                    'close_price': entity.close_price,
                    'volume': entity.volume,
                    'exchange': entity.exchange,
                    'instrument_type': entity.instrument_type
                })
                queries.append({'query': insert_query, 'parameters': params})

            affected_rows_list = await self.adapter.execute_batch(queries)

            self._log_operation("save_batch", None, {
                'batch_size': len(entities),
                'total_affected': sum(affected_rows_list)
            })

            return RepositoryResult(
                success=True,
                data={
                    'affected_rows': sum(affected_rows_list),
                    'batch_size': len(entities)
                }
            )

        except Exception as e:
            return self._handle_error("save_batch", e)

    async def find_by_id(self, entity_id: str) -> RepositoryResult:
        """Find latest market data by symbol"""
        try:
            query_builder = QueryBuilder(self.TABLE_NAME)
            query_builder.where("symbol = :symbol", symbol=entity_id)
            query_builder.order_by("timestamp", desc=True)
            query_builder.limit(1)

            select_query, params = query_builder.build_select()
            result = await self.adapter.execute_query(select_query, params)

            if result:
                entity = self._row_to_entity(result[0])
                self._log_operation("find_by_id", entity_id)
                return RepositoryResult(success=True, data=entity)
            else:
                return RepositoryResult(success=True, data=None)

        except Exception as e:
            return self._handle_error("find_by_id", e, entity_id)

    async def find_all(self, limit: int = 100, offset: int = 0) -> RepositoryResult:
        """Find all market data with pagination"""
        try:
            query_builder = QueryBuilder(self.TABLE_NAME)
            query_builder.order_by("timestamp", desc=True)
            query_builder.limit(limit)
            query_builder.offset(offset)

            select_query, params = query_builder.build_select()
            result = await self.adapter.execute_query(select_query, params)

            entities = [self._row_to_entity(row) for row in result]

            self._log_operation("find_all", None, {
                'limit': limit,
                'offset': offset,
                'result_count': len(entities)
            })

            return RepositoryResult(success=True, data=entities)

        except Exception as e:
            return self._handle_error("find_all", e)

    async def find_by_symbol_and_date_range(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        limit: int = 1000
    ) -> RepositoryResult:
        """Find market data for symbol within date range"""
        try:
            query_builder = QueryBuilder(self.TABLE_NAME)
            query_builder.where("symbol = :symbol", symbol=symbol)
            query_builder.where("timestamp >= :start_date", start_date=start_date.isoformat())
            query_builder.where("timestamp <= :end_date", end_date=end_date.isoformat())
            query_builder.order_by("timestamp", desc=False)
            query_builder.limit(limit)

            select_query, params = query_builder.build_select()
            result = await self.adapter.execute_query(select_query, params)

            entities = [self._row_to_entity(row) for row in result]

            self._log_operation("find_by_symbol_and_date_range", symbol, {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'result_count': len(entities)
            })

            return RepositoryResult(success=True, data=entities)

        except Exception as e:
            return self._handle_error("find_by_symbol_and_date_range", e, symbol)

    async def find_by_filter(self, filter_criteria: MarketDataFilter, limit: int = 1000) -> RepositoryResult:
        """Find market data by filter criteria"""
        try:
            query_builder = QueryBuilder(self.TABLE_NAME)

            if filter_criteria.symbol:
                query_builder.where("symbol = :symbol", symbol=filter_criteria.symbol)
            if filter_criteria.start_date:
                query_builder.where("timestamp >= :start_date", start_date=filter_criteria.start_date.isoformat())
            if filter_criteria.end_date:
                query_builder.where("timestamp <= :end_date", end_date=filter_criteria.end_date.isoformat())
            if filter_criteria.exchange:
                query_builder.where("exchange = :exchange", exchange=filter_criteria.exchange)
            if filter_criteria.instrument_type:
                query_builder.where("instrument_type = :instrument_type", instrument_type=filter_criteria.instrument_type)
            if filter_criteria.min_volume:
                query_builder.where("volume >= :min_volume", min_volume=filter_criteria.min_volume)
            if filter_criteria.max_volume:
                query_builder.where("volume <= :max_volume", max_volume=filter_criteria.max_volume)

            query_builder.order_by("timestamp", desc=True)
            query_builder.limit(limit)

            select_query, params = query_builder.build_select()
            result = await self.adapter.execute_query(select_query, params)

            entities = [self._row_to_entity(row) for row in result]

            self._log_operation("find_by_filter", None, {
                'filter_criteria': str(filter_criteria),
                'result_count': len(entities)
            })

            return RepositoryResult(success=True, data=entities)

        except Exception as e:
            return self._handle_error("find_by_filter", e)

    async def get_latest_price(self, symbol: str) -> RepositoryResult:
        """Get latest price for symbol"""
        try:
            query_builder = QueryBuilder(self.TABLE_NAME)
            query_builder.select("close_price", "timestamp")
            query_builder.where("symbol = :symbol", symbol=symbol)
            query_builder.order_by("timestamp", desc=True)
            query_builder.limit(1)

            select_query, params = query_builder.build_select()
            result = await self.adapter.execute_query(select_query, params)

            if result:
                latest_data = result[0]
                self._log_operation("get_latest_price", symbol, {
                    'price': latest_data['close_price'],
                    'timestamp': latest_data['timestamp']
                })
                return RepositoryResult(success=True, data=latest_data)
            else:
                return RepositoryResult(success=True, data=None)

        except Exception as e:
            return self._handle_error("get_latest_price", e, symbol)

    async def get_volume_analysis(self, symbol: str, days: int = 30) -> RepositoryResult:
        """Get volume analysis for symbol over specified days"""
        try:
            start_date = datetime.now() - timedelta(days=days)

            query = f"""
            SELECT
                AVG(volume) as avg_volume,
                MAX(volume) as max_volume,
                MIN(volume) as min_volume,
                SUM(volume) as total_volume,
                COUNT(*) as trading_days
            FROM {self.TABLE_NAME}
            WHERE symbol = ?
                AND timestamp >= ?
                AND volume > 0
            """

            params = [symbol, start_date.isoformat()]
            result = await self.adapter.execute_query(query, params)

            if result:
                analysis = result[0]
                self._log_operation("get_volume_analysis", symbol, {
                    'days': days,
                    'avg_volume': analysis['avg_volume']
                })
                return RepositoryResult(success=True, data=analysis)
            else:
                return RepositoryResult(success=True, data=None)

        except Exception as e:
            return self._handle_error("get_volume_analysis", e, symbol)

    async def delete_by_id(self, entity_id: str) -> RepositoryResult:
        """Delete market data by symbol (not recommended for time series data)"""
        try:
            query = f"DELETE FROM {self.TABLE_NAME} WHERE symbol = ?"
            affected_rows = await self.adapter.execute_update(query, [entity_id])

            self._log_operation("delete_by_id", entity_id, {'affected_rows': affected_rows})
            return RepositoryResult(success=True, data={'affected_rows': affected_rows})

        except Exception as e:
            return self._handle_error("delete_by_id", e, entity_id)

    async def exists_by_id(self, entity_id: str) -> bool:
        """Check if symbol has any market data"""
        try:
            query_builder = QueryBuilder(self.TABLE_NAME)
            query_builder.select("COUNT(*) as count")
            query_builder.where("symbol = :symbol", symbol=entity_id)

            count_query, params = query_builder.build_count()
            result = await self.adapter.execute_query(count_query, params)

            return result and result[0]['count'] > 0

        except Exception as e:
            logger.warning(f"Error checking existence for {entity_id}: {e}")
            return False

    async def count(self) -> int:
        """Count total market data records"""
        try:
            query_builder = QueryBuilder(self.TABLE_NAME)
            count_query, params = query_builder.build_count()
            result = await self.adapter.execute_query(count_query, params)

            return result[0]['count'] if result else 0

        except Exception as e:
            logger.warning(f"Error counting records: {e}")
            return 0

    async def find_by_criteria(self, criteria: dict, limit: int = 100, offset: int = 0) -> RepositoryResult:
        """Find by custom criteria"""
        try:
            query_builder = QueryBuilder(self.TABLE_NAME)

            # Build WHERE conditions from criteria
            for key, value in criteria.items():
                if key in self.TABLE_SCHEMA:
                    query_builder.where(f"{key} = :{key}", **{key: value})

            query_builder.limit(limit)
            query_builder.offset(offset)
            query_builder.order_by("timestamp", desc=True)

            select_query, params = query_builder.build_select()
            result = await self.adapter.execute_query(select_query, params)

            entities = [self._row_to_entity(row) for row in result]

            return RepositoryResult(success=True, data=entities)

        except Exception as e:
            return self._handle_error("find_by_criteria", e)

    def _row_to_entity(self, row: Dict[str, Any]) -> MarketData:
        """Convert database row to MarketData entity"""
        return MarketData(
            symbol=row['symbol'],
            timestamp=row['timestamp'],
            open_price=row['open_price'],
            high_price=row['high_price'],
            low_price=row['low_price'],
            close_price=row['close_price'],
            volume=row['volume'],
            exchange=row.get('exchange', 'NSE'),
            instrument_type=row.get('instrument_type', 'EQUITY')
        )

    async def get_symbols_list(self) -> RepositoryResult:
        """Get list of all available symbols"""
        try:
            query = f"SELECT DISTINCT symbol FROM {self.TABLE_NAME} ORDER BY symbol"
            result = await self.adapter.execute_query(query)

            symbols = [row['symbol'] for row in result]

            self._log_operation("get_symbols_list", None, {
                'symbol_count': len(symbols)
            })

            return RepositoryResult(success=True, data=symbols)

        except Exception as e:
            return self._handle_error("get_symbols_list", e)

    async def get_date_range(self, symbol: Optional[str] = None) -> RepositoryResult:
        """Get date range for symbol or all data"""
        try:
            query_builder = QueryBuilder(self.TABLE_NAME)
            query_builder.select("MIN(timestamp) as start_date", "MAX(timestamp) as end_date")

            if symbol:
                query_builder.where("symbol = :symbol", symbol=symbol)

            select_query, params = query_builder.build_select()
            result = await self.adapter.execute_query(select_query, params)

            if result and result[0]['start_date']:
                date_range = {
                    'start_date': result[0]['start_date'],
                    'end_date': result[0]['end_date']
                }
                return RepositoryResult(success=True, data=date_range)
            else:
                return RepositoryResult(success=True, data=None)

        except Exception as e:
            return self._handle_error("get_date_range", e, symbol)
