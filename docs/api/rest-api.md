# 🌐 REST API Reference

## Overview

The Trading System provides a comprehensive REST API for programmatic access to all trading functionality. Built with **FastAPI**, the API offers automatic OpenAPI/Swagger documentation, request validation, and high-performance async operations.

## 🔗 Base URL

```
Production:  https://api.trading-system.com/api/v1
Development: http://localhost:8000/api/v1
Staging:     https://api-staging.trading-system.com/api/v1
```

## 🔐 Authentication

### API Key Authentication
```bash
# Include API key in header
curl -H "X-API-Key: your-api-key" \
     https://api.trading-system.com/api/v1/market-data/current/AAPL

# Or in query parameter
curl "https://api.trading-system.com/api/v1/market-data/current/AAPL?api_key=your-api-key"
```

### JWT Token Authentication (Future)
```bash
# Get access token
curl -X POST "https://api.trading-system.com/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "user", "password": "pass"}'

# Use token in requests
curl -H "Authorization: Bearer your-jwt-token" \
     https://api.trading-system.com/api/v1/market-data/current/AAPL
```

## 📊 Market Data API

### Get Current Market Data

Get the latest market data for a specific symbol.

```http
GET /api/v1/market-data/current/{symbol}
```

#### Parameters
- `symbol` (path): Trading symbol (e.g., AAPL, RELIANCE)
- `timeframe` (query, optional): Data timeframe (default: "1D")
  - Options: "1D", "1H", "30m", "15m", "5m"

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/v1/market-data/current/AAPL" \
     -H "accept: application/json"
```

#### Example Response
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

#### Error Responses
```json
// 404 Not Found
{
  "detail": "Market data not found for symbol: INVALID"
}

// 500 Internal Server Error
{
  "detail": "Database connection failed"
}
```

### Get Historical Market Data

Retrieve historical market data for analysis.

```http
GET /api/v1/market-data/history/{symbol}
```

#### Parameters
- `symbol` (path): Trading symbol
- `timeframe` (query, optional): Data timeframe (default: "1D")
- `days` (query, optional): Number of days of history (default: 30)
- `limit` (query, optional): Maximum records to return (default: 1000)

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/v1/market-data/history/AAPL?days=7&timeframe=1D" \
     -H "accept: application/json"
```

#### Example Response
```json
{
  "symbol": "AAPL",
  "record_count": 7,
  "data": [
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
  ],
  "metadata": {
    "timeframe": "1D",
    "date_range": {
      "start": "2024-08-29T00:00:00",
      "end": "2024-09-05T23:59:59"
    }
  }
}
```

### Create Market Data

Add new market data record.

```http
POST /api/v1/market-data/
```

#### Request Body
```json
{
  "symbol": "AAPL",
  "timestamp": "2024-09-05T16:00:00Z",
  "open_price": 150.25,
  "high_price": 152.80,
  "low_price": 149.50,
  "close_price": 152.10,
  "volume": 45000000,
  "exchange": "NSE"
}
```

#### Example Request
```bash
curl -X POST "http://localhost:8000/api/v1/market-data/" \
     -H "Content-Type: application/json" \
     -d '{
       "symbol": "AAPL",
       "timestamp": "2024-09-05T16:00:00Z",
       "open_price": 150.25,
       "high_price": 152.80,
       "low_price": 149.50,
       "close_price": 152.10,
       "volume": 45000000
     }'
```

#### Example Response
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

### Update Market Data

Update existing market data.

```http
PUT /api/v1/market-data/{symbol}
```

#### Parameters
- `symbol` (path): Trading symbol to update

#### Request Body
Same as create market data request.

### Delete Market Data

Remove market data record.

```http
DELETE /api/v1/market-data/{symbol}
```

#### Parameters
- `symbol` (path): Trading symbol to delete
- `timestamp` (query): Specific timestamp to delete
- `timeframe` (query, optional): Timeframe (default: "1D")

## 📈 Analytics API

### Calculate Technical Indicators

Calculate technical indicators for a symbol.

```http
GET /api/v1/analytics/indicators/{symbol}
```

#### Parameters
- `symbol` (path): Trading symbol
- `indicators` (query, optional): Comma-separated list of indicators
  - Options: SMA, EMA, RSI, MACD, BB (Bollinger Bands)
- `timeframe` (query, optional): Data timeframe (default: "1D")
- `days` (query, optional): Analysis period in days (default: 90)

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/v1/analytics/indicators/AAPL?indicators=SMA,RSI&days=30" \
     -H "accept: application/json"
```

#### Example Response
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

### Detect Anomalies

Detect market anomalies and unusual patterns.

```http
GET /api/v1/analytics/anomalies/{symbol}
```

#### Parameters
- `symbol` (path): Trading symbol
- `anomaly_types` (query, optional): Types of anomalies to detect
  - Options: price_spike, volume_spike, gap_up, gap_down
- `sensitivity` (query, optional): Detection sensitivity (default: 0.05)
- `days` (query, optional): Analysis period (default: 30)

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/v1/analytics/anomalies/AAPL?sensitivity=0.03" \
     -H "accept: application/json"
```

#### Example Response
```json
{
  "symbol": "AAPL",
  "period_days": 30,
  "sensitivity_threshold": 0.03,
  "anomalies_detected": [
    {
      "type": "price_spike",
      "date": "2024-09-01",
      "value": 155.8,
      "threshold": 153.2,
      "severity": "high"
    },
    {
      "type": "volume_spike",
      "date": "2024-09-02",
      "value": 2500000,
      "threshold": 1800000,
      "severity": "medium"
    }
  ]
}
```

### Get Market Statistics

Generate comprehensive market statistics.

```http
GET /api/v1/analytics/statistics/{symbol}
```

#### Parameters
- `symbol` (path): Trading symbol
- `include_quality` (query, optional): Include data quality metrics (default: true)
- `include_coverage` (query, optional): Include date coverage analysis (default: true)

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/v1/analytics/statistics/AAPL" \
     -H "accept: application/json"
```

#### Example Response
```json
{
  "symbol": "AAPL",
  "price_stats": {
    "current": 152.4,
    "high": 175.8,
    "low": 135.2,
    "average": 152.4,
    "volatility": 0.025
  },
  "volume_stats": {
    "average": 1250000,
    "total": 1562500000,
    "peak": 2500000
  },
  "quality": {
    "completeness": 0.98,
    "accuracy": 0.95,
    "consistency": 0.92
  },
  "coverage": {
    "total_days": 584,
    "data_days": 572,
    "coverage_percentage": 97.9
  }
}
```

### Validate Data Quality

Validate market data quality over a date range.

```http
POST /api/v1/analytics/validate-data
```

#### Request Body
```json
{
  "symbol": "AAPL",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```

#### Example Request
```bash
curl -X POST "http://localhost:8000/api/v1/analytics/validate-data" \
     -H "Content-Type: application/json" \
     -d '{
       "symbol": "AAPL",
       "start_date": "2024-01-01",
       "end_date": "2024-12-31"
     }'
```

#### Example Response
```json
{
  "symbol": "AAPL",
  "quality_score": 0.95,
  "total_records": 250,
  "issues": [
    "Minor data gap on 2024-02-15",
    "Volume spike detected on 2024-07-15"
  ],
  "validation_period": {
    "start": "2024-01-01",
    "end": "2024-12-31"
  }
}
```

## 🔍 Scanner API

### Run Market Scan

Execute market scanner with specified rules.

```http
POST /api/v1/scanner/scan
```

#### Request Body
```json
{
  "symbols": ["AAPL", "MSFT", "GOOGL"],
  "rules": ["momentum_breakout", "volume_surge"]
}
```

#### Example Request
```bash
curl -X POST "http://localhost:8000/api/v1/scanner/scan" \
     -H "Content-Type: application/json" \
     -d '{
       "symbols": ["AAPL", "MSFT"],
       "rules": ["momentum_breakout"]
     }'
```

#### Example Response
```json
{
  "scan_id": "scan_20240905_143022",
  "symbols_scanned": 2,
  "rules_applied": ["momentum_breakout"],
  "results": [
    {
      "symbol": "AAPL",
      "rule": "momentum_breakout",
      "signal": "BUY",
      "confidence": 0.85,
      "timestamp": "2024-09-05T14:30:22Z",
      "metadata": {
        "breakout_level": 155.2,
        "volume_ratio": 1.8
      }
    }
  ]
}
```

### List Scanner Rules

Get available scanner rules and their configurations.

```http
GET /api/v1/scanner/rules
```

#### Parameters
- `category` (query, optional): Filter by category
  - Options: momentum, volume, price_action, oscillator

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/v1/scanner/rules?category=momentum" \
     -H "accept: application/json"
```

#### Example Response
```json
{
  "rules": [
    {
      "name": "momentum_breakout",
      "description": "Detects momentum breakouts above resistance levels",
      "category": "momentum",
      "parameters": ["threshold", "lookback_period"]
    },
    {
      "name": "volume_surge",
      "description": "Identifies unusual volume spikes",
      "category": "volume",
      "parameters": ["multiplier", "min_volume"]
    }
  ],
  "total_rules": 2,
  "categories": ["momentum", "volume"]
}
```

### Backtest Scanner Rule

Backtest a scanner rule on historical data.

```http
GET /api/v1/scanner/backtest/{rule_name}
```

#### Parameters
- `rule_name` (path): Name of the scanner rule
- `symbols` (query): Comma-separated list of symbols to test
- `start_date` (query): Start date (YYYY-MM-DD)
- `end_date` (query): End date (YYYY-MM-DD)

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/v1/scanner/backtest/momentum_breakout?symbols=AAPL&start_date=2024-01-01&end_date=2024-12-31" \
     -H "accept: application/json"
```

#### Example Response
```json
{
  "rule_name": "momentum_breakout",
  "symbols_tested": ["AAPL"],
  "test_period": {
    "start": "2024-01-01",
    "end": "2024-12-31"
  },
  "performance": {
    "total_signals": 245,
    "winning_signals": 132,
    "losing_signals": 113,
    "win_rate": 0.539,
    "avg_win": 2.8,
    "avg_loss": -1.4,
    "profit_factor": 1.35,
    "max_drawdown": -8.2,
    "sharpe_ratio": 1.45
  }
}
```

### Optimize Scanner Rule

Optimize scanner rule parameters for better performance.

```http
POST /api/v1/scanner/optimize/{rule_name}
```

#### Parameters
- `rule_name` (path): Name of the scanner rule to optimize

#### Request Body
```json
{
  "parameter": "threshold",
  "min_value": 0.5,
  "max_value": 2.0,
  "steps": 10
}
```

#### Example Request
```bash
curl -X POST "http://localhost:8000/api/v1/scanner/optimize/momentum_breakout" \
     -H "Content-Type: application/json" \
     -d '{
       "parameter": "threshold",
       "min_value": 0.5,
       "max_value": 2.0,
       "steps": 10
     }'
```

#### Example Response
```json
{
  "rule_name": "momentum_breakout",
  "optimization_method": "grid_search",
  "best_parameters": {
    "threshold": 0.75
  },
  "optimization_results": {
    "best_score": 0.723,
    "improvement": 0.156,
    "computation_time": "45.2s",
    "iterations": 10
  }
}
```

## 🏥 Health & System API

### System Health Check

Get overall system health status.

```http
GET /api/v1/health/
```

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/v1/health/" \
     -H "accept: application/json"
```

#### Example Response
```json
{
  "status": "healthy",
  "timestamp": "2024-09-05T14:30:22Z",
  "version": "2.0.0",
  "service": "trading_system_api"
}
```

### Detailed Health Check

Get detailed health status with component information.

```http
GET /api/v1/health/detailed
```

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/v1/health/detailed" \
     -H "accept: application/json"
```

#### Example Response
```json
{
  "status": "healthy",
  "timestamp": "2024-09-05T14:30:22Z",
  "version": "2.0.0",
  "service": "trading_system_api",
  "components": {
    "database": {
      "status": "healthy",
      "response_time": "15ms",
      "connection_pool": {
        "active": 3,
        "idle": 7,
        "total": 10
      }
    },
    "api_layer": {
      "status": "healthy",
      "routes_configured": true
    },
    "system": {
      "cpu_percent": 45.2,
      "memory_percent": 67.8,
      "disk_percent": 23.4
    }
  }
}
```

### System Metrics

Get detailed system performance metrics.

```http
GET /api/v1/health/metrics
```

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/v1/health/metrics" \
     -H "accept: application/json"
```

### Dependency Status

Check external service dependencies.

```http
GET /api/v1/health/dependencies
```

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/v1/health/dependencies" \
     -H "accept: application/json"
```

## 📋 Common Response Formats

### Success Response
```json
{
  "data": { ... },
  "metadata": {
    "request_id": "req_123456",
    "processing_time": 0.045,
    "cached": false
  }
}
```

### Error Response
```json
{
  "error": "ValidationError",
  "message": "Invalid symbol format",
  "details": {
    "field": "symbol",
    "value": "INVALID@",
    "expected": "Alphanumeric characters only"
  },
  "request_id": "req_123456",
  "timestamp": "2024-09-05T14:30:22Z"
}
```

### Paginated Response
```json
{
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_pages": 10,
    "total_records": 500,
    "has_next": true,
    "has_previous": false
  },
  "metadata": {
    "request_id": "req_123456",
    "processing_time": 0.123
  }
}
```

## 🔧 Rate Limiting

### Rate Limits
- **Authenticated requests**: 1000 requests per minute
- **Unauthenticated requests**: 100 requests per minute
- **Scanner operations**: 50 requests per minute
- **Analytics operations**: 200 requests per minute

### Rate Limit Headers
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1631049600
X-RateLimit-Retry-After: 60
```

## 📊 Webhooks (Future)

### Webhook Registration
```http
POST /api/v1/webhooks/
```

### Webhook Events
- `market_data.updated` - New market data available
- `scanner.signal_generated` - New scanner signal
- `analytics.report_ready` - Analytics report completed
- `system.alert` - System alerts and notifications

## 🎯 Best Practices

### Error Handling
```javascript
// Always check response status
const response = await fetch('/api/v1/market-data/current/AAPL');
if (!response.ok) {
  const error = await response.json();
  console.error('API Error:', error.message);
  // Handle error appropriately
}
```

### Request Batching
```javascript
// Batch multiple requests when possible
const symbols = ['AAPL', 'MSFT', 'GOOGL'];
const requests = symbols.map(symbol =>
  fetch(`/api/v1/market-data/current/${symbol}`)
);
const responses = await Promise.all(requests);
```

### Caching Strategy
```javascript
// Implement client-side caching
const cache = new Map();

async function getMarketData(symbol) {
  if (cache.has(symbol)) {
    const cached = cache.get(symbol);
    if (Date.now() - cached.timestamp < 60000) { // 1 minute
      return cached.data;
    }
  }

  const response = await fetch(`/api/v1/market-data/current/${symbol}`);
  const data = await response.json();

  cache.set(symbol, {
    data,
    timestamp: Date.now()
  });

  return data;
}
```

### Connection Management
```javascript
// Use connection pooling and keep-alive
const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  timeout: 10000,
  headers: {
    'Connection': 'keep-alive'
  }
});
```

This REST API provides comprehensive access to all trading system functionality with high performance, automatic documentation, and robust error handling.
