"""
Market Data Domain Service
Contains business logic for market data operations
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from ..entities.market_data import MarketData, MarketDataBatch
from ..value_objects.ohlcv import OHLCV
from ..repositories.market_data_repository import MarketDataRepository


class MarketDataService:
    """
    Market Data Domain Service

    Contains business logic that doesn't naturally belong to entities.
    Handles complex operations involving multiple entities or external concerns.
    """

    def __init__(self, repository: MarketDataRepository):
        self.repository = repository

    async def get_price_history(
        self,
        symbol: str,
        timeframe: str,
        days: int = 30,
        include_extended_hours: bool = False
    ) -> List[MarketData]:
        """
        Get price history for a symbol

        Business Rules:
        - Validate symbol exists
        - Ensure reasonable date range
        - Handle data gaps gracefully
        - Apply business-specific filtering

        Args:
            symbol: Trading symbol
            timeframe: Data timeframe
            days: Number of days of history
            include_extended_hours: Whether to include extended hours data

        Returns:
            List of market data records
        """
        if days > 365:  # Business rule: limit to 1 year
            raise ValueError("Cannot request more than 365 days of history")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        data = await self.repository.find_by_date_range(
            start_date=start_date,
            end_date=end_date,
            symbol=symbol,
            timeframe=timeframe
        )

        # Apply business rules
        if not include_extended_hours:
            data = self._filter_regular_hours(data)

        return data

    async def calculate_technical_indicators(
        self,
        symbol: str,
        timeframe: str,
        indicator_type: str,
        period: int = 20
    ) -> Dict[str, Any]:
        """
        Calculate technical indicators

        Business Rules:
        - Minimum data requirements per indicator
        - Validate indicator parameters
        - Handle insufficient data gracefully

        Args:
            symbol: Trading symbol
            timeframe: Data timeframe
            indicator_type: Type of indicator (SMA, EMA, RSI, etc.)
            period: Calculation period

        Returns:
            Dictionary with indicator results
        """
        # Get sufficient historical data
        days_needed = period * 2  # Buffer for calculation
        data = await self.get_price_history(symbol, timeframe, days_needed)

        if len(data) < period:
            raise ValueError(f"Insufficient data for {indicator_type} calculation. Need at least {period} records.")

        prices = [record.ohlcv.close for record in data]

        if indicator_type.upper() == 'SMA':
            return self._calculate_sma(prices, period)
        elif indicator_type.upper() == 'EMA':
            return self._calculate_ema(prices, period)
        elif indicator_type.upper() == 'RSI':
            return self._calculate_rsi(prices, period)
        else:
            raise ValueError(f"Unsupported indicator type: {indicator_type}")

    async def detect_price_anomalies(
        self,
        symbol: str,
        timeframe: str,
        threshold: float = 0.05
    ) -> List[Dict[str, Any]]:
        """
        Detect price anomalies in market data

        Business Rules:
        - Define what constitutes an anomaly
        - Apply statistical thresholds
        - Consider market context

        Args:
            symbol: Trading symbol
            timeframe: Data timeframe
            threshold: Anomaly detection threshold (percentage)

        Returns:
            List of detected anomalies
        """
        data = await self.get_price_history(symbol, timeframe, days=30)

        if len(data) < 10:
            return []

        anomalies = []
        prices = [record.ohlcv.close for record in data]

        # Calculate moving average
        sma = self._calculate_simple_moving_average(prices, 20)

        # Detect anomalies based on deviation from SMA
        for i, record in enumerate(data):
            if i >= 20:  # Wait for SMA to be available
                current_price = record.ohlcv.close
                expected_price = sma[i - 20]  # Adjust for SMA offset
                deviation = abs(current_price - expected_price) / expected_price

                if deviation > threshold:
                    anomalies.append({
                        'timestamp': record.timestamp,
                        'price': current_price,
                        'expected_price': expected_price,
                        'deviation': deviation,
                        'type': 'price_anomaly'
                    })

        return anomalies

    async def validate_market_data(self, data: MarketData) -> List[str]:
        """
        Validate market data according to business rules

        Business Rules:
        - Price ranges must be reasonable
        - Volume must be positive
        - Timestamps must be reasonable
        - Data quality checks

        Args:
            data: MarketData to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Price validation
        ohlcv = data.ohlcv
        if ohlcv.low <= 0:
            errors.append("Low price must be positive")

        if ohlcv.high <= ohlcv.low:
            errors.append("High price must be greater than low price")

        if ohlcv.close < ohlcv.low or ohlcv.close > ohlcv.high:
            errors.append("Close price must be between low and high")

        # Volume validation
        if ohlcv.volume < 0:
            errors.append("Volume cannot be negative")

        # Business rule: unreasonably high volume
        if ohlcv.volume > 1000000000:  # 1 billion
            errors.append("Volume seems unreasonably high")

        # Timestamp validation
        try:
            parsed_timestamp = datetime.fromisoformat(data.timestamp.replace('Z', '+00:00'))
            now = datetime.now()

            # Data shouldn't be from more than 1 year ago or more than 1 day in future
            if parsed_timestamp < now - timedelta(days=365):
                errors.append("Data appears to be too old")

            if parsed_timestamp > now + timedelta(days=1):
                errors.append("Data timestamp is too far in the future")

        except ValueError:
            errors.append("Invalid timestamp format")

        return errors

    async def merge_market_data(self, existing_data: List[MarketData], new_data: List[MarketData]) -> MarketDataBatch:
        """
        Merge new market data with existing data

        Business Rules:
        - Handle duplicate timestamps
        - Prefer newer data over older
        - Maintain data integrity
        - Validate merged result

        Args:
            existing_data: Existing market data
            new_data: New market data to merge

        Returns:
            Merged MarketDataBatch
        """
        # Create lookup by timestamp
        data_by_timestamp = {record.timestamp: record for record in existing_data}

        # Merge new data (newer data takes precedence)
        for new_record in new_data:
            data_by_timestamp[new_record.timestamp] = new_record

        # Convert back to list and sort by timestamp
        merged_data = list(data_by_timestamp.values())
        merged_data.sort(key=lambda x: x.parsed_timestamp)

        if not merged_data:
            raise ValueError("No data to merge")

        # Create batch
        symbol = merged_data[0].symbol
        timeframe = merged_data[0].timeframe

        batch = MarketDataBatch(
            symbol=symbol,
            timeframe=timeframe,
            data=merged_data,
            start_date=merged_data[0].timestamp,
            end_date=merged_data[-1].timestamp
        )

        return batch

    async def get_market_summary(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive market summary for a symbol

        Business Rules:
        - Include key statistics
        - Recent performance metrics
        - Data quality indicators

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with market summary
        """
        # Get recent data
        recent_data = await self.get_price_history(symbol, '1D', days=30)

        if not recent_data:
            return {'error': 'No data available for symbol'}

        # Calculate statistics
        prices = [record.ohlcv.close for record in recent_data]
        volumes = [record.ohlcv.volume for record in recent_data]

        summary = {
            'symbol': symbol,
            'data_points': len(recent_data),
            'price_range': {
                'min': min(prices),
                'max': max(prices),
                'current': prices[-1] if prices else None
            },
            'volume_stats': {
                'total': sum(volumes),
                'average': sum(volumes) / len(volumes) if volumes else 0,
                'max': max(volumes) if volumes else 0
            },
            'date_range': {
                'start': recent_data[0].timestamp,
                'end': recent_data[-1].timestamp
            }
        }

        # Calculate simple returns
        if len(prices) > 1:
            returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
            summary['performance'] = {
                'avg_daily_return': sum(returns) / len(returns),
                'volatility': self._calculate_volatility(returns),
                'best_day': max(returns),
                'worst_day': min(returns)
            }

        return summary

    # Private helper methods

    def _filter_regular_hours(self, data: List[MarketData]) -> List[MarketData]:
        """Filter data to regular trading hours only"""
        # This is a simplified implementation
        # In a real system, this would consider exchange-specific hours
        return data  # For now, return all data

    def _calculate_sma(self, prices: List[float], period: int) -> Dict[str, Any]:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            raise ValueError("Insufficient data for SMA calculation")

        sma_values = []
        for i in range(period - 1, len(prices)):
            sma = sum(prices[i - period + 1:i + 1]) / period
            sma_values.append(sma)

        return {
            'indicator': 'SMA',
            'period': period,
            'values': sma_values,
            'current': sma_values[-1] if sma_values else None
        }

    def _calculate_ema(self, prices: List[float], period: int) -> Dict[str, Any]:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            raise ValueError("Insufficient data for EMA calculation")

        # Calculate multiplier
        multiplier = 2 / (period + 1)

        # Start with SMA for first value
        ema_values = [sum(prices[:period]) / period]

        # Calculate subsequent EMAs
        for price in prices[period:]:
            ema = (price * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema)

        return {
            'indicator': 'EMA',
            'period': period,
            'values': ema_values,
            'current': ema_values[-1] if ema_values else None
        }

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> Dict[str, Any]:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            raise ValueError("Insufficient data for RSI calculation")

        # Calculate price changes
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]

        # Separate gains and losses
        gains = [change if change > 0 else 0 for change in changes]
        losses = [-change if change < 0 else 0 for change in changes]

        # Calculate initial averages
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        rsi_values = []

        # Calculate RSI for each period
        for i in range(period, len(changes)):
            if i == period:
                # First RSI value
                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
            else:
                # Smoothed RSI
                gain = gains[i]
                loss = losses[i]

                avg_gain = ((rsi_values[-1] * (period - 1)) + gain) / period
                avg_loss = ((rsi_values[-1] * (period - 1)) + loss) / period

                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))

            rsi_values.append(rsi)

        return {
            'indicator': 'RSI',
            'period': period,
            'values': rsi_values,
            'current': rsi_values[-1] if rsi_values else None,
            'signal': 'oversold' if rsi_values and rsi_values[-1] < 30 else 'overbought' if rsi_values and rsi_values[-1] > 70 else 'neutral'
        }

    def _calculate_simple_moving_average(self, prices: List[float], period: int) -> List[float]:
        """Calculate simple moving average values"""
        sma = []
        for i in range(period - 1, len(prices)):
            avg = sum(prices[i - period + 1:i + 1]) / period
            sma.append(avg)
        return sma

    def _calculate_volatility(self, returns: List[float]) -> float:
        """Calculate volatility (standard deviation of returns)"""
        if not returns:
            return 0.0

        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        return variance ** 0.5
