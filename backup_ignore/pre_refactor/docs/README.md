# DuckDB Financial Data Infrastructure

A comprehensive infrastructure for managing and querying financial market data using DuckDB, with advanced resampling capabilities and REST API access.

## 🚀 Features

### Core Capabilities
- **High-Performance Database**: DuckDB backend optimized for analytical workloads
- **Data Resampling**: Convert minute data to higher timeframes (5min, 15min, 1hour, daily, weekly, monthly)
- **Technical Indicators**: Built-in calculation of SMA, EMA, RSI, Bollinger Bands, and more
- **Complex Analytics**: Volume profile, correlation analysis, market summaries
- **REST API**: Full HTTP API for external program integration
- **Custom Queries**: Execute complex SQL queries with full DuckDB capabilities

### Supported Timeframes
- `1T` - 1 Minute (original data)
- `5T` - 5 Minutes
- `15T` - 15 Minutes  
- `30T` - 30 Minutes
- `1H` - 1 Hour
- `4H` - 4 Hours
- `1D` - 1 Day
- `1W` - 1 Week
- `1M` - 1 Month

## 📦 Installation

### 1. Environment Setup
```bash
# Create conda environment
conda create -n duckdb_infra python=3.11 -y
conda activate duckdb_infra

# Install dependencies
conda install -c conda-forge duckdb pandas pyarrow fastapi uvicorn pytest -y
```

### 2. Install from Source
```bash
cd /Users/apple/Downloads/duckDbData
pip install -e .
```

## 🏃‍♂️ Quick Start

### 1. Start the API Server
```bash
# Activate environment
conda activate duckdb_infra

# Start server
python start_api_server.py

# Or with custom settings
python start_api_server.py --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API Base**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 2. Basic Python Usage
```python
from duckdb_infra import DuckDBManager, QueryAPI, TimeFrame
from datetime import date, timedelta

# Initialize
db_manager = DuckDBManager()
db_manager.create_schema()
query_api = QueryAPI(db_manager)

# Load data for a symbol
end_date = date(2024, 12, 31)
start_date = end_date - timedelta(days=7)
records = db_manager.load_symbol_data("RELIANCE", start_date, end_date)

# Resample to different timeframes
daily_data = query_api.resample_data("RELIANCE", TimeFrame.DAILY, start_date, end_date)
hourly_data = query_api.resample_data("RELIANCE", TimeFrame.HOUR_1, start_date, end_date)

# Calculate technical indicators
indicators = query_api.calculate_technical_indicators(
    "RELIANCE", 
    TimeFrame.DAILY,
    indicators=['sma_20', 'rsi_14', 'bollinger_bands']
)

print(f"Daily data: {len(daily_data)} records")
print(f"Hourly data: {len(hourly_data)} records") 
print(f"Indicators: {list(indicators.columns)}")
```

### 3. API Usage Examples
```python
import requests

# Resample data via API
response = requests.post("http://localhost:8000/resample", json={
    "symbol": "RELIANCE",
    "timeframe": "1H",
    "start_date": "2024-12-25",
    "end_date": "2024-12-31"
})
hourly_data = response.json()

# Get multiple timeframes
response = requests.post("http://localhost:8000/multi-timeframe", json={
    "symbol": "RELIANCE", 
    "timeframes": ["15T", "1H", "1D"],
    "start_date": "2024-12-25",
    "end_date": "2024-12-31"
})
multi_tf_data = response.json()

# Calculate technical indicators
response = requests.post("http://localhost:8000/technical-indicators", json={
    "symbol": "RELIANCE",
    "timeframe": "1D", 
    "indicators": ["sma_20", "rsi_14", "bollinger_bands"]
})
indicators = response.json()
```

## 📊 API Endpoints

### Core Data Access
- `POST /market-data` - Get raw market data with filtering
- `POST /resample` - Resample data to higher timeframes
- `POST /multi-timeframe` - Get multiple timeframes simultaneously

### Analytics
- `POST /technical-indicators` - Calculate technical indicators
- `GET /market-summary` - Get market summary statistics
- `POST /correlation` - Calculate correlation matrix
- `GET /volume-profile/{symbol}` - Get volume profile analysis

### Utilities
- `GET /symbols` - Get symbol information
- `GET /available-symbols` - List available symbols
- `GET /timeframes` - Get supported timeframes
- `POST /custom-query` - Execute custom SQL queries

### Management
- `POST /load-symbol/{symbol}` - Load data for specific symbol
- `GET /health` - API health check

## 🔧 Advanced Usage

### Custom SQL Queries
```python
# Execute complex analytical queries
custom_query = """
    SELECT 
        symbol,
        date_partition,
        SUM(close * volume) / SUM(volume) as vwap,
        AVG(close) as avg_price,
        STDDEV(close) as volatility,
        SUM(volume) as total_volume
    FROM market_data 
    WHERE symbol IN (?, ?) AND date_partition >= ?
    GROUP BY symbol, date_partition
    ORDER BY date_partition
"""

result = query_api.execute_custom_analytical_query(
    custom_query, 
    ["RELIANCE", "TCS", "2024-12-01"]
)
```

### Volume Profile Analysis
```python
# Get volume distribution across price levels
volume_profile = query_api.get_volume_profile(
    symbol="RELIANCE",
    start_date=date(2024, 12, 1),
    end_date=date(2024, 12, 31),
    price_bins=50
)
```

### Correlation Analysis
```python
# Calculate correlation between symbols
correlation_matrix = query_api.get_correlation_matrix(
    symbols=["RELIANCE", "TCS", "INFY", "HDFC"],
    timeframe=TimeFrame.DAILY,
    method="returns"
)
```

## 🧪 Testing

### Run Integration Tests
```bash
# Activate environment
conda activate duckdb_infra

# Run tests
python -m pytest tests/test_integration.py -v

# Run specific test
python -m pytest tests/test_integration.py::TestDuckDBIntegration::test_data_resampling -v
```

### Example Scripts
```bash
# Basic usage examples
python examples/basic_usage.py

# API usage examples (requires running server)
python examples/api_usage.py
```

## 📁 Data Structure

The infrastructure expects parquet files organized as:
```
/Users/apple/Downloads/duckDbData/
├── 2024/
│   ├── 01/
│   │   ├── 01/
│   │   │   ├── RELIANCE_minute_2024-01-01.parquet
│   │   │   ├── TCS_minute_2024-01-01.parquet
│   │   │   └── ...
│   │   └── ...
│   └── ...
└── ...
```

Each parquet file contains OHLCV data with columns:
- `open` - Opening price
- `high` - High price  
- `low` - Low price
- `close` - Closing price
- `volume` - Trading volume

## 🔍 Database Schema

### market_data table
```sql
CREATE TABLE market_data (
    symbol VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open DOUBLE NOT NULL,
    high DOUBLE NOT NULL, 
    low DOUBLE NOT NULL,
    close DOUBLE NOT NULL,
    volume BIGINT NOT NULL,
    date_partition DATE NOT NULL,
    PRIMARY KEY (symbol, timestamp)
);
```

### symbols table
```sql
CREATE TABLE symbols (
    symbol VARCHAR PRIMARY KEY,
    name VARCHAR,
    sector VARCHAR,
    industry VARCHAR,
    first_date DATE,
    last_date DATE,
    total_records BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## ⚡ Performance Features

- **Optimized Indexes**: Strategic indexes on symbol, date, and timestamp
- **Parallel Loading**: Multi-threaded data loading
- **Memory Management**: Configurable memory limits and threading
- **Efficient Resampling**: DuckDB's time_bucket function for fast aggregation
- **Columnar Storage**: DuckDB's columnar format for analytical queries

## 🛠️ Configuration

### Environment Variables
- `DUCKDB_PATH` - Path to DuckDB database file (default: financial_data.duckdb)
- `DATA_ROOT` - Root directory for parquet files (default: /Users/apple/Downloads/duckDbData)

### Database Settings
```python
# Configure DuckDB for optimal performance
db_manager = DuckDBManager()
conn = db_manager.connect()
conn.execute("SET memory_limit='8GB'")
conn.execute("SET threads=8")
```

## 📈 Use Cases

### Algorithmic Trading
- Real-time data resampling for different strategy timeframes
- Technical indicator calculation for signal generation
- Historical backtesting with custom queries

### Risk Management  
- Correlation analysis between assets
- Volatility calculations across timeframes
- Volume profile analysis for liquidity assessment

### Research & Analytics
- Market microstructure analysis
- Cross-sectional studies with custom SQL
- Performance attribution analysis

### Portfolio Management
- Multi-timeframe analysis for position sizing
- Sector rotation analysis with correlation matrices
- Risk-adjusted return calculations

## 🤝 Contributing

1. Follow SOLID principles strictly
2. Write integration tests (no mocks allowed)
3. Use existing code and open-source libraries
4. Ensure production-ready implementations
5. Document third-party integrations clearly

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the interactive API docs at `/docs`
2. Run health checks at `/health`
3. Review integration tests for usage examples
4. Check logs for detailed error information

## 🔮 Roadmap

- [ ] Real-time data streaming integration
- [ ] Advanced technical indicators (MACD, Stochastic, etc.)
- [ ] Machine learning feature engineering
- [ ] Multi-database support (PostgreSQL, ClickHouse)
- [ ] WebSocket API for real-time updates
- [ ] Grafana dashboard integration
