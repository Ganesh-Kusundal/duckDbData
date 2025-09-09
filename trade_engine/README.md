# Intraday Trade Engine - Backtest + Live Parity

A unified trading engine that runs the same strategies in backtesting and live trading without code drift, built on DuckDB with DDD + SOLID principles.

## 🎯 Features

- **Unified Architecture**: Single codebase for backtest/live with complete parity
- **Top-3 Concentrate & Pyramid Strategy**: Sophisticated intraday strategy with leader selection
- **NSE Compliance**: Tick-size handling, quantity rounding, and fee calculations
- **DuckDB Integration**: Fast analytical queries and persistent telemetry
- **DDD + SOLID**: Clean architecture with clear bounded contexts
- **Real-time Processing**: Event-driven with timer-based rotation logic

## 🚀 Quick Start

### 1. Configuration
Edit `trade_engine/config/trade_engine.yaml` for your settings:
```yaml
mode: backtest                    # backtest | live
trading_day: "2025-08-20"         # backtest date
universe: NIFTY500
# ... other settings
```

### 2. Run Backtest
```bash
cd /path/to/duckDbData
python -m trade_engine.cli backtest --config trade_engine/config/trade_engine.yaml
```

### 3. Run Live Trading
```bash
python -m trade_engine.cli live --config trade_engine/config/trade_engine.yaml
```

### 4. Validate Setup
```bash
python -m trade_engine.cli validate --config trade_engine/config/trade_engine.yaml
```

## 📊 Strategy Overview

### Phase 1: 09:15-09:50 Warm-up
- Compute features: RET_0915_0950, VSpike_10m, OBVΔ_35m, RangeCompression, SectorStrength
- Select Top-3 symbols by composite score
- Filter by turnover, spread, and liquidity criteria

### Phase 2: Entry Triggers (1-minute bars)
- **EMA 9/30 Momentum**: 9>30, close>9, body in top 40%
- **Range Break**: Close > prior 09:35-09:50 high with vol ≥ 1.3× avg
- Position size = (Capital × Risk%) / (Entry - ISL)
- Capital split: 60/20/20 for A/B/C ranked symbols

### Phase 3: Leader Consolidation
- LeaderScore = 0.5z(%RET) + 0.3z(VSpike) + 0.2z(OBVΔ)
- Exit non-leaders when:
  - Leader ≥ +0.75R or outperforms peers by ≥0.6σ
  - Prints HH/HL with rising OBV

### Phase 4: Pyramiding
- Add at +0.75R, +1.25R, +2.0R with sizes 50%/33%/25%
- TSL modes: Chandelier ATR, EMA-close, swing-low
- Max 3 adds per position

### Phase 5: 20-Minute Rotation
- If T+20m no pos ≥ +0.5R, flatten laggards, rescan universe

## 🏗️ Architecture

### Bounded Contexts
- **MarketData**: Bars/quotes from DuckDB or live feeds
- **Analytics**: Technical indicators and scoring functions
- **Strategy**: Pure decision logic (side-effect free)
- **Portfolio & Risk**: Position sizing, stops, capital allocation
- **Execution**: Order routing via BrokerPort
- **Persistence**: DuckDB repositories for telemetry
- **Engine**: StrategyRunner orchestrating all components

### Ports & Adapters
```
StrategyRunner
├── DataFeedPort → DuckDBDataFeed (backtest) / LiveDataFeed (live)
├── AnalyticsPort → DuckDBAnalytics
├── BrokerPort → BacktestBroker / DhanBroker
└── RepositoryPort → DuckDBRepository
```

## 📁 Project Structure

```
trade_engine/
├── __init__.py
├── domain/                 # Core business models
│   ├── models.py          # Aggregates & value objects
│   └── nse_utils.py       # NSE-specific utilities
├── ports/                 # Abstract interfaces
│   ├── data_feed.py
│   ├── analytics.py
│   ├── broker.py
│   └── repository.py
├── adapters/              # Concrete implementations
│   ├── duckdb_data_feed.py
│   ├── duckdb_analytics.py
│   ├── duckdb_repository.py
│   └── backtest_broker.py
├── strategy/              # Strategy implementations
│   └── top3_concentrate_pyramid.py
├── engine/                # Orchestration layer
│   └── strategy_runner.py
├── config/                # Configuration files
│   ├── trade_engine.yaml
│   └── nse_ticks.yaml
├── tests/                 # Acceptance tests
│   └── test_acceptance.py
└── cli.py                 # Command-line interface
```

## 🔧 Configuration

### trade_engine.yaml
```yaml
mode: backtest
trading_day: "2025-08-20"
time:
  warmup_start: "09:15"
  shortlist_cutoff: "09:50"
  eod_flat: "15:15"
data:
  duckdb_path: "data/financial_data.duckdb"
  bars:
    trigger_timeframe: "1m"
    risk_timeframe: "5m"
selection:
  score_weights:
    ret_0915_0950: 0.35
    vspike_10m: 0.25
    obv_delta_35m: 0.20
    sector_strength: 0.10
    range_compression: 0.10
# ... see full config for all options
```

## 🧪 Testing

### Acceptance Tests
```bash
cd trade_engine/tests
python test_acceptance.py
```

### Unit Tests
```bash
pytest trade_engine/tests/ -v
```

## 📈 Performance & Metrics

### Backtest Results Structure
```json
{
  "run_id": "backtest_20250820_143022",
  "mode": "backtest",
  "date": "2025-08-20",
  "total_return": 1250.75,
  "total_trades": 23,
  "signals_generated": 45,
  "final_cash": 101250.75,
  "final_positions": 0
}
```

### Telemetry Tables
- `signals`: Trading signals with reasoning
- `orders`: Order lifecycle and fills
- `positions`: Position snapshots with P&L
- `scores`: Symbol scoring data
- `runs`: Run metadata and configuration

## 🔒 Safety Features

- **EOD Hard Flat**: All positions closed by 15:15
- **Risk Guards**: Per-trade R limits, daily DD stops
- **NSE Compliance**: Tick-size rounding, quantity validation
- **Circuit Breakers**: Automatic position flattening on anomalies
- **Audit Trail**: Complete telemetry for post-trade analysis

## 🚦 Status Indicators

- 🟢 **Ready**: System validated and ready for trading
- 🟡 **Caution**: Running with warnings or limited data
- 🔴 **Error**: System issues requiring attention

## 📚 Next Steps

1. **Live Integration**: Add Dhan broker adapter for live trading
2. **Advanced Analytics**: More sophisticated scoring models
3. **Risk Management**: Enhanced position sizing and hedging
4. **Performance**: Optimize DuckDB queries for real-time processing
5. **Monitoring**: Add dashboards and alerting

---

**Built with ❤️ using DDD + SOLID on DuckDB**
