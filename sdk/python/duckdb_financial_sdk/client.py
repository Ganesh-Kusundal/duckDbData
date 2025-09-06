"""
Main Financial Client
====================

Unified client for all DuckDB Financial Infrastructure operations.
"""

import requests
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date
import json
import logging

from .exceptions import APIError, AuthenticationError, ValidationError
from .market_data import MarketDataClient
from .scanners import ScannerClient
from .system import SystemClient
from .realtime import RealtimeClient


class FinancialClient:
    """
    Main client for DuckDB Financial Infrastructure API.

    Provides unified access to all platform features.

    Args:
        base_url: Base URL of the API server
        api_key: Optional API key for authentication
        timeout: Request timeout in seconds
        verify_ssl: Whether to verify SSL certificates
    """

    def __init__(self,
                 base_url: str = "http://localhost:8000",
                 api_key: Optional[str] = None,
                 timeout: int = 30,
                 verify_ssl: bool = True):
        """
        Initialize the financial client.

        Args:
            base_url: Base URL of the API server
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.session = requests.Session()

        # Configure session
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})

        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': f'DuckDB-Financial-SDK/{__import__(__name__.split(".")[0]).__version__}'
        })

        # Initialize sub-clients
        self.market_data = MarketDataClient(self)
        self.scanners = ScannerClient(self)
        self.system = SystemClient(self)
        self.realtime = RealtimeClient(self)

        self.logger = logging.getLogger(__name__)

    def _make_request(self,
                     method: str,
                     endpoint: str,
                     data: Optional[Dict] = None,
                     params: Optional[Dict] = None) -> Dict:
        """
        Make HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            data: Request data for POST/PUT requests
            params: Query parameters

        Returns:
            Response data as dictionary

        Raises:
            APIError: For API-related errors
            AuthenticationError: For authentication failures
            ValidationError: For validation errors
        """
        url = f"{self.base_url}{endpoint}"

        try:
            kwargs = {
                'timeout': self.timeout,
                'verify': self.verify_ssl
            }

            if params:
                kwargs['params'] = params

            if data:
                kwargs['json'] = data

            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()

            if response.content:
                return response.json()
            return {}

        except requests.exceptions.HTTPError as e:
            self._handle_http_error(e, response)
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {e}")
        except json.JSONDecodeError as e:
            raise APIError(f"Invalid JSON response: {e}")

    def _handle_http_error(self, error: requests.exceptions.HTTPError,
                          response: requests.Response):
        """Handle HTTP errors with appropriate exceptions."""
        try:
            error_data = response.json()
            message = error_data.get('detail', str(error))
        except:
            message = str(error)

        if response.status_code == 401:
            raise AuthenticationError(message)
        elif response.status_code == 422:
            raise ValidationError(message)
        else:
            raise APIError(f"HTTP {response.status_code}: {message}")

    def health_check(self) -> Dict:
        """
        Perform health check on the API server.

        Returns:
            Health status information
        """
        return self._make_request('GET', '/health')

    def get_status(self) -> Dict:
        """
        Get detailed system status.

        Returns:
            System status information
        """
        return self._make_request('GET', '/health/detailed')

    def get_metrics(self) -> str:
        """
        Get Prometheus metrics.

        Returns:
            Metrics in Prometheus format
        """
        response = self.session.get(f"{self.base_url}/metrics")
        response.raise_for_status()
        return response.text

    # Convenience methods for common operations
    def get_market_data(self,
                       symbol: str,
                       start_date: str,
                       end_date: str,
                       limit: Optional[int] = None) -> List[Dict]:
        """
        Get market data for a symbol.

        Args:
            symbol: Trading symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Maximum number of records

        Returns:
            List of market data records
        """
        return self.market_data.get_data(symbol, start_date, end_date, limit)

    def run_scanner(self, scanner_type: str, symbol: str, **params) -> Dict:
        """
        Run a scanner on a symbol.

        Args:
            scanner_type: Type of scanner to run
            symbol: Trading symbol
            **params: Additional scanner parameters

        Returns:
            Scanner results
        """
        return self.scanners.run_scanner(scanner_type, symbol, **params)

    def get_system_info(self) -> Dict:
        """
        Get system information.

        Returns:
            System information
        """
        return self.system.get_info()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.session.close()

    def __repr__(self) -> str:
        return f"FinancialClient(base_url='{self.base_url}')"
