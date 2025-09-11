"""
Indicator Calculation Service

This module defines the IndicatorCalculationService domain service
for calculating technical indicators and managing their lifecycle.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal

from domain.shared.exceptions import DomainException
from ..entities.indicator import Indicator, IndicatorId, IndicatorType, IndicatorValue
from ..entities.analysis import Symbol
from ..repositories.indicator_repository import IndicatorRepository


class IndicatorCalculationService:
    """
    Domain service for indicator calculation and management.

    Handles the business logic for calculating technical indicators,
    validating their parameters, and managing their lifecycle.
    """

    def __init__(self, indicator_repository: IndicatorRepository):
        self.indicator_repository = indicator_repository

    def calculate_indicator(
        self,
        indicator: Indicator,
        price_data: List[Dict[str, Any]]
    ) -> Indicator:
        """
        Calculate indicator values using provided price data.

        Args:
            indicator: The indicator to calculate
            price_data: List of OHLCV data points

        Returns:
            Indicator: Updated indicator with calculated values
        """
        if not price_data:
            raise DomainException("Price data is required for indicator calculation")

        if not indicator.is_ready_for_calculation(len(price_data)):
            raise DomainException(
                f"Insufficient data for {indicator.indicator_type.value} calculation. "
                f"Need at least {indicator.parameters.period} data points, got {len(price_data)}"
            )

        # Calculate indicator values based on type
        values = self._calculate_indicator_values(indicator, price_data)

        # Add calculated values to indicator
        for value in values:
            indicator.add_value(value)

        # Save updated indicator
        self.indicator_repository.save(indicator)

        return indicator

    def _calculate_indicator_values(
        self,
        indicator: Indicator,
        price_data: List[Dict[str, Any]]
    ) -> List[IndicatorValue]:
        """
        Calculate indicator values based on indicator type.

        This is a simplified implementation. In a real system,
        this would use specialized calculation libraries.
        """
        values = []

        if indicator.indicator_type == IndicatorType.MOVING_AVERAGE:
            values = self._calculate_moving_average(indicator, price_data)
        elif indicator.indicator_type == IndicatorType.RSI:
            values = self._calculate_rsi(indicator, price_data)
        elif indicator.indicator_type == IndicatorType.MACD:
            values = self._calculate_macd(indicator, price_data)
        elif indicator.indicator_type == IndicatorType.BOLLINGER_BANDS:
            values = self._calculate_bollinger_bands(indicator, price_data)
        elif indicator.indicator_type == IndicatorType.STOCHASTIC:
            values = self._calculate_stochastic(indicator, price_data)
        else:
            raise DomainException(f"Unsupported indicator type: {indicator.indicator_type.value}")

        return values

    def _calculate_moving_average(
        self,
        indicator: Indicator,
        price_data: List[Dict[str, Any]]
    ) -> List[IndicatorValue]:
        """Calculate simple moving average."""
        values = []
        period = indicator.parameters.period

        for i in range(period - 1, len(price_data)):
            # Calculate average of last 'period' closing prices
            prices = [Decimal(str(data['close'])) for data in price_data[i-period+1:i+1]]
            avg_price = sum(prices) / len(prices)

            value = IndicatorValue(
                indicator_id=indicator.id,
                value=avg_price,
                timestamp=datetime.fromisoformat(price_data[i]['timestamp']),
                metadata={'indicator_type': indicator.indicator_type}
            )
            values.append(value)

        return values

    def _calculate_rsi(
        self,
        indicator: Indicator,
        price_data: List[Dict[str, Any]]
    ) -> List[IndicatorValue]:
        """Calculate Relative Strength Index."""
        values = []
        period = indicator.parameters.period

        if len(price_data) < period + 1:
            return values

        # Calculate price changes
        gains = []
        losses = []

        for i in range(1, len(price_data)):
            change = Decimal(str(price_data[i]['close'])) - Decimal(str(price_data[i-1]['close']))
            if change > 0:
                gains.append(change)
                losses.append(Decimal('0'))
            else:
                gains.append(Decimal('0'))
                losses.append(abs(change))

        # Calculate RSI
        for i in range(period, len(price_data)):
            avg_gain = sum(gains[i-period:i]) / period
            avg_loss = sum(losses[i-period:i]) / period

            if avg_loss == 0:
                rsi = Decimal('100')
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))

            value = IndicatorValue(
                indicator_id=indicator.id,
                value=rsi,
                timestamp=datetime.fromisoformat(price_data[i]['timestamp']),
                metadata={
                    'indicator_type': indicator.indicator_type,
                    'avg_gain': avg_gain,
                    'avg_loss': avg_loss
                }
            )
            values.append(value)

        return values

    def _calculate_macd(
        self,
        indicator: Indicator,
        price_data: List[Dict[str, Any]]
    ) -> List[IndicatorValue]:
        """Calculate MACD (simplified version)."""
        values = []
        fast_period = indicator.parameters.get_parameter('fast_period', 12)
        slow_period = indicator.parameters.get_parameter('slow_period', 26)

        if len(price_data) < slow_period:
            return values

        # Calculate fast and slow EMAs (simplified as SMAs for this example)
        for i in range(slow_period - 1, len(price_data)):
            fast_prices = [Decimal(str(data['close'])) for data in price_data[i-fast_period+1:i+1]]
            slow_prices = [Decimal(str(data['close'])) for data in price_data[i-slow_period+1:i+1]]

            fast_ema = sum(fast_prices) / len(fast_prices)
            slow_ema = sum(slow_prices) / len(slow_prices)
            macd = fast_ema - slow_ema

            value = IndicatorValue(
                indicator_id=indicator.id,
                value=macd,
                timestamp=datetime.fromisoformat(price_data[i]['timestamp']),
                metadata={
                    'indicator_type': indicator.indicator_type,
                    'fast_ema': fast_ema,
                    'slow_ema': slow_ema
                }
            )
            values.append(value)

        return values

    def _calculate_bollinger_bands(
        self,
        indicator: Indicator,
        price_data: List[Dict[str, Any]]
    ) -> List[IndicatorValue]:
        """Calculate Bollinger Bands (simplified version)."""
        values = []
        period = indicator.parameters.period
        std_dev_multiplier = indicator.parameters.get_parameter('std_dev_multiplier', 2)

        for i in range(period - 1, len(price_data)):
            prices = [Decimal(str(data['close'])) for data in price_data[i-period+1:i+1]]

            # Calculate SMA
            sma = sum(prices) / len(prices)

            # Calculate standard deviation
            variance = sum((price - sma) ** 2 for price in prices) / len(prices)
            std_dev = variance ** Decimal('0.5')

            # Calculate bands
            upper_band = sma + (std_dev * Decimal(str(std_dev_multiplier)))
            lower_band = sma - (std_dev * Decimal(str(std_dev_multiplier)))

            # Return the middle band (SMA) as the main value
            value = IndicatorValue(
                indicator_id=indicator.id,
                value=sma,
                timestamp=datetime.fromisoformat(price_data[i]['timestamp']),
                metadata={
                    'indicator_type': indicator.indicator_type,
                    'upper_band': upper_band,
                    'lower_band': lower_band,
                    'std_dev': std_dev
                }
            )
            values.append(value)

        return values

    def _calculate_stochastic(
        self,
        indicator: Indicator,
        price_data: List[Dict[str, Any]]
    ) -> List[IndicatorValue]:
        """Calculate Stochastic Oscillator (simplified version)."""
        values = []
        k_period = indicator.parameters.period

        for i in range(k_period - 1, len(price_data)):
            # Get highest high and lowest low for the period
            period_data = price_data[i-k_period+1:i+1]
            highs = [Decimal(str(data['high'])) for data in period_data]
            lows = [Decimal(str(data['low'])) for data in period_data]

            highest_high = max(highs)
            lowest_low = min(lows)
            current_close = Decimal(str(price_data[i]['close']))

            # Calculate %K
            if highest_high == lowest_low:
                k_value = Decimal('50')  # Neutral when no range
            else:
                k_value = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100

            value = IndicatorValue(
                indicator_id=indicator.id,
                value=k_value,
                timestamp=datetime.fromisoformat(price_data[i]['timestamp']),
                metadata={
                    'indicator_type': indicator.indicator_type,
                    'highest_high': highest_high,
                    'lowest_low': lowest_low
                }
            )
            values.append(value)

        return values

    def get_indicator_signals(
        self,
        indicator: Indicator,
        threshold: Optional[Decimal] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate trading signals from indicator values.

        Args:
            indicator: The indicator to analyze
            threshold: Optional signal threshold

        Returns:
            List of signal dictionaries
        """
        signals = []

        if not indicator.calculated_values:
            return signals

        # Generate signals based on indicator type
        if indicator.indicator_type == IndicatorType.RSI:
            signals = self._generate_rsi_signals(indicator, threshold)
        elif indicator.indicator_type == IndicatorType.MACD:
            signals = self._generate_macd_signals(indicator, threshold)
        elif indicator.indicator_type == IndicatorType.STOCHASTIC:
            signals = self._generate_stochastic_signals(indicator, threshold)
        # Add more signal generation logic for other indicators

        return signals

    def _generate_rsi_signals(
        self,
        indicator: Indicator,
        threshold: Optional[Decimal]
    ) -> List[Dict[str, Any]]:
        """Generate signals from RSI indicator."""
        signals = []
        oversold = threshold or Decimal('30')
        overbought = threshold or Decimal('70')

        for value in indicator.calculated_values:
            if value.value <= oversold:
                signals.append({
                    'timestamp': value.timestamp,
                    'signal': 'BUY',
                    'confidence': min(1.0, (oversold - value.value) / oversold),
                    'reason': f'RSI oversold at {value.value}'
                })
            elif value.value >= overbought:
                signals.append({
                    'timestamp': value.timestamp,
                    'signal': 'SELL',
                    'confidence': min(1.0, (value.value - overbought) / (100 - overbought)),
                    'reason': f'RSI overbought at {value.value}'
                })

        return signals

    def _generate_macd_signals(
        self,
        indicator: Indicator,
        threshold: Optional[Decimal]
    ) -> List[Dict[str, Any]]:
        """Generate signals from MACD indicator."""
        signals = []

        for i, value in enumerate(indicator.calculated_values):
            if i == 0:
                continue

            prev_value = indicator.calculated_values[i-1]

            if value.value > 0 and prev_value.value <= 0:
                signals.append({
                    'timestamp': value.timestamp,
                    'signal': 'BUY',
                    'confidence': Decimal('0.7'),
                    'reason': 'MACD crossover above zero'
                })
            elif value.value < 0 and prev_value.value >= 0:
                signals.append({
                    'timestamp': value.timestamp,
                    'signal': 'SELL',
                    'confidence': Decimal('0.7'),
                    'reason': 'MACD crossover below zero'
                })

        return signals

    def _generate_stochastic_signals(
        self,
        indicator: Indicator,
        threshold: Optional[Decimal]
    ) -> List[Dict[str, Any]]:
        """Generate signals from Stochastic indicator."""
        signals = []
        oversold = threshold or Decimal('20')
        overbought = threshold or Decimal('80')

        for value in indicator.calculated_values:
            if value.value <= oversold:
                signals.append({
                    'timestamp': value.timestamp,
                    'signal': 'BUY',
                    'confidence': min(1.0, (oversold - value.value) / oversold),
                    'reason': f'Stochastic oversold at {value.value}'
                })
            elif value.value >= overbought:
                signals.append({
                    'timestamp': value.timestamp,
                    'signal': 'SELL',
                    'confidence': min(1.0, (value.value - overbought) / (100 - overbought)),
                    'reason': f'Stochastic overbought at {value.value}'
                })

        return signals

