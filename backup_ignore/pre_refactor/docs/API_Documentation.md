# DuckDB Financial Data API Documentation

## Overview

The DuckDB Financial Data API is a high-performance REST API for querying and analyzing financial market data with advanced resampling capabilities. Built on DuckDB for optimal analytical performance.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.example.com`

## Interactive Documentation

- **Swagger UI**: `{BASE_URL}/docs`
- **ReDoc**: `{BASE_URL}/redoc`
- **OpenAPI JSON**: `{BASE_URL}/openapi.json`

## Authentication

Currently no authentication is required. In production environments, implement appropriate security measures such as:
- API keys
- JWT tokens
- OAuth 2.0
- Rate limiting

## Data Format

All market data follows the standard OHLCV format:

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | string | Stock symbol (e.g., "RELIANCE") |
| `timestamp` | datetime | Timestamp in ISO format |
| `open` | float | Opening price |
| `high` | float | Highest price in period |
| `low` | float | Lowest price in period |
| `close` | float | Closing price |
| `volume` | integer | Trading volume |
| `date_partition` | date | Date partition for optimization |

## Supported Timeframes

| Timeframe | Description | Compression Ratio |
|-----------|-------------|-------------------|
| `1T` | 1 Minute | 1x (original) |
| `5T` | 5 Minutes | 5x |
| `15T` | 15 Minutes | 15x |
| `30T` | 30 Minutes | 30x |
| `1H` | 1 Hour | 60x |
| `4H` | 4 Hours | 240x |
| `1D` | 1 Day | ~375x |
| `1W` | 1 Week | ~1875x |
| `1M` | 1 Month | ~7500x |

## Aggregation Rules

When resampling to higher timeframes:

- **Open**: First open price in the period
- **High**: Maximum high price in the period
- **Low**: Minimum low price in the period
- **Close**: Last close price in the period
- **Volume**: Sum of all volumes in the period
- **Tick Count**: Number of minute bars aggregated

## API Endpoints

### Health & Information

#### GET `/`
Get basic API information and available endpoints.

#### GET `/health`
Check API and database health status.

**Response Example:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0"
}
```

### Data Access

#### POST `/market-data`
Retrieve raw minute-level OHLCV market data.

**Request Body:**
```json
{
  "symbol": "RELIANCE",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "start_time": "09:15",
  "end_time": "15:30",
  "limit": 1000
}
```

**Response Example:**
```json
{
  "data": [
    {
      "symbol": "RELIANCE",
      "timestamp": "2024-01-01 09:15:00",
      "open": 1000.0,
      "high": 1005.0,
      "low": 998.0,
      "close": 1002.0,
      "volume": 50000,
      "date_partition": "2024-01-01"
    }
  ],
  "count": 1,
  "columns": ["symbol", "timestamp", "open", "high", "low", "close", "volume", "date_partition"]
}
```

### Resampling

#### POST `/resample`
Resample data to higher timeframes using OHLCV aggregation.

**Request Body:**
```json
{
  "symbol": "RELIANCE",
  "timeframe": "1H",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31"
}
```

**Response Example:**
```json
{
  "data": [
    {
      "symbol": "RELIANCE",
      "timestamp": "2024-01-01 09:00:00",
      "open": 1000.0,
      "high": 1010.0,
      "low": 995.0,
      "close": 1005.0,
      "volume": 250000,
      "tick_count": 60,
      "timeframe": "1H"
    }
  ],
  "count": 1,
  "columns": ["symbol", "timestamp", "open", "high", "low", "close", "volume", "tick_count", "timeframe"]
}
```

#### POST `/multi-timeframe`
Get data for multiple timeframes simultaneously.

**Request Body:**
```json
{
  "symbol": "RELIANCE",
  "timeframes": ["15T", "1H", "1D"],
  "start_date": "2024-01-01",
  "end_date": "2024-01-31"
}
```

### Analytics

#### POST `/technical-indicators`
Calculate technical indicators.

**Request Body:**
```json
{
  "symbol": "RELIANCE",
  "timeframe": "1D",
  "indicators": ["sma_20", "rsi_14", "bollinger_bands"],
  "start_date": "2024-01-01",
  "end_date": "2024-01-31"
}
```

**Available Indicators:**
- `sma_20` - Simple Moving Average (20 periods)
- `sma_50` - Simple Moving Average (50 periods)
- `ema_12` - Exponential Moving Average (12 periods)
- `ema_26` - Exponential Moving Average (26 periods)
- `rsi_14` - Relative Strength Index (14 periods)
- `bollinger_bands` - Bollinger Bands (20 periods, 2 std dev)

#### GET `/market-summary`
Get market summary statistics.

**Query Parameters:**
- `symbols` - List of symbols to include
- `date_filter` - Specific date for analysis

#### POST `/correlation`
Calculate correlation matrix between symbols.

**Request Body:**
```json
{
  "symbols": ["RELIANCE", "TCS", "INFY"],
  "timeframe": "1D",
  "method": "returns",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31"
}
```

#### GET `/volume-profile/{symbol}`
Get volume profile analysis for a symbol.

**Query Parameters:**
- `start_date` - Start date for analysis
- `end_date` - End date for analysis
- `price_bins` - Number of price bins (default: 50)

### Custom Queries

#### POST `/custom-query`
Execute custom analytical SQL queries.

**Request Body:**
```json
{
  "query": "SELECT symbol, AVG(close) as avg_price, SUM(volume) as total_volume FROM market_data WHERE symbol = ? GROUP BY symbol",
  "params": ["RELIANCE"]
}
```

**Security Note:** Only SELECT statements are allowed for security reasons.

### Utilities

#### GET `/available-symbols`
Get list of all available symbols.

**Response Example:**
```json
{
  "symbols": ["RELIANCE", "TCS", "INFY", "HDFC", "ICICIBANK"],
  "count": 5
}
```

#### GET `/timeframes`
Get supported timeframes and technical indicators.

#### GET `/symbols`
Get symbol metadata from database.

### Management

#### POST `/load-symbol/{symbol}`
Load data for a specific symbol into the database.

**Query Parameters:**
- `start_date` - Start date for loading
- `end_date` - End date for loading

## Error Handling

The API uses standard HTTP status codes:

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found - Resource not found |
| 500 | Internal Server Error |

**Error Response Format:**
```json
{
  "detail": "Error message describing what went wrong"
}
```

## Rate Limiting

Currently no rate limiting is implemented. For production use, consider implementing:
- Request rate limits per IP/API key
- Concurrent connection limits
- Query complexity limits

## Performance Characteristics

- **Data Loading**: 3,495 records/second
- **Query Execution**: <10ms for 1000 records
- **Resampling**: 2-5ms per timeframe
- **Complex Analytics**: <1ms execution time
- **Concurrent Users**: Supports multiple simultaneous connections

## Client Libraries

### Python Example
```python
import requests

# Get available symbols
response = requests.get("http://localhost:8000/available-symbols")
symbols = response.json()["symbols"]

# Resample data
payload = {
    "symbol": "RELIANCE",
    "timeframe": "1H",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
}
response = requests.post("http://localhost:8000/resample", json=payload)
data = response.json()
```

### JavaScript Example
```javascript
// Get market data
const response = await fetch('http://localhost:8000/market-data', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    symbol: 'RELIANCE',
    start_date: '2024-01-01',
    limit: 1000
  })
});
const data = await response.json();
```

### cURL Example
```bash
# Health check
curl -X GET "http://localhost:8000/health"

# Resample data
curl -X POST "http://localhost:8000/resample" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "RELIANCE",
    "timeframe": "1H",
    "start_date": "2024-01-01"
  }'
```

## Best Practices

1. **Use appropriate timeframes** for your use case to optimize performance
2. **Limit query ranges** for large datasets to avoid timeouts
3. **Cache results** when possible to reduce API calls
4. **Use batch operations** for multiple symbols when available
5. **Monitor API health** using the `/health` endpoint
6. **Handle errors gracefully** with proper retry logic

## Support

- **Health Check**: `GET /health`
- **API Documentation**: `GET /docs`
- **OpenAPI Specification**: `GET /openapi.json`

For issues and questions, check the health endpoint and server logs for detailed error information.
