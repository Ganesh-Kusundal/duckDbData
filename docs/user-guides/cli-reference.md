# 🎛️ CLI Reference Guide

Complete reference for the Trading System Command Line Interface (CLI).

## 📋 Overview

The CLI provides a rich, interactive interface for trading operations, market analysis, system management, and data processing. Built with **Typer** and **Rich** for excellent user experience.

## 🚀 Quick Start

```bash
# Check system status
python -m src.interfaces.cli.main status

# Get help
python -m src.interfaces.cli.main --help

# Run with verbose logging
python -m src.interfaces.cli.main --verbose scanner run
```

## 📊 System Commands

### Status & Health

```bash
# System overview
trading status

# Detailed health check
trading system health --detailed

# System configuration
trading system config --section database

# System logs
trading system logs --level INFO --lines 50

# System logs with follow mode
trading system logs --follow
```

### Backup & Maintenance

```bash
# Create system backup
trading system backup --destination ./backups --include-data --compress

# Cleanup old data
trading system cleanup --older-than-days 30 --dry-run

# Show cleanup plan
trading system cleanup --older-than-days 30 --dry-run
```

## 📈 Trading Operations

### Order Management

```bash
# Submit market order
trading trading submit-order --symbol AAPL --side BUY --quantity 100 --type MARKET

# Submit limit order
trading trading submit-order --symbol GOOGL --side SELL --quantity 50 --type LIMIT --price 2800.00

# Cancel order
trading trading cancel-order --order-id ord_12345 --reason "Changed mind"

# Modify order
trading trading modify-order --order-id ord_12345 --quantity 75 --price 150.00
```

### Backtesting

```bash
# Run backtest with defaults
trading trading backtest --strategy breakout --symbol AAPL

# Advanced backtest
trading trading backtest \
  --strategy momentum \
  --symbols AAPL,GOOGL,MSFT \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --initial-capital 100000 \
  --commission 0.001 \
  --slippage 0.0005 \
  --output-file results.json \
  --detailed
```

### Strategy Optimization

```bash
# Optimize RSI strategy
trading trading optimize \
  --strategy rsi_divergence \
  --symbols AAPL \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --parameters "rsi_period=10-20" "overbought=65-75" \
  --method grid \
  --max-evaluations 100 \
  --metric sharpe_ratio

# Genetic algorithm optimization
trading trading optimize \
  --strategy macd_crossover \
  --method genetic \
  --max-evaluations 200 \
  --metric total_return
```

### Portfolio Management

```bash
# View portfolio summary
trading trading portfolio

# View specific portfolio
trading trading portfolio --portfolio-id my_portfolio

# Detailed position view
trading trading portfolio --detailed

# Portfolio in JSON format
trading trading portfolio --format json
```

### Rule Management

```bash
# List all rules
trading trading rules

# List active rules only
trading trading rules --active-only

# List breakout rules
trading trading rules --rule-type breakout

# Detailed rule information
trading trading rules --detailed

# Enable rule
trading trading rule-enable --rule-id breakout_standard

# Disable rule
trading trading rule-disable --rule-id rsi_divergence
```

## 📊 Market Analysis

### Scanner Operations

```bash
# Run market scanner
trading scanner run --symbol AAPL --date 2024-09-05

# Scan multiple symbols
trading scanner run --symbols AAPL,GOOGL,MSFT --date 2024-09-05

# Advanced scanning
trading scanner run \
  --symbols AAPL \
  --date 2024-09-05 \
  --scan-type breakout \
  --timeframe 1H \
  --criteria "volume_multiplier=1.5,min_price_change=0.02" \
  --max-results 20

# CRP analysis
trading scanner run \
  --symbol AAPL \
  --scan-type crp \
  --date 2024-09-05 \
  --criteria "range_threshold=0.03,close_position=near_high"
```

### Market Data Operations

```bash
# View market data
trading market-data show --symbol AAPL --date 2024-09-05

# Import market data
trading market-data import --file data.csv --symbol AAPL

# Export market data
trading market-data export --symbol AAPL --start-date 2024-01-01 --end-date 2024-12-31 --format csv
```

### Analytics

```bash
# Calculate technical indicators
trading analytics calculate \
  --symbol AAPL \
  --indicators RSI,MACD,SMA \
  --period 14 \
  --date 2024-09-05

# Generate signals
trading analytics signals \
  --symbol AAPL \
  --strategy mean_reversion \
  --date 2024-09-05

# Run analysis
trading analytics analyze \
  --symbol AAPL \
  --analysis-type trend_analysis \
  --parameters "period=20,method=linear"
```

## 🔧 Configuration

### Environment Setup

```bash
# Set environment variables
export LOG_LEVEL=DEBUG
export DATABASE_PATH=./data/trading.db
export API_HOST=0.0.0.0
export API_PORT=8000

# Or use .env file
cp .env.example .env
# Edit .env with your settings
```

### Configuration Files

```bash
# View current configuration
trading system config

# View database configuration
trading system config --section database

# View API configuration
trading system config --section api

# View all configuration
trading system config --format json
```

## 📋 Command Reference

### Global Options

```bash
# Verbose output
trading --verbose <command>

# Debug logging
trading --debug <command>

# Help for any command
trading <command> --help
```

### Command Groups

| Group | Description | Commands |
|-------|-------------|----------|
| `system` | System management | health, config, logs, backup, cleanup |
| `trading` | Trading operations | submit-order, cancel-order, modify-order, backtest, optimize, portfolio, rules |
| `scanner` | Market scanning | run |
| `market-data` | Market data operations | show, import, export |
| `analytics` | Analytics operations | calculate, signals, analyze |

## 🎨 CLI Features

### Rich Output Formatting

The CLI uses **Rich** library for beautiful output:

- **Colored output** for different message types
- **Tables** for structured data
- **Progress bars** for long-running operations
- **Syntax highlighting** for JSON/XML output
- **Interactive prompts** for confirmations

### Interactive Mode

```bash
# Interactive rule management
trading trading rules --interactive

# Interactive backtest configuration
trading trading backtest --interactive
```

### Output Formats

```bash
# Table format (default)
trading trading portfolio

# JSON format
trading trading portfolio --format json

# CSV format
trading trading portfolio --format csv --output portfolio.csv
```

## 🐛 Troubleshooting

### Common Issues

#### Command Not Found
```bash
# Check if CLI is properly installed
python -m src.interfaces.cli.main --help

# Check Python path
python -c "import sys; print(sys.path)"
```

#### Database Connection Issues
```bash
# Check database status
trading system health

# Check database configuration
trading system config --section database

# Test database connection
trading market-data show --symbol TEST
```

#### Permission Issues
```bash
# Check file permissions
ls -la data/
ls -la logs/

# Fix permissions
chmod 755 data/
chmod 755 logs/
```

#### Memory Issues
```bash
# Check system resources
trading system health --detailed

# Run with reduced memory usage
trading scanner run --batch-size 100 --symbol AAPL
```

### Debug Mode

```bash
# Enable debug logging
trading --debug scanner run --symbol AAPL

# View detailed logs
trading system logs --level DEBUG --lines 100

# Check system metrics
trading system health --detailed --format json
```

## 📊 Performance Tuning

### Memory Optimization

```bash
# Process in batches
trading scanner run --batch-size 500 --symbol AAPL

# Limit result set
trading scanner run --max-results 1000 --symbol AAPL

# Use streaming for large datasets
trading market-data export --streaming --symbol AAPL
```

### Parallel Processing

```bash
# Enable parallel processing
trading scanner run --parallel 4 --symbols AAPL,GOOGL,MSFT

# Optimize thread pool
trading system config --set scanner.threads=8
```

### Caching

```bash
# Enable result caching
trading system config --set cache.enabled=true

# Set cache TTL
trading system config --set cache.ttl=3600

# Clear cache
trading system cache clear
```

## 🔐 Security

### Authentication

```bash
# Login to secure system
trading auth login --username trader --password

# Use API key
trading --api-key YOUR_API_KEY scanner run

# Logout
trading auth logout
```

### Secure Configuration

```bash
# Use encrypted configuration
trading system config --encrypt

# Set secure database credentials
trading system config --set database.password=encrypted_value

# Enable SSL/TLS
trading system config --set api.ssl=true
```

## 📈 Monitoring & Metrics

### Performance Monitoring

```bash
# View system metrics
trading system metrics

# Monitor command performance
trading system metrics --command scanner

# Export metrics
trading system metrics --export metrics.json
```

### Health Checks

```bash
# Quick health check
trading system health

# Detailed health report
trading system health --detailed --format json

# Health check with history
trading system health --history 24h
```

## 🚀 Advanced Usage

### Scripting

```bash
#!/bin/bash
# Automated daily scan script

DATE=$(date +%Y-%m-%d)
SYMBOLS="AAPL,GOOGL,MSFT,TSLA"

trading scanner run \
  --symbols $SYMBOLS \
  --date $DATE \
  --output results_$DATE.json \
  --format json
```

### Batch Processing

```bash
# Process multiple symbols in batch
cat symbols.txt | xargs -I {} trading scanner run --symbol {} --date 2024-09-05

# Parallel batch processing
cat symbols.txt | parallel trading scanner run --symbol {} --date 2024-09-05
```

### Integration with Other Tools

```bash
# Pipe to jq for JSON processing
trading trading portfolio --format json | jq '.positions[] | select(.pnl > 0)'

# Export to CSV for analysis
trading market-data export --format csv > market_data.csv

# Use with cron for automation
# Add to crontab: 0 9 * * 1-5 trading scanner run --symbol AAPL
```

## 📚 Examples

### Complete Trading Workflow

```bash
# 1. Check system status
trading status

# 2. Run market analysis
trading scanner run --symbol AAPL --scan-type breakout --date 2024-09-05

# 3. Submit order based on analysis
trading trading submit-order --symbol AAPL --side BUY --quantity 100 --type LIMIT --price 150.00

# 4. Monitor portfolio
trading trading portfolio --detailed

# 5. Backtest strategy
trading trading backtest --strategy breakout --symbol AAPL --start-date 2024-01-01 --end-date 2024-09-05

# 6. Optimize strategy
trading trading optimize --strategy breakout --symbol AAPL --metric sharpe_ratio
```

### Risk Management Workflow

```bash
# 1. Assess portfolio risk
trading risk assess --portfolio-id main_portfolio

# 2. Check risk limits
trading risk limits --portfolio-id main_portfolio

# 3. Update risk profile
trading risk update-profile --portfolio-id main_portfolio --max-drawdown 0.15

# 4. Monitor positions
trading risk monitor --portfolio-id main_portfolio --alert-threshold 0.10
```

### Analytics Workflow

```bash
# 1. Calculate indicators
trading analytics calculate --symbol AAPL --indicators RSI,MACD,BOLLINGER

# 2. Generate signals
trading analytics signals --symbol AAPL --strategy mean_reversion

# 3. Run comprehensive analysis
trading analytics analyze --symbol AAPL --analysis-type full_suite

# 4. Export results
trading analytics export --symbol AAPL --format csv --output analysis.csv
```

## 🔗 API Integration

### REST API

```bash
# Start API server
trading api start --host 0.0.0.0 --port 8000

# API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/market-data/AAPL
curl http://localhost:8000/api/v1/portfolio
```

### WebSocket

```bash
# Connect to WebSocket
trading websocket connect ws://localhost:8000/ws/market-data

# Stream real-time data
trading websocket stream --symbols AAPL,GOOGL --events price,volume
```

---

## 📞 Support

- **Command Help**: `trading <command> --help`
- **Documentation**: [Full Documentation](../README.md)
- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)

---

**The CLI is designed to be both powerful for advanced users and intuitive for beginners, providing a comprehensive interface to all trading system capabilities.**
