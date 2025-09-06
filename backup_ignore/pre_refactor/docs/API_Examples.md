# DuckDB Financial Data API - Examples

This document provides comprehensive examples for using the DuckDB Financial Data API across different programming languages and use cases.

## Table of Contents

1. [Quick Start Examples](#quick-start-examples)
2. [Python Examples](#python-examples)
3. [JavaScript/Node.js Examples](#javascriptnodejs-examples)
4. [cURL Examples](#curl-examples)
5. [Advanced Use Cases](#advanced-use-cases)
6. [Error Handling](#error-handling)
7. [Performance Optimization](#performance-optimization)

## Quick Start Examples

### 1. Check API Health
```bash
curl -X GET "http://localhost:8000/health"
```

### 2. Get Available Symbols
```bash
curl -X GET "http://localhost:8000/available-symbols"
```

### 3. Resample Data to 1-Hour Timeframe
```bash
curl -X POST "http://localhost:8000/resample" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "RELIANCE",
    "timeframe": "1H",
    "start_date": "2024-01-01",
    "end_date": "2024-01-02"
  }'
```

## Python Examples

### Basic Client Setup
```python
import requests
import pandas as pd
from datetime import date, timedelta
import json

class FinancialDataAPI:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_available_symbols(self):
        response = self.session.get(f"{self.base_url}/available-symbols")
        response.raise_for_status()
        return response.json()["symbols"]
    
    def resample_data(self, symbol, timeframe, start_date=None, end_date=None):
        payload = {"symbol": symbol, "timeframe": timeframe}
        if start_date:
            payload["start_date"] = start_date.isoformat()
        if end_date:
            payload["end_date"] = end_date.isoformat()
        
        response = self.session.post(f"{self.base_url}/resample", json=payload)
        response.raise_for_status()
        
        data = response.json()
        return pd.DataFrame(data["data"]) if data["count"] > 0 else pd.DataFrame()

# Usage
api = FinancialDataAPI()
symbols = api.get_available_symbols()
print(f"Available symbols: {len(symbols)}")

# Get hourly data for RELIANCE
hourly_data = api.resample_data("RELIANCE", "1H", date(2024, 1, 1), date(2024, 1, 2))
print(f"Hourly data shape: {hourly_data.shape}")
```

### Multi-Timeframe Analysis
```python
def multi_timeframe_analysis(api, symbol, start_date, end_date):
    """Perform multi-timeframe analysis for a symbol."""
    
    timeframes = ["15T", "1H", "4H", "1D"]
    results = {}
    
    # Get data for all timeframes
    payload = {
        "symbol": symbol,
        "timeframes": timeframes,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat()
    }
    
    response = api.session.post(f"{api.base_url}/multi-timeframe", json=payload)
    response.raise_for_status()
    
    data = response.json()
    
    for tf in timeframes:
        if data[tf]["count"] > 0:
            results[tf] = pd.DataFrame(data[tf]["data"])
            print(f"{tf}: {len(results[tf])} records")
    
    return results

# Usage
results = multi_timeframe_analysis(api, "RELIANCE", date(2024, 1, 1), date(2024, 1, 7))
```

### Technical Indicators
```python
def calculate_indicators(api, symbol, timeframe="1D", start_date=None, end_date=None):
    """Calculate technical indicators for a symbol."""
    
    payload = {
        "symbol": symbol,
        "timeframe": timeframe,
        "indicators": ["sma_20", "sma_50", "rsi_14", "bollinger_bands"]
    }
    
    if start_date:
        payload["start_date"] = start_date.isoformat()
    if end_date:
        payload["end_date"] = end_date.isoformat()
    
    response = api.session.post(f"{api.base_url}/technical-indicators", json=payload)
    response.raise_for_status()
    
    data = response.json()
    return pd.DataFrame(data["data"]) if data["count"] > 0 else pd.DataFrame()

# Usage
indicators = calculate_indicators(api, "RELIANCE", "1D", date(2024, 1, 1), date(2024, 1, 31))
print(f"Indicators calculated: {list(indicators.columns)}")
```

### Custom Analytical Queries
```python
def custom_analysis(api, query, params=None):
    """Execute custom analytical query."""
    
    payload = {"query": query}
    if params:
        payload["params"] = params
    
    response = api.session.post(f"{api.base_url}/custom-query", json=payload)
    response.raise_for_status()
    
    data = response.json()
    return pd.DataFrame(data["data"]) if data["count"] > 0 else pd.DataFrame()

# Example: Calculate VWAP for multiple symbols
vwap_query = """
    SELECT 
        symbol,
        date_partition,
        SUM(close * volume) / SUM(volume) as vwap,
        AVG(close) as avg_price,
        SUM(volume) as total_volume,
        STDDEV(close) as volatility
    FROM market_data 
    WHERE symbol IN (?, ?, ?) AND date_partition >= ?
    GROUP BY symbol, date_partition
    ORDER BY symbol, date_partition
"""

vwap_data = custom_analysis(api, vwap_query, ["RELIANCE", "TCS", "INFY", "2024-01-01"])
print(f"VWAP analysis: {vwap_data.shape}")
```

## JavaScript/Node.js Examples

### Basic Client Setup
```javascript
class FinancialDataAPI {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }

    async getAvailableSymbols() {
        const response = await fetch(`${this.baseUrl}/available-symbols`);
        const data = await response.json();
        return data.symbols;
    }

    async resampleData(symbol, timeframe, startDate = null, endDate = null) {
        const payload = { symbol, timeframe };
        if (startDate) payload.start_date = startDate;
        if (endDate) payload.end_date = endDate;

        const response = await fetch(`${this.baseUrl}/resample`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        return data.data;
    }

    async getMarketData(symbol, startDate = null, endDate = null, limit = null) {
        const payload = { symbol };
        if (startDate) payload.start_date = startDate;
        if (endDate) payload.end_date = endDate;
        if (limit) payload.limit = limit;

        const response = await fetch(`${this.baseUrl}/market-data`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        return data.data;
    }
}

// Usage
const api = new FinancialDataAPI();

async function example() {
    try {
        // Get available symbols
        const symbols = await api.getAvailableSymbols();
        console.log(`Available symbols: ${symbols.length}`);

        // Get hourly data
        const hourlyData = await api.resampleData('RELIANCE', '1H', '2024-01-01', '2024-01-02');
        console.log(`Hourly data records: ${hourlyData.length}`);

        // Get raw market data
        const marketData = await api.getMarketData('RELIANCE', '2024-01-01', null, 1000);
        console.log(`Market data records: ${marketData.length}`);

    } catch (error) {
        console.error('API Error:', error);
    }
}

example();
```

### Real-time Data Processing
```javascript
async function realTimeProcessor(api, symbols, timeframe = '5T') {
    const processSymbol = async (symbol) => {
        try {
            const data = await api.resampleData(symbol, timeframe);
            
            if (data.length > 0) {
                const latest = data[data.length - 1];
                console.log(`${symbol} (${timeframe}): ${latest.close} (Vol: ${latest.volume})`);
                
                // Process the data (e.g., send to dashboard, trigger alerts, etc.)
                return { symbol, latest, status: 'success' };
            }
        } catch (error) {
            console.error(`Error processing ${symbol}:`, error);
            return { symbol, status: 'error', error: error.message };
        }
    };

    // Process all symbols in parallel
    const results = await Promise.all(symbols.map(processSymbol));
    return results;
}

// Usage
const symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFC'];
realTimeProcessor(api, symbols, '15T').then(results => {
    console.log('Processing complete:', results);
});
```

## cURL Examples

### Health Check
```bash
curl -X GET "http://localhost:8000/health" \
  -H "Accept: application/json"
```

### Get Market Data with Filters
```bash
curl -X POST "http://localhost:8000/market-data" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "RELIANCE",
    "start_date": "2024-01-01",
    "end_date": "2024-01-02",
    "start_time": "09:15",
    "end_time": "15:30",
    "limit": 500
  }'
```

### Resample to Multiple Timeframes
```bash
curl -X POST "http://localhost:8000/multi-timeframe" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "RELIANCE",
    "timeframes": ["5T", "15T", "1H", "1D"],
    "start_date": "2024-01-01",
    "end_date": "2024-01-07"
  }'
```

### Calculate Technical Indicators
```bash
curl -X POST "http://localhost:8000/technical-indicators" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "RELIANCE",
    "timeframe": "1D",
    "indicators": ["sma_20", "rsi_14", "bollinger_bands"],
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  }'
```

### Custom Query - Top Performers
```bash
curl -X POST "http://localhost:8000/custom-query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT symbol, AVG(close) as avg_price, SUM(volume) as total_volume FROM market_data WHERE date_partition >= ? GROUP BY symbol ORDER BY total_volume DESC LIMIT 10",
    "params": ["2024-01-01"]
  }'
```

### Volume Profile Analysis
```bash
curl -X GET "http://localhost:8000/volume-profile/RELIANCE?start_date=2024-01-01&end_date=2024-01-31&price_bins=20" \
  -H "Accept: application/json"
```

## Advanced Use Cases

### 1. Multi-Symbol Portfolio Analysis
```python
def portfolio_analysis(api, symbols, start_date, end_date):
    """Analyze a portfolio of symbols."""
    
    # Get daily data for all symbols
    portfolio_data = {}
    
    for symbol in symbols:
        daily_data = api.resample_data(symbol, "1D", start_date, end_date)
        if not daily_data.empty:
            portfolio_data[symbol] = daily_data
    
    # Calculate portfolio metrics
    results = {}
    
    for symbol, data in portfolio_data.items():
        if len(data) > 1:
            # Calculate returns
            data['returns'] = data['close'].pct_change()
            
            results[symbol] = {
                'total_return': (data['close'].iloc[-1] / data['close'].iloc[0] - 1) * 100,
                'volatility': data['returns'].std() * 100,
                'avg_volume': data['volume'].mean(),
                'max_drawdown': ((data['close'] / data['close'].cummax()) - 1).min() * 100
            }
    
    return results

# Usage
portfolio = ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'ICICIBANK']
analysis = portfolio_analysis(api, portfolio, date(2024, 1, 1), date(2024, 1, 31))

for symbol, metrics in analysis.items():
    print(f"{symbol}: Return={metrics['total_return']:.2f}%, Vol={metrics['volatility']:.2f}%")
```

### 2. Algorithmic Trading Strategy Backtesting
```python
def simple_moving_average_strategy(api, symbol, short_window=20, long_window=50):
    """Backtest a simple moving average crossover strategy."""
    
    # Get technical indicators
    indicators = calculate_indicators(api, symbol, "1D")
    
    if indicators.empty:
        return None
    
    # Calculate signals
    indicators['sma_short'] = indicators['close'].rolling(window=short_window).mean()
    indicators['sma_long'] = indicators['close'].rolling(window=long_window).mean()
    
    # Generate trading signals
    indicators['signal'] = 0
    indicators.loc[indicators['sma_short'] > indicators['sma_long'], 'signal'] = 1
    indicators.loc[indicators['sma_short'] <= indicators['sma_long'], 'signal'] = -1
    
    # Calculate strategy returns
    indicators['strategy_returns'] = indicators['signal'].shift(1) * indicators['close'].pct_change()
    indicators['cumulative_returns'] = (1 + indicators['strategy_returns']).cumprod()
    
    # Performance metrics
    total_return = indicators['cumulative_returns'].iloc[-1] - 1
    sharpe_ratio = indicators['strategy_returns'].mean() / indicators['strategy_returns'].std() * (252**0.5)
    
    return {
        'total_return': total_return * 100,
        'sharpe_ratio': sharpe_ratio,
        'data': indicators
    }

# Usage
strategy_results = simple_moving_average_strategy(api, "RELIANCE")
if strategy_results:
    print(f"Strategy Return: {strategy_results['total_return']:.2f}%")
    print(f"Sharpe Ratio: {strategy_results['sharpe_ratio']:.2f}")
```

### 3. Market Microstructure Analysis
```python
def microstructure_analysis(api, symbol, date_filter):
    """Analyze market microstructure for a specific day."""
    
    # Get minute-level data
    payload = {
        "symbol": symbol,
        "start_date": date_filter.isoformat(),
        "end_date": date_filter.isoformat()
    }
    
    response = api.session.post(f"{api.base_url}/market-data", json=payload)
    data = response.json()
    
    if data["count"] == 0:
        return None
    
    df = pd.DataFrame(data["data"])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Calculate microstructure metrics
    df['spread'] = df['high'] - df['low']
    df['mid_price'] = (df['high'] + df['low']) / 2
    df['price_impact'] = abs(df['close'] - df['mid_price'])
    df['volume_rate'] = df['volume'] / df['volume'].rolling(window=20).mean()
    
    # Intraday patterns
    df['hour'] = df['timestamp'].dt.hour
    hourly_stats = df.groupby('hour').agg({
        'volume': 'mean',
        'spread': 'mean',
        'price_impact': 'mean'
    })
    
    return {
        'total_volume': df['volume'].sum(),
        'avg_spread': df['spread'].mean(),
        'avg_price_impact': df['price_impact'].mean(),
        'hourly_patterns': hourly_stats.to_dict(),
        'data': df
    }

# Usage
microstructure = microstructure_analysis(api, "RELIANCE", date(2024, 1, 15))
if microstructure:
    print(f"Total Volume: {microstructure['total_volume']:,}")
    print(f"Average Spread: {microstructure['avg_spread']:.2f}")
```

## Error Handling

### Python Error Handling
```python
import requests
from requests.exceptions import RequestException, HTTPError, Timeout

def safe_api_call(api_func, *args, **kwargs):
    """Wrapper for safe API calls with error handling."""
    
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            return api_func(*args, **kwargs)
            
        except HTTPError as e:
            if e.response.status_code == 400:
                print(f"Bad request: {e.response.text}")
                break  # Don't retry on client errors
            elif e.response.status_code >= 500:
                print(f"Server error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
            raise
            
        except Timeout:
            print(f"Request timeout (attempt {attempt + 1})")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            raise
            
        except RequestException as e:
            print(f"Request failed: {e}")
            raise
    
    return None

# Usage
result = safe_api_call(api.resample_data, "RELIANCE", "1H", date(2024, 1, 1))
```

### JavaScript Error Handling
```javascript
async function safeApiCall(apiFunction, ...args) {
    const maxRetries = 3;
    let retryDelay = 1000;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
        try {
            return await apiFunction(...args);
        } catch (error) {
            if (error.response?.status === 400) {
                console.error('Bad request:', error.response.data);
                break; // Don't retry client errors
            } else if (error.response?.status >= 500) {
                console.error(`Server error (attempt ${attempt + 1}):`, error.message);
                if (attempt < maxRetries - 1) {
                    await new Promise(resolve => setTimeout(resolve, retryDelay * Math.pow(2, attempt)));
                    continue;
                }
            }
            throw error;
        }
    }
    return null;
}

// Usage
const result = await safeApiCall(api.resampleData.bind(api), 'RELIANCE', '1H', '2024-01-01');
```

## Performance Optimization

### 1. Batch Processing
```python
def batch_process_symbols(api, symbols, timeframe, batch_size=10):
    """Process symbols in batches for better performance."""
    
    results = {}
    
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        batch_results = {}
        
        # Process batch in parallel
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(api.resample_data, symbol, timeframe): symbol 
                for symbol in batch
            }
            
            for future in concurrent.futures.as_completed(futures):
                symbol = futures[future]
                try:
                    data = future.result()
                    batch_results[symbol] = data
                except Exception as e:
                    print(f"Error processing {symbol}: {e}")
        
        results.update(batch_results)
        print(f"Processed batch {i//batch_size + 1}: {len(batch)} symbols")
    
    return results

# Usage
all_symbols = api.get_available_symbols()
results = batch_process_symbols(api, all_symbols[:50], "1D", batch_size=10)
```

### 2. Caching Strategy
```python
import pickle
import os
from datetime import datetime, timedelta

class CachedAPI:
    def __init__(self, api, cache_dir="./cache"):
        self.api = api
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_key(self, method, *args, **kwargs):
        """Generate cache key from method and parameters."""
        key_data = f"{method}_{args}_{sorted(kwargs.items())}"
        return hash(key_data)
    
    def _is_cache_valid(self, cache_file, max_age_hours=1):
        """Check if cache file is still valid."""
        if not os.path.exists(cache_file):
            return False
        
        file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file))
        return file_age < timedelta(hours=max_age_hours)
    
    def resample_data_cached(self, symbol, timeframe, start_date=None, end_date=None):
        """Cached version of resample_data."""
        
        cache_key = self._get_cache_key("resample", symbol, timeframe, start_date, end_date)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        
        # Try to load from cache
        if self._is_cache_valid(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except:
                pass  # Cache corrupted, fetch fresh data
        
        # Fetch fresh data
        data = self.api.resample_data(symbol, timeframe, start_date, end_date)
        
        # Save to cache
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
        except:
            pass  # Cache write failed, but we have the data
        
        return data

# Usage
cached_api = CachedAPI(api)
data = cached_api.resample_data_cached("RELIANCE", "1H")  # Cached for 1 hour
```

### 3. Connection Pooling
```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class OptimizedAPI:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        
        # Configure connection pooling and retries
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        adapter = HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=retry_strategy
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set timeouts
        self.session.timeout = 30

# Usage
optimized_api = OptimizedAPI()
```

This comprehensive collection of examples demonstrates the full capabilities of the DuckDB Financial Data API across different programming languages and use cases. The API supports complex queries, resampling to higher timeframes, and advanced analytical operations suitable for professional financial applications.
