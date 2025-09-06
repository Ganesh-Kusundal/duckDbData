"""Domain entities for market data."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class OHLCV(BaseModel):
    """OHLCV (Open, High, Low, Close, Volume) data structure."""

    model_config = ConfigDict(validate_assignment=True)

    open: Decimal = Field(..., ge=0, description="Opening price")
    high: Decimal = Field(..., ge=0, description="Highest price")
    low: Decimal = Field(..., ge=0, description="Lowest price")
    close: Decimal = Field(..., ge=0, description="Closing price")
    volume: int = Field(..., ge=0, description="Trading volume")

    @field_validator('volume')
    @classmethod
    def validate_volume(cls, v):
        """Validate that volume is positive."""
        if v <= 0:
            raise ValueError('volume must be positive')
        return v

    @model_validator(mode='after')
    def validate_price_range(self):
        """Validate that high >= low."""
        if self.low > self.high:
            raise ValueError('low cannot be higher than high')
        return self


@dataclass(frozen=True)
class MarketData:
    """Market data entity representing a single price bar."""

    symbol: str
    timestamp: datetime
    timeframe: str
    ohlcv: OHLCV
    date_partition: str

    def __post_init__(self):
        """Validate entity after initialization."""
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if not self.timeframe:
            raise ValueError("Timeframe cannot be empty")
        if not self.date_partition:
            raise ValueError("Date partition cannot be empty")

    @property
    def is_valid(self) -> bool:
        """Check if the market data is valid."""
        return bool(
            self.symbol and
            self.timestamp and
            self.timeframe and
            self.ohlcv and
            self.date_partition
        )


@dataclass(frozen=True)
class MarketDataBatch:
    """Batch of market data for efficient processing."""

    symbol: str
    timeframe: str
    data: list[MarketData]
    start_date: datetime
    end_date: datetime

    def __post_init__(self):
        """Validate batch after initialization."""
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if not self.timeframe:
            raise ValueError("Timeframe cannot be empty")
        if not self.data:
            raise ValueError("Data cannot be empty")
        if self.start_date > self.end_date:
            raise ValueError("Start date cannot be after end date")

        # Validate that all data has the same symbol
        for item in self.data:
            if item.symbol != self.symbol:
                raise ValueError(f"All data must have symbol '{self.symbol}', found '{item.symbol}'")

    @property
    def record_count(self) -> int:
        """Get the number of records in the batch."""
        return len(self.data)

    @property
    def is_sorted(self) -> bool:
        """Check if data is sorted by timestamp."""
        return all(
            self.data[i].timestamp <= self.data[i + 1].timestamp
            for i in range(len(self.data) - 1)
        )
