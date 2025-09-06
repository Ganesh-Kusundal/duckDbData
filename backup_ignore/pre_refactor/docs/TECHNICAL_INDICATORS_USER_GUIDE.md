# Technical Indicators System - User Guide

## Overview

The Technical Indicators System provides pre-calculated technical analysis data for all symbols across multiple timeframes. It calculates 99+ indicators including support/resistance levels, supply/demand zones, and all major technical indicators.

## Quick Start

### 1. Update All Indicators
```bash
# Update indicators for all symbols and timeframes
python scripts/update_technical_indicators.py

# Update with progress display
python scripts/update_technical_indicators.py --verbose
```

### 2. Check System Status
```bash
# View storage statistics
python scripts/update_technical_indicators.py --stats

# See what needs updating
python scripts/update_technical_indicators.py --dry-run
```

### 3. Update Specific Symbols
```bash
# Update specific symbols only
python scripts/update_technical_indicators.py --symbols RELIANCE,TCS,INFY

# Update limited number of symbols
python scripts/update_technical_indicators.py --max-symbols 10
```

## Command Line Options

### Basic Commands

| Command | Description |
|---------|-------------|
| `python scripts/update_technical_indicators.py` | Update all indicators |
| `--help` | Show all available options |
| `--stats` | Display storage statistics |
| `--dry-run` | Show update plan without executing |

### Filtering Options

| Option | Example | Description |
|--------|---------|-------------|
| `--symbols` | `--symbols RELIANCE,TCS` | Update specific symbols only |
| `--timeframes` | `--timeframes 1T,5T` | Update specific timeframes only |
| `--max-symbols` | `--max-symbols 50` | Limit number of symbols to process |
| `--start-date` | `--start-date 2025-01-01` | Start date for updates |
| `--end-date` | `--end-date 2025-01-31` | End date for updates |

### Performance Options

| Option | Example | Description |
|--------|---------|-------------|
| `--max-workers` | `--max-workers 8` | Number of parallel workers |
| `--batch-size` | `--batch-size 100` | Records per batch |
| `--force` | `--force` | Force update even if not stale |

### Output Options

| Option | Description |
|--------|-------------|
| `--verbose` | Show detailed progress |
| `--quiet` | Minimal output |
| `--log-level DEBUG` | Set logging level |

## Usage Examples

### Daily Operations

```bash
# Morning routine - update all indicators
python scripts/update_technical_indicators.py --verbose

# Check what was updated
python scripts/update_technical_indicators.py --stats
```

### Specific Symbol Analysis

```bash
# Update indicators for specific stocks
python scripts/update_technical_indicators.py --symbols RELIANCE,TCS,INFY,HDFCBANK

# Update only intraday timeframes
python scripts/update_technical_indicators.py --symbols RELIANCE --timeframes 1T,5T,15T
```

### Performance Optimization

```bash
# High-performance update with 8 workers
python scripts/update_technical_indicators.py --max-workers 8 --batch-size 200

# Update recent data only
python scripts/update_technical_indicators.py --start-date 2025-01-01 --max-symbols 100
```

### Development & Testing

```bash
# Test update plan without executing
python scripts/update_technical_indicators.py --dry-run --max-symbols 5

# Force update specific symbol (ignore staleness)
python scripts/update_technical_indicators.py --symbols RELIANCE --force

# Debug mode with detailed logging
python scripts/update_technical_indicators.py --symbols TCS --log-level DEBUG
```

## Data Access

### File Structure

Indicators are stored in partitioned Parquet files:

```
data/technical_indicators/
├── 2025/
│   ├── 01/
│   │   ├── 01/
│   │   │   ├── 1T/
│   │   │   │   ├── RELIANCE_indicators_1T_2025-01-01.parquet
│   │   │   │   └── TCS_indicators_1T_2025-01-01.parquet
│   │   │   ├── 5T/
│   │   │   │   ├── RELIANCE_indicators_5T_2025-01-01.parquet
│   │   │   │   └── TCS_indicators_5T_2025-01-01.parquet
│   │   │   └── 1H/
│   │   │       ├── RELIANCE_indicators_1H_2025-01-01.parquet
│   │   │       └── TCS_indicators_1H_2025-01-01.parquet
│   │   └── 02/
│   │       └── ...
│   └── 02/
│       └── ...
```

### Python API Usage

```python
from core.technical_indicators.storage import TechnicalIndicatorsStorage
from datetime import date

# Initialize storage
storage = TechnicalIndicatorsStorage('data/technical_indicators')

# Load indicators for a symbol
indicators = storage.load_indicators(
    symbol='RELIANCE',
    timeframe='1T',
    start_date=date(2025, 1, 1),
    end_date=date(2025, 1, 31)
)

# Access specific indicators
print(f"RSI: {indicators['rsi_14'].iloc[-1]}")
print(f"Support Level: {indicators['support_level_1'].iloc[-1]}")
print(f"Supply Zone: {indicators['supply_zone_high'].iloc[-1]}")
```

### Loading Multiple Symbols

```python
# Load multiple symbols concurrently
symbols = ['RELIANCE', 'TCS', 'INFY']
data = storage.load_multiple_symbols(
    symbols=symbols,
    timeframe='5T',
    start_date=date(2025, 1, 1),
    end_date=date(2025, 1, 31),
    max_workers=4
)

# Access data for each symbol
for symbol, df in data.items():
    print(f"{symbol}: {len(df)} records")
```

## Available Indicators

### Technical Indicators (70+ indicators)

#### Moving Averages
- `sma_10`, `sma_20`, `sma_50`, `sma_100`, `sma_200`
- `ema_10`, `ema_20`, `ema_50`, `ema_100`, `ema_200`

#### Momentum Indicators
- `rsi_14`, `rsi_21` - Relative Strength Index
- `stoch_k`, `stoch_d` - Stochastic Oscillator
- `williams_r` - Williams %R

#### Trend Indicators
- `adx_14`, `adx_21` - Average Directional Index
- `di_plus`, `di_minus` - Directional Indicators
- `aroon_up`, `aroon_down`, `aroon_oscillator`

#### Volatility Indicators
- `atr_14`, `atr_21` - Average True Range
- `bb_upper`, `bb_middle`, `bb_lower` - Bollinger Bands
- `bb_width`, `bb_percent`
- `keltner_upper`, `keltner_middle`, `keltner_lower`

#### Volume Indicators
- `obv` - On-Balance Volume
- `ad_line` - Accumulation/Distribution Line
- `cmf` - Chaikin Money Flow
- `mfi` - Money Flow Index
- `vwap` - Volume Weighted Average Price
- `volume_sma_20`, `volume_ratio`

#### MACD
- `macd_line`, `macd_signal`, `macd_histogram`

### Support & Resistance Levels (12 indicators)

```python
# Primary levels (strongest)
support_level_1, support_strength_1
resistance_level_1, resistance_strength_1

# Secondary levels
support_level_2, support_strength_2
resistance_level_2, resistance_strength_2

# Tertiary levels
support_level_3, support_strength_3
resistance_level_3, resistance_strength_3
```

### Supply & Demand Zones (8 indicators)

```python
# Supply zones (selling pressure areas)
supply_zone_high, supply_zone_low
supply_zone_strength, supply_zone_volume

# Demand zones (buying pressure areas)
demand_zone_high, demand_zone_low
demand_zone_strength, demand_zone_volume
```

### Pivot Points (7 indicators)

```python
pivot_point          # Central pivot
pivot_r1, pivot_r2, pivot_r3  # Resistance levels
pivot_s1, pivot_s2, pivot_s3  # Support levels
```

### Fibonacci Levels (5 indicators)

```python
fib_23_6, fib_38_2, fib_50_0, fib_61_8, fib_78_6
```

### Price Action Patterns (4 indicators)

```python
higher_high, higher_low, lower_high, lower_low
```

### Candlestick Patterns (5 indicators)

```python
doji, hammer, shooting_star, engulfing_bullish, engulfing_bearish
```

## Timeframes Supported

| Timeframe | Code | Description |
|-----------|------|-------------|
| 1 Minute | `1T` | Intraday scalping |
| 5 Minutes | `5T` | Short-term trading |
| 15 Minutes | `15T` | Intraday swing trading |
| 1 Hour | `1H` | Medium-term analysis |
| Daily | `1D` | Long-term analysis |

## Monitoring & Maintenance

### Check System Health

```bash
# View storage statistics
python scripts/update_technical_indicators.py --stats
```

Output:
```
📈 STORAGE STATISTICS
==================================================
Total Files: 2,435
Total Size: 1,247.32 MB
Symbols Count: 487
Timeframes: 1T, 5T, 15T, 1H, 1D

📊 SYMBOLS BY TIMEFRAME
==================================================
1T: 487 symbols
5T: 487 symbols
15T: 487 symbols
1H: 487 symbols
1D: 487 symbols
```

### Identify Stale Data

```bash
# Check what needs updating
python scripts/update_technical_indicators.py --dry-run
```

Output:
```
⚠️  STALE INDICATORS DETECTED:
Symbols with stale data: 25
  RELIANCE: 1T, 5T, 15T, 1H, 1D
  TCS: 1T, 5T
  INFY: 1D
```

### Performance Monitoring

```bash
# Update with timing information
python scripts/update_technical_indicators.py --verbose --max-symbols 10
```

## Automation & Scheduling

### Cron Job Setup

Add to crontab for automatic updates:

```bash
# Update indicators every hour during market hours (9 AM - 4 PM)
0 9-16 * * 1-5 cd /path/to/duckDbData && python scripts/update_technical_indicators.py

# Full update every morning at 8 AM
0 8 * * 1-5 cd /path/to/duckDbData && python scripts/update_technical_indicators.py --force

# Weekend maintenance - update all with high performance
0 10 * * 6 cd /path/to/duckDbData && python scripts/update_technical_indicators.py --max-workers 8 --force
```

### Systemd Service (Linux)

Create `/etc/systemd/system/technical-indicators.service`:

```ini
[Unit]
Description=Technical Indicators Update
After=network.target

[Service]
Type=oneshot
User=your-user
WorkingDirectory=/path/to/duckDbData
ExecStart=/path/to/python scripts/update_technical_indicators.py
Environment=PATH=/path/to/conda/envs/duckdb_infra/bin

[Install]
WantedBy=multi-user.target
```

Create timer `/etc/systemd/system/technical-indicators.timer`:

```ini
[Unit]
Description=Run Technical Indicators Update
Requires=technical-indicators.service

[Timer]
OnCalendar=*-*-* 09,10,11,12,13,14,15,16:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:
```bash
sudo systemctl enable technical-indicators.timer
sudo systemctl start technical-indicators.timer
```

## Troubleshooting

### Common Issues

#### 1. No Data Updated
```bash
# Check if market data exists
python -c "from core.duckdb_infra.database import DuckDBManager; db = DuckDBManager(); print(db.get_available_symbols()[:10])"

# Force update
python scripts/update_technical_indicators.py --force --symbols RELIANCE
```

#### 2. Performance Issues
```bash
# Reduce workers and batch size
python scripts/update_technical_indicators.py --max-workers 2 --batch-size 50

# Update specific timeframes only
python scripts/update_technical_indicators.py --timeframes 1D
```

#### 3. Storage Issues
```bash
# Check disk space
df -h data/technical_indicators/

# Clean old data (if needed)
find data/technical_indicators/ -name "*.parquet" -mtime +30 -delete
```

#### 4. Memory Issues
```bash
# Process fewer symbols at once
python scripts/update_technical_indicators.py --max-symbols 50 --max-workers 2
```

### Debug Mode

```bash
# Enable debug logging
python scripts/update_technical_indicators.py --log-level DEBUG --symbols RELIANCE

# Check specific calculation
python -c "
from core.technical_indicators.calculator import TechnicalIndicatorsCalculator
from core.duckdb_infra.database import DuckDBManager
import pandas as pd

db = DuckDBManager()
data = db.get_market_data('RELIANCE', '1T', '2025-01-01', '2025-01-02')
calc = TechnicalIndicatorsCalculator()
result = calc.calculate_all_indicators(data, 'RELIANCE', '1T')
print(result[['close', 'rsi_14', 'support_level_1']].tail())
"
```

## Best Practices

### 1. Regular Updates
- Update indicators after market close
- Use `--dry-run` to check before major updates
- Monitor storage space regularly

### 2. Performance Optimization
- Use appropriate `--max-workers` for your system
- Process recent data more frequently than historical
- Use specific symbol lists for targeted updates

### 3. Data Validation
- Check indicator values for reasonableness
- Monitor for missing data or calculation errors
- Verify support/resistance levels make sense

### 4. Backup Strategy
- Backup `data/technical_indicators/` directory regularly
- Keep configuration files in version control
- Document any custom modifications

## Integration Examples

### Trading Strategy Development

```python
from core.technical_indicators.storage import TechnicalIndicatorsStorage
from datetime import date, timedelta

storage = TechnicalIndicatorsStorage('data/technical_indicators')

# Load recent data for analysis
end_date = date.today()
start_date = end_date - timedelta(days=30)

indicators = storage.load_indicators('RELIANCE', '5T', start_date, end_date)

# Example: RSI oversold strategy
oversold = indicators[indicators['rsi_14'] < 30]
near_support = indicators[
    (indicators['close'] <= indicators['support_level_1'] * 1.02) &
    (indicators['close'] >= indicators['support_level_1'] * 0.98)
]

print(f"RSI oversold signals: {len(oversold)}")
print(f"Near support signals: {len(near_support)}")
```

### Real-time Monitoring

```python
import pandas as pd
from datetime import date

def get_latest_signals(symbol, timeframe='5T'):
    """Get latest technical signals for a symbol."""
    storage = TechnicalIndicatorsStorage('data/technical_indicators')
    
    # Load today's data
    today = date.today()
    data = storage.load_indicators(symbol, timeframe, today, today)
    
    if data.empty:
        return None
    
    latest = data.iloc[-1]
    
    signals = {
        'symbol': symbol,
        'timestamp': latest['timestamp'],
        'close': latest['close'],
        'rsi': latest['rsi_14'],
        'support': latest['support_level_1'],
        'resistance': latest['resistance_level_1'],
        'supply_zone': f"{latest['supply_zone_low']:.2f}-{latest['supply_zone_high']:.2f}",
        'demand_zone': f"{latest['demand_zone_low']:.2f}-{latest['demand_zone_high']:.2f}",
    }
    
    return signals

# Monitor multiple symbols
symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK']
for symbol in symbols:
    signals = get_latest_signals(symbol)
    if signals:
        print(f"{symbol}: RSI={signals['rsi']:.1f}, S/R={signals['support']:.1f}/{signals['resistance']:.1f}")
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review log files for error messages
3. Test with a single symbol using `--symbols RELIANCE --verbose`
4. Check system resources (CPU, memory, disk space)

The system is designed to be robust and handle most scenarios automatically. Regular monitoring and maintenance will ensure optimal performance.
