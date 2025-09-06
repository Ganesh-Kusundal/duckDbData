# Technical Indicators Implementation

## Overview

This implementation provides a comprehensive technical indicators system for storing pre-calculated technical analysis data in parquet format. The system supports multiple timeframes, concurrent processing, and automatic updates when market data changes.

## Features

### 📊 Comprehensive Technical Indicators
- **Moving Averages**: SMA (10, 20, 50, 100, 200), EMA (10, 20, 50, 100, 200)
- **Momentum Indicators**: RSI (14, 21), Stochastic (K, D), Williams %R
- **Trend Indicators**: ADX (14, 21), DI+/DI-, Aroon (Up, Down, Oscillator)
- **Volatility Indicators**: ATR (14, 21), Bollinger Bands, Keltner Channels
- **Volume Indicators**: OBV, A/D Line, CMF, MFI, VWAP, Volume SMA/Ratio
- **MACD**: MACD Line, Signal Line, Histogram
- **Pivot Points**: Traditional pivot points (R1-R3, S1-S3)
- **Fibonacci Levels**: 23.6%, 38.2%, 50%, 61.8%, 78.6%

### 🎯 Support/Resistance & Supply/Demand Zones
- **Support/Resistance Zones**: Up to 3 levels with strength calculation
- **Supply/Demand Zones**: High/Low levels with volume and strength metrics
- **Price Action Patterns**: Higher highs/lows, candlestick patterns (Doji, Hammer, etc.)
- **Market Structure**: Trend direction, strength, volatility/volume regimes

### ⏱️ Multi-Timeframe Support
- **1T**: 1 Minute
- **5T**: 5 Minutes  
- **15T**: 15 Minutes
- **1H**: 1 Hour
- **1D**: 1 Day

### 🚀 Performance Features
- **Concurrent Processing**: Multi-threaded calculations and storage
- **Efficient Storage**: Parquet format with compression and partitioning
- **Incremental Updates**: Only calculate new/missing data
- **Stale Detection**: Automatic detection of outdated indicators
- **Fallback Implementations**: Works with TA-Lib, pandas_ta, or pure pandas

## Architecture

### Core Components

#### 1. Schema (`core/technical_indicators/schema.py`)
- Defines comprehensive parquet schema for all indicators
- 99 columns covering all technical analysis needs
- Proper data types and nullable fields
- File path management and validation

#### 2. Calculator (`core/technical_indicators/calculator.py`)
- Calculates all technical indicators from OHLCV data
- Multi-library support (TA-Lib, pandas_ta, fallbacks)
- Custom implementations for zones and patterns
- Data quality scoring

#### 3. Storage (`core/technical_indicators/storage.py`)
- Efficient parquet file storage with partitioning
- Concurrent read/write operations
- Directory structure: `year/month/day/timeframe/symbol_indicators_tf_date.parquet`
- Metadata and statistics tracking

#### 4. Updater (`core/technical_indicators/updater.py`)
- Automatic update mechanism when market data changes
- Incremental processing for efficiency
- Stale indicator detection
- Concurrent symbol processing
- Update statistics and error tracking

### Directory Structure
```
data/technical_indicators/
├── 2025/
│   ├── 09/
│   │   ├── 03/
│   │   │   ├── 1T/
│   │   │   │   ├── RELIANCE_indicators_1T_2025-09-03.parquet
│   │   │   │   └── TCS_indicators_1T_2025-09-03.parquet
│   │   │   ├── 5T/
│   │   │   ├── 15T/
│   │   │   ├── 1H/
│   │   │   └── 1D/
│   │   └── ...
│   └── ...
└── ...
```

## Usage

### 1. Basic Usage
```python
from core.technical_indicators import (
    TechnicalIndicatorsCalculator,
    TechnicalIndicatorsStorage,
    TechnicalIndicatorsUpdater
)
from core.duckdb_infra.database import DuckDBManager

# Initialize components
db_manager = DuckDBManager()
storage = TechnicalIndicatorsStorage()
calculator = TechnicalIndicatorsCalculator()
updater = TechnicalIndicatorsUpdater(db_manager, storage, calculator)

# Calculate indicators for OHLCV data
indicators_df = calculator.calculate_all_indicators(
    ohlcv_data, 'RELIANCE', '1T'
)

# Store indicators
storage.store_indicators(indicators_df, 'RELIANCE', '1T', date(2025, 9, 3))

# Load indicators
loaded_df = storage.load_indicators('RELIANCE', '1T', start_date, end_date)

# Update all symbols
results = updater.update_all_symbols(timeframes=['1T', '5T', '15T'])
```

### 2. Command Line Usage
```bash
# Update all symbols and timeframes
python scripts/update_technical_indicators.py

# Update specific symbols
python scripts/update_technical_indicators.py --symbols RELIANCE TCS INFY

# Update specific timeframes
python scripts/update_technical_indicators.py --timeframes 1T 5T

# Dry run to see what would be updated
python scripts/update_technical_indicators.py --dry-run

# Update only stale indicators
python scripts/update_technical_indicators.py --stale-only

# Show storage statistics
python scripts/update_technical_indicators.py --stats

# Force recalculation
python scripts/update_technical_indicators.py --force-recalculate

# Limit processing
python scripts/update_technical_indicators.py --max-symbols 10 --max-workers 2
```

### 3. Scheduled Updates
```bash
# Add to crontab for automatic updates
# Update indicators every hour
0 * * * * cd /path/to/project && python scripts/update_technical_indicators.py --stale-only

# Full recalculation daily at 2 AM
0 2 * * * cd /path/to/project && python scripts/update_technical_indicators.py --force-recalculate
```

## Schema Details

### Core Columns
- `symbol`: Trading symbol (VARCHAR)
- `timeframe`: Timeframe string (VARCHAR)
- `timestamp`: Data timestamp (TIMESTAMP)
- `date_partition`: Date for partitioning (DATE)
- `open`, `high`, `low`, `close`, `volume`: OHLCV data

### Indicator Categories
1. **Moving Averages** (10 columns): SMA/EMA for various periods
2. **Momentum** (5 columns): RSI, Stochastic, Williams %R
3. **Trend** (7 columns): ADX, DI+/DI-, Aroon indicators
4. **Volatility** (9 columns): ATR, Bollinger Bands, Keltner Channels
5. **Volume** (7 columns): OBV, A/D Line, CMF, MFI, VWAP
6. **MACD** (3 columns): Line, Signal, Histogram
7. **Pivot Points** (7 columns): Traditional pivot levels
8. **Fibonacci** (5 columns): Retracement levels
9. **Support/Resistance** (12 columns): 3 levels each with strength
10. **Supply/Demand** (8 columns): Zone levels with volume/strength
11. **Price Action** (9 columns): Candlestick patterns and trends
12. **Market Structure** (4 columns): Trend/volatility regimes

### Metadata Columns
- `calculation_timestamp`: When indicators were calculated
- `data_quality_score`: Quality score (0-100)
- `lookback_periods`: Number of periods used in calculation

## Integration Tests

The implementation includes comprehensive integration tests:

```bash
# Run all technical indicators tests
python -m pytest tests/test_technical_indicators.py -v

# Run specific test categories
python -m pytest tests/test_technical_indicators.py::TestTechnicalIndicatorsIntegration::test_storage_operations -v
python -m pytest tests/test_technical_indicators.py::TestTechnicalIndicatorsIntegration::test_calculator_basic_functionality -v
```

## Performance Characteristics

### Storage Efficiency
- **Compression**: Snappy compression reduces file sizes by ~70%
- **Partitioning**: Date-based partitioning for efficient queries
- **Columnar Format**: Parquet's columnar storage optimizes analytical queries

### Processing Speed
- **Concurrent Processing**: 4 workers by default (configurable)
- **Incremental Updates**: Only processes new/missing data
- **Batch Operations**: Efficient bulk storage and retrieval

### Memory Usage
- **Streaming Processing**: Processes data in chunks to manage memory
- **Efficient Libraries**: Uses optimized TA-Lib when available
- **Fallback Implementations**: Pure pandas implementations as backup

## Dependencies

### Required
- `pandas >= 2.0.0`
- `numpy >= 1.20.0`
- `pyarrow >= 10.0.0`
- `duckdb >= 0.8.0`

### Optional (for enhanced performance)
- `TA-Lib >= 0.4.0` (preferred for technical indicators)
- `pandas_ta >= 0.3.0` (alternative technical analysis library)

### Installation
```bash
# Install in duckdb_infra environment
conda activate duckdb_infra
pip install TA-Lib pandas_ta

# Or use fallback implementations (no additional dependencies)
```

## Error Handling

### Graceful Degradation
- **Library Fallbacks**: Automatically uses available libraries
- **Missing Data**: Handles incomplete data gracefully
- **Calculation Errors**: Continues processing other indicators on failure
- **Storage Errors**: Provides detailed error reporting

### Data Quality
- **Validation**: Schema validation before storage
- **Quality Scoring**: Automatic data quality assessment
- **Error Tracking**: Comprehensive error logging and statistics

## Future Enhancements

### Planned Features
1. **Additional Indicators**: Ichimoku, Parabolic SAR, Commodity Channel Index
2. **Pattern Recognition**: Advanced candlestick pattern detection
3. **Machine Learning**: ML-based support/resistance detection
4. **Real-time Updates**: WebSocket-based real-time indicator updates
5. **API Integration**: REST API endpoints for indicator access
6. **Visualization**: Built-in charting capabilities

### Performance Optimizations
1. **Caching**: In-memory caching for frequently accessed data
2. **Parallel Processing**: GPU acceleration for complex calculations
3. **Delta Updates**: More efficient incremental update mechanisms
4. **Compression**: Advanced compression algorithms

## Conclusion

This technical indicators implementation provides a robust, scalable solution for pre-calculating and storing technical analysis data. It supports all major indicators, multiple timeframes, and provides efficient update mechanisms suitable for production trading systems.

The system follows SOLID principles, includes comprehensive testing, and provides both high-level convenience methods and low-level control for advanced users.
