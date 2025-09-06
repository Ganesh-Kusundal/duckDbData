"""Domain entities for trading symbols."""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class Symbol:
    """Trading symbol entity."""

    symbol: str
    name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    exchange: str = "NSE"
    first_date: Optional[date] = None
    last_date: Optional[date] = None
    total_records: int = 0

    def __post_init__(self):
        """Validate entity after initialization."""
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if not self.exchange:
            raise ValueError("Exchange cannot be empty")
        if self.first_date and self.last_date and self.first_date > self.last_date:
            raise ValueError("First date cannot be after last date")
        if self.total_records < 0:
            raise ValueError("Total records cannot be negative")

    @property
    def is_active(self) -> bool:
        """Check if the symbol is currently active."""
        if not self.last_date:
            return True
        return self.last_date >= date.today()

    @property
    def has_data(self) -> bool:
        """Check if the symbol has any data."""
        return self.total_records > 0

    @property
    def data_completeness(self) -> float:
        """Calculate data completeness ratio."""
        if not self.first_date or not self.last_date:
            return 0.0

        expected_days = (self.last_date - self.first_date).days + 1
        if expected_days <= 0:
            return 0.0

        return min(1.0, self.total_records / expected_days)


@dataclass(frozen=True)
class SymbolInfo:
    """Additional information about a symbol."""

    symbol: str
    lot_size: int = 1
    tick_size: float = 0.01
    price_band: tuple[float, float] = (0.0, 0.0)  # (lower, upper) percentage
    is_index: bool = False
    is_future: bool = False
    is_option: bool = False
    expiry_date: Optional[date] = None
    strike_price: Optional[float] = None

    def __post_init__(self):
        """Validate entity after initialization."""
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if self.lot_size <= 0:
            raise ValueError("Lot size must be positive")
        if self.tick_size <= 0:
            raise ValueError("Tick size must be positive")
        if self.price_band[0] > self.price_band[1]:
            raise ValueError("Lower price band cannot be higher than upper")

    @property
    def is_derivative(self) -> bool:
        """Check if this is a derivative instrument."""
        return self.is_future or self.is_option

    @property
    def is_expired(self) -> bool:
        """Check if the derivative is expired."""
        if not self.expiry_date:
            return False
        return self.expiry_date < date.today()
