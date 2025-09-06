# Technical Indicators - Quick Reference

## 🚀 Most Common Commands

```bash
# Update all indicators
python scripts/update_technical_indicators.py

# Check system status
python scripts/update_technical_indicators.py --stats

# Update specific symbols
python scripts/update_technical_indicators.py --symbols RELIANCE,TCS,INFY

# See what needs updating (without doing it)
python scripts/update_technical_indicators.py --dry-run
```

## 📊 Available Indicators (99 total)

### 🎯 Support & Resistance (12)
```
support_level_1, support_level_2, support_level_3
support_strength_1, support_strength_2, support_strength_3
resistance_level_1, resistance_level_2, resistance_level_3  
resistance_strength_1, resistance_strength_2, resistance_strength_3
```

### 📦 Supply & Demand Zones (8)
```
supply_zone_high, supply_zone_low, supply_zone_strength, supply_zone_volume
demand_zone_high, demand_zone_low, demand_zone_strength, demand_zone_volume
```

### 📈 Technical Indicators (70+)
```
# Moving Averages
sma_10, sma_20, sma_50, sma_100, sma_200
ema_10, ema_20, ema_50, ema_100, ema_200

# Momentum
rsi_14, rsi_21, stoch_k, stoch_d, williams_r

# Trend  
adx_14, adx_21, di_plus, di_minus, aroon_up, aroon_down

# Volatility
atr_14, atr_21, bb_upper, bb_middle, bb_lower, bb_width

# Volume
obv, ad_line, cmf, mfi, vwap, volume_sma_20

# MACD
macd_line, macd_signal, macd_histogram

# Pivot Points
pivot_point, pivot_r1, pivot_r2, pivot_r3, pivot_s1, pivot_s2, pivot_s3

# Fibonacci
fib_23_6, fib_38_2, fib_50_0, fib_61_8, fib_78_6

# Patterns
higher_high, higher_low, lower_high, lower_low
doji, hammer, shooting_star, engulfing_bullish, engulfing_bearish
```

## ⏰ Timeframes
- `1T` - 1 minute
- `5T` - 5 minutes  
- `15T` - 15 minutes
- `1H` - 1 hour
- `1D` - Daily

## 🔧 Common Options

| Option | Example | Purpose |
|--------|---------|---------|
| `--symbols` | `--symbols RELIANCE,TCS` | Specific symbols |
| `--timeframes` | `--timeframes 1T,5T` | Specific timeframes |
| `--max-symbols` | `--max-symbols 10` | Limit symbols |
| `--max-workers` | `--max-workers 4` | Parallel processing |
| `--verbose` | `--verbose` | Show progress |
| `--force` | `--force` | Force update |
| `--dry-run` | `--dry-run` | Preview only |

## 💻 Python Usage

```python
from core.technical_indicators.storage import TechnicalIndicatorsStorage
from datetime import date

# Load indicators
storage = TechnicalIndicatorsStorage('data/technical_indicators')
data = storage.load_indicators('RELIANCE', '5T', date(2025,1,1), date(2025,1,31))

# Access indicators
print(f"RSI: {data['rsi_14'].iloc[-1]}")
print(f"Support: {data['support_level_1'].iloc[-1]}")
print(f"Supply Zone: {data['supply_zone_high'].iloc[-1]}")
```

## 📁 Data Location
```
data/technical_indicators/YYYY/MM/DD/TIMEFRAME/SYMBOL_indicators_TIMEFRAME_YYYY-MM-DD.parquet
```

## 🔍 Troubleshooting

```bash
# Debug specific symbol
python scripts/update_technical_indicators.py --symbols RELIANCE --verbose --log-level DEBUG

# Check available symbols
python -c "from core.duckdb_infra.database import DuckDBManager; print(DuckDBManager().get_available_symbols()[:10])"

# Force update if stuck
python scripts/update_technical_indicators.py --force --max-symbols 5
```

## ⚡ Performance Tips

- Use `--max-workers 4-8` for faster processing
- Update specific symbols with `--symbols` for targeted analysis
- Use `--dry-run` first to see what will be updated
- Monitor with `--stats` to track storage usage

## 📋 Daily Workflow

```bash
# Morning: Check status
python scripts/update_technical_indicators.py --stats

# Update all indicators  
python scripts/update_technical_indicators.py --verbose

# Evening: Quick update of key symbols
python scripts/update_technical_indicators.py --symbols RELIANCE,TCS,INFY,HDFCBANK
```
