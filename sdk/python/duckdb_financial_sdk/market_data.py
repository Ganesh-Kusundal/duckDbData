"""
Market Data Client
==================

Client for market data operations.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, date


class MarketDataClient:
    """
    Client for market data operations.

    Provides methods to retrieve and manipulate market data.
    """

    def __init__(self, client):
        """Initialize market data client."""
        self.client = client

    def get_data(self,
                symbol: str,
                start_date: str,
                end_date: str,
                limit: Optional[int] = None,
                timeframe: str = "1D") -> List[Dict]:
        """
        Get market data for a symbol.

        Args:
            symbol: Trading symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Maximum number of records
            timeframe: Data timeframe (1m, 5m, 1H, 1D, etc.)

        Returns:
            List of market data records
        """
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'timeframe': timeframe
        }

        if limit:
            params['limit'] = limit

        return self.client._make_request('GET', f'/market-data/{symbol}', params=params)

    def get_latest(self, symbol: str, limit: int = 100) -> List[Dict]:
        """
        Get latest market data for a symbol.

        Args:
            symbol: Trading symbol
            limit: Number of recent records

        Returns:
            List of recent market data records
        """
        return self.client._make_request('GET', f'/market-data/{symbol}/latest',
                                       params={'limit': limit})

    def get_statistics(self, symbol: Optional[str] = None) -> Dict:
        """
        Get market data statistics.

        Args:
            symbol: Specific symbol or None for all symbols

        Returns:
            Statistics data
        """
        endpoint = '/market-data/statistics'
        if symbol:
            endpoint = f'/market-data/{symbol}/statistics'

        return self.client._make_request('GET', endpoint)

    def search_symbols(self, query: str, limit: int = 50) -> List[Dict]:
        """
        Search for trading symbols.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching symbols
        """
        return self.client._make_request('GET', '/market-data/symbols/search',
                                       params={'q': query, 'limit': limit})

    def get_available_symbols(self) -> List[str]:
        """
        Get list of available symbols.

        Returns:
            List of trading symbols
        """
        result = self.client._make_request('GET', '/market-data/symbols')
        return result.get('symbols', [])

    def get_ohlc_data(self,
                     symbol: str,
                     start_date: str,
                     end_date: str,
                     timeframe: str = "1D") -> Dict:
        """
        Get OHLC data for charting.

        Args:
            symbol: Trading symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            timeframe: Data timeframe

        Returns:
            OHLC data formatted for charting
        """
        return self.client._make_request('GET', f'/market-data/{symbol}/ohlc',
                                       params={
                                           'start_date': start_date,
                                           'end_date': end_date,
                                           'timeframe': timeframe
                                       })

    def get_volume_profile(self,
                          symbol: str,
                          start_date: str,
                          end_date: str) -> Dict:
        """
        Get volume profile analysis.

        Args:
            symbol: Trading symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Volume profile data
        """
        return self.client._make_request('GET', f'/market-data/{symbol}/volume-profile',
                                       params={
                                           'start_date': start_date,
                                           'end_date': end_date
                                       })

    def get_price_history(self,
                         symbol: str,
                         period: str = "1M") -> List[Dict]:
        """
        Get price history for a symbol.

        Args:
            symbol: Trading symbol
            period: Time period (1D, 1W, 1M, 3M, 6M, 1Y)

        Returns:
            Price history data
        """
        return self.client._make_request('GET', f'/market-data/{symbol}/history',
                                       params={'period': period})

    def get_intraday_data(self,
                         symbol: str,
                         date: str) -> List[Dict]:
        """
        Get intraday data for a specific date.

        Args:
            symbol: Trading symbol
            date: Date (YYYY-MM-DD)

        Returns:
            Intraday price data
        """
        return self.client._make_request('GET', f'/market-data/{symbol}/intraday',
                                       params={'date': date})
