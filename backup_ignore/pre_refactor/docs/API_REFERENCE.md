# Technical Indicators API Reference

## Core Classes

### TechnicalIndicatorsStorage

Main class for storing and retrieving indicator data.

```python
from core.technical_indicators.storage import TechnicalIndicatorsStorage

storage = TechnicalIndicatorsStorage(base_path='data/technical_indicators')
```

#### Methods

##### `load_indicators(symbol, timeframe, start_date, end_date)`
Load indicators for a symbol and timeframe.

**Parameters:**
- `symbol` (str): Symbol name (e.g., 'RELIANCE')
- `timeframe` (str): Timeframe ('1T', '5T', '15T', '1H', '1D')
- `start_date` (date): Start date
- `end_date` (date): End date

**Returns:** pandas.DataFrame with all indicators

**Example:**
```python
from datetime import date
data = storage.load_indicators('RELIANCE', '5T', date(2025,1,1), date(2025,1,31))
```

##### `load_multiple_symbols(symbols, timeframe, start_date, end_date, max_workers=4)`
Load indicators for multiple symbols concurrently.

**Parameters:**
- `symbols` (list): List of symbol names
- `timeframe` (str): Timeframe
- `start_date` (date): Start date  
- `end_date` (date): End date
- `max_workers` (int): Number of parallel workers

**Returns:** dict {symbol: DataFrame}

**Example:**
```python
symbols = ['RELIANCE', 'TCS', 'INFY']
data = storage.load_multiple_symbols(symbols, '1H', date(2025,1,1), date(2025,1,31))
```

##### `get_available_symbols(timeframe=None)`
Get list of available symbols.

**Parameters:**
- `timeframe` (str, optional): Filter by timeframe

**Returns:** list of symbol names

**Example:**
```python
symbols = storage.get_available_symbols('1D')
```

##### `get_storage_stats()`
Get storage statistics.

**Returns:** dict with statistics

**Example:**
```python
stats = storage.get_storage_stats()
print(f"Total files: {stats['total_files']}")
print(f"Total size: {stats['total_size_mb']:.2f} MB")
```

### TechnicalIndicatorsCalculator

Class for calculating technical indicators.

```python
from core.technical_indicators.calculator import TechnicalIndicatorsCalculator

calculator = TechnicalIndicatorsCalculator()
```

#### Methods

##### `calculate_all_indicators(df, symbol, timeframe)`
Calculate all technical indicators for OHLCV data.

**Parameters:**
- `df` (pandas.DataFrame): OHLCV data with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
- `symbol` (str): Symbol name
- `timeframe` (str): Timeframe

**Returns:** pandas.DataFrame with all indicators

**Example:**
```python
# Assuming you have OHLCV data
indicators = calculator.calculate_all_indicators(ohlcv_data, 'RELIANCE', '5T')
```

### TechnicalIndicatorsUpdater

Class for updating indicators from database.

```python
from core.technical_indicators.updater import TechnicalIndicatorsUpdater
from core.duckdb_infra.database import DuckDBManager

db_manager = DuckDBManager()
storage = TechnicalIndicatorsStorage('data/technical_indicators')
updater = TechnicalIndicatorsUpdater(db_manager, storage)
```

#### Methods

##### `update_all_indicators(symbols=None, timeframes=None, start_date=None, end_date=None, max_workers=4, force=False)`
Update indicators for multiple symbols and timeframes.

**Parameters:**
- `symbols` (list, optional): Symbols to update (None = all)
- `timeframes` (list, optional): Timeframes to update (None = all)
- `start_date` (date, optional): Start date
- `end_date` (date, optional): End date
- `max_workers` (int): Number of parallel workers
- `force` (bool): Force update even if not stale

**Returns:** dict with update results

##### `detect_stale_indicators(max_age_hours=24)`
Detect indicators that need updating.

**Parameters:**
- `max_age_hours` (int): Maximum age in hours before considering stale

**Returns:** dict {symbol: [timeframes]}

## Data Schema

### Input Data (OHLCV)
Required columns for calculation:
- `timestamp` (datetime): Timestamp
- `open` (float): Opening price
- `high` (float): High price  
- `low` (float): Low price
- `close` (float): Closing price
- `volume` (int): Volume

### Output Data (Indicators)
The system generates 99 columns including:

#### Metadata Columns
- `symbol` (str): Symbol name
- `timeframe` (str): Timeframe
- `timestamp` (datetime): Timestamp
- `date_partition` (date): Date partition
- `calculation_timestamp` (datetime): When calculated
- `data_quality_score` (float): Data quality score (0-100)
- `lookback_periods` (int): Periods used for calculation

#### Price Data
- `open`, `high`, `low`, `close`, `volume` (original OHLCV data)

#### Moving Averages (10 columns)
- `sma_10`, `sma_20`, `sma_50`, `sma_100`, `sma_200`
- `ema_10`, `ema_20`, `ema_50`, `ema_100`, `ema_200`

#### Momentum Indicators (5 columns)
- `rsi_14`, `rsi_21`: Relative Strength Index
- `stoch_k`, `stoch_d`: Stochastic Oscillator
- `williams_r`: Williams %R

#### Trend Indicators (7 columns)
- `adx_14`, `adx_21`: Average Directional Index
- `di_plus`, `di_minus`: Directional Indicators
- `aroon_up`, `aroon_down`, `aroon_oscillator`: Aroon indicators

#### Volatility Indicators (9 columns)
- `atr_14`, `atr_21`: Average True Range
- `bb_upper`, `bb_middle`, `bb_lower`: Bollinger Bands
- `bb_width`, `bb_percent`: Bollinger Band width and position
- `keltner_upper`, `keltner_middle`, `keltner_lower`: Keltner Channels

#### Volume Indicators (7 columns)
- `obv`: On-Balance Volume
- `ad_line`: Accumulation/Distribution Line
- `cmf`: Chaikin Money Flow
- `mfi`: Money Flow Index
- `vwap`: Volume Weighted Average Price
- `volume_sma_20`: 20-period volume SMA
- `volume_ratio`: Current volume / average volume

#### MACD (3 columns)
- `macd_line`: MACD line
- `macd_signal`: Signal line
- `macd_histogram`: MACD histogram

#### Pivot Points (7 columns)
- `pivot_point`: Central pivot point
- `pivot_r1`, `pivot_r2`, `pivot_r3`: Resistance levels
- `pivot_s1`, `pivot_s2`, `pivot_s3`: Support levels

#### Fibonacci Levels (5 columns)
- `fib_23_6`, `fib_38_2`, `fib_50_0`, `fib_61_8`, `fib_78_6`

#### Support & Resistance (12 columns)
- `support_level_1`, `support_level_2`, `support_level_3`
- `support_strength_1`, `support_strength_2`, `support_strength_3`
- `resistance_level_1`, `resistance_level_2`, `resistance_level_3`
- `resistance_strength_1`, `resistance_strength_2`, `resistance_strength_3`

#### Supply & Demand Zones (8 columns)
- `supply_zone_high`, `supply_zone_low`
- `supply_zone_strength`, `supply_zone_volume`
- `demand_zone_high`, `demand_zone_low`
- `demand_zone_strength`, `demand_zone_volume`

#### Price Action Patterns (4 columns)
- `higher_high`, `higher_low`, `lower_high`, `lower_low` (boolean)

#### Candlestick Patterns (5 columns)
- `doji`, `hammer`, `shooting_star` (boolean)
- `engulfing_bullish`, `engulfing_bearish` (boolean)

#### Market Regime (4 columns)
- `trend_direction` (str): 'BULLISH', 'BEARISH', 'SIDEWAYS'
- `trend_strength` (float): Trend strength (0-100)
- `volatility_regime` (str): 'LOW', 'MEDIUM', 'HIGH'
- `volume_regime` (str): 'LOW', 'MEDIUM', 'HIGH'

## Timeframes

| Code | Description | Typical Use |
|------|-------------|-------------|
| `1T` | 1 minute | Scalping, very short-term |
| `5T` | 5 minutes | Short-term trading |
| `15T` | 15 minutes | Intraday swing trading |
| `1H` | 1 hour | Medium-term analysis |
| `1D` | Daily | Long-term analysis |

## Error Handling

All methods handle errors gracefully and return appropriate values:

- **Empty DataFrames**: Returned when no data is available
- **Missing Files**: Methods return empty results without raising exceptions
- **Invalid Parameters**: Validation with helpful error messages
- **Calculation Errors**: Fallback implementations ensure robustness

## Performance Considerations

### Loading Data
- Use date ranges to limit data size
- Use `load_multiple_symbols()` for concurrent loading
- Consider timeframe - higher timeframes have less data

### Memory Usage
- Large date ranges consume more memory
- Multiple symbols loaded simultaneously increase memory usage
- Consider processing in batches for large datasets

### Storage
- Parquet format provides efficient compression
- Partitioned by date for fast filtering
- Snappy compression reduces file sizes

## Examples

### Basic Usage
```python
from core.technical_indicators.storage import TechnicalIndicatorsStorage
from datetime import date, timedelta

# Initialize
storage = TechnicalIndicatorsStorage('data/technical_indicators')

# Load recent data
end_date = date.today()
start_date = end_date - timedelta(days=7)
data = storage.load_indicators('RELIANCE', '5T', start_date, end_date)

# Access indicators
if not data.empty:
    latest = data.iloc[-1]
    print(f"RSI: {latest['rsi_14']:.2f}")
    print(f"Support: {latest['support_level_1']:.2f}")
    print(f"Resistance: {latest['resistance_level_1']:.2f}")
```

### Batch Processing
```python
# Load multiple symbols
symbols = ['RELIANCE', 'TCS', 'INFY']
data_dict = storage.load_multiple_symbols(symbols, '1H', start_date, end_date)

# Process each symbol
for symbol, df in data_dict.items():
    if not df.empty:
        latest_rsi = df['rsi_14'].iloc[-1]
        print(f"{symbol}: RSI = {latest_rsi:.2f}")
```

### Statistics and Monitoring
```python
# Get storage statistics
stats = storage.get_storage_stats()
print(f"Total indicators stored: {stats['total_files']} files")
print(f"Storage size: {stats['total_size_mb']:.2f} MB")
print(f"Available symbols: {stats['symbols_count']}")
print(f"Timeframes: {', '.join(stats['timeframes'])}")

# Get available symbols
symbols = storage.get_available_symbols('1D')
print(f"Symbols with daily data: {len(symbols)}")
```
