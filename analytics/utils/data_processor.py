"""
Data Processing Utilities
========================

Helper functions for processing and transforming market data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DataProcessor:
    """Utility class for processing market data."""

    @staticmethod
    def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for market data."""
        if df.empty:
            return df

        df = df.copy()

        # Ensure we have required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            logger.warning("Missing required columns for technical indicators")
            return df

        # Simple Moving Averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()

        # Exponential Moving Averages
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()

        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']

        # RSI (Relative Strength Index)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)

        # Volume indicators
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma_20']

        # Price change indicators
        df['price_change'] = df['close'].pct_change()
        df['price_change_5'] = df['close'].pct_change(5)
        df['price_change_10'] = df['close'].pct_change(10)

        logger.info("Calculated technical indicators for dataset")
        return df

    @staticmethod
    def detect_volume_spikes(df: pd.DataFrame,
                           window: int = 20,
                           threshold: float = 1.5) -> pd.DataFrame:
        """Detect volume spikes in the data."""
        if df.empty or 'volume' not in df.columns:
            return df

        df = df.copy()

        # Calculate rolling volume average
        df['volume_ma'] = df['volume'].rolling(window=window).mean()
        df['volume_spike'] = df['volume'] / df['volume_ma']

        # Mark spikes above threshold
        df['is_volume_spike'] = df['volume_spike'] >= threshold

        spike_count = df['is_volume_spike'].sum()
        logger.info(f"Detected {spike_count} volume spikes (threshold: {threshold})")

        return df

    @staticmethod
    def identify_time_windows(df: pd.DataFrame,
                            start_time: str = "09:35",
                            end_time: str = "09:50") -> pd.DataFrame:
        """Identify data points within specific time windows."""
        if df.empty or 'timestamp' not in df.columns:
            return df

        df = df.copy()

        # Extract time from timestamp
        df['time'] = pd.to_datetime(df['timestamp']).dt.time

        # Define time window
        start = pd.to_datetime(start_time).time()
        end = pd.to_datetime(end_time).time()

        # Mark points within time window
        df['in_time_window'] = df['time'].between(start, end)

        window_count = df['in_time_window'].sum()
        logger.info(f"Found {window_count} data points in time window {start_time}-{end_time}")

        return df

    @staticmethod
    def calculate_breakout_metrics(df: pd.DataFrame,
                                 lookback_period: int = 10,
                                 breakout_window: int = 60) -> pd.DataFrame:
        """Calculate breakout-related metrics."""
        if df.empty:
            return df

        df = df.copy()

        # Rolling statistics for lookback period
        df['lookback_high'] = df['high'].rolling(window=lookback_period).max()
        df['lookback_low'] = df['low'].rolling(window=lookback_period).min()
        df['lookback_volume_avg'] = df['volume'].rolling(window=lookback_period).mean()

        # Future price movement (breakout window)
        df['future_high'] = df['high'].shift(-breakout_window).rolling(window=breakout_window).max()
        df['future_low'] = df['low'].shift(-breakout_window).rolling(window=breakout_window).min()

        # Breakout calculations
        df['breakout_up'] = df['close'] > df['lookback_high']
        df['breakout_down'] = df['close'] < df['lookback_low']

        # Breakout magnitude
        df['breakout_up_pct'] = (df['close'] - df['lookback_high']) / df['lookback_high']
        df['breakout_down_pct'] = (df['lookback_low'] - df['close']) / df['lookback_low']

        # Volume confirmation
        df['volume_confirmation'] = df['volume'] > df['lookback_volume_avg']

        logger.info("Calculated breakout metrics")
        return df

    @staticmethod
    def filter_significant_patterns(df: pd.DataFrame,
                                 min_volume_multiplier: float = 1.5,
                                 min_price_move: float = 0.02) -> pd.DataFrame:
        """Filter for significant breakout patterns."""
        if df.empty:
            return df

        # Apply filters
        filtered = df[
            (df['volume_spike'] >= min_volume_multiplier) &
            (
                (df['breakout_up_pct'] >= min_price_move) |
                (df['breakout_down_pct'] >= min_price_move)
            ) &
            (df['volume_confirmation'] == True)
        ].copy()

        logger.info(f"Filtered {len(filtered)} significant patterns from {len(df)} total")
        return filtered

    @staticmethod
    def aggregate_by_time_window(df: pd.DataFrame,
                               time_windows: List[Tuple[str, str]] = None) -> pd.DataFrame:
        """Aggregate pattern statistics by time windows."""
        if df.empty or 'timestamp' not in df.columns:
            return pd.DataFrame()

        if time_windows is None:
            time_windows = [
                ("09:35", "09:50"),
                ("10:00", "10:30"),
                ("14:00", "15:30")
            ]

        results = []

        for start_time, end_time in time_windows:
            # Filter data for time window
            window_data = DataProcessor.identify_time_windows(df, start_time, end_time)
            window_patterns = window_data[window_data['in_time_window']]

            if len(window_patterns) > 0:
                stats = {
                    'time_window': f"{start_time}-{end_time}",
                    'total_patterns': len(window_patterns),
                    'volume_spikes': window_patterns['is_volume_spike'].sum(),
                    'breakouts_up': window_patterns['breakout_up'].sum(),
                    'breakouts_down': window_patterns['breakout_down'].sum(),
                    'avg_volume_multiplier': window_patterns['volume_spike'].mean(),
                    'avg_price_move': window_patterns['breakout_up_pct'].mean(),
                    'success_rate': (window_patterns['breakout_up'].sum() /
                                   len(window_patterns)) if len(window_patterns) > 0 else 0
                }
                results.append(stats)

        return pd.DataFrame(results)

    @staticmethod
    def export_patterns_to_csv(df: pd.DataFrame,
                             filename: str = "patterns_export.csv") -> None:
        """Export patterns to CSV file."""
        if df.empty:
            logger.warning("No data to export")
            return

        df.to_csv(filename, index=False)
        logger.info(f"Exported {len(df)} patterns to {filename}")

    @staticmethod
    def generate_pattern_report(df: pd.DataFrame) -> Dict[str, Any]:
        """Generate a summary report of detected patterns."""
        if df.empty:
            return {"error": "No data available"}

        report = {
            "total_records": len(df),
            "date_range": {
                "start": df['timestamp'].min() if 'timestamp' in df.columns else None,
                "end": df['timestamp'].max() if 'timestamp' in df.columns else None
            },
            "pattern_statistics": {
                "volume_spikes": int(df['is_volume_spike'].sum()) if 'is_volume_spike' in df.columns else 0,
                "breakouts_up": int(df['breakout_up'].sum()) if 'breakout_up' in df.columns else 0,
                "breakouts_down": int(df['breakout_down'].sum()) if 'breakout_down' in df.columns else 0
            },
            "average_metrics": {
                "volume_multiplier": float(df['volume_spike'].mean()) if 'volume_spike' in df.columns else 0,
                "price_move_pct": float(df['breakout_up_pct'].mean()) if 'breakout_up_pct' in df.columns else 0
            }
        }

        return report
