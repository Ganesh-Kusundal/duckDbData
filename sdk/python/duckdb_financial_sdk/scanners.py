"""
Scanners Client
==============

Client for scanner operations.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, date


class ScannerClient:
    """
    Client for scanner operations.

    Provides methods to execute scanners and retrieve results.
    """

    def __init__(self, client):
        """Initialize scanner client."""
        self.client = client

    def list_scanners(self) -> List[Dict]:
        """
        Get list of available scanners.

        Returns:
            List of scanner information
        """
        return self.client._make_request('GET', '/scanners')

    def get_scanner_info(self, scanner_id: str) -> Dict:
        """
        Get information about a specific scanner.

        Args:
            scanner_id: Scanner identifier

        Returns:
            Scanner information
        """
        return self.client._make_request('GET', f'/scanners/{scanner_id}')

    def run_scanner(self,
                   scanner_type: str,
                   symbol: str,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   **params) -> Dict:
        """
        Run a scanner on a symbol.

        Args:
            scanner_type: Type of scanner to run
            symbol: Trading symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            **params: Additional scanner parameters

        Returns:
            Scanner results
        """
        data = {
            'scanner_type': scanner_type,
            'symbol': symbol,
            **params
        }

        if start_date:
            data['start_date'] = start_date
        if end_date:
            data['end_date'] = end_date

        return self.client._make_request('POST', '/scanners/run', data=data)

    def run_technical_scanner(self,
                             symbol: str,
                             indicators: List[str] = None,
                             start_date: str = None,
                             end_date: str = None) -> Dict:
        """
        Run technical analysis scanner.

        Args:
            symbol: Trading symbol
            indicators: List of indicators to calculate
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Technical analysis results
        """
        params = {'symbol': symbol}

        if indicators:
            params['indicators'] = indicators
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date

        return self.client._make_request('POST', '/scanners/technical', data=params)

    def run_pattern_scanner(self,
                           symbol: str,
                           patterns: List[str] = None,
                           start_date: str = None,
                           end_date: str = None) -> Dict:
        """
        Run pattern recognition scanner.

        Args:
            symbol: Trading symbol
            patterns: List of patterns to detect
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Pattern recognition results
        """
        params = {'symbol': symbol}

        if patterns:
            params['patterns'] = patterns
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date

        return self.client._make_request('POST', '/scanners/pattern', data=params)

    def backtest_scanner(self,
                        scanner_type: str,
                        symbol: str,
                        start_date: str,
                        end_date: str,
                        **params) -> Dict:
        """
        Backtest a scanner strategy.

        Args:
            scanner_type: Type of scanner to backtest
            symbol: Trading symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            **params: Backtest parameters

        Returns:
            Backtest results
        """
        data = {
            'scanner_type': scanner_type,
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date,
            **params
        }

        return self.client._make_request('POST', '/scanners/backtest', data=data)

    def get_scanner_results(self,
                           scanner_id: str,
                           limit: int = 100) -> List[Dict]:
        """
        Get historical results for a scanner.

        Args:
            scanner_id: Scanner identifier
            limit: Maximum number of results

        Returns:
            List of scanner results
        """
        return self.client._make_request('GET', f'/scanners/{scanner_id}/results',
                                       params={'limit': limit})

    def optimize_scanner(self,
                        scanner_type: str,
                        symbol: str,
                        parameter_ranges: Dict,
                        start_date: str,
                        end_date: str) -> Dict:
        """
        Optimize scanner parameters.

        Args:
            scanner_type: Type of scanner to optimize
            symbol: Trading symbol
            parameter_ranges: Parameter ranges to test
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Optimization results
        """
        data = {
            'scanner_type': scanner_type,
            'symbol': symbol,
            'parameter_ranges': parameter_ranges,
            'start_date': start_date,
            'end_date': end_date
        }

        return self.client._make_request('POST', '/scanners/optimize', data=data)

    def get_scanner_performance(self,
                               scanner_id: str,
                               start_date: str,
                               end_date: str) -> Dict:
        """
        Get performance metrics for a scanner.

        Args:
            scanner_id: Scanner identifier
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Performance metrics
        """
        return self.client._make_request('GET', f'/scanners/{scanner_id}/performance',
                                       params={
                                           'start_date': start_date,
                                           'end_date': end_date
                                       })

    def create_custom_scanner(self,
                             name: str,
                             description: str,
                             scanner_logic: Dict) -> Dict:
        """
        Create a custom scanner.

        Args:
            name: Scanner name
            description: Scanner description
            scanner_logic: Scanner logic definition

        Returns:
            Created scanner information
        """
        data = {
            'name': name,
            'description': description,
            'logic': scanner_logic
        }

        return self.client._make_request('POST', '/scanners/custom', data=data)

    def delete_scanner(self, scanner_id: str) -> Dict:
        """
        Delete a custom scanner.

        Args:
            scanner_id: Scanner identifier

        Returns:
            Deletion confirmation
        """
        return self.client._make_request('DELETE', f'/scanners/{scanner_id}')

    def get_scanner_templates(self) -> List[Dict]:
        """
        Get available scanner templates.

        Returns:
            List of scanner templates
        """
        return self.client._make_request('GET', '/scanners/templates')
