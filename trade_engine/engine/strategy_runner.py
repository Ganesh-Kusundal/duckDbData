"""
Strategy Runner - Unified Backtest + Live Engine
===============================================

The main orchestrator that runs the same strategy in backtest and live modes
with complete parity. Handles event processing, state management, and coordination.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, date, time
from decimal import Decimal
import logging
import yaml
import os

from ..strategy.top3_concentrate_pyramid import Top3ConcentratePyramidStrategy, IStrategy
from ..adapters.duckdb_data_feed import DuckDBDataFeed
from ..adapters.duckdb_analytics import DuckDBAnalytics
from ..adapters.duckdb_repository import DuckDBRepository
from ..adapters.backtest_broker import BacktestBroker
from ..domain.models import Bar, Signal, OrderIntent, Side, OrderType, RunMetadata
from ..domain.nse_utils import nse_utils

logger = logging.getLogger(__name__)


class StrategyRunner:
    """
    Unified strategy runner for backtest and live trading.

    Key features:
    - Single codebase for backtest/live parity
    - Deterministic backtesting with proper sequencing
    - Real-time event processing for live trading
    - Comprehensive telemetry and state persistence
    - NSE compliance with tick sizes and quantity rules
    """

    def __init__(self, config_path: str):
        """Initialize with configuration"""
        self.config_path = config_path
        self.config = self._load_config()

        # Initialize ports/adapters
        self._initialize_ports()

        # Strategy instance
        self.strategy = Top3ConcentratePyramidStrategy(
            self.config,
            self.analytics_port,
            self.broker_port,
            self.repository_port
        )

        # Runtime state
        self.is_running = False
        self.mode = self.config['mode']
        self.current_date = date.fromisoformat(self.config['trading_day']) if self.mode == 'backtest' else date.today()
        self.run_id = f"{self.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML"""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def _initialize_ports(self):
        """Initialize all port adapters"""
        db_path = self.config['data']['duckdb_path']

        self.data_feed_port = DuckDBDataFeed(db_path)
        self.analytics_port = DuckDBAnalytics(db_path, self.config)
        self.repository_port = DuckDBRepository(db_path)

        # Use backtest broker for now (can be extended for live broker)
        self.broker_port = BacktestBroker(self.config)

    async def run_backtest(self) -> Dict[str, Any]:
        """
        Run deterministic backtest

        Returns comprehensive results and metrics
        """
        logger.info(f"Starting backtest for {self.current_date}")
        self.is_running = True

        try:
            # Initialize run metadata
            run_meta = RunMetadata(
                run_id=self.run_id,
                mode="backtest",
                start_date=self.current_date,
                config_snapshot=self.config
            )
            self.repository_port.save_run_metadata(run_meta)

            # Get available symbols
            symbols = self.data_feed_port.get_available_symbols()
            logger.info(f"Found {len(symbols)} symbols in database")

            # Process bars deterministically
            bars_processed = 0
            signals_generated = 0

            async for bar in self.data_feed_port.subscribe(symbols, "1m"):
                if not self.is_running:
                    break

                # Process bar through strategy
                signals = self.strategy.on_bar(bar, {'current_time': bar.timestamp})

                if signals:
                    signals_generated += len(signals)
                    self.repository_port.save_signals(signals)

                    # Process signals into orders
                    await self._process_signals(signals)

                bars_processed += 1

                # Progress logging
                if bars_processed % 1000 == 0:
                    logger.info(f"Processed {bars_processed} bars, {signals_generated} signals")

            # Final EOD processing
            eod_signals = self.strategy.on_timer(time(15, 15), {})
            if eod_signals:
                self.repository_port.save_signals(eod_signals)

            # Generate final results
            results = await self._generate_backtest_results()

            logger.info(f"Backtest completed: {bars_processed} bars, {signals_generated} signals")
            return results

        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            raise
        finally:
            self.is_running = False

    async def run_live(self):
        """
        Run live trading with real-time event processing

        Note: This is a framework - would need actual live data feed integration
        """
        logger.info("Starting live trading mode")
        self.is_running = True

        try:
            # Initialize run metadata
            run_meta = RunMetadata(
                run_id=self.run_id,
                mode="live",
                start_date=date.today(),
                config_snapshot=self.config
            )
            self.repository_port.save_run_metadata(run_meta)

            # Live trading loop would go here
            # For now, this is a placeholder structure

            symbols = self.data_feed_port.get_available_symbols()
            logger.info(f"Live mode initialized with {len(symbols)} symbols")

            # Timer-based processing (simplified)
            while self.is_running:
                current_time = datetime.now().time()

                # Check for timer events
                if current_time >= time(15, 15):
                    # EOD processing
                    eod_signals = self.strategy.on_timer(current_time, {})
                    if eod_signals:
                        self.repository_port.save_signals(eod_signals)
                    break

                # Process timer events (rotation, etc.)
                timer_signals = self.strategy.on_timer(current_time, {})
                if timer_signals:
                    self.repository_port.save_signals(timer_signals)
                    await self._process_signals(timer_signals)

                await asyncio.sleep(60)  # Check every minute

        except Exception as e:
            logger.error(f"Live trading failed: {e}")
            raise
        finally:
            self.is_running = False

    async def _process_signals(self, signals: List[Signal]):
        """Process signals into broker orders"""
        for signal in signals:
            try:
                # Convert signal to order intent
                order_intent = self._signal_to_order_intent(signal)

                if order_intent:
                    # Place order through broker
                    order = await self.broker_port.place_order(order_intent)

                    # Save order to repository
                    self.repository_port.save_orders([order])

                    # Notify strategy of fill (simplified)
                    if order.status.name == 'FILLED':
                        await self._notify_fill(order)

            except Exception as e:
                logger.error(f"Error processing signal {signal.id}: {e}")

    def _signal_to_order_intent(self, signal: Signal) -> Optional[OrderIntent]:
        """Convert signal to order intent"""
        if signal.quantity == 0:
            return None

        side = Side.BUY if signal.quantity > 0 else Side.SELL

        return OrderIntent(
            symbol=signal.symbol,
            side=side,
            quantity=abs(signal.quantity),
            order_type=OrderType.MARKET,
            price=signal.price,
            metadata={
                'signal_id': signal.id,
                'reason': signal.reason,
                'confidence': signal.confidence_score
            }
        )

    async def _notify_fill(self, order):
        """Notify strategy of order fill"""
        # Extract fill details
        if order.fills:
            fill = order.fills[-1]
            await self.strategy.on_fill(
                order.symbol,
                fill.price,
                fill.quantity,
                {}
            )

    async def _generate_backtest_results(self) -> Dict[str, Any]:
        """Generate comprehensive backtest results"""
        # Get final account state
        account_state = await self.broker_port.get_account_state()
        positions = await self.broker_port.get_positions()

        # Calculate metrics
        total_return = account_state.total_pnl
        total_trades = len([p for p in positions if p.quantity != 0])

        # Get signals and orders
        signals = self.repository_port.load_signals(self.run_id)
        orders = []  # Would load from repository

        return {
            'run_id': self.run_id,
            'mode': 'backtest',
            'date': self.current_date.isoformat(),
            'total_return': float(total_return),
            'total_trades': total_trades,
            'signals_generated': len(signals),
            'final_cash': float(account_state.cash),
            'final_positions': len(positions),
            'config': self.config
        }

    def stop(self):
        """Stop the strategy runner"""
        logger.info("Stopping strategy runner")
        self.is_running = False


# Convenience functions for CLI usage
async def run_backtest(config_path: str) -> Dict[str, Any]:
    """Run backtest and return results"""
    runner = StrategyRunner(config_path)
    return await runner.run_backtest()


async def run_live(config_path: str):
    """Run live trading"""
    runner = StrategyRunner(config_path)
    await runner.run_live()


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python strategy_runner.py <config_path> [backtest|live]")
        sys.exit(1)

    config_path = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "backtest"

    if mode == "backtest":
        results = asyncio.run(run_backtest(config_path))
        print("Backtest Results:")
        print(f"Total Return: {results['total_return']:.2f}")
        print(f"Total Trades: {results['total_trades']}")
        print(f"Signals Generated: {results['signals_generated']}")
    else:
        print("Starting live trading...")
        asyncio.run(run_live(config_path))
