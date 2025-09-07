# Scanner API for Frontend Development

## Overview

This document provides a comprehensive analysis and implementation of the Scanner API for the DuckDB Financial Infrastructure project. The API exposes powerful breakout pattern detection capabilities for frontend applications with real-time scanning, comprehensive analytics, and professional-grade performance metrics.

## 🏗️ Architecture Analysis

### Core Components

1. **BreakoutScanner** (`src/application/scanners/strategies/breakout_scanner.py`)
   - Enhanced breakout pattern detection with probability scoring
   - Date range analysis with end-of-day tracking
   - Configurable parameters for different market conditions
   - Professional table display and CSV export functionality

2. **BaseScanner** (`src/application/scanners/base_scanner.py`)
   - Abstract base class for all scanner implementations
   - Database connectivity and query execution
   - Technical indicators integration
   - Async support for concurrent operations

3. **Enhanced Scanner API** (`src/interfaces/api/routes/scanner_api.py`)
   - Comprehensive REST endpoints
   - Real-time WebSocket support
   - Batch processing capabilities
   - Performance monitoring and statistics

## 🚀 API Capabilities

### Core Features

- **Real-time Scanning**: Execute breakout pattern scans with configurable parameters
- **Date Range Analysis**: Scan multiple trading days with comprehensive tracking
- **Market Overview**: Get current market statistics and sentiment
- **Performance Analytics**: Historical performance tracking and optimization
- **Live Updates**: WebSocket-based real-time scan results
- **Export Functionality**: CSV export for further analysis
- **Batch Processing**: Execute multiple scans concurrently

### Scanner Types

1. **Enhanced Breakout** (`enhanced_breakout`)
   - Probability-based scoring system
   - Volume confirmation analysis
   - End-of-day performance tracking
   - Success rate calculation

2. **Basic Breakout** (`breakout`)
   - Simple resistance level breaks
   - Volume ratio confirmation
   - Single-day analysis

3. **Volume Spike** (`volume_spike`)
   - Unusual volume detection
   - Momentum confirmation
   - Time-based filtering

4. **Technical** (`technical`)
   - Technical indicator combinations
   - Multi-timeframe analysis
   - Pattern recognition

## 📊 Key Metrics & Analytics

### Breakout Analysis Metrics

- **Probability Score**: Weighted combination of breakout strength, volume confirmation, and price momentum
- **Performance Rank**: Overall ranking based on probability and historical performance
- **Success Rate**: Percentage of successful breakouts over time
- **Volume Ratio**: Current volume vs. average volume
- **Price Change**: Breakout price to end-of-day price movement
- **Day Range**: Intraday volatility measurement

### Market Overview Metrics

- **Total Symbols**: Available symbols in the database
- **Advancing/Declining**: Market breadth indicators
- **Breakout Candidates**: Current breakout opportunities
- **High Volume Count**: Symbols with unusual volume
- **Top Sector**: Best performing sector
- **Market Sentiment**: Overall market direction
- **Volatility Regime**: Current volatility classification

## 🔧 Configuration Options

### Scanner Configuration

```json
{
  "consolidation_period": 5,        // Days for consolidation analysis
  "breakout_volume_ratio": 1.5,     // Minimum volume ratio for confirmation
  "resistance_break_pct": 0.5,      // Minimum breakout percentage
  "min_price": 50,                  // Minimum stock price filter
  "max_price": 2000,                // Maximum stock price filter
  "max_results_per_day": 3,         // Top results per trading day
  "min_volume": 10000,              // Minimum volume threshold
  "min_probability_score": 10.0     // Minimum probability score
}
```

### Time Windows

- **Morning Session**: 09:15-09:50 (Pre-market breakouts)
- **Mid-Morning**: 09:50-11:00 (Early momentum)
- **Midday**: 11:00-13:00 (Consolidation period)
- **Afternoon**: 13:00-15:15 (Late session moves)
- **Full Day**: 09:15-15:15 (Complete session analysis)

## 🌐 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health check |
| GET | `/scanners` | Available scanners status |
| POST | `/scan` | Execute market scan |
| GET | `/market-overview` | Current market statistics |
| GET | `/symbols` | Available symbols list |
| GET | `/config/default` | Default configuration |
| POST | `/config/validate` | Validate configuration |
| GET | `/export/{scan_id}/csv` | Export results to CSV |
| GET | `/stats/performance` | Performance statistics |
| POST | `/batch-scan` | Execute multiple scans |
| WebSocket | `/ws/live-scan` | Real-time updates |

### Request/Response Examples

#### Execute Scan Request
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
    "max_results_per_day": 5,
    "min_probability_score": 15.0
  }
}
```

#### Scan Response
```json
{
  "scan_id": "scan_20250115_103000",
  "scanner_type": "enhanced_breakout",
  "total_results": 15,
  "successful_breakouts": 10,
  "success_rate": 66.7,
  "avg_price_change": 2.34,
  "avg_probability_score": 75.2,
  "execution_time_ms": 2340,
  "results": [
    {
      "symbol": "RELIANCE",
      "breakout_price": 2450.50,
      "eod_price": 2467.80,
      "price_change_pct": 0.71,
      "probability_score": 75.5,
      "breakout_successful": true
    }
  ]
}
```

## 💻 Frontend Integration

### JavaScript/React Example

```javascript
// Initialize scanner client
class ScannerClient {
  constructor(baseUrl = 'http://localhost:8000/api/v1/scanner') {
    this.baseUrl = baseUrl;
    this.websocket = null;
  }

  async executeScan(config) {
    const response = await fetch(`${this.baseUrl}/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    return response.json();
  }

  async getMarketOverview() {
    const response = await fetch(`${this.baseUrl}/market-overview`);
    return response.json();
  }

  connectLiveFeed(onUpdate) {
    this.websocket = new WebSocket(`ws://localhost:8000/api/v1/scanner/ws/live-scan`);
    this.websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onUpdate(data);
    };
  }
}

// Usage example
const scanner = new ScannerClient();

// Execute scan
const results = await scanner.executeScan({
  scanner_type: 'enhanced_breakout',
  scan_date: '2025-01-15',
  config: { max_results_per_day: 10 }
});

// Connect live feed
scanner.connectLiveFeed((data) => {
  console.log('Live update:', data.results);
});
```

### React Component Example

```jsx
import React, { useState, useEffect } from 'react';

const ScannerDashboard = () => {
  const [scanResults, setScanResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [marketOverview, setMarketOverview] = useState(null);

  const executeScan = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/scanner/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scanner_type: 'enhanced_breakout',
          scan_date: new Date().toISOString().split('T')[0]
        })
      });
      const data = await response.json();
      setScanResults(data);
    } catch (error) {
      console.error('Scan failed:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Load market overview on component mount
    fetch('/api/v1/scanner/market-overview')
      .then(response => response.json())
      .then(data => setMarketOverview(data));
  }, []);

  return (
    <div className="scanner-dashboard">
      <h1>Market Scanner</h1>
      
      {marketOverview && (
        <div className="market-overview">
          <div className="metric">
            <span>Total Symbols: {marketOverview.total_symbols}</span>
          </div>
          <div className="metric">
            <span>Breakout Candidates: {marketOverview.breakout_candidates}</span>
          </div>
          <div className="metric">
            <span>Market Sentiment: {marketOverview.market_sentiment}</span>
          </div>
        </div>
      )}

      <button onClick={executeScan} disabled={loading}>
        {loading ? 'Scanning...' : 'Run Scan'}
      </button>

      {scanResults && (
        <div className="scan-results">
          <h2>Scan Results ({scanResults.total_results})</h2>
          <div className="summary">
            <span>Success Rate: {scanResults.success_rate}%</span>
            <span>Avg Price Change: {scanResults.avg_price_change}%</span>
            <span>Execution Time: {scanResults.execution_time_ms}ms</span>
          </div>
          
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Probability Score</th>
                <th>Price Change %</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {scanResults.results.map((result, index) => (
                <tr key={index}>
                  <td>{result.symbol}</td>
                  <td>{result.probability_score.toFixed(1)}</td>
                  <td className={result.price_change_pct >= 0 ? 'positive' : 'negative'}>
                    {result.price_change_pct.toFixed(2)}%
                  </td>
                  <td>{result.breakout_successful ? '✅' : '❌'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default ScannerDashboard;
```

## 🎯 Frontend Demo

A complete frontend demo is available at `frontend_demo/index.html` featuring:

- **Interactive Controls**: Scanner type, date selection, time windows
- **Real-time Updates**: WebSocket integration for live scanning
- **Visual Results**: Professional table display with color-coded metrics
- **Export Functionality**: CSV download capability
- **Performance Metrics**: Execution time and success rate tracking
- **Responsive Design**: Mobile-friendly interface

### Running the Demo

1. Start the FastAPI server:
```bash
cd /Users/apple/Downloads/duckDbData
python web.py
```

2. Open the demo in a browser:
```bash
open frontend_demo/index.html
```

## 🔧 Development Setup

### Prerequisites

- Python 3.8+
- FastAPI
- DuckDB
- Pandas
- Pydantic v2

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the API server:
```bash
python web.py
```

3. Access the API documentation:
```
http://localhost:8000/docs
```

## 📈 Performance Characteristics

### Typical Performance Metrics

- **Single Day Scan**: 1-3 seconds for 500 symbols
- **Date Range Scan**: 5-15 seconds for 5-day range
- **Market Overview**: 500ms-1s
- **WebSocket Updates**: 30-second intervals
- **CSV Export**: 2-5 seconds depending on result size

### Optimization Recommendations

1. **Caching**: Implement Redis for frequently accessed data
2. **Database Indexing**: Ensure proper indexes on timestamp and symbol columns
3. **Connection Pooling**: Use connection pools for database access
4. **Async Processing**: Leverage async endpoints for concurrent operations
5. **Result Pagination**: Implement pagination for large result sets

## 🛡️ Security Considerations

### Production Deployment

1. **Authentication**: Implement JWT or API key authentication
2. **Rate Limiting**: Add rate limiting to prevent abuse
3. **CORS**: Configure CORS policies appropriately
4. **Input Validation**: Validate all input parameters
5. **Error Handling**: Implement proper error handling and logging

### Example Security Configuration

```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

# Rate limiting
@router.post("/scan")
@limiter.limit("10/minute")
async def run_scan(request: Request, scan_request: ScanRequest):
    # Implementation
    pass

# Authentication
from fastapi.security import HTTPBearer
security = HTTPBearer()

@router.post("/scan")
async def run_scan(scan_request: ScanRequest, token: str = Depends(security)):
    # Validate token
    # Implementation
    pass
```

## 🚀 Deployment

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "src.interfaces.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration

```bash
# .env file
DATABASE_URL=duckdb:///data/financial_data.duckdb
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:3000", "https://yourdomain.com"]
```

## 📚 Additional Resources

- **API Documentation**: Available at `/docs` when server is running
- **Interactive Testing**: Use the Swagger UI at `/docs` for testing
- **WebSocket Testing**: Use browser developer tools or WebSocket clients
- **Performance Monitoring**: Check `/metrics` endpoint for Prometheus metrics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Note**: This Scanner API provides a comprehensive foundation for building sophisticated financial analysis applications. The combination of real-time scanning, detailed analytics, and professional-grade performance makes it suitable for both development and production environments.