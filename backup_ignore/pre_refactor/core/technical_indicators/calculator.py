"""
Technical Indicators Calculator

Calculates comprehensive technical indicators including:
- All standard indicators (RSI, MACD, ADX, ATR, etc.)
- Support/Resistance zones
- Supply/Demand zones
- Pivot points
- Price action patterns
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, date
import logging
from pathlib import Path

# Import technical analysis libraries
ta = None
talib = None

try:
    import pandas_ta as ta
except ImportError:
    try:
        import talib
    except ImportError:
        pass

if ta is None and talib is None:
    logging.warning("No technical analysis library available. Install with: pip install pandas_ta or pip install TA-Lib")

from .schema import TechnicalIndicatorsSchema, TimeFrame

logger = logging.getLogger(__name__)


class TechnicalIndicatorsCalculator:
    """
    Comprehensive technical indicators calculator.
    
    Calculates all technical indicators, zones, and patterns defined in the schema.
    Uses pandas_ta library for standard indicators and custom implementations for zones.
    """
    
    def __init__(self):
        """Initialize the calculator."""
        if ta is None and talib is None:
            logger.warning("No technical analysis library available. Using fallback implementations.")
        
        self.schema = TechnicalIndicatorsSchema()
        self.use_ta = ta is not None
        self.use_talib = talib is not None
    
    def calculate_all_indicators(self, 
                               df: pd.DataFrame, 
                               symbol: str, 
                               timeframe: str) -> pd.DataFrame:
        """
        Calculate all technical indicators for the given OHLCV data.
        
        Args:
            df: OHLCV DataFrame with columns [open, high, low, close, volume, timestamp]
            symbol: Trading symbol
            timeframe: Timeframe string (1T, 5T, 15T, 1H, 1D)
            
        Returns:
            pd.DataFrame: Complete indicators DataFrame following the schema
        """
        if df.empty:
            return self.schema.create_empty_dataframe()
        
        logger.info(f"Calculating indicators for {symbol} {timeframe} - {len(df)} records")
        
        # Ensure required columns exist
        required_cols = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Sort by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Create result DataFrame with base structure
        result = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
        
        # Add metadata columns
        result['symbol'] = symbol
        result['timeframe'] = timeframe
        result['date_partition'] = pd.to_datetime(result['timestamp']).dt.date
        result['calculation_timestamp'] = datetime.now()
        result['lookback_periods'] = len(df)
        
        # Calculate all indicator categories
        try:
            # Moving Averages
            self._calculate_moving_averages(result)
            
            # Momentum Indicators
            self._calculate_momentum_indicators(result)
            
            # Trend Indicators
            self._calculate_trend_indicators(result)
            
            # Volatility Indicators
            self._calculate_volatility_indicators(result)
            
            # Volume Indicators
            self._calculate_volume_indicators(result)
            
            # MACD
            self._calculate_macd(result)
            
            # Pivot Points
            self._calculate_pivot_points(result, timeframe)
            
            # Fibonacci Levels
            self._calculate_fibonacci_levels(result)
            
            # Support/Resistance Zones
            self._calculate_support_resistance_zones(result)
            
            # Supply/Demand Zones
            self._calculate_supply_demand_zones(result)
            
            # Price Action Patterns
            self._calculate_price_action_patterns(result)
            
            # Market Structure
            self._calculate_market_structure(result)
            
            # Data Quality Score
            self._calculate_data_quality_score(result)
            
            logger.info(f"Successfully calculated all indicators for {symbol} {timeframe}")
            
        except Exception as e:
            logger.error(f"Error calculating indicators for {symbol} {timeframe}: {e}")
            raise
        
        return result
    
    def _calculate_moving_averages(self, df: pd.DataFrame) -> None:
        """Calculate Simple and Exponential Moving Averages."""
        if self.use_ta:
            # Simple Moving Averages
            df['sma_10'] = ta.sma(df['close'], length=10)
            df['sma_20'] = ta.sma(df['close'], length=20)
            df['sma_50'] = ta.sma(df['close'], length=50)
            df['sma_100'] = ta.sma(df['close'], length=100)
            df['sma_200'] = ta.sma(df['close'], length=200)
            
            # Exponential Moving Averages
            df['ema_10'] = ta.ema(df['close'], length=10)
            df['ema_20'] = ta.ema(df['close'], length=20)
            df['ema_50'] = ta.ema(df['close'], length=50)
            df['ema_100'] = ta.ema(df['close'], length=100)
            df['ema_200'] = ta.ema(df['close'], length=200)
        elif self.use_talib:
            # Simple Moving Averages using TA-Lib
            df['sma_10'] = talib.SMA(df['close'], timeperiod=10)
            df['sma_20'] = talib.SMA(df['close'], timeperiod=20)
            df['sma_50'] = talib.SMA(df['close'], timeperiod=50)
            df['sma_100'] = talib.SMA(df['close'], timeperiod=100)
            df['sma_200'] = talib.SMA(df['close'], timeperiod=200)
            
            # Exponential Moving Averages using TA-Lib
            df['ema_10'] = talib.EMA(df['close'], timeperiod=10)
            df['ema_20'] = talib.EMA(df['close'], timeperiod=20)
            df['ema_50'] = talib.EMA(df['close'], timeperiod=50)
            df['ema_100'] = talib.EMA(df['close'], timeperiod=100)
            df['ema_200'] = talib.EMA(df['close'], timeperiod=200)
        else:
            # Fallback implementations using pandas
            df['sma_10'] = df['close'].rolling(window=10).mean()
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['sma_100'] = df['close'].rolling(window=100).mean()
            df['sma_200'] = df['close'].rolling(window=200).mean()
            
            # Simple EMA implementation
            df['ema_10'] = df['close'].ewm(span=10).mean()
            df['ema_20'] = df['close'].ewm(span=20).mean()
            df['ema_50'] = df['close'].ewm(span=50).mean()
            df['ema_100'] = df['close'].ewm(span=100).mean()
            df['ema_200'] = df['close'].ewm(span=200).mean()
    
    def _calculate_momentum_indicators(self, df: pd.DataFrame) -> None:
        """Calculate momentum indicators."""
        if self.use_ta:
            # RSI
            df['rsi_14'] = ta.rsi(df['close'], length=14)
            df['rsi_21'] = ta.rsi(df['close'], length=21)
            
            # Stochastic
            stoch = ta.stoch(df['high'], df['low'], df['close'], k=14, d=3)
            if stoch is not None and not stoch.empty:
                df['stoch_k'] = stoch.iloc[:, 0] if len(stoch.columns) > 0 else None
                df['stoch_d'] = stoch.iloc[:, 1] if len(stoch.columns) > 1 else None
            
            # Williams %R
            df['williams_r'] = ta.willr(df['high'], df['low'], df['close'], length=14)
        elif self.use_talib:
            # RSI using TA-Lib
            df['rsi_14'] = talib.RSI(df['close'], timeperiod=14)
            df['rsi_21'] = talib.RSI(df['close'], timeperiod=21)
            
            # Stochastic using TA-Lib
            df['stoch_k'], df['stoch_d'] = talib.STOCH(df['high'], df['low'], df['close'], 
                                                     fastk_period=14, slowk_period=3, slowd_period=3)
            
            # Williams %R using TA-Lib
            df['williams_r'] = talib.WILLR(df['high'], df['low'], df['close'], timeperiod=14)
        else:
            # Fallback RSI implementation
            df['rsi_14'] = self._calculate_rsi_fallback(df['close'], 14)
            df['rsi_21'] = self._calculate_rsi_fallback(df['close'], 21)
            
            # Simple stochastic implementation
            df['stoch_k'] = ((df['close'] - df['low'].rolling(14).min()) / 
                           (df['high'].rolling(14).max() - df['low'].rolling(14).min())) * 100
            df['stoch_d'] = df['stoch_k'].rolling(3).mean()
            
            # Williams %R fallback
            df['williams_r'] = ((df['high'].rolling(14).max() - df['close']) / 
                              (df['high'].rolling(14).max() - df['low'].rolling(14).min())) * -100
    
    def _calculate_trend_indicators(self, df: pd.DataFrame) -> None:
        """Calculate trend indicators."""
        if self.use_ta:
            # ADX
            adx_data = ta.adx(df['high'], df['low'], df['close'], length=14)
            if adx_data is not None and not adx_data.empty:
                df['adx_14'] = adx_data.iloc[:, 0] if len(adx_data.columns) > 0 else None
                df['di_plus'] = adx_data.iloc[:, 1] if len(adx_data.columns) > 1 else None
                df['di_minus'] = adx_data.iloc[:, 2] if len(adx_data.columns) > 2 else None
            
            # ADX 21
            adx_21_data = ta.adx(df['high'], df['low'], df['close'], length=21)
            if adx_21_data is not None and not adx_21_data.empty:
                df['adx_21'] = adx_21_data.iloc[:, 0] if len(adx_21_data.columns) > 0 else None
            
            # Aroon
            aroon_data = ta.aroon(df['high'], df['low'], length=14)
            if aroon_data is not None and not aroon_data.empty:
                df['aroon_up'] = aroon_data.iloc[:, 0] if len(aroon_data.columns) > 0 else None
                df['aroon_down'] = aroon_data.iloc[:, 1] if len(aroon_data.columns) > 1 else None
                df['aroon_oscillator'] = aroon_data.iloc[:, 2] if len(aroon_data.columns) > 2 else None
        elif self.use_talib:
            # ADX using TA-Lib
            df['adx_14'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
            df['adx_21'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=21)
            df['di_plus'] = talib.PLUS_DI(df['high'], df['low'], df['close'], timeperiod=14)
            df['di_minus'] = talib.MINUS_DI(df['high'], df['low'], df['close'], timeperiod=14)
            
            # Aroon using TA-Lib
            df['aroon_down'], df['aroon_up'] = talib.AROON(df['high'], df['low'], timeperiod=14)
            df['aroon_oscillator'] = talib.AROONOSC(df['high'], df['low'], timeperiod=14)
        else:
            # Fallback implementations (simplified)
            df['adx_14'] = None  # ADX is complex, skip for fallback
            df['adx_21'] = None
            df['di_plus'] = None
            df['di_minus'] = None
            
            # Simple Aroon implementation
            high_14 = df['high'].rolling(14)
            low_14 = df['low'].rolling(14)
            
            df['aroon_up'] = ((14 - (high_14.apply(lambda x: 14 - 1 - x.argmax() if len(x) == 14 else np.nan))) / 14) * 100
            df['aroon_down'] = ((14 - (low_14.apply(lambda x: 14 - 1 - x.argmin() if len(x) == 14 else np.nan))) / 14) * 100
            df['aroon_oscillator'] = df['aroon_up'] - df['aroon_down']
    
    def _calculate_volatility_indicators(self, df: pd.DataFrame) -> None:
        """Calculate volatility indicators."""
        if self.use_ta:
            # ATR
            df['atr_14'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            df['atr_21'] = ta.atr(df['high'], df['low'], df['close'], length=21)
        elif self.use_talib:
            # ATR using TA-Lib
            df['atr_14'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
            df['atr_21'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=21)
        else:
            # Fallback ATR implementation
            df['tr'] = np.maximum(df['high'] - df['low'], 
                                np.maximum(abs(df['high'] - df['close'].shift(1)),
                                         abs(df['low'] - df['close'].shift(1))))
            df['atr_14'] = df['tr'].rolling(14).mean()
            df['atr_21'] = df['tr'].rolling(21).mean()
            df.drop('tr', axis=1, inplace=True)
        
        if self.use_ta:
            # Bollinger Bands
            bb_data = ta.bbands(df['close'], length=20, std=2)
            if bb_data is not None and not bb_data.empty:
                df['bb_lower'] = bb_data.iloc[:, 0] if len(bb_data.columns) > 0 else None
                df['bb_middle'] = bb_data.iloc[:, 1] if len(bb_data.columns) > 1 else None
                df['bb_upper'] = bb_data.iloc[:, 2] if len(bb_data.columns) > 2 else None
                df['bb_width'] = bb_data.iloc[:, 3] if len(bb_data.columns) > 3 else None
                df['bb_percent'] = bb_data.iloc[:, 4] if len(bb_data.columns) > 4 else None
            
            # Keltner Channels
            kc_data = ta.kc(df['high'], df['low'], df['close'], length=20)
            if kc_data is not None and not kc_data.empty:
                df['keltner_lower'] = kc_data.iloc[:, 0] if len(kc_data.columns) > 0 else None
                df['keltner_middle'] = kc_data.iloc[:, 1] if len(kc_data.columns) > 1 else None
                df['keltner_upper'] = kc_data.iloc[:, 2] if len(kc_data.columns) > 2 else None
        elif self.use_talib:
            # Bollinger Bands using TA-Lib
            df['bb_upper'], df['bb_middle'], df['bb_lower'] = talib.BBANDS(df['close'], timeperiod=20, nbdevup=2, nbdevdn=2)
            df['bb_width'] = df['bb_upper'] - df['bb_lower']
            df['bb_percent'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            # Keltner Channels (approximation using ATR)
            df['keltner_middle'] = talib.EMA(df['close'], timeperiod=20)
            atr_20 = talib.ATR(df['high'], df['low'], df['close'], timeperiod=20)
            df['keltner_upper'] = df['keltner_middle'] + (2 * atr_20)
            df['keltner_lower'] = df['keltner_middle'] - (2 * atr_20)
        else:
            # Fallback Bollinger Bands
            df['bb_middle'] = df['close'].rolling(20).mean()
            bb_std = df['close'].rolling(20).std()
            df['bb_upper'] = df['bb_middle'] + (2 * bb_std)
            df['bb_lower'] = df['bb_middle'] - (2 * bb_std)
            df['bb_width'] = df['bb_upper'] - df['bb_lower']
            df['bb_percent'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            # Fallback Keltner Channels
            df['keltner_middle'] = df['close'].ewm(span=20).mean()
            df['keltner_upper'] = df['keltner_middle'] + (2 * df['atr_14'])
            df['keltner_lower'] = df['keltner_middle'] - (2 * df['atr_14'])
    
    def _calculate_volume_indicators(self, df: pd.DataFrame) -> None:
        """Calculate volume indicators."""
        if self.use_ta:
            # OBV
            df['obv'] = ta.obv(df['close'], df['volume'])
            
            # Accumulation/Distribution Line
            df['ad_line'] = ta.ad(df['high'], df['low'], df['close'], df['volume'])
            
            # Chaikin Money Flow
            df['cmf'] = ta.cmf(df['high'], df['low'], df['close'], df['volume'], length=20)
            
            # Money Flow Index
            df['mfi'] = ta.mfi(df['high'], df['low'], df['close'], df['volume'], length=14)
        elif self.use_talib:
            # OBV using TA-Lib
            df['obv'] = talib.OBV(df['close'], df['volume'])
            
            # Accumulation/Distribution Line using TA-Lib
            df['ad_line'] = talib.AD(df['high'], df['low'], df['close'], df['volume'])
            
            # Money Flow Index using TA-Lib
            df['mfi'] = talib.MFI(df['high'], df['low'], df['close'], df['volume'], timeperiod=14)
            
            # Chaikin Money Flow (approximation)
            df['cmf'] = None  # Not directly available in TA-Lib
        else:
            # Fallback implementations
            # Simple OBV
            obv = [0]
            for i in range(1, len(df)):
                if df['close'].iloc[i] > df['close'].iloc[i-1]:
                    obv.append(obv[-1] + df['volume'].iloc[i])
                elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                    obv.append(obv[-1] - df['volume'].iloc[i])
                else:
                    obv.append(obv[-1])
            df['obv'] = obv
            
            # Simple A/D Line
            clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
            df['ad_line'] = (clv * df['volume']).cumsum()
            
            # Simplified indicators
            df['cmf'] = None
            df['mfi'] = None
        
        # VWAP - requires proper datetime index
        try:
            # Set timestamp as index for VWAP calculation
            df_temp = df.set_index('timestamp')
            vwap_result = ta.vwap(df_temp['high'], df_temp['low'], df_temp['close'], df_temp['volume'])
            if vwap_result is not None:
                df['vwap'] = vwap_result.values
            else:
                # Manual VWAP calculation as fallback
                df['vwap'] = (df['high'] + df['low'] + df['close']) / 3 * df['volume']
                df['vwap'] = df['vwap'].cumsum() / df['volume'].cumsum()
        except Exception as e:
            logger.warning(f"VWAP calculation failed: {e}, using fallback")
            # Manual VWAP calculation
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            df['vwap'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        
        # Volume SMA and ratio
        if self.use_ta:
            df['volume_sma_20'] = ta.sma(df['volume'], length=20)
        elif self.use_talib:
            df['volume_sma_20'] = talib.SMA(df['volume'], timeperiod=20)
        else:
            df['volume_sma_20'] = df['volume'].rolling(20).mean()
        
        df['volume_ratio'] = df['volume'] / df['volume_sma_20']
    
    def _calculate_macd(self, df: pd.DataFrame) -> None:
        """Calculate MACD indicators."""
        if self.use_ta:
            macd_data = ta.macd(df['close'], fast=12, slow=26, signal=9)
            if macd_data is not None and not macd_data.empty:
                df['macd_line'] = macd_data.iloc[:, 0] if len(macd_data.columns) > 0 else None
                df['macd_histogram'] = macd_data.iloc[:, 1] if len(macd_data.columns) > 1 else None
                df['macd_signal'] = macd_data.iloc[:, 2] if len(macd_data.columns) > 2 else None
        elif self.use_talib:
            df['macd_line'], df['macd_signal'], df['macd_histogram'] = talib.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        else:
            # Fallback MACD implementation
            ema_12 = df['close'].ewm(span=12).mean()
            ema_26 = df['close'].ewm(span=26).mean()
            df['macd_line'] = ema_12 - ema_26
            df['macd_signal'] = df['macd_line'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd_line'] - df['macd_signal']
    
    def _calculate_pivot_points(self, df: pd.DataFrame, timeframe: str) -> None:
        """Calculate traditional pivot points."""
        # For intraday timeframes, calculate daily pivots
        # For daily timeframe, calculate weekly/monthly pivots
        
        if timeframe in ['1T', '5T', '15T', '1H']:
            # Use previous day's data for pivot calculation
            prev_high = df['high'].shift(1).rolling(window=375, min_periods=1).max()  # Approx daily bars
            prev_low = df['low'].shift(1).rolling(window=375, min_periods=1).min()
            prev_close = df['close'].shift(375)  # Previous day close
        else:
            # For daily data, use previous period
            prev_high = df['high'].shift(1)
            prev_low = df['low'].shift(1)
            prev_close = df['close'].shift(1)
        
        # Calculate pivot points
        df['pivot_point'] = (prev_high + prev_low + prev_close) / 3
        
        # Resistance levels
        df['pivot_r1'] = 2 * df['pivot_point'] - prev_low
        df['pivot_r2'] = df['pivot_point'] + (prev_high - prev_low)
        df['pivot_r3'] = prev_high + 2 * (df['pivot_point'] - prev_low)
        
        # Support levels
        df['pivot_s1'] = 2 * df['pivot_point'] - prev_high
        df['pivot_s2'] = df['pivot_point'] - (prev_high - prev_low)
        df['pivot_s3'] = prev_low - 2 * (prev_high - df['pivot_point'])
    
    def _calculate_fibonacci_levels(self, df: pd.DataFrame) -> None:
        """Calculate Fibonacci retracement levels."""
        # Calculate swing high and low over rolling window
        window = min(50, len(df))
        swing_high = df['high'].rolling(window=window, min_periods=1).max()
        swing_low = df['low'].rolling(window=window, min_periods=1).min()
        
        swing_range = swing_high - swing_low
        
        # Fibonacci retracement levels
        df['fib_23_6'] = swing_high - (swing_range * 0.236)
        df['fib_38_2'] = swing_high - (swing_range * 0.382)
        df['fib_50_0'] = swing_high - (swing_range * 0.500)
        df['fib_61_8'] = swing_high - (swing_range * 0.618)
        df['fib_78_6'] = swing_high - (swing_range * 0.786)
    
    def _calculate_support_resistance_zones(self, df: pd.DataFrame) -> None:
        """Calculate support and resistance zones using price action analysis."""
        # Identify swing highs and lows
        window = 10
        
        # Swing highs (resistance candidates)
        swing_highs = df['high'][(df['high'].shift(window) < df['high']) & 
                                (df['high'].shift(-window) < df['high'])]
        
        # Swing lows (support candidates)
        swing_lows = df['low'][(df['low'].shift(window) > df['low']) & 
                              (df['low'].shift(-window) > df['low'])]
        
        # Calculate support levels (most recent swing lows)
        if not swing_lows.empty:
            recent_lows = swing_lows.tail(10).sort_values()
            
            # Group similar levels (within 1% of each other)
            support_levels = self._group_similar_levels(recent_lows.values, tolerance=0.01)
            
            for i, (level, strength) in enumerate(support_levels[:3]):
                df[f'support_level_{i+1}'] = level
                df[f'support_strength_{i+1}'] = strength
        
        # Calculate resistance levels (most recent swing highs)
        if not swing_highs.empty:
            recent_highs = swing_highs.tail(10).sort_values(ascending=False)
            
            # Group similar levels
            resistance_levels = self._group_similar_levels(recent_highs.values, tolerance=0.01)
            
            for i, (level, strength) in enumerate(resistance_levels[:3]):
                df[f'resistance_level_{i+1}'] = level
                df[f'resistance_strength_{i+1}'] = strength
    
    def _calculate_supply_demand_zones(self, df: pd.DataFrame) -> None:
        """Calculate supply and demand zones based on volume and price action."""
        # Supply zones: Areas where price dropped with high volume
        volume_threshold = df['volume'].quantile(0.8)
        price_drop_threshold = -0.02  # 2% drop
        
        price_change = df['close'].pct_change()
        high_volume_drops = (price_change < price_drop_threshold) & (df['volume'] > volume_threshold)
        
        if high_volume_drops.any():
            supply_indices = df.index[high_volume_drops]
            if len(supply_indices) > 0:
                latest_supply_idx = supply_indices[-1]
                df.loc[latest_supply_idx:, 'supply_zone_high'] = df.loc[latest_supply_idx, 'high']
                df.loc[latest_supply_idx:, 'supply_zone_low'] = df.loc[latest_supply_idx, 'low']
                df.loc[latest_supply_idx:, 'supply_zone_volume'] = df.loc[latest_supply_idx, 'volume']
                df.loc[latest_supply_idx:, 'supply_zone_strength'] = abs(price_change.loc[latest_supply_idx]) * 100
        
        # Demand zones: Areas where price rose with high volume
        price_rise_threshold = 0.02  # 2% rise
        high_volume_rises = (price_change > price_rise_threshold) & (df['volume'] > volume_threshold)
        
        if high_volume_rises.any():
            demand_indices = df.index[high_volume_rises]
            if len(demand_indices) > 0:
                latest_demand_idx = demand_indices[-1]
                df.loc[latest_demand_idx:, 'demand_zone_high'] = df.loc[latest_demand_idx, 'high']
                df.loc[latest_demand_idx:, 'demand_zone_low'] = df.loc[latest_demand_idx, 'low']
                df.loc[latest_demand_idx:, 'demand_zone_volume'] = df.loc[latest_demand_idx, 'volume']
                df.loc[latest_demand_idx:, 'demand_zone_strength'] = price_change.loc[latest_demand_idx] * 100
    
    def _calculate_price_action_patterns(self, df: pd.DataFrame) -> None:
        """Calculate price action patterns and candlestick patterns."""
        # Higher highs and higher lows (uptrend)
        df['higher_high'] = df['high'] > df['high'].shift(1)
        df['higher_low'] = df['low'] > df['low'].shift(1)
        df['lower_high'] = df['high'] < df['high'].shift(1)
        df['lower_low'] = df['low'] < df['low'].shift(1)
        
        # Candlestick patterns using pandas_ta
        try:
            # Use available candlestick patterns
            df['doji'] = ta.cdl_doji(df['open'], df['high'], df['low'], df['close'])
            
            # Use generic pattern function for other patterns
            patterns = ta.cdl_pattern(df['open'], df['high'], df['low'], df['close'])
            if patterns is not None and not patterns.empty:
                # Extract specific patterns if available
                if 'CDL_HAMMER' in patterns.columns:
                    df['hammer'] = patterns['CDL_HAMMER']
                else:
                    df['hammer'] = self._detect_hammer_pattern(df)
                
                if 'CDL_SHOOTINGSTAR' in patterns.columns:
                    df['shooting_star'] = patterns['CDL_SHOOTINGSTAR']
                else:
                    df['shooting_star'] = self._detect_shooting_star_pattern(df)
                
                if 'CDL_ENGULFING' in patterns.columns:
                    df['engulfing_bullish'] = patterns['CDL_ENGULFING'] > 0
                    df['engulfing_bearish'] = patterns['CDL_ENGULFING'] < 0
                else:
                    df['engulfing_bullish'] = self._detect_bullish_engulfing(df)
                    df['engulfing_bearish'] = self._detect_bearish_engulfing(df)
            else:
                # Fallback to manual pattern detection
                df['hammer'] = self._detect_hammer_pattern(df)
                df['shooting_star'] = self._detect_shooting_star_pattern(df)
                df['engulfing_bullish'] = self._detect_bullish_engulfing(df)
                df['engulfing_bearish'] = self._detect_bearish_engulfing(df)
            
        except Exception as e:
            logger.warning(f"Error calculating candlestick patterns: {e}")
            # Fallback to manual detection
            df['doji'] = self._detect_doji_pattern(df)
            df['hammer'] = self._detect_hammer_pattern(df)
            df['shooting_star'] = self._detect_shooting_star_pattern(df)
            df['engulfing_bullish'] = self._detect_bullish_engulfing(df)
            df['engulfing_bearish'] = self._detect_bearish_engulfing(df)
        
        # Convert to boolean
        pattern_cols = ['doji', 'hammer', 'shooting_star', 'engulfing_bullish', 'engulfing_bearish']
        for col in pattern_cols:
            if col in df.columns:
                df[col] = df[col].fillna(0) != 0
    
    def _calculate_market_structure(self, df: pd.DataFrame) -> None:
        """Calculate market structure indicators."""
        # Trend direction based on moving averages
        if 'ema_20' in df.columns and 'ema_50' in df.columns:
            trend_condition = df['ema_20'] > df['ema_50']
            df['trend_direction'] = np.where(trend_condition, 'bullish', 
                                           np.where(df['ema_20'] < df['ema_50'], 'bearish', 'sideways'))
        
        # Trend strength based on ADX
        if 'adx_14' in df.columns:
            df['trend_strength'] = df['adx_14']
        
        # Volatility regime based on ATR
        if 'atr_14' in df.columns:
            atr_percentile = df['atr_14'].rolling(window=50, min_periods=1).rank(pct=True)
            df['volatility_regime'] = np.where(atr_percentile > 0.7, 'high',
                                             np.where(atr_percentile < 0.3, 'low', 'medium'))
        
        # Volume regime
        if 'volume_ratio' in df.columns:
            df['volume_regime'] = np.where(df['volume_ratio'] > 1.5, 'high',
                                         np.where(df['volume_ratio'] < 0.7, 'low', 'medium'))
    
    def _calculate_data_quality_score(self, df: pd.DataFrame) -> None:
        """Calculate data quality score based on completeness and consistency."""
        # Count non-null values for key indicators
        key_indicators = ['close', 'volume', 'rsi_14', 'sma_20', 'atr_14']
        available_indicators = [col for col in key_indicators if col in df.columns]
        
        if available_indicators:
            completeness_scores = []
            for col in available_indicators:
                completeness = df[col].notna().mean()
                completeness_scores.append(completeness)
            
            avg_completeness = np.mean(completeness_scores)
            df['data_quality_score'] = avg_completeness * 100
        else:
            df['data_quality_score'] = 0.0
    
    def _group_similar_levels(self, levels: np.ndarray, tolerance: float = 0.01) -> List[Tuple[float, float]]:
        """
        Group similar price levels and calculate their strength.
        
        Args:
            levels: Array of price levels
            tolerance: Tolerance for grouping (as percentage)
            
        Returns:
            List of (level, strength) tuples
        """
        if len(levels) == 0:
            return []
        
        grouped_levels = []
        used_indices = set()
        
        for i, level in enumerate(levels):
            if i in used_indices:
                continue
            
            # Find similar levels
            similar_levels = []
            for j, other_level in enumerate(levels):
                if j not in used_indices and abs(level - other_level) / level <= tolerance:
                    similar_levels.append(other_level)
                    used_indices.add(j)
            
            if similar_levels:
                avg_level = np.mean(similar_levels)
                strength = len(similar_levels)  # Strength based on number of touches
                grouped_levels.append((avg_level, strength))
        
        # Sort by strength (descending)
        grouped_levels.sort(key=lambda x: x[1], reverse=True)
        return grouped_levels
    
    def _detect_doji_pattern(self, df: pd.DataFrame) -> pd.Series:
        """Detect Doji candlestick pattern manually."""
        body_size = abs(df['close'] - df['open'])
        range_size = df['high'] - df['low']
        
        # Doji: body is very small compared to the range
        doji_threshold = 0.1  # Body should be less than 10% of the range
        return (body_size / range_size) <= doji_threshold
    
    def _detect_hammer_pattern(self, df: pd.DataFrame) -> pd.Series:
        """Detect Hammer candlestick pattern manually."""
        body_size = abs(df['close'] - df['open'])
        lower_shadow = np.minimum(df['open'], df['close']) - df['low']
        upper_shadow = df['high'] - np.maximum(df['open'], df['close'])
        
        # Hammer: long lower shadow, small body, small upper shadow
        return (lower_shadow >= 2 * body_size) & (upper_shadow <= body_size)
    
    def _detect_shooting_star_pattern(self, df: pd.DataFrame) -> pd.Series:
        """Detect Shooting Star candlestick pattern manually."""
        body_size = abs(df['close'] - df['open'])
        lower_shadow = np.minimum(df['open'], df['close']) - df['low']
        upper_shadow = df['high'] - np.maximum(df['open'], df['close'])
        
        # Shooting Star: long upper shadow, small body, small lower shadow
        return (upper_shadow >= 2 * body_size) & (lower_shadow <= body_size)
    
    def _detect_bullish_engulfing(self, df: pd.DataFrame) -> pd.Series:
        """Detect Bullish Engulfing pattern manually."""
        prev_open = df['open'].shift(1)
        prev_close = df['close'].shift(1)
        
        # Current candle is bullish and engulfs previous bearish candle
        current_bullish = df['close'] > df['open']
        prev_bearish = prev_close < prev_open
        engulfs = (df['open'] < prev_close) & (df['close'] > prev_open)
        
        return current_bullish & prev_bearish & engulfs
    
    def _detect_bearish_engulfing(self, df: pd.DataFrame) -> pd.Series:
        """Detect Bearish Engulfing pattern manually."""
        prev_open = df['open'].shift(1)
        prev_close = df['close'].shift(1)
        
        # Current candle is bearish and engulfs previous bullish candle
        current_bearish = df['close'] < df['open']
        prev_bullish = prev_close > prev_open
        engulfs = (df['open'] > prev_close) & (df['close'] < prev_open)
        
        return current_bearish & prev_bullish & engulfs
    
    def _calculate_rsi_fallback(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI using pandas (fallback implementation)."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
