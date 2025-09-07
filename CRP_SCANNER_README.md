# CRP Scanner - Intraday Stock Selection

## Overview

The **CRP Scanner** is an advanced intraday stock selection tool that identifies stocks exhibiting **C**lose, **R**ange, **P**attern characteristics for potential trading opportunities.

## What is CRP?

CRP stands for:
- **C**lose: Stock closes near its daily high or low
- **R**ange: Trading range is narrow/tight (consolidation)
- **P**attern: Combines volume, momentum, and technical indicators

## Key Features

### 🎯 Pattern Detection
- **Close Analysis**: Identifies stocks closing within 2% of their daily high/low
- **Range Analysis**: Finds stocks with trading ranges under 3%
- **Volume Confirmation**: Validates patterns with volume analysis
- **Momentum Scoring**: Includes price momentum in probability calculations

### 📊 Advanced Analytics
- **Probability Scoring**: Weighted scoring system (0-100) combining all CRP factors
- **Date Range Analysis**: Scan multiple days with end-of-day performance tracking
- **Performance Metrics**: Success rate analysis and ranking
- **Real-time Results**: Comprehensive table display with key metrics

### 🔧 Technical Specifications
- **Database**: DuckDB integration for fast queries
- **Configuration**: Fully configurable thresholds and parameters
- **Export**: CSV export functionality
- **Testing**: Comprehensive integration tests

## Configuration

```python
DEFAULT_CONFIG = {
    'consolidation_period': 5,        # Days for pattern analysis
    'close_threshold_pct': 2.0,       # Max % from high/low for close
    'range_threshold_pct': 3.0,       # Max % for tight range
    'min_volume': 50000,              # Minimum volume threshold
    'max_volume': 5000000,            # Maximum volume threshold
    'min_price': 50,                  # Minimum stock price
    'max_price': 2000,                # Maximum stock price
    'max_results_per_day': 3,         # Top results per day
    'crp_cutoff_time': time(9, 50),   # Pattern detection time
    'end_of_day_time': time(15, 15)   # End-of-day analysis time
}
```

## Usage Examples

### Basic Single Day Scan

```python
from src.application.scanners.strategies.crp_scanner import CRPScanner
from datetime import date, time

scanner = CRPScanner()
results = scanner.scan(
    scan_date=date(2024, 1, 15),
    cutoff_time=time(9, 50)
)
print(results.head())
```

### Advanced Date Range Analysis

```python
from datetime import date, time, timedelta

start_date = date(2024, 1, 10)
end_date = date(2024, 1, 15)

results = scanner.scan_date_range(
    start_date=start_date,
    end_date=end_date,
    cutoff_time=time(9, 50),
    end_of_day_time=time(15, 15)
)

scanner.display_results_table(results)
scanner.export_results(results, "crp_analysis.csv")
```

## CRP Probability Scoring

The scanner uses a weighted scoring system:

### Components (40% weight each)
1. **Close Position** (40%): How close the stock closes to its high/low
   - Near High/Low: 0.4 points
   - Mid Range: 0.1 points

2. **Range Tightness** (30%): How narrow the trading range is
   - Under 3%: 0.3 points
   - Under 4.5%: 0.2 points
   - Over 4.5%: 0.05 points

3. **Volume Pattern** (20%): Volume confirmation
   - High volume: 0.2 points
   - Medium volume: 0.15 points
   - Low volume: 0.05 points

4. **Momentum** (10%): Price momentum
   - Positive momentum: 0.1 points
   - Neutral: 0.05 points
   - Negative: 0.02 points

### Final Score
- **Total Score** = (Close + Range + Volume + Momentum) × 100
- **Threshold**: Minimum 30% for inclusion
- **Ranking**: Higher scores = better patterns

## Output Format

### Table Display
```
┌──────────┬──────────┬────────────┬──────────┬────────────┬──────────┬──────────┬────────┬──────┬────────────┐
│ Symbol   │ Date     │ CRP Price  │ EOD Price│ Price Change│ Close Pos│ Current  │ Prob   │ Rank │ Perform    │
│          │          │            │          │             │          │ Range%   │ Score  │      │ Rank       │
├──────────┼──────────┼────────────┼──────────┼────────────┼──────────┼──────────┼────────┼──────┼────────────┤
│ RELIANCE │ 2024-01-15│ ₹2500.50  │ ₹2520.50 │    +0.80%  │ Near High│   1.02%  │ 85.5%  │ 8.50 │     8.50   │
│ TCS      │ 2024-01-15│ ₹3200.75  │ ₹3220.75 │    +0.62%  │ Near High│   1.27%  │ 78.2%  │ 7.82 │     7.82   │
└──────────┴──────────┴────────────┴──────────┴──────────┴──────────┴──────────┴────────┴──────┴────────────┘
```

### CSV Export Fields
- `symbol`: Stock symbol
- `scan_date`: Date of scan
- `crp_price`: Price at CRP detection time
- `eod_price`: End-of-day price
- `price_change_pct`: Percentage change from CRP to EOD
- `close_position`: Near High/Low/Mid Range
- `current_range_pct`: Current trading range percentage
- `crp_probability_score`: Overall CRP probability (0-100)
- `performance_rank`: Combined performance ranking

## Performance Metrics

### Success Rate Calculation
- **Successful CRP**: Price increases from detection to end-of-day
- **Overall Success Rate**: Percentage of successful patterns
- **Average Change**: Mean price change across all patterns

### Example Statistics
```
📈 Summary Statistics (Top 3 Stocks Per Day):
   Total CRP Patterns: 15
   Successful CRP Patterns: 12
   Success Rate: 80.0%
   Average Price Change: +0.65%
   Average CRP Probability Score: 76.8%
```

## Testing

Run the comprehensive test suite:

```bash
# Run CRP scanner tests
pytest tests/application/test_crp_scanner.py -v

# Run demo script
python crp_scanner_demo.py

# Show examples only
python crp_scanner_demo.py --examples
```

## Integration

The CRP scanner integrates seamlessly with the existing scanner framework:

```python
# Can be used alongside other scanners
from src.application.scanners.strategies.breakout_scanner import BreakoutScanner
from src.application.scanners.strategies.crp_scanner import CRPScanner

breakout_scanner = BreakoutScanner()
crp_scanner = CRPScanner()

# Compare different scanning strategies
breakout_results = breakout_scanner.scan_date_range(start_date, end_date)
crp_results = crp_scanner.scan_date_range(start_date, end_date)
```

## Best Practices

### Optimal Usage
1. **Time Windows**: Best results between 9:50 AM - 10:30 AM
2. **Market Conditions**: Works best in ranging/consolidating markets
3. **Volume Confirmation**: Always check volume > 50K for reliability
4. **Probability Threshold**: Focus on patterns with > 70% probability scores

### Risk Management
1. **Position Sizing**: Limit exposure to 2-3% per trade
2. **Stop Losses**: Place stops at recent swing lows/highs
3. **Time Exits**: Exit by 3:00 PM if target not reached
4. **Portfolio Diversification**: Spread across different sectors

### Performance Monitoring
1. **Track Success Rate**: Monitor weekly/monthly performance
2. **Adjust Thresholds**: Fine-tune based on market conditions
3. **Review Patterns**: Analyze why certain patterns succeed/fail
4. **Backtesting**: Validate with historical data

## Troubleshooting

### Common Issues

**No Patterns Found**
- Check market data availability
- Adjust volume/price thresholds
- Verify time ranges

**Low Success Rate**
- Review probability score thresholds
- Check market conditions (avoid trending markets)
- Adjust close/range thresholds

**Performance Issues**
- Ensure database indexes are optimized
- Check memory usage for large date ranges
- Consider reducing max_results_per_day

## Architecture

```
CRPScanner
├── BaseScanner (inheritance)
├── Database Integration (DuckDB)
├── Configuration Management
├── Pattern Detection Engine
├── Probability Scoring System
├── Performance Analytics
└── Export/Reporting
```

## Dependencies

- Python 3.8+
- pandas
- numpy
- duckdb
- pytest (for testing)

## License

This CRP scanner is part of the enhanced trading analytics framework.

---

## Quick Start

```bash
# 1. Run demo
python crp_scanner_demo.py

# 2. Run tests
pytest tests/application/test_crp_scanner.py

# 3. Start using in your trading strategy
from src.application.scanners.strategies.crp_scanner import CRPScanner

scanner = CRPScanner()
results = scanner.scan_date_range(
    start_date=date.today() - timedelta(days=5),
    end_date=date.today()
)
scanner.display_results_table(results)
```
