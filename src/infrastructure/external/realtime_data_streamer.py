"""Real-time data streaming service for live market data."""

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, date
from decimal import Decimal
import asyncio
import logging
import threading
import time

from ...domain.entities.market_data import MarketData, OHLCV
from ...domain.repositories.market_data_repo import MarketDataRepository
from ...infrastructure.repositories.duckdb_market_repo import DuckDBMarketDataRepository
from ...infrastructure.messaging.event_bus import publish_event
from ...domain.events import DataIngestedEvent


logger = logging.getLogger(__name__)


class RealtimeDataStreamer:
    """Real-time data streaming service."""

    def __init__(self,
                 market_data_repo: Optional[MarketDataRepository] = None,
                 broker_adapter=None):
        """Initialize the real-time data streamer."""
        self.market_data_repo = market_data_repo or DuckDBMarketDataRepository()
        self.broker_adapter = broker_adapter

        # Streaming state
        self._is_streaming = False
        self._stream_thread: Optional[threading.Thread] = None
        self._monitored_symbols: List[str] = []
        self._callbacks: List[Callable] = []

        # Streaming configuration
        self._update_interval = 1.0  # seconds
        self._batch_size = 10  # symbols per batch
        self._max_retries = 3

        logger.info("Real-time data streamer initialized")

    def add_callback(self, callback: Callable):
        """Add callback for real-time updates."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable):
        """Remove callback for real-time updates."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_callbacks(self, event_type: str, data: Dict[str, Any]):
        """Notify all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in streaming callback: {e}")

    async def start_streaming(self,
                            symbols: List[str],
                            update_interval: float = 1.0) -> bool:
        """
        Start real-time data streaming.

        Args:
            symbols: List of symbols to monitor
            update_interval: Update interval in seconds

        Returns:
            True if streaming started successfully
        """
        if self._is_streaming:
            logger.warning("Real-time streaming already running")
            return False

        if not self.broker_adapter:
            logger.error("Broker adapter not configured for streaming")
            return False

        try:
            self._is_streaming = True
            self._monitored_symbols = symbols.copy()
            self._update_interval = update_interval

            logger.info(f"Starting real-time streaming for {len(symbols)} symbols")

            # Start streaming in background thread
            self._stream_thread = threading.Thread(
                target=self._run_streaming_loop,
                daemon=True
            )
            self._stream_thread.start()

            return True

        except Exception as e:
            logger.error(f"Error starting real-time streaming: {e}")
            self._is_streaming = False
            return False

    async def stop_streaming(self) -> bool:
        """Stop real-time data streaming."""
        if not self._is_streaming:
            return True

        try:
            logger.info("Stopping real-time streaming")
            self._is_streaming = False

            if self._stream_thread and self._stream_thread.is_alive():
                self._stream_thread.join(timeout=5.0)

            self._monitored_symbols.clear()
            self._callbacks.clear()

            return True

        except Exception as e:
            logger.error(f"Error stopping real-time streaming: {e}")
            return False

    def _run_streaming_loop(self):
        """Run the streaming loop in background thread."""
        logger.info("Real-time streaming loop started")

        try:
            while self._is_streaming:
                try:
                    # Fetch real-time data for all symbols
                    self._fetch_realtime_data_batch()

                    # Wait for next update
                    time.sleep(self._update_interval)

                except Exception as e:
                    logger.error(f"Error in streaming loop: {e}")
                    time.sleep(5.0)  # Wait before retrying

        except Exception as e:
            logger.error(f"Streaming loop failed: {e}")
        finally:
            self._is_streaming = False
            logger.info("Real-time streaming loop stopped")

    def _fetch_realtime_data_batch(self):
        """Fetch real-time data for a batch of symbols."""
        if not self._monitored_symbols:
            return

        # Process symbols in batches to avoid overwhelming the broker
        for i in range(0, len(self._monitored_symbols), self._batch_size):
            batch = self._monitored_symbols[i:i + self._batch_size]

            for symbol in batch:
                try:
                    # Fetch real-time data for this symbol
                    realtime_data = self._fetch_symbol_realtime_data(symbol)

                    if realtime_data:
                        # Process the data
                        self._process_realtime_data(symbol, realtime_data)

                        # Notify callbacks
                        self._notify_callbacks('realtime_update', {
                            'symbol': symbol,
                            'data': realtime_data,
                            'timestamp': datetime.now()
                        })

                except Exception as e:
                    logger.error(f"Error fetching real-time data for {symbol}: {e}")

            # Small delay between batches
            time.sleep(0.1)

    def _fetch_symbol_realtime_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time data for a single symbol."""
        try:
            if hasattr(self.broker_adapter, 'get_quote_data'):
                # Get 5-level market depth
                quote_data = self.broker_adapter.get_quote_data(symbol)

                if quote_data and isinstance(quote_data, dict):
                    return {
                        'symbol': symbol,
                        'quote_data': quote_data,
                        'timestamp': datetime.now(),
                        'depth_level': 5
                    }

            elif hasattr(self.broker_adapter, 'get_market_depth'):
                # Get market depth
                depth_data = self.broker_adapter.get_market_depth(symbol)

                if depth_data:
                    return {
                        'symbol': symbol,
                        'depth_data': depth_data,
                        'timestamp': datetime.now(),
                        'depth_level': depth_data.depth_level if hasattr(depth_data, 'depth_level') else 5
                    }

        except Exception as e:
            logger.error(f"Error fetching real-time data for {symbol}: {e}")

        return None

    def _process_realtime_data(self, symbol: str, data: Dict[str, Any]):
        """Process real-time data and save to repository."""
        try:
            # Extract OHLCV data from real-time update
            ohlcv_data = self._extract_ohlcv_from_realtime(data)

            if ohlcv_data:
                # Create domain entity
                market_data = MarketData(
                    symbol=symbol,
                    timestamp=data['timestamp'],
                    timeframe='1m',  # Real-time data is typically 1-minute
                    ohlcv=ohlcv_data,
                    date_partition=data['timestamp'].date()
                )

                # Save to repository
                self.market_data_repo.save(market_data)

                # Publish event
                self._publish_realtime_event(symbol, market_data)

        except Exception as e:
            logger.error(f"Error processing real-time data for {symbol}: {e}")

    def _extract_ohlcv_from_realtime(self, data: Dict[str, Any]) -> Optional[OHLCV]:
        """Extract OHLCV data from real-time update."""
        try:
            if 'quote_data' in data:
                quote = data['quote_data']

                # Try to extract from different possible formats
                if isinstance(quote, dict):
                    # Look for symbol-specific data
                    symbol_data = None
                    if data['symbol'] in quote:
                        symbol_data = quote[data['symbol']]
                    elif 'data' in quote:
                        symbol_data = quote['data']
                    else:
                        symbol_data = quote

                    if symbol_data and isinstance(symbol_data, dict):
                        # Extract OHLCV values
                        last_price = symbol_data.get('last_price', 0)
                        volume = symbol_data.get('volume', 0)

                        # For real-time data, we might only have last price
                        # Use last price for all OHLC values as approximation
                        return OHLCV(
                            open=Decimal(str(last_price)),
                            high=Decimal(str(last_price)),
                            low=Decimal(str(last_price)),
                            close=Decimal(str(last_price)),
                            volume=int(volume)
                        )

            elif 'depth_data' in data:
                # Extract from market depth data
                depth = data['depth_data']
                if hasattr(depth, 'best_bid') and depth.best_bid:
                    price = depth.best_bid['price']
                    return OHLCV(
                        open=price,
                        high=price,
                        low=price,
                        close=price,
                        volume=depth.best_bid.get('quantity', 0)
                    )

        except Exception as e:
            logger.error(f"Error extracting OHLCV from real-time data: {e}")

        return None

    def _publish_realtime_event(self, symbol: str, market_data: MarketData):
        """Publish real-time data event."""
        try:
            event = DataIngestedEvent(
                symbol=symbol,
                timeframe='1m',
                records_count=1,
                start_date=market_data.date_partition,
                end_date=market_data.date_partition,
                metadata={
                    'realtime': True,
                    'source': 'streaming',
                    'price': float(market_data.ohlcv.close),
                    'volume': market_data.ohlcv.volume
                }
            )

            # Publish event asynchronously
            asyncio.create_task(publish_event(event))

        except Exception as e:
            logger.error(f"Error publishing real-time event for {symbol}: {e}")

    def get_streaming_status(self) -> Dict[str, Any]:
        """Get current streaming status."""
        return {
            'is_streaming': self._is_streaming,
            'monitored_symbols': len(self._monitored_symbols),
            'active_callbacks': len(self._callbacks),
            'update_interval': self._update_interval,
            'timestamp': datetime.now()
        }

    def update_symbols(self, symbols: List[str]):
        """Update the list of monitored symbols."""
        self._monitored_symbols = symbols.copy()
        logger.info(f"Updated monitored symbols: {len(symbols)} symbols")

    def get_monitored_symbols(self) -> List[str]:
        """Get list of currently monitored symbols."""
        return self._monitored_symbols.copy()


class CandleAggregator:
    """Aggregates real-time tick data into candles."""

    def __init__(self, timeframe_minutes: int = 1):
        """Initialize candle aggregator."""
        self.timeframe_minutes = timeframe_minutes
        self._candles: Dict[str, Dict[str, Any]] = {}
        self._last_update: Dict[str, datetime] = {}

    def update_tick(self, symbol: str, price: Decimal, volume: int, timestamp: datetime):
        """Update candle with new tick data."""
        try:
            # Get current candle period
            candle_key = self._get_candle_key(timestamp)

            if symbol not in self._candles:
                self._candles[symbol] = {}
                self._last_update[symbol] = timestamp

            if candle_key not in self._candles[symbol]:
                # Initialize new candle
                self._candles[symbol][candle_key] = {
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': volume,
                    'timestamp': timestamp,
                    'complete': False
                }
            else:
                # Update existing candle
                candle = self._candles[symbol][candle_key]
                candle['high'] = max(candle['high'], price)
                candle['low'] = min(candle['low'], price)
                candle['close'] = price
                candle['volume'] += volume
                candle['timestamp'] = timestamp

            self._last_update[symbol] = timestamp

        except Exception as e:
            logger.error(f"Error updating candle for {symbol}: {e}")

    def get_current_candle(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current incomplete candle for symbol."""
        try:
            if symbol in self._candles:
                current_key = max(self._candles[symbol].keys())
                return self._candles[symbol][current_key]
        except Exception as e:
            logger.error(f"Error getting current candle for {symbol}: {e}")

        return None

    def get_completed_candles(self, symbol: str) -> List[Dict[str, Any]]:
        """Get all completed candles for symbol."""
        try:
            if symbol in self._candles:
                completed = []
                for candle_key, candle in self._candles[symbol].items():
                    if candle['complete']:
                        completed.append(candle)
                return completed
        except Exception as e:
            logger.error(f"Error getting completed candles for {symbol}: {e}")

        return []

    def _get_candle_key(self, timestamp: datetime) -> str:
        """Get candle key for timestamp."""
        # Round down to nearest timeframe
        minutes = timestamp.minute // self.timeframe_minutes * self.timeframe_minutes
        candle_time = timestamp.replace(minute=minutes, second=0, microsecond=0)
        return candle_time.strftime('%Y%m%d_%H%M%S')

    def mark_candle_complete(self, symbol: str, candle_key: str):
        """Mark a candle as complete."""
        try:
            if symbol in self._candles and candle_key in self._candles[symbol]:
                self._candles[symbol][candle_key]['complete'] = True
        except Exception as e:
            logger.error(f"Error marking candle complete for {symbol}: {e}")
