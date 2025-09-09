"""
Top-3 Concentrate & Pyramid Strategy
==================================

Implements the core intraday strategy:
1. 09:15-09:50 Warm-up & Top-3 Selection
2. Entry Triggers (EMA 9/30, Range Break)
3. Leader Consolidation & Exit Others
4. Pyramiding with TSL
5. 20-Minute Rotation
6. EOD Guardrails
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import logging

from ..domain.models import (
    Bar, Signal, SignalType, OrderIntent, Side, OrderType,
    Position, LeaderScore, TSLMode, StopLevel
)
from ..ports.analytics import AnalyticsPort
from ..ports.broker import BrokerPort
from ..ports.repository import RepositoryPort
from ..domain.nse_utils import nse_utils

logger = logging.getLogger(__name__)


class IStrategy(ABC):
    """Strategy interface - pure functions for decision logic"""

    @abstractmethod
    def on_bar(self, bar: Bar, context: Dict[str, Any]) -> List[Signal]:
        """Process new bar and generate signals"""
        pass

    @abstractmethod
    def on_timer(self, current_time: time, context: Dict[str, Any]) -> List[Signal]:
        """Process timer events (rotation, EOD, etc.)"""
        pass

    @abstractmethod
    def on_fill(self, symbol: str, fill_price: Decimal, fill_qty: int,
                context: Dict[str, Any]) -> List[Signal]:
        """Process order fills"""
        pass


class Top3ConcentratePyramidStrategy(IStrategy):
    """Top-3 Concentrate & Pyramid intraday strategy implementation"""

    def __init__(self, config: Dict[str, Any], analytics_port: AnalyticsPort,
                 broker_port: BrokerPort, repository_port: RepositoryPort):
        self.config = config
        self.analytics = analytics_port
        self.broker = broker_port
        self.repository = repository_port

        # Strategy state
        self.warmup_complete = False
        self.selected_symbols: List[str] = []
        self.positions: Dict[str, Position] = {}
        self.entry_times: Dict[str, time] = {}
        self.leader_symbol: Optional[str] = None
        self.rotation_timer_start: Optional[datetime] = None

        # Trading parameters
        self.warmup_start = time.fromisoformat(config['time']['warmup_start'])
        self.shortlist_cutoff = time.fromisoformat(config['time']['shortlist_cutoff'])
        self.eod_flat = time.fromisoformat(config['time']['eod_flat'])

    def on_bar(self, bar: Bar, context: Dict[str, Any]) -> List[Signal]:
        """Process new bar and generate signals"""
        signals = []
        current_time = bar.timestamp.time()

        # Phase 1: Warm-up (09:15-09:50)
        if not self.warmup_complete and current_time >= self.shortlist_cutoff:
            signals.extend(self._complete_warmup(bar.timestamp.date()))
            return signals

        # Skip if warmup not complete or not in selected symbols
        if not self.warmup_complete or bar.symbol not in self.selected_symbols:
            return signals

        # Phase 2: Entry Triggers
        if bar.symbol not in self.positions:
            entry_signals = self._check_entry_triggers(bar, context)
            signals.extend(entry_signals)

        # Phase 3: Leader Management
        elif self.leader_symbol and bar.symbol != self.leader_symbol:
            exit_signals = self._check_exit_signals(bar, context)
            signals.extend(exit_signals)

        # Phase 4: Pyramiding & TSL
        elif bar.symbol in self.positions:
            pyramid_signals = self._check_pyramid_signals(bar, context)
            signals.extend(pyramid_signals)

        return signals

    def on_timer(self, current_time: time, context: Dict[str, Any]) -> List[Signal]:
        """Process timer events"""
        signals = []

        # EOD Flat
        if current_time >= self.eod_flat:
            signals.extend(self._eod_flat())
            return signals

        # 20-Minute Rotation Check
        if self.rotation_timer_start:
            elapsed = datetime.now() - self.rotation_timer_start
            if elapsed.seconds >= self.config['rotation']['check_after_minutes'] * 60:
                signals.extend(self._check_rotation())
                self.rotation_timer_start = None

        return signals

    def on_fill(self, symbol: str, fill_price: Decimal, fill_qty: int,
                context: Dict[str, Any]) -> List[Signal]:
        """Process order fills"""
        signals = []

        if symbol not in self.positions:
            # New position
            position = Position(
                symbol=symbol,
                quantity=fill_qty,
                avg_cost=fill_price,
                current_price=fill_price,
                entry_timestamp=datetime.now()
            )
            self.positions[symbol] = position
            self.entry_times[symbol] = datetime.now().time()

            # Set initial stop
            signals.extend(self._set_initial_stop(position))

        else:
            # Update existing position
            position = self.positions[symbol]
            total_qty = position.quantity + fill_qty
            total_cost = (position.avg_cost * position.quantity) + (fill_price * fill_qty)
            position.avg_cost = total_cost / total_qty
            position.quantity = total_qty
            position.ladder_stage += 1

        return signals

    def _complete_warmup(self, trading_date: date) -> List[Signal]:
        """Complete warmup and select top-3 symbols"""
        signals = []

        try:
            # Get scores from analytics
            scores = self.analytics.compute_warmup_features(
                trading_date, [], self.warmup_start, self.shortlist_cutoff
            )

            # Sort by score and select top 3
            sorted_scores = sorted(scores.values(), key=lambda x: x.total_score, reverse=True)
            self.selected_symbols = [score.symbol for score in sorted_scores[:3]]

            logger.info(f"Selected top-3 symbols: {self.selected_symbols}")
            self.warmup_complete = True

        except Exception as e:
            logger.error(f"Warmup completion failed: {e}")

        return signals

    def _check_entry_triggers(self, bar: Bar, context: Dict[str, Any]) -> List[Signal]:
        """Check entry trigger conditions"""
        signals = []

        # Get technical indicators
        ema_9 = self.analytics.calculate_ema(bar.symbol, 9, bar.timestamp.date(), "1m")
        ema_30 = self.analytics.calculate_ema(bar.symbol, 30, bar.timestamp.date(), "1m")

        if not ema_9 or not ema_30:
            return signals

        # EMA 9/30 Momentum Trigger
        ema_trigger = (ema_9 > ema_30 and
                      bar.close > ema_9 and
                      (bar.close - bar.open) / (bar.high - bar.low) > self.config['entry']['ema_9_30']['body_top_pct'] / 100)

        # Range Break Trigger
        range_trigger = self._check_range_break(bar)

        if ema_trigger or range_trigger:
            signals.append(Signal(
                symbol=bar.symbol,
                signal_type=SignalType.ENTRY,
                timestamp=bar.timestamp,
                price=bar.close,
                quantity=self._calculate_position_size(bar.close, bar.symbol),
                reason=f"EMA9/30: {ema_trigger}, Range Break: {range_trigger}",
                confidence_score=0.8 if (ema_trigger and range_trigger) else 0.6
            ))

        return signals

    def _check_range_break(self, bar: Bar) -> bool:
        """Check range break condition"""
        # Simplified range break logic - can be enhanced
        return bar.volume > bar.volume * self.config['entry']['range_break']['vol_mult']

    def _calculate_position_size(self, price: Decimal, symbol: str) -> int:
        """Calculate position size based on risk management"""
        # Get ATR for risk calculation
        atr = self.analytics.calculate_atr(symbol, date.today(), 14, "5m")
        if not atr:
            atr = price * Decimal('0.02')  # Fallback 2% range

        # Risk amount per trade
        risk_pct = Decimal(str(self.config['risk']['per_trade_r_pct'])) / 100
        stop_distance = atr * Decimal(str(self.config['risk']['k_atr_initial']))

        # Position size = (Capital * Risk%) / Stop Distance
        capital = Decimal('100000')  # Placeholder - should come from account state
        risk_amount = capital * risk_pct
        position_value = risk_amount / stop_distance

        quantity = int(position_value / price)
        return nse_utils.validate_quantity(quantity)

    def _check_pyramid_signals(self, bar: Bar, context: Dict[str, Any]) -> List[Signal]:
        """Check pyramiding conditions"""
        signals = []

        if bar.symbol not in self.positions:
            return signals

        position = self.positions[bar.symbol]
        entry_price = position.avg_cost
        current_price = bar.close

        # Calculate current R multiple
        r_multiple = float((current_price - entry_price) / (entry_price - position.stops[0].stop_price)) if position.stops else 0

        # Check pyramid levels
        pyramid_levels = self.config['pyramiding']['add_levels_r']
        add_sizes = self.config['pyramiding']['add_sizes_frac']

        for i, level in enumerate(pyramid_levels):
            if r_multiple >= level and position.ladder_stage == i:
                # Add to position
                add_qty = int(position.quantity * add_sizes[i])
                signals.append(Signal(
                    symbol=bar.symbol,
                    signal_type=SignalType.ADD_POSITION,
                    timestamp=bar.timestamp,
                    price=bar.close,
                    quantity=add_qty,
                    reason=f"Pyramid at {level}R",
                    confidence_score=0.7
                ))
                break

        return signals

    def _check_exit_signals(self, bar: Bar, context: Dict[str, Any]) -> List[Signal]:
        """Check exit conditions for non-leader positions"""
        signals = []

        if bar.symbol not in self.positions:
            return signals

        # Exit if not leader and we've consolidated
        if self.leader_symbol and bar.symbol != self.leader_symbol:
            signals.append(Signal(
                symbol=bar.symbol,
                signal_type=SignalType.EXIT,
                timestamp=bar.timestamp,
                price=bar.close,
                quantity=-self.positions[bar.symbol].quantity,  # Full exit
                reason="Non-leader exit - concentration phase",
                confidence_score=0.9
            ))

        return signals

    def _set_initial_stop(self, position: Position) -> List[Signal]:
        """Set initial stop loss"""
        atr = self.analytics.calculate_atr(position.symbol, date.today(), 14, "5m")
        if not atr:
            return []

        stop_price = position.avg_cost - (atr * Decimal(str(self.config['risk']['k_atr_initial'])))

        return [Signal(
            symbol=position.symbol,
            signal_type=SignalType.STOP_LOSS,
            timestamp=datetime.now(),
            price=stop_price,
            quantity=0,  # Stop signal, not order
            reason="Initial ATR stop",
            confidence_score=0.95
        )]

    def _check_rotation(self) -> List[Signal]:
        """Check if rotation is needed"""
        signals = []

        # Check if any position has achieved minimum R target
        min_r = self.config['rotation']['min_leader_r']
        has_leader = any(
            position.quantity > 0 for position in self.positions.values()
            # Add R calculation logic here
        )

        if not has_leader:
            # Flatten all positions and restart
            for symbol, position in self.positions.items():
                if position.quantity > 0:
                    signals.append(Signal(
                        symbol=symbol,
                        signal_type=SignalType.EXIT,
                        timestamp=datetime.now(),
                        price=Decimal('0'),  # Market exit
                        quantity=-position.quantity,
                        reason="20m rotation - no leader",
                        confidence_score=0.8
                    ))

            # Reset for new cycle
            self.positions.clear()
            self.selected_symbols.clear()
            self.leader_symbol = None

        return signals

    def _eod_flat(self) -> List[Signal]:
        """End of day flat all positions"""
        signals = []

        for symbol, position in self.positions.items():
            if position.quantity != 0:
                signals.append(Signal(
                    symbol=symbol,
                    signal_type=SignalType.EXIT,
                    timestamp=datetime.now(),
                    price=Decimal('0'),  # Market exit
                    quantity=-position.quantity,
                    reason="EOD flat",
                    confidence_score=1.0
                ))

        return signals
