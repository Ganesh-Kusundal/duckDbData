"""Test domain entities."""

import pytest
from datetime import datetime, date
from decimal import Decimal

from duckdb_financial_infra.domain.entities.market_data import MarketData, OHLCV
from duckdb_financial_infra.domain.entities.symbol import Symbol
from duckdb_financial_infra.domain.entities.scanner import (
    TradingSignal, SignalType, SignalStrength,
    ScannerResult
)
from duckdb_financial_infra.domain.entities.trading import (
    Order, OrderType, OrderSide, OrderStatus,
    Position, PositionType,
    Account, MarketDepth
)


class TestMarketDataEntity:
    """Test market data domain entity."""

    def test_valid_market_data_creation(self):
        """Test creating valid market data entity."""
        ohlcv = OHLCV(
            open=Decimal('100.50'),
            high=Decimal('105.25'),
            low=Decimal('99.75'),
            close=Decimal('104.00'),
            volume=10000
        )

        market_data = MarketData(
            symbol='TEST',
            timestamp=datetime.now(),
            timeframe='1D',
            ohlcv=ohlcv,
            date_partition=date.today()
        )

        assert market_data.symbol == 'TEST'
        assert market_data.timeframe == '1D'
        assert market_data.is_valid
        assert market_data.ohlcv.close == Decimal('104.00')

    def test_invalid_market_data(self):
        """Test market data validation."""
        ohlcv = OHLCV(
            open=Decimal('-100.00'),  # Invalid negative price
            high=Decimal('105.25'),
            low=Decimal('99.75'),
            close=Decimal('104.00'),
            volume=10000
        )

        with pytest.raises(ValueError):
            MarketData(
                symbol='TEST',
                timestamp=datetime.now(),
                timeframe='1D',
                ohlcv=ohlcv,
                date_partition=date.today()
            )

    def test_ohlcv_calculations(self):
        """Test OHLCV calculations."""
        ohlcv = OHLCV(
            open=Decimal('100.00'),
            high=Decimal('110.00'),
            low=Decimal('95.00'),
            close=Decimal('105.00'),
            volume=5000
        )

        assert ohlcv.price_range == Decimal('15.00')
        assert ohlcv.midpoint == Decimal('102.50')


class TestSymbolEntity:
    """Test symbol domain entity."""

    def test_valid_symbol_creation(self):
        """Test creating valid symbol entity."""
        symbol = Symbol(
            symbol='RELIANCE',
            name='Reliance Industries',
            sector='Energy',
            industry='Oil & Gas',
            exchange='NSE'
        )

        assert symbol.symbol == 'RELIANCE'
        assert symbol.name == 'Reliance Industries'
        assert symbol.sector == 'Energy'
        assert symbol.is_active

    def test_symbol_with_last_date(self):
        """Test symbol with last trading date."""
        past_date = date(2020, 1, 1)
        symbol = Symbol(
            symbol='OLD_STOCK',
            name='Old Stock',
            sector='Finance',
            last_date=past_date
        )

        assert not symbol.is_active


class TestScannerEntities:
    """Test scanner domain entities."""

    def test_trading_signal_creation(self):
        """Test trading signal creation."""
        signal = TradingSignal(
            symbol='TEST',
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            timestamp=datetime.now(),
            price=Decimal('100.00'),
            confidence=0.85,
            scanner_name='test_scanner'
        )

        assert signal.symbol == 'TEST'
        assert signal.signal_type == SignalType.BUY
        assert signal.is_buy_signal
        assert signal.signal_score > 0

    def test_scanner_result_creation(self):
        """Test scanner result creation."""
        signals = [
            TradingSignal(
                symbol='TEST',
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                timestamp=datetime.now(),
                price=Decimal('100.00'),
                confidence=0.8,
                scanner_name='test_scanner'
            )
        ]

        result = ScannerResult(
            scanner_name='test_scanner',
            symbol='TEST',
            timestamp=datetime.now(),
            signals=signals,
            metadata={'test': 'data'},
            execution_time_ms=150.5
        )

        assert result.scanner_name == 'test_scanner'
        assert result.has_signals
        assert len(result.buy_signals) == 1


class TestTradingEntities:
    """Test trading domain entities."""

    def test_order_creation(self):
        """Test order creation."""
        order = Order(
            order_id='ORD123',
            symbol='TEST',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            price=Decimal('100.00'),
            status=OrderStatus.PENDING,
            timestamp=datetime.now()
        )

        assert order.order_id == 'ORD123'
        assert order.is_buy_order
        assert order.is_active
        assert order.value == Decimal('10000.00')

    def test_position_creation(self):
        """Test position creation."""
        position = Position(
            symbol='TEST',
            position_type=PositionType.LONG,
            quantity=100,
            average_price=Decimal('100.00'),
            current_price=Decimal('105.00'),
            unrealized_pnl=Decimal('500.00'),
            realized_pnl=Decimal('0.00'),
            timestamp=datetime.now()
        )

        assert position.symbol == 'TEST'
        assert position.is_long
        assert position.market_value == Decimal('10500.00')
        assert position.total_pnl == Decimal('500.00')

    def test_account_creation(self):
        """Test account creation."""
        account = Account(
            account_id='ACC123',
            balance=Decimal('100000.00'),
            margin_available=Decimal('50000.00'),
            margin_used=Decimal('20000.00'),
            timestamp=datetime.now()
        )

        assert account.account_id == 'ACC123'
        assert account.total_margin == Decimal('70000.00')
        assert account.margin_utilization == 0.2857  # 20000/70000

    def test_market_depth_creation(self):
        """Test market depth creation."""
        bids = [
            {'price': Decimal('100.00'), 'quantity': 100},
            {'price': Decimal('99.50'), 'quantity': 200}
        ]
        asks = [
            {'price': Decimal('100.50'), 'quantity': 150},
            {'price': Decimal('101.00'), 'quantity': 250}
        ]

        depth = MarketDepth(
            symbol='TEST',
            bids=bids,
            asks=asks,
            timestamp=datetime.now(),
            depth_level=5
        )

        assert depth.symbol == 'TEST'
        assert depth.best_bid['price'] == Decimal('100.00')
        assert depth.best_ask['price'] == Decimal('100.50')
        assert depth.spread == Decimal('0.50')
        assert depth.mid_price == Decimal('100.25')
