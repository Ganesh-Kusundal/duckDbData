"""
Market Data Entity
Represents a single market data record in the domain
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from uuid import uuid4

from ..value_objects.ohlcv import OHLCV


@dataclass
class MarketData:
    """
    Market Data Entity - Represents a single market data record

    This is an entity in Domain-Driven Design terms, meaning:
    - Has an identity (symbol + timestamp + timeframe)
    - Mutable state
    - Business logic and validation
    - Can track its own lifecycle
    """

    symbol: str
    timestamp: str  # ISO format timestamp
    timeframe: str  # e.g., "1D", "1H", "5m"
    ohlcv: OHLCV
    date_partition: str  # Date string for partitioning

    def __post_init__(self):
        """Validate market data after initialization"""
        self._validate_symbol()
        self._validate_timestamp()
        self._validate_timeframe()
        self._validate_date_partition()

    def _validate_symbol(self):
        """Validate trading symbol"""
        if not self.symbol or not isinstance(self.symbol, str):
            raise ValueError("Symbol must be a non-empty string")

        # Remove any whitespace and convert to uppercase
        self.symbol = self.symbol.strip().upper()

        if len(self.symbol) < 1 or len(self.symbol) > 10:
            raise ValueError("Symbol must be between 1 and 10 characters")

    def _validate_timestamp(self):
        """Validate timestamp format"""
        if not self.timestamp:
            raise ValueError("Timestamp is required")

        try:
            # Handle both string and datetime inputs
            if isinstance(self.timestamp, datetime):
                parsed = self.timestamp
            else:
                # Try to parse the timestamp to validate format
                parsed = datetime.fromisoformat(str(self.timestamp).replace('Z', '+00:00'))

            # Ensure it's not in the future (with some tolerance)
            now = datetime.now(parsed.tzinfo) if parsed.tzinfo else datetime.now()
            if parsed > now + timedelta(hours=1):
                raise ValueError("Timestamp cannot be in the future")
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid timestamp format: {e}")

    def _validate_timeframe(self):
        """Validate timeframe format"""
        if not self.timeframe:
            raise ValueError("Timeframe is required")

        # Common timeframe formats
        valid_timeframes = [
            '1m', '5m', '15m', '30m', '1H', '4H', '1D', '1W', '1M'
        ]

        if self.timeframe not in valid_timeframes:
            raise ValueError(f"Invalid timeframe. Must be one of: {valid_timeframes}")

    def _validate_date_partition(self):
        """Validate date partition format"""
        if not self.date_partition:
            raise ValueError("Date partition cannot be empty")

        # Basic date format validation (YYYY-MM-DD)
        if len(self.date_partition) != 10 or self.date_partition[4] != '-' or self.date_partition[7] != '-':
            raise ValueError("Date partition must be in YYYY-MM-DD format")

    @property
    def entity_id(self) -> str:
        """Unique identifier for this market data record"""
        timestamp_str = self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp)
        return f"{self.symbol}_{timestamp_str}_{self.timeframe}"

    @property
    def parsed_timestamp(self) -> datetime:
        """Get parsed timestamp as datetime object"""
        if isinstance(self.timestamp, datetime):
            return self.timestamp
        else:
            return datetime.fromisoformat(str(self.timestamp).replace('Z', '+00:00'))

    @property
    def is_intraday(self) -> bool:
        """Check if this is intraday data"""
        return self.timeframe in ['1m', '5m', '15m', '30m', '1H', '4H']

    @property
    def is_daily(self) -> bool:
        """Check if this is daily data"""
        return self.timeframe == '1D'

    def update_ohlcv(self, new_ohlcv: OHLCV) -> 'MarketData':
        """
        Create a new MarketData with updated OHLCV
        Since this is an entity, we return a new instance rather than mutating
        """
        return MarketData(
            symbol=self.symbol,
            timestamp=self.timestamp,
            timeframe=self.timeframe,
            ohlcv=new_ohlcv,
            date_partition=self.date_partition
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Convert OHLCV to dict as well
        data['ohlcv'] = self.ohlcv.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MarketData':
        """Create MarketData from dictionary"""
        # Convert OHLCV dict back to object
        ohlcv_data = data.pop('ohlcv')
        ohlcv = OHLCV.from_dict(ohlcv_data)
        return cls(ohlcv=ohlcv, **data)

    def __eq__(self, other) -> bool:
        """Equality based on entity identity"""
        if not isinstance(other, MarketData):
            return False
        return self.entity_id == other.entity_id

    def __hash__(self) -> int:
        """Hash based on entity identity"""
        return hash(self.entity_id)

    def __str__(self) -> str:
        """String representation"""
        return f"MarketData({self.symbol} {self.timeframe} {self.timestamp})"

    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"MarketData(symbol='{self.symbol}', timeframe='{self.timeframe}', "
                f"timestamp='{self.timestamp}', ohlcv={self.ohlcv})")


@dataclass
class MarketDataBatch:
    """
    Market Data Batch - Represents a collection of market data records

    Used for bulk operations and data transfer between bounded contexts
    """

    symbol: str
    timeframe: str
    data: list[MarketData]
    start_date: str  # ISO format
    end_date: str    # ISO format

    def __post_init__(self):
        """Validate batch data"""
        self._validate_batch_data()

    def _validate_batch_data(self):
        """Validate all data in the batch"""
        if not self.data:
            raise ValueError("Batch data cannot be empty")

        if len(self.data) > 10000:  # Reasonable limit
            raise ValueError("Batch size cannot exceed 10,000 records")

        # Validate date range
        if self.start_date > self.end_date:
            raise ValueError("Start date cannot be after end date")

        # Validate all records belong to the same symbol and timeframe
        for record in self.data:
            if record.symbol != self.symbol:
                raise ValueError(f"Batch contains inconsistent symbol: {record.symbol}")
            if record.timeframe != self.timeframe:
                raise ValueError(f"Batch contains inconsistent timeframe: {record.timeframe}")

        # Sort data by timestamp
        self.data.sort(key=lambda x: x.parsed_timestamp)

    @property
    def record_count(self) -> int:
        """Number of records in the batch"""
        return len(self.data)

    @property
    def total_volume(self) -> int:
        """Total volume across all records"""
        return sum(record.ohlcv.volume for record in self.data)

    @property
    def average_price(self) -> float:
        """Average closing price across the batch"""
        if not self.data:
            return 0.0
        return sum(record.ohlcv.close for record in self.data) / len(self.data)

    @property
    def price_range(self) -> tuple[float, float]:
        """Min and max prices in the batch"""
        if not self.data:
            return (0.0, 0.0)

        prices = [record.ohlcv.close for record in self.data]
        return (min(prices), max(prices))

    def split_by_size(self, chunk_size: int) -> list['MarketDataBatch']:
        """Split batch into smaller chunks"""
        chunks = []
        for i in range(0, len(self.data), chunk_size):
            chunk_data = self.data[i:i + chunk_size]
            chunk = MarketDataBatch(
                symbol=self.symbol,
                timeframe=self.timeframe,
                data=chunk_data,
                start_date=chunk_data[0].timestamp,
                end_date=chunk_data[-1].timestamp
            )
            chunks.append(chunk)
        return chunks

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Convert MarketData objects to dicts
        data['data'] = [record.to_dict() for record in self.data]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MarketDataBatch':
        """Create MarketDataBatch from dictionary"""
        # Convert dicts back to MarketData objects
        market_data_list = [MarketData.from_dict(record) for record in data['data']]
        data_copy = data.copy()
        data_copy['data'] = market_data_list
        return cls(**data_copy)

    def __str__(self) -> str:
        """String representation"""
        return f"MarketDataBatch({self.symbol} {self.timeframe}: {self.record_count} records)"

    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"MarketDataBatch(symbol='{self.symbol}', timeframe='{self.timeframe}', "
                f"records={self.record_count}, period='{self.start_date}' to '{self.end_date}')")
