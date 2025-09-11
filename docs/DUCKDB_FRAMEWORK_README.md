# 🚀 DuckDB Financial Framework

A robust, high-performance framework for complex financial data analysis, algorithmic trading, and real-time market data processing using DuckDB.

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Query Framework](#query-framework)
- [Analytics Framework](#analytics-framework)
- [Scanner Framework](#scanner-framework)
- [Real-time Trading](#real-time-trading)
- [Examples](#examples)
- [Performance](#performance)
- [API Reference](#api-reference)

## 🎯 Overview

The DuckDB Financial Framework provides a comprehensive solution for financial data analysis and algorithmic trading. Built on DuckDB's high-performance analytical database, it offers:

- **Complex Query Building**: Fluent API for building sophisticated SQL queries
- **Advanced Analytics**: Technical indicators, time series analysis, risk metrics
- **Pattern Recognition**: Automated scanner framework for trading signals
- **Real-time Trading**: Live data streaming and order management
- **Risk Management**: Portfolio risk monitoring and position sizing

## ✨ Key Features

### 🔍 Query Framework
- **Fluent API**: Chain operations for complex query building
- **Advanced Joins**: Multiple join types with alias support
- **Window Functions**: Rolling calculations, rankings, percentiles
- **CTEs**: Common Table Expressions for complex queries
- **Parameter Binding**: Secure parameterized queries

### 📊 Analytics Framework
- **Technical Indicators**: 15+ indicators (SMA, RSI, MACD, Bollinger Bands, etc.)
- **Time Series Analysis**: Returns, volatility, Sharpe ratio, drawdown analysis
- **Risk Metrics**: VaR, CVaR, correlation matrices, portfolio optimization
- **Statistical Functions**: Custom aggregations and statistical tests

### 🔍 Scanner Framework
- **Pattern Recognition**: Double tops/bottoms, head & shoulders, flags
- **Technical Scanners**: RSI divergences, moving average crossovers
- **Signal Generation**: Buy/sell signals with confidence scoring
- **Backtesting**: Historical signal performance analysis
- **Risk Filtering**: Pre-trade risk assessment

### 📡 Real-time Trading
- **Live Data Streaming**: WebSocket connections for real-time prices
- **Order Management**: Market, limit, stop, and stop-limit orders
- **Position Tracking**: Real-time P&L and portfolio monitoring
- **Risk Controls**: Position limits, stop losses, portfolio constraints
- **Emergency Stops**: Circuit breakers and emergency position closure

## 🏗️ Architecture

```
DuckDB Financial Framework
├── Query Framework
│   ├── QueryBuilder (Fluent SQL builder)
│   ├── AdvancedQueryBuilder (Financial-specific queries)
│   └── CTEBuilder (Complex query composition)
├── Analytics Framework
│   ├── TechnicalIndicators (15+ indicators)
│   ├── FinancialAnalytics (Portfolio analysis)
│   └── TimeSeriesAnalysis (Returns & risk metrics)
├── Scanner Framework
│   ├── BaseScanner (Abstract scanner)
│   ├── TechnicalScanner (Technical analysis)
│   ├── PatternScanner (Chart patterns)
│   └── SignalEngine (Risk & signal processing)
└── Real-time Trading
    ├── RealtimeManager (Live data streaming)
    ├── OrderManager (Order lifecycle)
    ├── RiskManager (Risk controls)
    └── PositionTracker (Portfolio monitoring)
```

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install duckdb pandas numpy websockets asyncio

# Clone and setup
cd duckdb-financial-framework
pip install -e .
```

### Basic Usage

```python
from duckdb_financial_framework import (
    AdvancedQueryBuilder,
    FinancialAnalytics,
    ScannerFramework
)

# Initialize framework
query_builder = AdvancedQueryBuilder()
analytics = FinancialAnalytics(connection)
scanner = ScannerFramework(connection)

# Complex query example
result = (query_builder
    .select("symbol", "timestamp", "close", "volume")
    .time_series_filter("2024-01-01", "2024-12-31")
    .symbol_filter(["AAPL", "GOOGL", "MSFT"])
    .price_filter(min_price=100)
    .order_by("volume", "DESC")
    .limit(100)
    .build())

# Technical analysis
indicators = analytics.calculate_rsi("AAPL", period=14)

# Scanning for signals
signals = scanner.run_scan(
    scanner_types=['technical', 'pattern'],
    symbols=['AAPL', 'GOOGL'],
    start_date="2024-01-01",
    end_date="2024-12-31"
)
```

## 🔍 Query Framework

### Basic Query Building

```python
from duckdb_financial_framework import QueryBuilder

# Simple query
query = QueryBuilder("market_data")
result = (query
    .select("symbol", "close", "volume")
    .where("symbol", "=", "AAPL")
    .order_by("timestamp", "DESC")
    .limit(100)
    .build())

# Complex query with joins
query = (QueryBuilder("market_data")
    .select("m.symbol", "m.close", "c.sector")
    .join("company_info c", "m.symbol = c.symbol", JoinType.LEFT)
    .where("c.sector", "=", "Technology")
    .group_by("m.symbol")
    .having("COUNT(*)", ">", 1000)
    .order_by("AVG(m.close)", "DESC")
    .build())
```

### Advanced Financial Queries

```python
from duckdb_financial_framework import AdvancedQueryBuilder

query = AdvancedQueryBuilder()

# Time series analysis with technical indicators
result = (query
    .time_series_filter("2024-01-01", "2024-12-31")
    .symbol_filter(["AAPL", "GOOGL"])
    .technical_indicator("RSI", period=14)
    .pivot_by_timeframe("1W")  # Weekly aggregation
    .correlation_analysis(["AAPL", "GOOGL"])
    .build())
```

## 📊 Analytics Framework

### Technical Indicators

```python
from duckdb_financial_framework import TechnicalIndicators

indicators = TechnicalIndicators(connection)

# Calculate multiple indicators
sma = indicators.calculate_sma("AAPL", period=20)
rsi = indicators.calculate_rsi("AAPL", period=14)
macd = indicators.calculate_macd("AAPL")
bollinger = indicators.calculate_bollinger_bands("AAPL", period=20)

# Access results
print(f"Latest RSI: {rsi.data['rsi_14'].iloc[-1]:.2f}")
print(f"Signal: {'BUY' if rsi.data['rsi_14'].iloc[-1] < 30 else 'HOLD'}")
```

### Portfolio Analysis

```python
from duckdb_financial_framework import FinancialAnalytics

analytics = FinancialAnalytics(connection)

# Analyze portfolio returns
portfolio_analysis = analytics.analyze_portfolio_returns(
    symbols=["AAPL", "GOOGL", "MSFT"],
    start_date="2024-01-01",
    end_date="2024-12-31"
)

# Calculate correlation matrix
correlation = analytics.correlation_matrix(
    symbols=["AAPL", "GOOGL", "MSFT"],
    start_date="2024-01-01",
    end_date="2024-12-31"
)

# Risk metrics
risk_metrics = analytics.risk_metrics("AAPL")
print(f"VaR(95%): {risk_metrics['var_95']:.2%}")
print(f"Sharpe Ratio: {risk_metrics['sharpe_ratio']:.2f}")
```

## 🔍 Scanner Framework

### Running Scanners

```python
from duckdb_financial_framework import ScannerFramework

scanner = ScannerFramework(connection)

# Run comprehensive scan
result = scanner.run_scan(
    scanner_types=['technical', 'pattern'],
    symbols=['AAPL', 'GOOGL', 'MSFT'],
    start_date="2024-01-01",
    end_date="2024-12-31"
)

print(f"Signals found: {len(result.signals)}")
print(f"Execution time: {result.execution_time:.2f}s")

# Process signals
for signal in result.signals:
    if signal.confidence > 0.7:
        print(f"Strong signal: {signal.symbol} {signal.signal_type} "
              f"@ ${signal.price:.2f} (conf: {signal.confidence:.2f})")
```

### Backtesting Signals

```python
# Backtest trading signals
backtest_result = scanner.signal_engine.backtest_signals(
    signals=result.signals,
    start_date="2024-01-01",
    end_date="2024-12-31"
)

print("Backtest Results:")
print(f"Win Rate: {backtest_result['win_rate']:.2%}")
print(f"Total Return: {backtest_result['total_return']:.2%}")
print(f"Sharpe Ratio: {backtest_result['sharpe_ratio']:.2f}")
```

## 📡 Real-time Trading

### Live Data Streaming

```python
import asyncio
from duckdb_financial_framework import RealtimeManager

async def main():
    realtime_manager = RealtimeManager(connection)

    # Subscribe to symbols
    def price_handler(data):
        print(f"{data.symbol}: ${data.price:.2f} "
              f"(Vol: {data.volume:,})")

    realtime_manager.subscribe("AAPL", price_handler)
    realtime_manager.subscribe("GOOGL", price_handler)

    # Start streaming
    await realtime_manager.start_streaming()

asyncio.run(main())
```

### Order Management

```python
from duckdb_financial_framework import OrderManager, RiskManager

order_manager = OrderManager(connection)
risk_manager = RiskManager(order_manager)

# Create order
order = order_manager.create_order(
    symbol="AAPL",
    side="BUY",
    order_type="LIMIT",
    quantity=100,
    price=150.00
)

# Validate with risk manager
is_valid, reason = risk_manager.validate_order(order)
if is_valid:
    print(f"Order {order.order_id} validated and submitted")
else:
    print(f"Order rejected: {reason}")

# Monitor positions
positions = order_manager.get_positions()
portfolio_value = order_manager.get_portfolio_value()
```

## 📈 Examples

### Comprehensive Workflow

```python
from duckdb_financial_framework.examples import run_comprehensive_workflow

# Run complete analysis workflow
results = run_comprehensive_workflow(
    connection=connection,
    symbols=["AAPL", "GOOGL", "MSFT", "AMZN"],
    start_date="2024-01-01",
    end_date="2024-12-31"
)

print("Analysis Complete:")
print(f"- Complex queries: {len(results['query_results'])} results")
print(f"- Technical signals: {len(results['scanner_results'].signals)} signals")
print(f"- Portfolio return: {results['portfolio_analysis']['total_return']:.2%}")
```

### Performance Demo

```bash
# Run framework demo
python framework_demo.py

# Quick analytics demo
python framework_demo.py quick

# Performance test
python framework_demo.py performance
```

## ⚡ Performance

### Benchmarks

- **Query Performance**: Sub-millisecond complex queries
- **Data Processing**: 67M+ records processed in seconds
- **Real-time Updates**: 1000+ price updates per second
- **Memory Usage**: Optimized for large datasets
- **Concurrent Users**: Supports multiple simultaneous analyses

### Optimization Features

- **Query Caching**: Automatic result caching
- **Index Optimization**: Smart indexing strategies
- **Parallel Processing**: Multi-threaded analytics
- **Memory Management**: Efficient resource utilization
- **Connection Pooling**: Optimized database connections

## 📚 API Reference

### Core Classes

- **`QueryBuilder`**: Fluent SQL query construction
- **`AdvancedQueryBuilder`**: Financial-specific query patterns
- **`TechnicalIndicators`**: 15+ technical indicators
- **`FinancialAnalytics`**: Portfolio and risk analysis
- **`ScannerFramework`**: Automated signal generation
- **`SignalEngine`**: Risk management and backtesting
- **`RealtimeManager`**: Live data streaming
- **`OrderManager`**: Order lifecycle management
- **`RiskManager`**: Portfolio risk controls

### Key Methods

#### QueryBuilder
- `select(*columns)`: Specify columns
- `where(column, operator, value)`: Add conditions
- `join(table, condition, type)`: Add joins
- `group_by(*columns)`: Group results
- `order_by(column, direction)`: Sort results
- `build()`: Generate SQL and parameters

#### TechnicalIndicators
- `calculate_sma(symbol, period)`: Simple Moving Average
- `calculate_rsi(symbol, period)`: Relative Strength Index
- `calculate_macd(symbol)`: MACD indicator
- `calculate_bollinger_bands(symbol, period)`: Bollinger Bands

#### ScannerFramework
- `run_scan(types, symbols, dates)`: Execute scanners
- `get_signals(symbols, dates)`: Get trading signals
- `backtest_signals(signals, dates)`: Test signal performance

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

- **Documentation**: Full API docs and examples
- **Issues**: GitHub issue tracker
- **Discussions**: Community forum for questions
- **Performance**: Optimization and tuning guides

---

**Built with ❤️ for the financial technology community**
