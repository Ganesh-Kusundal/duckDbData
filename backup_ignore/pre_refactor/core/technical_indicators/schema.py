"""
Technical Indicators Schema Definition

Defines the comprehensive schema for storing pre-calculated technical indicators,
support/resistance zones, supply/demand zones, and pivot points across multiple timeframes.
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from typing import Dict, List, Optional, Union
from datetime import datetime, date
from enum import Enum
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class TimeFrame(Enum):
    """Supported timeframes for technical indicators."""
    MINUTE_1 = "1T"
    MINUTE_5 = "5T"
    MINUTE_15 = "15T"
    HOUR_1 = "1H"
    DAILY = "1D"


class ZoneType(Enum):
    """Types of support/resistance and supply/demand zones."""
    SUPPORT = "support"
    RESISTANCE = "resistance"
    SUPPLY = "supply"
    DEMAND = "demand"


class TechnicalIndicatorsSchema:
    """
    Comprehensive schema for technical indicators and zones.
    
    This schema stores pre-calculated values for:
    - Technical indicators (OBV, ADX, ATR, RSI, MACD, etc.)
    - Support/Resistance zones
    - Supply/Demand zones
    - Pivot points
    - Volume analysis
    """
    
    @staticmethod
    def get_parquet_schema() -> pa.Schema:
        """
        Get the PyArrow schema for technical indicators parquet files.
        
        Returns:
            pa.Schema: Complete schema definition
        """
        return pa.schema([
            # Basic identification
            pa.field("symbol", pa.string(), nullable=False),
            pa.field("timeframe", pa.string(), nullable=False),
            pa.field("timestamp", pa.timestamp('us'), nullable=False),
            pa.field("date_partition", pa.date32(), nullable=False),
            
            # OHLCV data (for reference)
            pa.field("open", pa.float64(), nullable=True),
            pa.field("high", pa.float64(), nullable=True),
            pa.field("low", pa.float64(), nullable=True),
            pa.field("close", pa.float64(), nullable=True),
            pa.field("volume", pa.int64(), nullable=True),
            
            # Moving Averages
            pa.field("sma_10", pa.float64(), nullable=True),
            pa.field("sma_20", pa.float64(), nullable=True),
            pa.field("sma_50", pa.float64(), nullable=True),
            pa.field("sma_100", pa.float64(), nullable=True),
            pa.field("sma_200", pa.float64(), nullable=True),
            pa.field("ema_10", pa.float64(), nullable=True),
            pa.field("ema_20", pa.float64(), nullable=True),
            pa.field("ema_50", pa.float64(), nullable=True),
            pa.field("ema_100", pa.float64(), nullable=True),
            pa.field("ema_200", pa.float64(), nullable=True),
            
            # Momentum Indicators
            pa.field("rsi_14", pa.float64(), nullable=True),
            pa.field("rsi_21", pa.float64(), nullable=True),
            pa.field("stoch_k", pa.float64(), nullable=True),
            pa.field("stoch_d", pa.float64(), nullable=True),
            pa.field("williams_r", pa.float64(), nullable=True),
            
            # Trend Indicators
            pa.field("adx_14", pa.float64(), nullable=True),
            pa.field("adx_21", pa.float64(), nullable=True),
            pa.field("di_plus", pa.float64(), nullable=True),
            pa.field("di_minus", pa.float64(), nullable=True),
            pa.field("aroon_up", pa.float64(), nullable=True),
            pa.field("aroon_down", pa.float64(), nullable=True),
            pa.field("aroon_oscillator", pa.float64(), nullable=True),
            
            # Volatility Indicators
            pa.field("atr_14", pa.float64(), nullable=True),
            pa.field("atr_21", pa.float64(), nullable=True),
            pa.field("bb_upper", pa.float64(), nullable=True),
            pa.field("bb_middle", pa.float64(), nullable=True),
            pa.field("bb_lower", pa.float64(), nullable=True),
            pa.field("bb_width", pa.float64(), nullable=True),
            pa.field("bb_percent", pa.float64(), nullable=True),
            pa.field("keltner_upper", pa.float64(), nullable=True),
            pa.field("keltner_middle", pa.float64(), nullable=True),
            pa.field("keltner_lower", pa.float64(), nullable=True),
            
            # Volume Indicators
            pa.field("obv", pa.float64(), nullable=True),
            pa.field("ad_line", pa.float64(), nullable=True),  # Accumulation/Distribution
            pa.field("cmf", pa.float64(), nullable=True),      # Chaikin Money Flow
            pa.field("mfi", pa.float64(), nullable=True),      # Money Flow Index
            pa.field("vwap", pa.float64(), nullable=True),
            pa.field("volume_sma_20", pa.float64(), nullable=True),
            pa.field("volume_ratio", pa.float64(), nullable=True),
            
            # MACD
            pa.field("macd_line", pa.float64(), nullable=True),
            pa.field("macd_signal", pa.float64(), nullable=True),
            pa.field("macd_histogram", pa.float64(), nullable=True),
            
            # Pivot Points (Traditional)
            pa.field("pivot_point", pa.float64(), nullable=True),
            pa.field("pivot_r1", pa.float64(), nullable=True),
            pa.field("pivot_r2", pa.float64(), nullable=True),
            pa.field("pivot_r3", pa.float64(), nullable=True),
            pa.field("pivot_s1", pa.float64(), nullable=True),
            pa.field("pivot_s2", pa.float64(), nullable=True),
            pa.field("pivot_s3", pa.float64(), nullable=True),
            
            # Fibonacci Levels
            pa.field("fib_23_6", pa.float64(), nullable=True),
            pa.field("fib_38_2", pa.float64(), nullable=True),
            pa.field("fib_50_0", pa.float64(), nullable=True),
            pa.field("fib_61_8", pa.float64(), nullable=True),
            pa.field("fib_78_6", pa.float64(), nullable=True),
            
            # Support/Resistance Zones
            pa.field("support_level_1", pa.float64(), nullable=True),
            pa.field("support_level_2", pa.float64(), nullable=True),
            pa.field("support_level_3", pa.float64(), nullable=True),
            pa.field("support_strength_1", pa.float64(), nullable=True),
            pa.field("support_strength_2", pa.float64(), nullable=True),
            pa.field("support_strength_3", pa.float64(), nullable=True),
            pa.field("resistance_level_1", pa.float64(), nullable=True),
            pa.field("resistance_level_2", pa.float64(), nullable=True),
            pa.field("resistance_level_3", pa.float64(), nullable=True),
            pa.field("resistance_strength_1", pa.float64(), nullable=True),
            pa.field("resistance_strength_2", pa.float64(), nullable=True),
            pa.field("resistance_strength_3", pa.float64(), nullable=True),
            
            # Supply/Demand Zones
            pa.field("supply_zone_high", pa.float64(), nullable=True),
            pa.field("supply_zone_low", pa.float64(), nullable=True),
            pa.field("supply_zone_strength", pa.float64(), nullable=True),
            pa.field("supply_zone_volume", pa.int64(), nullable=True),
            pa.field("demand_zone_high", pa.float64(), nullable=True),
            pa.field("demand_zone_low", pa.float64(), nullable=True),
            pa.field("demand_zone_strength", pa.float64(), nullable=True),
            pa.field("demand_zone_volume", pa.int64(), nullable=True),
            
            # Price Action Patterns
            pa.field("higher_high", pa.bool_(), nullable=True),
            pa.field("higher_low", pa.bool_(), nullable=True),
            pa.field("lower_high", pa.bool_(), nullable=True),
            pa.field("lower_low", pa.bool_(), nullable=True),
            pa.field("doji", pa.bool_(), nullable=True),
            pa.field("hammer", pa.bool_(), nullable=True),
            pa.field("shooting_star", pa.bool_(), nullable=True),
            pa.field("engulfing_bullish", pa.bool_(), nullable=True),
            pa.field("engulfing_bearish", pa.bool_(), nullable=True),
            
            # Market Structure
            pa.field("trend_direction", pa.string(), nullable=True),  # "bullish", "bearish", "sideways"
            pa.field("trend_strength", pa.float64(), nullable=True),   # 0-100 scale
            pa.field("volatility_regime", pa.string(), nullable=True), # "low", "medium", "high"
            pa.field("volume_regime", pa.string(), nullable=True),     # "low", "medium", "high"
            
            # Metadata
            pa.field("calculation_timestamp", pa.timestamp('us'), nullable=False),
            pa.field("data_quality_score", pa.float64(), nullable=True),  # 0-100 quality score
            pa.field("lookback_periods", pa.int32(), nullable=True),      # Number of periods used in calculation
        ])
    
    @staticmethod
    def get_column_names() -> List[str]:
        """Get list of all column names in the schema."""
        schema = TechnicalIndicatorsSchema.get_parquet_schema()
        return [field.name for field in schema]
    
    @staticmethod
    def get_indicator_columns() -> Dict[str, List[str]]:
        """
        Get indicator columns grouped by category.
        
        Returns:
            Dict[str, List[str]]: Dictionary with categories as keys and column lists as values
        """
        return {
            "moving_averages": [
                "sma_10", "sma_20", "sma_50", "sma_100", "sma_200",
                "ema_10", "ema_20", "ema_50", "ema_100", "ema_200"
            ],
            "momentum": [
                "rsi_14", "rsi_21", "stoch_k", "stoch_d", "williams_r"
            ],
            "trend": [
                "adx_14", "adx_21", "di_plus", "di_minus",
                "aroon_up", "aroon_down", "aroon_oscillator"
            ],
            "volatility": [
                "atr_14", "atr_21", "bb_upper", "bb_middle", "bb_lower",
                "bb_width", "bb_percent", "keltner_upper", "keltner_middle", "keltner_lower"
            ],
            "volume": [
                "obv", "ad_line", "cmf", "mfi", "vwap", "volume_sma_20", "volume_ratio"
            ],
            "macd": [
                "macd_line", "macd_signal", "macd_histogram"
            ],
            "pivot_points": [
                "pivot_point", "pivot_r1", "pivot_r2", "pivot_r3",
                "pivot_s1", "pivot_s2", "pivot_s3"
            ],
            "fibonacci": [
                "fib_23_6", "fib_38_2", "fib_50_0", "fib_61_8", "fib_78_6"
            ],
            "support_resistance": [
                "support_level_1", "support_level_2", "support_level_3",
                "support_strength_1", "support_strength_2", "support_strength_3",
                "resistance_level_1", "resistance_level_2", "resistance_level_3",
                "resistance_strength_1", "resistance_strength_2", "resistance_strength_3"
            ],
            "supply_demand": [
                "supply_zone_high", "supply_zone_low", "supply_zone_strength", "supply_zone_volume",
                "demand_zone_high", "demand_zone_low", "demand_zone_strength", "demand_zone_volume"
            ],
            "price_action": [
                "higher_high", "higher_low", "lower_high", "lower_low",
                "doji", "hammer", "shooting_star", "engulfing_bullish", "engulfing_bearish"
            ],
            "market_structure": [
                "trend_direction", "trend_strength", "volatility_regime", "volume_regime"
            ]
        }
    
    @staticmethod
    def create_empty_dataframe() -> pd.DataFrame:
        """
        Create an empty DataFrame with the correct schema.
        
        Returns:
            pd.DataFrame: Empty DataFrame with proper column types
        """
        schema = TechnicalIndicatorsSchema.get_parquet_schema()
        
        # Create empty DataFrame with correct dtypes
        data = {}
        for field in schema:
            if field.type == pa.string():
                data[field.name] = pd.Series(dtype='object')
            elif field.type == pa.float64():
                data[field.name] = pd.Series(dtype='float64')
            elif field.type == pa.int64():
                data[field.name] = pd.Series(dtype='int64')
            elif field.type == pa.int32():
                data[field.name] = pd.Series(dtype='int32')
            elif field.type == pa.bool_():
                data[field.name] = pd.Series(dtype='bool')
            elif field.type == pa.timestamp('us'):
                data[field.name] = pd.Series(dtype='datetime64[us]')
            elif field.type == pa.date32():
                data[field.name] = pd.Series(dtype='datetime64[ns]').dt.date
            else:
                data[field.name] = pd.Series(dtype='object')
        
        return pd.DataFrame(data)
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame) -> bool:
        """
        Validate that a DataFrame conforms to the schema.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            schema = TechnicalIndicatorsSchema.get_parquet_schema()
            expected_columns = {field.name for field in schema}
            actual_columns = set(df.columns)
            
            # Check if all required columns are present
            required_columns = {"symbol", "timeframe", "timestamp", "date_partition", "calculation_timestamp"}
            missing_required = required_columns - actual_columns
            
            if missing_required:
                logger.error(f"Missing required columns: {missing_required}")
                return False
            
            # Check for unexpected columns
            unexpected_columns = actual_columns - expected_columns
            if unexpected_columns:
                logger.warning(f"Unexpected columns found: {unexpected_columns}")
            
            return True
            
        except Exception as e:
            logger.error(f"Schema validation error: {e}")
            return False
    
    @staticmethod
    def get_file_path(symbol: str, timeframe: str, date_partition: date, 
                     base_path: Union[str, Path] = "/Users/apple/Downloads/duckDbData/data/technical_indicators") -> Path:
        """
        Get the file path for storing technical indicators data.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (1T, 5T, 15T, 1H, 1D)
            date_partition: Date for partitioning
            base_path: Base directory for storage
            
        Returns:
            Path: Complete file path
        """
        base_path = Path(base_path)
        year = date_partition.year
        month = f"{date_partition.month:02d}"
        day = f"{date_partition.day:02d}"
        
        file_path = base_path / str(year) / month / day / timeframe / f"{symbol}_indicators_{timeframe}_{date_partition}.parquet"
        return file_path
    
    @staticmethod
    def ensure_directory_exists(file_path: Path) -> None:
        """Ensure the directory for a file path exists."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
