# 🗄️ DuckDB Database Infrastructure

Consolidated database layer for the financial data platform using DuckDB.

## 📁 Structure

```
database/
├── core/                 # Core database abstractions
├── adapters/             # Database adapters (DuckDB, future: PostgreSQL, etc.)
├── repositories/         # Repository implementations
├── framework/            # Advanced query builders and analytics
└── README.md            # This file
```

## 🔧 Components

### Core Database Layer
- **Connection management** for DuckDB
- **Schema management** and migrations
- **Query optimization** and performance monitoring

### Repository Pattern
- **MarketDataRepository** - Stock data operations
- **Abstract interfaces** for database independence
- **DuckDB implementations** with optimized queries

### Advanced Framework
- **Query Builder** - Fluent SQL construction
- **Analytics Engine** - Technical indicators and statistics
- **Real-time Manager** - Streaming data processing
- **Scanner Framework** - Pattern recognition and signals

## 🚀 Usage

```python
from src.infrastructure.adapters.duckdb_adapter import DuckDBAdapter
from src.infrastructure.adapters.market_data_repository import DuckDBMarketDataRepository

# Initialize database connection
adapter = DuckDBAdapter()
repo = DuckDBMarketDataRepository(adapter)

# Use repository for data operations
data = repo.find_by_symbol_and_date_range("RELIANCE", "2024-01-01", "2024-12-31")
```

## 🎯 Benefits of Consolidation

1. **Technology Isolation** - All DuckDB code in one place
2. **Easier Migration** - Switch databases by replacing adapters
3. **Better Testing** - Database layer can be tested independently
4. **Code Reusability** - Extract as separate package if needed
5. **Clear Boundaries** - Database concerns separated from business logic

## 🔄 Integration Points

- **Business Logic**: Uses repository interfaces (database-independent)
- **Analytics**: Direct connection to DuckDB for complex queries
- **API Layer**: Repository pattern for clean data access
- **CLI Tools**: Direct database access for administrative tasks

## 📊 Database Features

- **Parquet Integration** - Direct querying of Parquet files
- **Time Series Optimization** - Window functions for financial data
- **Concurrent Access** - Multi-threaded query execution
- **Schema Evolution** - Flexible data structure support
- **Performance Monitoring** - Query execution statistics

## 🛠️ Future Extensions

- **PostgreSQL Adapter** - For production deployments
- **Redis Caching Layer** - For frequently accessed data
- **Time Series Extensions** - Specialized financial time series features
- **Distributed Processing** - Multi-node DuckDB clusters
