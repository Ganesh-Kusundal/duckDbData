# 🚀 Quick Start Guide

Get up and running with the Trading System in minutes! This guide covers installation, basic setup, and your first API calls.

## 📋 Prerequisites

### System Requirements
- **Python**: 3.11 or higher
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 10GB free disk space
- **Network**: Internet connection for data feeds

### Optional Dependencies
- **Docker**: For containerized deployment
- **PostgreSQL**: For production database (DuckDB included for development)
- **Redis**: For caching and session management

## ⚡ Quick Installation

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-org/trading-system.git
cd trading-system

# Start with Docker Compose
docker-compose up -d

# Check if services are running
docker-compose ps
```

The system will be available at:
- **API**: http://localhost:8000
- **Dashboard**: http://localhost:8080
- **Documentation**: http://localhost:8000/docs

### Option 2: Local Installation

```bash
# Clone the repository
git clone https://github.com/your-org/trading-system.git
cd trading-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python scripts/setup.py

# Start the API server
python -m src.interfaces.api.main
```

## 🔧 Basic Configuration

### Environment Setup

Create a `.env` file in the project root:

```bash
# Copy the template
cp .env.example .env

# Edit with your settings
nano .env
```

Basic `.env` configuration:

```bash
# Application Environment
TRADING_ENV=development

# Database Configuration
DATABASE_PATH=data/financial_data.duckdb
DATABASE_MEMORY=false

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Dashboard Configuration
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8080

# WebSocket Configuration
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=8081
```

### Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2024-09-05T10:30:00Z",
  "version": "2.0.0",
  "service": "trading_system_api"
}
```

## 📊 Your First API Calls

### 1. Add Market Data

Let's add some sample market data for Apple Inc. (AAPL):

```bash
# Add market data via API
curl -X POST "http://localhost:8000/api/v1/market-data/" \
     -H "Content-Type: application/json" \
     -d '{
       "symbol": "AAPL",
       "timestamp": "2024-09-05T16:00:00Z",
       "open_price": 150.25,
       "high_price": 152.80,
       "low_price": 149.50,
       "close_price": 152.10,
       "volume": 45000000,
       "exchange": "NASDAQ"
     }'
```

**Expected Response:**
```json
{
  "symbol": "AAPL",
  "timestamp": "2024-09-05T16:00:00",
  "timeframe": "1D",
  "ohlcv": {
    "open": 150.25,
    "high": 152.80,
    "low": 149.50,
    "close": 152.10,
    "volume": 45000000
  },
  "date_partition": "2024-09-05"
}
```

### 2. Retrieve Market Data

Get the current market data for AAPL:

```bash
# Get current market data
curl -X GET "http://localhost:8000/api/v1/market-data/current/AAPL" \
     -H "accept: application/json"
```

**Expected Response:**
```json
{
  "symbol": "AAPL",
  "timestamp": "2024-09-05T16:00:00",
  "timeframe": "1D",
  "ohlcv": {
    "open": 150.25,
    "high": 152.80,
    "low": 149.50,
    "close": 152.10,
    "volume": 45000000
  },
  "date_partition": "2024-09-05"
}
```

### 3. Get Historical Data

Retrieve historical market data:

```bash
# Get 7 days of historical data
curl -X GET "http://localhost:8000/api/v1/market-data/history/AAPL?days=7" \
     -H "accept: application/json"
```

### 4. Run Analytics

Calculate technical indicators:

```bash
# Calculate RSI and SMA indicators
curl -X GET "http://localhost:8000/api/v1/analytics/indicators/AAPL?indicators=RSI,SMA&days=30" \
     -H "accept: application/json"
```

**Expected Response:**
```json
{
  "symbol": "AAPL",
  "timeframe": "1D",
  "period_days": 30,
  "indicators": {
    "SMA_20": 152.34,
    "SMA_50": 148.67,
    "RSI_14": 68.5
  }
}
```

### 5. Run Market Scanner

Execute a market scan:

```bash
# Scan for momentum breakouts
curl -X POST "http://localhost:8000/api/v1/scanner/scan" \
     -H "Content-Type: application/json" \
     -d '{
       "symbols": ["AAPL"],
       "rules": ["momentum_breakout"]
     }'
```

## 🖥️ Using the Dashboard

### Access Dashboard

1. Open your browser and go to: http://localhost:8080
2. The dashboard will show:
   - System status and health
   - Recent market data
   - Active scanner signals
   - Performance metrics

### Dashboard Features

#### Market Data View
- **Real-time Updates**: Live price feeds
- **Historical Charts**: Interactive price charts
- **Data Table**: Sortable and filterable market data
- **Export Options**: Download data in CSV/JSON format

#### Analytics View
- **Technical Indicators**: RSI, MACD, Bollinger Bands
- **Anomaly Detection**: Unusual price/volume patterns
- **Statistical Analysis**: Comprehensive market statistics
- **Custom Reports**: Generate custom analytics reports

#### Scanner View
- **Rule Management**: Configure and manage scanner rules
- **Signal Monitoring**: Real-time signal generation
- **Backtesting**: Test rules on historical data
- **Performance Tracking**: Rule effectiveness metrics

#### System View
- **Health Monitoring**: System and service health
- **Performance Metrics**: CPU, memory, disk usage
- **Log Viewer**: System logs and error tracking
- **Configuration**: Runtime configuration management

## 💻 CLI Usage

### Start CLI

```bash
# Activate virtual environment (if using local installation)
source venv/bin/activate

# Start CLI
python -m src.interfaces.cli.main --help
```

### CLI Examples

```bash
# Get help
trading-system --help

# Get market data
trading-system market-data get AAPL

# Calculate indicators
trading-system analytics indicators AAPL --indicators SMA RSI

# Run scanner
trading-system scanner scan --symbols AAPL MSFT

# Check system health
trading-system system health
```

## 🔌 WebSocket Real-time Data

### Connect to WebSocket

```javascript
// Connect to market data stream
const ws = new WebSocket('ws://localhost:8081/ws/market-data');

// Subscribe to symbols
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'subscribe',
    symbols: ['AAPL', 'MSFT']
  }));
};

// Handle incoming data
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Market Data:', data);
};
```

### WebSocket Message Types

```javascript
// Subscription message
{
  "type": "subscribe",
  "symbols": ["AAPL", "MSFT"]
}

// Market data update
{
  "type": "market_data",
  "symbol": "AAPL",
  "price": 152.34,
  "change": 0.85,
  "volume": 45000000,
  "timestamp": "2024-09-05T16:00:00Z"
}

// Scanner signal
{
  "type": "scanner_signal",
  "rule": "momentum_breakout",
  "symbol": "AAPL",
  "signal": "BUY",
  "confidence": 0.87,
  "timestamp": "2024-09-05T16:00:00Z"
}
```

## 📝 Adding More Data

### Bulk Data Import

Create a CSV file with market data:

```csv
symbol,timestamp,open,high,low,close,volume
AAPL,2024-09-04T16:00:00Z,149.50,151.20,148.80,150.95,42000000
MSFT,2024-09-04T16:00:00Z,305.80,308.50,304.20,307.85,28000000
GOOGL,2024-09-04T16:00:00Z,2840.00,2865.50,2825.25,2858.75,1800000
```

Import using the API:

```bash
# Import CSV data (future feature)
curl -X POST "http://localhost:8000/api/v1/market-data/import" \
     -F "file=@market_data.csv" \
     -F "format=csv"
```

### Programmatic Data Addition

```python
import requests
import json
from datetime import datetime, timedelta

# Base URL
BASE_URL = "http://localhost:8000/api/v1"

# Sample data for multiple symbols
symbols_data = {
    "AAPL": {"price": 152.10, "volume": 45000000},
    "MSFT": {"price": 307.85, "volume": 28000000},
    "GOOGL": {"price": 2858.75, "volume": 1800000}
}

# Add data for each symbol
for symbol, data in symbols_data.items():
    payload = {
        "symbol": symbol,
        "timestamp": datetime.now().isoformat() + "Z",
        "open_price": data["price"] * 0.98,  # Simulate OHLC
        "high_price": data["price"] * 1.02,
        "low_price": data["price"] * 0.96,
        "close_price": data["price"],
        "volume": data["volume"]
    }

    response = requests.post(f"{BASE_URL}/market-data/", json=payload)
    print(f"Added {symbol}: {response.status_code}")
```

## 🧪 Testing Your Setup

### Run Health Checks

```bash
# API health
curl http://localhost:8000/health

# Detailed health
curl http://localhost:8000/api/v1/health/detailed

# System metrics
curl http://localhost:8000/api/v1/health/metrics
```

### Run Basic Tests

```bash
# Run unit tests
python -m pytest tests/unit/ -v

# Run API integration tests
python -m pytest tests/integration/test_api_integration.py -v

# Run all tests
python -m pytest tests/ --cov=src --cov-report=html
```

### Check Logs

```bash
# View application logs
tail -f logs/app.log

# View API logs
tail -f logs/api.log

# View database logs
tail -f logs/database.log
```

## 🚀 Next Steps

### Explore Advanced Features

1. **Technical Analysis**
   ```bash
   # Calculate multiple indicators
   trading-system analytics indicators AAPL \
     --indicators SMA,EMA,RSI,MACD \
     --days 90
   ```

2. **Backtesting**
   ```bash
   # Backtest a trading strategy
   trading-system analytics backtest momentum \
     --symbol AAPL \
     --start-date 2024-01-01 \
     --end-date 2024-12-31
   ```

3. **Real-time Monitoring**
   ```bash
   # Monitor system in real-time
   trading-system system monitor
   ```

### Production Deployment

1. **Environment Configuration**
   ```bash
   export TRADING_ENV=production
   export DATABASE_PATH=/var/lib/trading/data.duckdb
   export API_SECRET_KEY=your-production-secret
   ```

2. **SSL Configuration**
   ```bash
   # Configure SSL certificates
   export SSL_CERT_PATH=/etc/ssl/certs/trading.crt
   export SSL_KEY_PATH=/etc/ssl/private/trading.key
   ```

3. **Load Balancing**
   ```bash
   # Use reverse proxy (nginx, traefik)
   # Configure multiple instances
   # Set up health checks
   ```

### Integration Examples

1. **Python Integration**
   ```python
   import requests

   class TradingClient:
       def __init__(self, base_url="http://localhost:8000/api/v1"):
           self.base_url = base_url

       def get_market_data(self, symbol):
           response = requests.get(f"{self.base_url}/market-data/current/{symbol}")
           return response.json()

       def add_market_data(self, data):
           response = requests.post(f"{self.base_url}/market-data/", json=data)
           return response.json()

   client = TradingClient()
   data = client.get_market_data("AAPL")
   ```

2. **JavaScript/Node.js Integration**
   ```javascript
   const axios = require('axios');

   class TradingAPI {
       constructor(baseURL = 'http://localhost:8000/api/v1') {
           this.client = axios.create({ baseURL });
       }

       async getMarketData(symbol) {
           const response = await this.client.get(`/market-data/current/${symbol}`);
           return response.data;
       }

       async addMarketData(data) {
           const response = await this.client.post('/market-data/', data);
           return response.data;
       }
   }

   const api = new TradingAPI();
   const data = await api.getMarketData('AAPL');
   ```

## 🆘 Troubleshooting

### Common Issues

#### API Not Starting
```bash
# Check if port is available
netstat -tlnp | grep :8000

# Check Python path
python -c "import src.interfaces.api.main"

# Check configuration
cat .env
```

#### Database Connection Failed
```bash
# Check database file permissions
ls -la data/financial_data.duckdb

# Check database path in config
grep DATABASE_PATH .env

# Verify DuckDB installation
python -c "import duckdb; print('DuckDB OK')"
```

#### WebSocket Connection Failed
```bash
# Check WebSocket port
netstat -tlnp | grep :8081

# Verify WebSocket server is running
curl http://localhost:8081/health

# Check browser console for WebSocket errors
```

### Getting Help

- **Documentation**: Check [API Documentation](../api/rest-api.md)
- **Logs**: View application logs in `logs/` directory
- **Health Checks**: Use `/health` endpoints for diagnostics
- **Community**: Check GitHub issues and discussions

---

🎉 **Congratulations!** You now have a fully functional trading system. Explore the [API Documentation](../api/rest-api.md) and [Architecture Guide](../architecture/system-overview.md) for advanced features and customization options.
