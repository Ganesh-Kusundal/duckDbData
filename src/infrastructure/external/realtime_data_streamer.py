"""Real-time data streaming service for live market data."""

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, date
from decimal import Decimal
import asyncio
import logging
import threading
import time

from src.infrastructure.config.config_manager import ConfigManager

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


class AsyncRealtimeStreamer:
    """Async real-time data streamer using asyncio for non-blocking I/O."""
    
    def __init__(self,
                 market_data_repo: Optional[MarketDataRepository] = None,
                 broker_adapter=None,
                 config_manager: Optional[ConfigManager] = None):
        """Initialize the async real-time data streamer."""
        self.market_data_repo = market_data_repo or DuckDBMarketDataRepository()
        self.broker_adapter = broker_adapter
        self.config_manager = config_manager
        
        # Streaming state
        self._is_streaming = False
        self._tasks: List[asyncio.Task] = []
        self._monitored_symbols: List[str] = []
        self._websockets: Dict[str, Any] = {}  # Store websocket connections per symbol
        self._semaphore = asyncio.Semaphore(10)  # Limit concurrent operations
        
        # Configuration from ConfigManager
        self._concurrent_streams = 10
        self._timeout = 30.0
        self._max_retries = 3
        self._load_config()
        
        logger.info("Async real-time data streamer initialized")
    
    def _load_config(self):
        """Load async configuration from ConfigManager."""
        if self.config_manager:
            try:
                analytics_config = self.config_manager.get_config('analytics')
                self._concurrent_streams = analytics_config.get('max_concurrent_streams', 10)
                self._timeout = analytics_config.get('realtime_timeout', 30.0)
                self._max_retries = analytics_config.get('max_retries', 3)
                logger.info(f"Loaded async config: concurrent_streams={self._concurrent_streams}, timeout={self._timeout}")
            except Exception as e:
                logger.warning(f"Failed to load async config, using defaults: {e}")
    
    async def start_streaming(self, symbols: List[str], update_interval: float = 1.0) -> bool:
        """
        Start async real-time data streaming.
        
        Args:
            symbols: List of symbols to monitor
            update_interval: Update interval in seconds
            
        Returns:
            True if streaming started successfully
        """
        if self._is_streaming:
            logger.warning("Async real-time streaming already running")
            return False
        
        if not self.broker_adapter:
            logger.error("Broker adapter not configured for async streaming")
            return False
        
        try:
            self._is_streaming = True
            self._monitored_symbols = symbols.copy()
            
            logger.info(f"Starting async real-time streaming for {len(symbols)} symbols")
            
            # Create concurrent tasks for each symbol using semaphore to limit concurrency
            semaphore = asyncio.Semaphore(self._concurrent_streams)
            
            async def stream_symbol(symbol):
                async with semaphore:
                    await self._stream_symbol_data(symbol)
            
            # Create tasks for all symbols
            self._tasks = [asyncio.create_task(stream_symbol(symbol)) for symbol in symbols]
            
            # Wait for all tasks to complete or handle cancellation
            await asyncio.gather(*self._tasks, return_exceptions=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting async real-time streaming: {e}")
            await self.stop_streaming()
            return False
    
    async def stop_streaming(self) -> bool:
        """Stop async real-time data streaming."""
        if not self._is_streaming:
            return True
        
        try:
            logger.info("Stopping async real-time streaming")
            self._is_streaming = False
            
            # Cancel all running tasks
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete with timeout
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            # Close websocket connections
            for symbol, ws in self._websockets.items():
                if hasattr(ws, 'close'):
                    await ws.close()
            
            self._monitored_symbols.clear()
            self._websockets.clear()
            self._tasks.clear()
            
            logger.info("Async real-time streaming stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping async real-time streaming: {e}")
            return False
    
    async def _stream_symbol_data(self, symbol: str):
        """Stream data for a single symbol asynchronously."""
        max_retries = self._max_retries
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Starting async stream for symbol {symbol} (attempt {attempt + 1})")
                
                # Establish websocket connection (mock implementation - adapt to actual broker)
                websocket = await self._connect_websocket(symbol)
                if not websocket:
                    raise BrokerAPIError(f"Failed to connect websocket for {symbol}", "realtime_streamer")
                
                self._websockets[symbol] = websocket
                
                # Listen for real-time data
                async for message in websocket:
                    if not self._is_streaming:
                        break
                    
                    try:
                        async with asyncio.wait_for(self._process_websocket_message(message, symbol), timeout=self._timeout):
                            pass
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout processing message for {symbol}")
                        # Wrap in custom error
                        raise BrokerAPIError("Message processing timeout", "realtime_streamer", symbol=symbol)
                    
            except Exception as e:
                logger.error(f"Error streaming symbol {symbol} (attempt {attempt + 1}): {e}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(5 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"Max retries exceeded for symbol {symbol}")
                    # Publish error event
                    await self._publish_streaming_error(symbol, str(e))
            
            finally:
                # Clean up websocket
                if symbol in self._websockets:
                    ws = self._websockets.pop(symbol)
                    if hasattr(ws, 'close'):
                        await ws.close()
        
        logger.info(f"Stopped streaming for symbol {symbol}")
    
    async def _connect_websocket(self, symbol: str) -> Optional[Any]:
        """Connect to websocket for symbol (mock - implement actual broker websocket)."""
        try:
            # This is a mock implementation. In reality, this would connect to broker's websocket API
            # For example, using websockets library or broker-specific async client
            
            # Simulate websocket connection
            import asyncio
            
            async def mock_websocket():
                """Mock websocket generator for testing."""
                while self._is_streaming:
                    # Simulate receiving tick data every 0.5 seconds
                    yield {
                        'symbol': symbol,
                        'last_price': 100 + (hash(symbol + str(time.time())) % 1000) / 10,
                        'volume': 1000 + (hash(symbol) % 10000),
                        'timestamp': datetime.now().isoformat()
                    }
                    await asyncio.sleep(0.5)
            
            return mock_websocket()
            
        except Exception as e:
            logger.error(f"Failed to connect websocket for {symbol}: {e}")
            raise BrokerAPIError(f"Websocket connection failed for {symbol}", "realtime_streamer")
    
    async def _process_websocket_message(self, message: Dict[str, Any], symbol: str):
        """Process incoming websocket message asynchronously."""
        try:
            # Extract real-time data
            realtime_data = {
                'symbol': symbol,
                'quote_data': message,
                'timestamp': datetime.fromisoformat(message.get('timestamp', datetime.now().isoformat()))
            }
            
            # Process the data (reuse sync processing but make it async)
            ohlcv_data = self._extract_ohlcv_from_realtime(realtime_data)
            
            if ohlcv_data:
                # Create domain entity
                market_data = MarketData(
                    symbol=symbol,
                    timestamp=realtime_data['timestamp'],
                    timeframe='1m',
                    ohlcv=ohlcv_data,
                    date_partition=realtime_data['timestamp'].date()
                )
                
                # Save to repository asynchronously
                await self._save_market_data_async(market_data)
                
                # Publish event asynchronously
                await self._publish_realtime_event_async(symbol, market_data)
                
                # Notify callbacks if any
                await self._notify_async_callbacks('realtime_update', {
                    'symbol': symbol,
                    'data': realtime_data,
                    'timestamp': datetime.now()
                })
                
        except Exception as e:
            logger.error(f"Error processing websocket message for {symbol}: {e}")
            # Wrap async exceptions in custom errors
            if isinstance(e, asyncio.TimeoutError):
                raise BrokerAPIError("Async processing timeout", "realtime_streamer", symbol=symbol)
            raise
    
    async def _save_market_data_async(self, market_data: MarketData):
        """Save market data asynchronously."""
        # For now, use sync save with asyncio.to_thread
        # In production, implement async database operations
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.market_data_repo.save, market_data)
    
    async def _publish_realtime_event_async(self, symbol: str, market_data: MarketData):
        """Publish real-time data event asynchronously."""
        try:
            event = DataIngestedEvent(
                symbol=symbol,
                timeframe='1m',
                records_count=1,
                start_date=market_data.date_partition,
                end_date=market_data.date_partition,
                metadata={
                    'realtime': True,
                    'source': 'async_streaming',
                    'price': float(market_data.ohlcv.close),
                    'volume': market_data.ohlcv.volume
                }
            )
            
            # Use asyncio.create_task for non-blocking publish
            asyncio.create_task(publish_event(event))
            
        except Exception as e:
            logger.error(f"Error publishing async real-time event for {symbol}: {e}")
    
    async def _publish_streaming_error(self, symbol: str, error_msg: str):
        """Publish streaming error event."""
        try:
            # Create error event (assuming DataIngestedEvent can handle errors)
            error_event = DataIngestedEvent(
                symbol=symbol,
                timeframe='1m',
                records_count=0,
                start_date=date.today(),
                end_date=date.today(),
                metadata={
                    'error': True,
                    'source': 'async_streamer',
                    'error_message': error_msg
                }
            )
            asyncio.create_task(publish_event(error_event))
        except Exception as e:
            logger.error(f"Failed to publish streaming error for {symbol}: {e}")
    
    async def _notify_async_callbacks(self, event_type: str, data: Dict[str, Any]):
        """Notify async callbacks."""
        # For now, using sync callbacks with run_in_executor
        # In future, support async callbacks
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._notify_sync_callbacks, event_type, data)
    
    def _notify_sync_callbacks(self, event_type: str, data: Dict[str, Any]):
        """Notify synchronous callbacks (compatibility method)."""
        # Reuse existing sync callback notification
        # This assumes _callbacks list is shared or needs to be maintained
        if hasattr(self, '_callbacks') and self._callbacks:
            for callback in self._callbacks:
                try:
                    callback(event_type, data)
                except Exception as e:
                    logger.error(f"Error in async streaming callback: {e}")
    
    def add_callback(self, callback: Callable):
        """Add callback for real-time updates (compatibility)."""
        if not hasattr(self, '_callbacks'):
            self._callbacks = []
        self._callbacks.append(callback)
    
    def get_streaming_status(self) -> Dict[str, Any]:
        """Get current async streaming status."""
        return {
            'is_streaming': self._is_streaming,
            'monitored_symbols': len(self._monitored_symbols),
            'active_tasks': len([t for t in self._tasks if not t.done()]),
            'active_websockets': len(self._websockets),
            'concurrent_streams': self._concurrent_streams,
            'timestamp': datetime.now()
        }
    
    async def update_symbols(self, symbols: List[str]):
        """Update monitored symbols asynchronously."""
        self._monitored_symbols = symbols.copy()
        logger.info(f"Updated async monitored symbols: {len(symbols)} symbols")
        
        # Cancel existing tasks and restart streaming
        if self._is_streaming:
            await self.stop_streaming()
            await self.start_streaming(symbols)
    
    def _extract_ohlcv_from_realtime(self, data: Dict[str, Any]) -> Optional[OHLCV]:
        """Extract OHLCV data from real-time update (shared with sync class)."""
        # Reuse the existing sync extraction method
        # This would need to be made a static method or utility function in production
        try:
            if 'quote_data' in data:
                quote = data['quote_data']
                if isinstance(quote, dict):
                    last_price = quote.get('last_price', 0)
                    volume = quote.get('volume', 0)
                    
                    return OHLCV(
                        open=Decimal(str(last_price)),
                        high=Decimal(str(last_price)),
                        low=Decimal(str(last_price)),
                        close=Decimal(str(last_price)),
                        volume=int(volume)
                    )
        except Exception as e:
            logger.error(f"Error extracting OHLCV from async real-time data: {e}")
        
        return None
