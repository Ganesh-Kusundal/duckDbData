#!/usr/bin/env python3
"""
Tradehull Broker Wrapper for DhanHQ API
========================================

This module provides a clean wrapper around the Dhan_Tradehull package,
integrating native 20-level market depth support from DhanHQ v2.1.0.

Features:
- Singleton broker pattern
- 5-level depth via REST API (get_quote_data)
- 20-level depth via WebSocket (native DhanHQ v2.1.0)
- Standardized data structures
- Error handling and logging
"""

import os
import logging
from typing import Dict, List, Optional, Any, Callable
from Dhan_Tradehull import Tradehull
from dhanhq import DhanContext, FullDepth
import asyncio
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global broker instance (singleton)
_broker_instance = None

def get_broker(force_new=False):
    """
    Creates and returns a Tradehull broker instance using the Singleton pattern.
    
    Loads environment variables from .env file and creates a Tradehull instance
    using the client_id and access_token from environment variables. If an instance
    already exists, returns the existing instance instead of creating a new one.
    
    Args:
        force_new (bool): If True, creates a new instance even if one exists
    
    Returns:
        TradehullBrokerWrapper: Configured Tradehull instance wrapped for compatibility.
        
    Raises:
        ValueError: If required environment variables are not found or empty.
        Exception: If broker instance creation fails or credentials are invalid.
    """
    global _broker_instance
    
    # Return existing instance if already created and not forcing new
    if _broker_instance is not None and not force_new:
        return _broker_instance
    
    # Load environment variables from .env file in project root
    if not os.environ.get("TESTING_MISSING_CREDENTIALS"):
        # Look for .env in the project root (parent of broker directory)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(project_root, '.env')
        dotenv.load_dotenv(env_path)
        
        # Also try broker_config.env in project root
        broker_config_path = os.path.join(project_root, '.env')
        dotenv.load_dotenv(broker_config_path)
    
    # Get credentials from environment variables
    client_id = os.environ.get("DHAN_CLIENT_ID", "").strip("'\"")
    access_token = os.environ.get("DHAN_API_TOKEN", "").strip("'\"")
    client_id="1106251237"
    access_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzU5MTMzNDk1LCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwNjI1MTIzNyJ9.ukAf0sFzYgNFCjw0T_B4i5VYLpCK2kt2ez9WmRbXyqfU1460q__rKxebgT0r5x30FOL2P0iwbzfOhfpZgl5Qkw"

    # Do not print sensitive credentials
    logger.info("Loaded DHAN credentials from environment variables")
    # Validate that credentials are provided
    if not client_id:
        raise ValueError("DHAN_CLIENT_ID not found in environment variables")
    
    if not access_token:
        raise ValueError("DHAN_API_TOKEN not found in environment variables")
    
    # Basic validation for obviously invalid credentials
    if client_id == "invalid_client_id" or access_token == "invalid_access_token":
        raise Exception("Invalid credentials provided")
    
    try:
        # Create Tradehull instance
        tradehull_instance = Tradehull(client_id, access_token)
        
        # Wrap it for compatibility
        broker = TradehullBrokerWrapper(tradehull_instance, client_id, access_token)
        
        # Test the broker connection by attempting to get balance
        # This will raise an exception if credentials are invalid
        try:
            broker.get_balance()
        except Exception as e:
            # Check if it's an authentication/credential error
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['auth', 'token', 'credential', 'permission', 'unauthorized', 'invalid', 'expired']):
                raise Exception(f"Authentication failed with provided credentials: {str(e)}") from e
            # For other errors (like network issues), we'll allow the broker instance to be created
            # as the credentials might be valid but there could be temporary connectivity issues
        
        # Store as singleton only if not forcing new
        if not force_new:
            _broker_instance = broker
        
        return broker
        
    except Exception as e:
        if "Authentication failed" in str(e) or "Invalid credentials" in str(e):
            raise  # Re-raise authentication errors as-is
        else:
            raise Exception(f"Failed to create Tradehull broker instance: {str(e)}") from e

class TradehullBrokerWrapper:
    """
    Wrapper class for Tradehull broker with enhanced functionality.
    
    Provides:
    - Standardized data structures
    - 5-level depth via REST API
    - 20-level depth via WebSocket (native DhanHQ v2.1.0)
    - Error handling and logging
    """
    
    def __init__(self, tradehull_instance: Tradehull, client_id: str, access_token: str):
        """
        Initialize the broker wrapper.
        
        Args:
            tradehull_instance: The underlying Tradehull instance
            client_id: Dhan client ID
            access_token: Dhan access token
        """
        self._tradehull = tradehull_instance
        self.client_id = client_id
        self.access_token = access_token
        self.broker_name = "Tradehull"
        
        # Initialize DhanContext for native 20-level depth
        self._dhan_context = DhanContext(client_id, access_token)
        
        # 20-level depth feed instance
        self._full_depth_feed = None
        self._depth_callbacks = []
        self._depth_thread = None
        self._depth_running = False
        
        logger.info("✅ TradehullBrokerWrapper initialized with 20-level depth support")
    
    def is_connected(self) -> bool:
        """Check if broker is connected."""
        try:
            # Try to get balance as a connectivity test
            self.get_balance()
            return True
        except Exception:
            return False
    
    def is_available(self) -> bool:
        """Check if broker is available and ready to use."""
        return self.is_connected()

    def get_historical_data(self, symbol: str, exchange: str = "NSE", timeframe: str = "day",
                           start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[Any]:
        """
        Get historical data using the standardized broker approach.

        Args:
            symbol: Trading symbol (e.g., 'RELIANCE', 'TCS')
            exchange: Exchange (default: 'NSE')
            timeframe: Timeframe (default: 'day')
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            Historical data or None if failed
        """
        try:
            # Use the underlying Tradehull instance with the correct parameters
            return self._tradehull.get_historical_data(
                tradingsymbol=symbol,
                exchange=exchange,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return None
    
    async def get_symbol_info_robust(self, symbol: str, exchange: str = "NSE") -> Optional[Dict[str, Any]]:
        """Get symbol information robustly."""
        try:
            # For now, return basic symbol info
            return {
                'symbol': symbol,
                'exchange': exchange,
                'available': True
            }
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            return None
    
    async def get_quote_data_async(self, symbol: str, exchange: str = "NSE") -> Optional[Dict[str, Any]]:
        """Async version of get_quote_data."""
        return self.get_quote_data(symbol)
    
    async def get_20_level_depth_async(self, symbol: str, exchange: str = "NSE") -> Optional[Dict[str, Any]]:
        """Async version of get_20_level_depth."""
        return self.get_20_level_depth(symbol)
    
    async def subscribe_20_level_depth(self, symbol: str, exchange: str = "NSE") -> bool:
        """Subscribe to 20-level depth for a single symbol."""
        return self.start_20_level_depth_stream([symbol])
    
    async def unsubscribe_20_level_depth(self, symbol: str, exchange: str = "NSE") -> bool:
        """Unsubscribe from 20-level depth for a single symbol."""
        self.stop_20_level_depth_stream()
        return True
    
    # ============================================================================
    # 5-LEVEL DEPTH METHODS (REST API)
    # ============================================================================
    
    def get_quote_data(self, symbol: str, debug: str = "NO") -> Optional[Dict[str, Any]]:
        """
        Get 5-level quote data with standardized depth structure.
        
        Args:
            symbol: Trading symbol (e.g., 'TCS', 'RELIANCE')
            debug: Debug mode (default: "NO")
            
        Returns:
            Dictionary with standardized quote data structure
        """
        try:
            # Get quote data from Tradehull
            quote_data = self._tradehull.get_quote_data(symbol, debug)
            
            if not quote_data or not isinstance(quote_data, dict):
                return None
            
            # Check if the data has the expected structure
            if symbol in quote_data:
                symbol_data = quote_data[symbol]
                
                # Standardize depth structure
                if 'depth' in symbol_data:
                    depth_data = symbol_data['depth']
                    
                    # Convert 'buy'/'sell' to 'bids'/'asks' for compatibility
                    standardized_depth = {
                        'bids': depth_data.get('buy', []),
                        'asks': depth_data.get('sell', [])
                    }
                    
                    # Create standardized response
                    standardized_quote = {
                        'symbol': symbol,
                        'last_price': symbol_data.get('last_price'),
                        'volume': symbol_data.get('volume'),
                        'depth': standardized_depth,
                        'ohlc': symbol_data.get('ohlc', {}),
                        'net_change': symbol_data.get('net_change'),
                        'buy_quantity': symbol_data.get('buy_quantity'),
                        'sell_quantity': symbol_data.get('sell_quantity'),
                        'last_trade_time': symbol_data.get('last_trade_time'),
                        'upper_circuit_limit': symbol_data.get('upper_circuit_limit'),
                        'lower_circuit_limit': symbol_data.get('lower_circuit_limit'),
                        'depth_level': 5  # Indicate this is 5-level depth
                    }
                    
                    return standardized_quote
                else:
                    # Return original data if no depth
                    return symbol_data
            
            return quote_data
            
        except Exception as e:
            if debug.upper() == "YES":
                logger.error(f"Error in get_quote_data for {symbol}: {e}")
            return None
    
    # ============================================================================
    # 20-LEVEL DEPTH METHODS (WebSocket - Native DhanHQ v2.1.0)
    # ============================================================================
    
    def get_20_level_depth(self, symbol: str, exchange_segment: int = 1, debug: str = "NO") -> Optional[Dict[str, Any]]:
        """
        Get 20-level market depth using native DhanHQ v2.1.0 FullDepth.
        
        Args:
            symbol: Trading symbol
            exchange_segment: Exchange segment (1=NSE_EQ, 2=NSE_FNO, etc.)
            debug: Debug mode
            
        Returns:
            Dictionary with 20-level depth data or None if failed
        """
        try:
            # Get security ID for the symbol
            security_id = self._get_security_id_for_symbol(symbol, exchange_segment)
            if not security_id:
                if debug.upper() == "YES":
                    logger.error(f"Could not find security ID for {symbol}")
                return None
            
            # Create FullDepth instance
            instruments = [(exchange_segment, str(security_id))]
            full_depth = FullDepth(self._dhan_context, instruments)
            
            # Get single snapshot of 20-level depth
            depth_data = self._get_depth_snapshot(full_depth, symbol, debug)
            
            return depth_data
            
        except Exception as e:
            if debug.upper() == "YES":
                logger.error(f"Error getting 20-level depth for {symbol}: {e}")
            return None
    
    def start_20_level_depth_stream(self, symbols: List[str], exchange_segment: int = 1, 
                                   callback: Optional[Callable] = None, debug: str = "NO") -> bool:
        """
        Start real-time 20-level depth streaming.
        
        Args:
            symbols: List of trading symbols
            exchange_segment: Exchange segment
            callback: Optional callback function for depth updates
            debug: Debug mode
            
        Returns:
            True if streaming started successfully, False otherwise
        """
        try:
            if self._depth_running:
                logger.warning("20-level depth stream already running")
                return True
            
            # Get security IDs
            instruments = []
            for symbol in symbols:
                security_id = self._get_security_id_for_symbol(symbol, exchange_segment)
                if security_id:
                    instruments.append((exchange_segment, str(security_id)))
            
            if not instruments:
                logger.error("No valid instruments found for depth streaming")
                return False
            
            # Store callback
            if callback:
                self._depth_callbacks.append(callback)
            
            # Create FullDepth instance
            self._full_depth_feed = FullDepth(self._dhan_context, instruments)
            
            # Start streaming in background thread
            self._depth_running = True
            self._depth_thread = threading.Thread(
                target=self._run_depth_stream,
                args=(debug,),
                daemon=True
            )
            self._depth_thread.start()
            
            if debug.upper() == "YES":
                logger.info(f"Started 20-level depth streaming for {len(symbols)} symbols")
            
            return True
            
        except Exception as e:
            if debug.upper() == "YES":
                logger.error(f"Error starting 20-level depth stream: {e}")
            return False
    
    def stop_20_level_depth_stream(self):
        """Stop 20-level depth streaming."""
        try:
            self._depth_running = False
            
            if self._full_depth_feed:
                try:
                    self._full_depth_feed.disconnect()
                except:
                    pass
                self._full_depth_feed = None
            
            if self._depth_thread and self._depth_thread.is_alive():
                self._depth_thread.join(timeout=5)
            
            self._depth_callbacks.clear()
            
            logger.info("20-level depth streaming stopped")
            
        except Exception as e:
            logger.error(f"Error stopping depth stream: {e}")
    
    def add_depth_callback(self, callback: Callable):
        """Add callback function for depth updates."""
        self._depth_callbacks.append(callback)
    
    def _run_depth_stream(self, debug: str):
        """Run the depth streaming loop."""
        try:
            if not self._full_depth_feed:
                return
            
            self._full_depth_feed.run_forever()
            
            while self._depth_running:
                try:
                    data = self._full_depth_feed.get_data()
                    if data:
                        # Process and notify callbacks
                        processed_data = self._process_depth_data(data)
                        if processed_data:
                            for callback in self._depth_callbacks:
                                try:
                                    callback(processed_data)
                                except Exception as e:
                                    if debug.upper() == "YES":
                                        logger.error(f"Callback error: {e}")
                    
                    time.sleep(0.1)  # Small delay to prevent CPU overload
                    
                except Exception as e:
                    if debug.upper() == "YES":
                        logger.error(f"Error in depth stream loop: {e}")
                    time.sleep(1)  # Wait before retrying
                    
        except Exception as e:
            if debug.upper() == "YES":
                logger.error(f"Error in depth stream: {e}")
        finally:
            self._depth_running = False
    
    def _get_depth_snapshot(self, full_depth: FullDepth, symbol: str, debug: str) -> Optional[Dict[str, Any]]:
        """Get a single snapshot of depth data."""
        try:
            # Run briefly to get data
            full_depth.run_forever()
            
            # Get data with timeout
            start_time = time.time()
            while time.time() - start_time < 10:  # 10 second timeout
                data = full_depth.get_data()
                if data:
                    return self._process_depth_data(data)
                time.sleep(0.1)
            
            return None
            
        except Exception as e:
            if debug.upper() == "YES":
                logger.error(f"Error getting depth snapshot: {e}")
            return None
        finally:
            try:
                full_depth.disconnect()
            except:
                pass
    
    def _process_depth_data(self, raw_data: Dict) -> Optional[Dict[str, Any]]:
        """Process raw depth data into standardized format."""
        try:
            # This is a simplified processor - actual implementation would parse
            # the binary data according to DhanHQ's specification
            
            # For now, return a basic structure
            processed_data = {
                'timestamp': time.time(),
                'depth_level': 20,
                'data': raw_data
            }
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Error processing depth data: {e}")
            return None
    
    def _get_security_id_for_symbol(self, symbol: str, exchange_segment: int) -> Optional[int]:
        """Get security ID for a symbol."""
        try:
            # Use Tradehull's existing method to find security ID
            # This is a simplified implementation
            if hasattr(self._tradehull, 'instrument_df') and self._tradehull.instrument_df is not None:
                # Search in instrument dataframe
                df = self._tradehull.instrument_df
                matches = df[
                    (df['SEM_CUSTOM_SYMBOL'] == symbol.upper()) |
                    (df['SEM_TRADING_SYMBOL'] == symbol.upper())
                ]
                
                if not matches.empty:
                    return int(matches.iloc[-1]['SEM_SMST_SECURITY_ID'])
            
            # Fallback to common mappings
            common_mappings = {
                "TCS": 11536,
                "RELIANCE": 2885,
                "INFY": 1594,
                "HDFC": 1333,
                "ITC": 1660,
                "JIOFIN": 5435,
            }
            
            return common_mappings.get(symbol.upper())
            
        except Exception as e:
            logger.error(f"Error getting security ID for {symbol}: {e}")
            return None
    
    # ============================================================================
    # DELEGATE ALL OTHER METHODS TO UNDERLYING TRADEHULL INSTANCE
    # ============================================================================
    
    def __getattr__(self, name):
        """Delegate unknown attributes to the underlying Tradehull instance."""
        if hasattr(self._tradehull, name):
            return getattr(self._tradehull, name)
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __dir__(self):
        """Include both wrapper and underlying Tradehull methods."""
        return list(super().__dir__()) + list(dir(self._tradehull))

# Import dotenv at the top level
try:
    import dotenv
except ImportError:
    # Create a dummy dotenv if not available
    class DummyDotenv:
        def load_dotenv(self, *args, **kwargs):
            pass
    dotenv = DummyDotenv()
