"""
Technical Scanner for intraday stock selection.
Identifies stocks based on technical indicators and patterns.
"""

from typing import Dict, Any, List
from datetime import datetime, date, time, timedelta
import pandas as pd
import numpy as np

from ..base_scanner import BaseScanner
from src.domain.services.technical.storage import TechnicalIndicatorsStorage


class TechnicalScanner(BaseScanner):
    """Scanner that identifies stocks based on technical analysis."""

    def __init__(self, db_manager, pattern_analyzer=None):
        super().__init__(db_manager, pattern_analyzer=pattern_analyzer)
        self.ti_storage = TechnicalIndicatorsStorage()

    @property
    def scanner_name(self) -> str:
        return "technical"

    def _get_default_config(self) -> Dict[str, Any]:
        return {
            'required_indicators': ['rsi', 'macd', 'bollinger_bands'],
            'rsi_overbought': 70,         # RSI overbought level
            'rsi_oversold': 30,           # RSI oversold level
            'macd_threshold': 0.1,        # MACD signal strength
            'bb_deviation': 1.5,          # Bollinger Band deviation
            'min_price': 50,              # Minimum stock price
            'max_price': 2000,            # Maximum stock price
            'max_results': 50
        }

    def scan(self, scan_date: date, cutoff_time: time = time(9, 50)) -> pd.DataFrame:
        """
        Scan for stocks with favorable technical patterns.
        
        Args:
            scan_date: Date to scan
            cutoff_time: Time cutoff for scanning
        
        Returns:
            DataFrame with technical scan results
        """
        print(f"📊 Scanning for favorable technical patterns by {cutoff_time}")

        # Get available symbols for technical analysis
        all_symbols = self.get_available_symbols()
        print(f"📈 Analyzing {len(all_symbols)} symbols for technical indicators...")

        # Load indicators for all symbols
        indicators_df = self.ti_storage.load_multiple_symbols(
            symbols=all_symbols,
            timeframe='1D',
            start_date=scan_date - timedelta(days=60),
            end_date=scan_date
        )

        if not indicators_df:
            print("⚠️  No technical indicators found for the given date range.")
            return pd.DataFrame()

        # Combine all dataframes into one
        combined_df = pd.concat(indicators_df.values())

        # Filter for the scan date
        combined_df['date'] = pd.to_datetime(combined_df['timestamp']).dt.date
        scan_day_df = combined_df[combined_df['date'] == scan_date]

        if scan_day_df.empty:
            print("⚠️  No stocks found with favorable technical patterns")
            return pd.DataFrame()

        # Apply filters
        filtered_df = scan_day_df[
            (scan_day_df['close'] > self.config['min_price']) &
            (scan_day_df['close'] < self.config['max_price'])
        ]

        # Add additional analysis
        filtered_df['setup_type'] = filtered_df.apply(
            lambda row: self._classify_technical_setup(row), axis=1
        )

        filtered_df['risk_level'] = filtered_df.apply(
            lambda row: self._assess_risk(row), axis=1
        )

        # Sort and limit results
        final_df = filtered_df.sort_values(by=['risk_level', 'setup_type'], ascending=[True, False]).head(self.config['max_results'])

        print(f"✅ Found {len(final_df)} stocks with favorable technical setups")
        return final_df

    def _classify_technical_setup(self, row) -> str:
        """Classify the type of technical setup."""
        if pd.isna(row.get('rsi_14')) or pd.isna(row.get('macd_histogram')) or pd.isna(row.get('ema_20')) or pd.isna(row.get('ema_50')):
            return "UNKNOWN"

        setup = []

        if row['rsi_14'] <= self.config['rsi_oversold']:
            setup.append("OVERSOLD")
        elif row['rsi_14'] > self.config['rsi_overbought']:
            setup.append("OVERBOUGHT")

        if row['macd_histogram'] > self.config['macd_threshold']:
            setup.append("MACD_BULLISH")
        elif row['macd_histogram'] < -self.config['macd_threshold']:
            setup.append("MACD_BEARISH")

        if row['ema_20'] > row['ema_50']:
            setup.append("TREND_UP")
        elif row['ema_20'] < row['ema_50']:
            setup.append("TREND_DOWN")

        if not setup:
            return "NEUTRAL"

        return " + ".join(sorted(set(setup)))

    def _assess_risk(self, row) -> str:
        """Assess technical risk level."""
        if pd.isna(row.get('rsi_14')) or pd.isna(row.get('bb_bbm')):
            return "UNKNOWN"

        risk_factors = 0

        # RSI near extremes
        if row['rsi_14'] >= 75 or row['rsi_14'] <= 25:
            risk_factors += 2

        # Price at Bollinger Band extremes
        if row['close'] <= row['bb_bbl'] or row['close'] >= row['bb_bbh']:
            risk_factors += 1

        # Volatility warning
        if abs(row.get('price_change_pct', 0)) > 3:
            risk_factors += 1

        if risk_factors >= 3:
            return "HIGH_RISK"
        elif risk_factors >= 2:
            return "MEDIUM_RISK"
        elif risk_factors >= 1:
            return "LOW_RISK"
        else:
            return "VERY_LOW_RISK"
