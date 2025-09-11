# Scanner API Documentation

## Overview

The Enhanced Scanner API provides comprehensive REST endpoints for executing breakout pattern scans on financial market data. This API is designed for frontend applications that need real-time scanning capabilities with detailed breakout analysis.

## Base URL

```
http://localhost:8000/api/v1/scanner
```

## Authentication

Currently, no authentication is required. In production, implement appropriate authentication mechanisms.

## API Endpoints

### 1. Health Check

**GET** `/health`

Check the health status of the scanner service.

**Response:**
```json
{
  "status": "healthy",
  "service": "scanner_api",
  "version": "1.0.0",
  "database_connected": true,
  "available_symbols": 500,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 2. Get Available Scanners

**GET** `/scanners`

Retrieve list of available scanners with their status.

**Response:**
```json
[
  {
    "scanner_name": "enhanced_breakout",
    "is_available": true,
    "last_scan": "2025-01-15T10:25:00Z",
    "total_scans": 1247,
    "avg_execution_time_ms": 2340.5,
    "success_rate": 67.8
  }
]
```

### 3. Execute Market Scan

**POST** `/scan`

Execute a comprehensive market scan with specified parameters.

**Request Body:**
```json
{
  "scanner_type": "enhanced_breakout",
  "scan_date": "2025-01-15",
  "start_date": "2025-01-10",
  "end_date": "2025-01-15",
  "cutoff_time": "09:50:00",
  "end_of_day_time": "15:15:00",
  "symbols": ["RELIANCE", "TCS", "HDFCBANK"],
  "config": {
    "consolidation_period": 5,
    "breakout_volume_ratio": 1.5,
    "resistance_break_pct": 0.5,
    "min_price": 50,
    "max_price": 2000,
    "max_results_per_day": 3,
    "min_probability_score": 10.0
  }
}
```

**Response:**
```json
{
  "scan_id": "scan_20250115_103000",
  "scanner_type": "enhanced_breakout",
  "scan_date": "2025-01-15",
  "start_date": "2025-01-10",
  "end_date": "2025-01-15",
  "total_results": 15,
  "successful_breakouts": 10,
  "success_rate": 66.7,
  "avg_price_change": 2.34,
  "avg_probability_score": 75.2,
  "execution_time_ms": 2340,
  "results": [
    {
      "symbol": "RELIANCE",
      "scan_date": "2025-01-15",
      "breakout_price": 2450.50,
      "eod_price": 2467.80,
      "price_change_pct": 0.71,
      "breakout_pct": 1.2,
      "volume_ratio": 2.3,
      "probability_score": 75.5,
      "performance_rank": 8.2,
      "day_range_pct": 3.1,
      "breakout_successful": true,
      "current_volume": 1250000,
      "eod_volume": 1450000,
      "breakout_time": "09:50:00",
      "overall_success_rate": 66.7
    }
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 4. Get Market Overview

**GET** `/market-overview`

Get current market overview with key statistics.

**Response:**
```json
{
  "total_symbols": 500,
  "advancing_count": 300,
  "declining_count": 200,
  "breakout_candidates": 15,
  "high_volume_count": 75,
  "top_sector": "Information Technology",
  "market_sentiment": "Bullish",
  "volatility_regime": "Medium",
  "last_updated": "2025-01-15T10:30:00Z"
}
```

### 5. Get Available Symbols

**GET** `/symbols`

Get list of available symbols for scanning.

**Query Parameters:**
- `limit` (int): Maximum number of symbols (default: 100, max: 1000)
- `search` (string): Search filter for symbol names

**Response:**
```json
["RELIANCE", "TCS", "HDFCBANK", "INFY", "ITC", "WIPRO", "LT", "SBIN"]
```

### 6. Get Default Configuration

**GET** `/config/default`

Get default scanner configuration parameters.

**Response:**
```json
{
  "consolidation_period": 5,
  "breakout_volume_ratio": 1.5,
  "resistance_break_pct": 0.5,
  "min_price": 50,
  "max_price": 2000,
  "max_results_per_day": 3,
  "min_volume": 10000,
  "min_probability_score": 10.0
}
```

### 7. Validate Configuration

**POST** `/config/validate`

Validate scanner configuration parameters.

**Request Body:**
```json
{
  "consolidation_period": 5,
  "breakout_volume_ratio": 1.5,
  "resistance_break_pct": 0.5,
  "min_price": 50,
  "max_price": 2000,
  "max_results_per_day": 3,
  "min_volume": 10000,
  "min_probability_score": 10.0
}
```

**Response:**
```json
{
  "valid": true,
  "message": "Configuration is valid",
  "config": { /* validated config */ }
}
```

### 8. Export Scan Results

**GET** `/export/{scan_id}/csv`

Export scan results to CSV format.

**Response:** CSV file download

### 9. Get Performance Statistics

**GET** `/stats/performance`

Get scanner performance statistics over specified period.

**Query Parameters:**
- `days` (int): Number of days to analyze (default: 30, max: 365)

**Response:**
```json
{
  "period_days": 30,
  "start_date": "2024-12-16",
  "end_date": "2025-01-15",
  "total_scans": 45,
  "total_breakouts_found": 127,
  "successful_breakouts": 86,
  "overall_success_rate": 67.7,
  "avg_price_change": 2.34,
  "best_performing_day": "2025-01-10",
  "worst_performing_day": "2025-01-05",
  "top_symbols": ["RELIANCE", "TCS", "HDFCBANK"],
  "avg_execution_time_ms": 2340,
  "generated_at": "2025-01-15T10:30:00Z"
}
```

### 10. Batch Scan

**POST** `/batch-scan`

Execute multiple scans concurrently.

**Query Parameters:**
- `max_concurrent` (int): Maximum concurrent scans (default: 3, max: 10)

**Request Body:**
```json
[
  {
    "scanner_type": "enhanced_breakout",
    "scan_date": "2025-01-15",
    "cutoff_time": "09:50:00"
  },
  {
    "scanner_type": "enhanced_breakout",
    "scan_date": "2025-01-14",
    "cutoff_time": "09:50:00"
  }
]
```

**Response:** Array of scan responses

### 11. WebSocket Live Scan

**WebSocket** `/ws/live-scan`

Real-time scanning updates via WebSocket connection.

**Message Format:**
```json
{
  "type": "scan_update",
  "timestamp": "2025-01-15T10:30:00Z",
  "results": [
    {
      "symbol": "RELIANCE",
      "current_price": 2450.50,
      "breakout_pct": 1.2,
      "volume_ratio": 2.3,
      "probability_score": 75.5
    }
  ]
}
```

## Scanner Types

- `enhanced_breakout`: Comprehensive breakout scanner with probability scoring
- `breakout`: Basic breakout pattern detection
- `volume_spike`: Volume spike detection
- `technical`: Technical indicator-based scanning

## Configuration Parameters

### Scanner Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `consolidation_period` | int | 5 | Days for consolidation check |
| `breakout_volume_ratio` | float | 1.5 | Volume ratio for breakout confirmation |
| `resistance_break_pct` | float | 0.5 | Break above resistance percentage |
| `min_price` | float | 50 | Minimum stock price |
| `max_price` | float | 2000 | Maximum stock price |
| `max_results_per_day` | int | 3 | Maximum results per day |
| `min_volume` | int | 10000 | Minimum volume threshold |
| `min_probability_score` | float | 10.0 | Minimum probability score |

## Error Handling

The API uses standard HTTP status codes:

- `200`: Success
- `400`: Bad Request (invalid parameters)
- `404`: Not Found (scan ID not found)
- `500`: Internal Server Error
- `503`: Service Unavailable

**Error Response Format:**
```json
{
  "error": "Scanner error",
  "detail": "Detailed error message"
}
```

## Rate Limiting

- Maximum 100 requests per minute per IP
- Batch scans limited to 10 concurrent requests
- WebSocket connections limited to 5 per IP

## Frontend Integration Examples

### JavaScript/React Example

```javascript
// Execute a scan
const scanData = {
  scanner_type: "enhanced_breakout",
  scan_date: "2025-01-15",
  cutoff_time: "09:50:00",
  config: {
    max_results_per_day: 5,
    min_probability_score: 15.0
  }
};

const response = await fetch('/api/v1/scanner/scan', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(scanData)
});

const results = await response.json();
console.log(`Found ${results.total_results} breakout candidates`);
```

### WebSocket Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/scanner/ws/live-scan');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'scan_update') {
    updateUI(data.results);
  }
};
```

### Python Client Example

```python
import requests
import json

# Execute scan
scan_request = {
    "scanner_type": "enhanced_breakout",
    "scan_date": "2025-01-15",
    "cutoff_time": "09:50:00"
}

response = requests.post(
    "http://localhost:8000/api/v1/scanner/scan",
    json=scan_request
)

if response.status_code == 200:
    results = response.json()
    print(f"Found {results['total_results']} breakout candidates")
    for result in results['results']:
        print(f"{result['symbol']}: {result['probability_score']:.1f}%")
```

## Best Practices

1. **Caching**: Cache market overview and symbol lists to reduce API calls
2. **Error Handling**: Implement proper error handling for network failures
3. **Rate Limiting**: Respect rate limits and implement exponential backoff
4. **WebSocket**: Use WebSocket for real-time updates instead of polling
5. **Batch Operations**: Use batch scan for multiple date ranges
6. **Configuration**: Validate configuration before sending scan requests

## Performance Considerations

- Single scans typically complete in 1-3 seconds
- Date range scans may take 5-15 seconds depending on range
- WebSocket updates are sent every 30 seconds
- CSV exports are generated on-demand and may take 2-5 seconds

## Support

For API support and questions:
- Check the interactive API documentation at `/docs`
- Review error logs for detailed error information
- Monitor performance statistics for optimization opportunities