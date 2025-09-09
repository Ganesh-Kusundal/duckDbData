"""
NSE Utilities for Tick Size and Quantity Handling
===============================================

Handles NSE-specific requirements for price rounding, tick sizes,
and quantity validation for Indian equity markets.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional
import yaml
import os


class NSEUtils:
    """Utility class for NSE market conventions"""

    def __init__(self, config_path: str = None):
        """Initialize with NSE configuration"""
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'nse_ticks.yaml')

        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Parse tick size ranges
        self.tick_sizes = self._parse_tick_sizes()

    def _parse_tick_sizes(self) -> Dict[tuple, float]:
        """Parse tick size configuration into usable ranges"""
        ranges = {}
        for range_str, tick_size in self.config['tick_sizes'].items():
            if range_str == "500+":
                ranges[(500.0, float('inf'))] = tick_size
            else:
                min_price, max_price = map(float, range_str.split('-'))
                ranges[(min_price, max_price)] = tick_size
        return ranges

    def get_tick_size(self, price: Decimal) -> Decimal:
        """
        Get appropriate tick size for given price

        Args:
            price: Current market price

        Returns:
            Tick size as Decimal
        """
        price_float = float(price)

        for (min_price, max_price), tick_size in self.tick_sizes.items():
            if min_price <= price_float < max_price:
                return Decimal(str(tick_size))

        # Default to smallest tick size if not found
        return Decimal('0.05')

    def round_to_tick(self, price: Decimal) -> Decimal:
        """
        Round price to nearest valid tick

        Args:
            price: Price to round

        Returns:
            Rounded price
        """
        tick_size = self.get_tick_size(price)
        if tick_size == 0:
            return price

        # Round to nearest tick using banker's rounding
        multiplier = Decimal('1') / tick_size
        rounded = (price * multiplier).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        return rounded / multiplier

    def validate_quantity(self, quantity: int) -> int:
        """
        Validate and round quantity to valid lot size

        Args:
            quantity: Desired quantity

        Returns:
            Validated quantity (must be positive integer)
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        # For NSE cash market, most stocks have lot size of 1
        # Round down to nearest integer
        return int(quantity)

    def apply_price_bands(self, price: Decimal, previous_close: Decimal) -> Decimal:
        """
        Apply NSE price bands to limit price movement

        Args:
            price: Proposed price
            previous_close: Previous day's close

        Returns:
            Price clamped to price bands
        """
        bands = self.config['price_bands']['default']

        lower_limit = previous_close * (1 + Decimal(str(bands['lower_limit_pct'])) / 100)
        upper_limit = previous_close * (1 + Decimal(str(bands['upper_limit_pct'])) / 100)

        return max(lower_limit, min(upper_limit, price))

    def calculate_fees(self, trade_value: Decimal, is_sell: bool = False) -> Dict[str, Decimal]:
        """
        Calculate total trading fees for a trade

        Args:
            trade_value: Total trade value
            is_sell: Whether this is a sell transaction

        Returns:
            Dictionary of fee components
        """
        fees = self.config['fees']

        # Brokerage
        brokerage = trade_value * Decimal(str(fees['brokerage_per_trade']))

        # STT only on sell
        stt = trade_value * Decimal(str(fees['stt'])) if is_sell else Decimal('0')

        # Transaction charges
        transaction = trade_value * Decimal(str(fees['transaction_charges']))

        # GST on brokerage
        gst = brokerage * Decimal(str(fees['gst']))

        # SEBI charges
        sebi = trade_value * Decimal(str(fees['sebi_charges']))

        total_fees = brokerage + stt + transaction + gst + sebi

        return {
            'brokerage': brokerage,
            'stt': stt,
            'transaction': transaction,
            'gst': gst,
            'sebi': sebi,
            'total': total_fees
        }

    def apply_slippage(self, price: Decimal, slippage_bps: float) -> Decimal:
        """
        Apply slippage to price for backtesting

        Args:
            price: Base price
            slippage_bps: Slippage in basis points

        Returns:
            Adjusted price with slippage
        """
        slippage_factor = Decimal(str(slippage_bps)) / Decimal('10000')  # Convert bps to decimal
        return price * (Decimal('1') + slippage_factor)


# Global instance for convenience
nse_utils = NSEUtils()
