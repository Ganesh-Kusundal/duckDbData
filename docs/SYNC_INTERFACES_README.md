# Market Data Sync Interfaces

## Overview

The enhanced Market Data Synchronization Service provides multiple interfaces to handle the 90-day API limitation with intelligent chunking and comprehensive monitoring.

## 🎯 Key Features

- **90-Day API Limitation Handling**: Automatic chunking for periods >90 days
- **Multiple Interfaces**: CLI, REST API, and Web Dashboard
- **Intelligent Sync Modes**: Incremental, Historical, and Chunked sync
- **Real-time Monitoring**: Progress tracking and comprehensive reporting
- **Production Ready**: Async processing, error recovery, and scalability

## 📊 Interfaces

### 1. Command Line Interface (CLI)

#### Basic Usage

```bash
# Single symbol sync
python market_sync.py TCS

# Multiple symbols
python market_sync.py TCS RELIANCE INFY

# All symbols in database
python market_sync.py --all-symbols

# Generate report
python market_sync.py --report
```

#### Advanced Options

```bash
# Historical sync with custom days
python market_sync.py TCS --historical-days 180

# Chunked sync for periods >90 days
python market_sync.py TCS --historical-days 365 --chunked-sync

# Force update all data
python market_sync.py TCS --force

# JSON output for automation
python market_sync.py --report --json-output

# Custom batch size
python market_sync.py --all-symbols --batch-size 20

# Quiet mode (suppress progress)
python market_sync.py --all-symbols --quiet
```

#### CLI Examples

```bash
# Daily incremental sync
python market_sync.py --all-symbols --historical-days 1

# Weekly comprehensive sync
python market_sync.py --all-symbols --chunked-sync --historical-days 180

# Force refresh specific symbols
python market_sync.py TCS RELIANCE --force --historical-days 90

# Monitor sync status
python market_sync.py --report
```

### 2. REST API Interface

#### Starting the API Server

```bash
# Development mode
python sync_api.py

# Production mode
uvicorn sync_api:app --host 0.0.0.0 --port 8000

# With auto-reload
uvicorn sync_api:app --reload
```

#### API Endpoints

##### Health Check
```bash
GET /health
```
Returns service health and database status.

##### Sync Single Symbol
```bash
POST /sync/symbol
Content-Type: application/json

{
  "symbol": "TCS",
  "historical_days": 90,
  "force_update": false
}
```

##### Batch Sync
```bash
POST /sync/batch
Content-Type: application/json

{
  "symbols": ["TCS", "RELIANCE", "INFY"],
  "historical_days": 180,
  "use_chunked_sync": true,
  "batch_size": 10
}
```

##### Historical Sync with Chunking
```bash
POST /sync/historical
Content-Type: application/json

{
  "symbol": "TCS",
  "days_back": 365,
  "force_update": false
}
```

##### Sync All Symbols
```bash
POST /sync/all?historical_days=90&use_chunked_sync=false&force_update=false
```

##### Get Available Symbols
```bash
GET /symbols
GET /symbols?limit=100&search=TCS
```

##### Generate Report
```bash
GET /sync/report
GET /sync/report?symbols=TCS,RELIANCE
```

#### API Usage Examples

```bash
# Check service health
curl http://localhost:8000/health

# Sync single symbol
curl -X POST "http://localhost:8000/sync/symbol" \
     -H "Content-Type: application/json" \
     -d '{"symbol": "TCS", "historical_days": 90}'

# Batch sync with chunking
curl -X POST "http://localhost:8000/sync/batch" \
     -H "Content-Type: application/json" \
     -d '{
       "symbols": ["TCS", "RELIANCE"],
       "historical_days": 365,
       "use_chunked_sync": true
     }'

# Sync all symbols
curl -X POST "http://localhost:8000/sync/all?historical_days=90"

# Get symbols list
curl "http://localhost:8000/symbols?limit=50"
```

### 3. Web Dashboard Interface

#### Starting the Dashboard

```bash
# Basic start
streamlit run sync_dashboard.py

# Custom port
streamlit run sync_dashboard.py --server.port 8501

# Custom configuration
streamlit run sync_dashboard.py --server.headless true
```

#### Dashboard Features

1. **📊 Overview Tab**
   - Real-time database metrics
   - Data quality indicators
   - Sync status summary

2. **📈 Analytics Tab**
   - Interactive charts and graphs
   - Symbol performance analysis
   - Data freshness distribution

3. **📋 Results Tab**
   - Recent sync operations
   - Detailed result history
   - Error tracking and recovery

4. **⚙️ Settings Tab**
   - Database configuration
   - Performance tuning
   - System monitoring

#### Dashboard Usage

- **Symbol Selection**: Choose individual symbols or batch operations
- **Sync Configuration**: Set historical days, chunking options, and force updates
- **Real-time Monitoring**: Track sync progress and view results
- **Interactive Charts**: Visualize data quality and sync performance

## 🔧 Configuration

### Environment Variables

```bash
# Database Configuration
export DATABASE_PATH="data/financial_data.duckdb"

# API Configuration
export API_HOST="0.0.0.0"
export API_PORT="8000"

# Sync Configuration
export DEFAULT_HISTORICAL_DAYS="90"
export DEFAULT_BATCH_SIZE="10"
export MAX_RETRIES="3"
```

### Configuration Files

Create a `config.yaml` file for advanced configuration:

```yaml
database:
  path: "data/financial_data.duckdb"
  connection_pool_size: 10

sync:
  default_historical_days: 90
  batch_size: 10
  max_retries: 3
  delay_between_requests: 1.0
  use_chunked_sync: false

api:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  reload: true

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "logs/sync.log"
```

## 📈 Monitoring and Reporting

### Sync Reports

```bash
# CLI Report
python market_sync.py --report

# API Report
curl http://localhost:8000/sync/report

# JSON Report for Automation
python market_sync.py --report --json-output > report.json
```

### Performance Monitoring

- **Real-time Metrics**: Processing speed, success rates, error counts
- **Historical Analytics**: Trend analysis, performance optimization
- **Health Checks**: Service availability, database connectivity
- **Error Tracking**: Failed operations, retry mechanisms

### Logging

All interfaces provide comprehensive logging:

```bash
# View recent logs
tail -f logs/sync.log

# Filter by symbol
grep "TCS" logs/sync.log

# Error analysis
grep "ERROR" logs/sync.log | tail -20
```

## 🚀 Advanced Usage

### Automated Sync Operations

#### Cron Jobs for Daily Sync

```bash
# Daily incremental sync (weekdays 6 AM)
0 6 * * 1-5 python market_sync.py --all-symbols --historical-days 1

# Weekly comprehensive sync (Sundays 2 AM)
0 2 * * 0 python market_sync.py --all-symbols --chunked-sync --historical-days 180
```

#### Scripted Automation

```python
import requests
import time

# Automated daily sync
def daily_sync():
    response = requests.post(
        "http://localhost:8000/sync/all",
        params={
            "historical_days": 1,
            "use_chunked_sync": False,
            "force_update": False
        }
    )
    return response.json()

# Check sync status
def check_status():
    response = requests.get("http://localhost:8000/health")
    return response.json()
```

### Large-Scale Operations

#### Handling 500+ Symbols

```bash
# Large batch with optimized settings
python market_sync.py --all-symbols --batch-size 25 --chunked-sync --historical-days 365

# Monitor progress
watch -n 30 'python market_sync.py --report | grep "successful"'
```

#### Memory Optimization

```bash
# Reduce batch size for memory-constrained environments
python market_sync.py --all-symbols --batch-size 5 --historical-days 180

# Use chunked sync to reduce memory usage
python market_sync.py --all-symbols --chunked-sync --historical-days 720
```

## 🛠️ Troubleshooting

### Common Issues

#### API Rate Limiting
```bash
# Increase delays between requests
python market_sync.py --all-symbols --delay-between-requests 2.0

# Reduce batch size
python market_sync.py --all-symbols --batch-size 5
```

#### Database Locks
```bash
# Use smaller batches
python market_sync.py --all-symbols --batch-size 10

# Check database status
python market_sync.py --report
```

#### Network Issues
```bash
# Increase retry attempts
python market_sync.py TCS --max-retries 5

# Check API connectivity
curl http://localhost:8000/health
```

### Error Recovery

```bash
# Identify failed symbols
python market_sync.py --report | grep "failed"

# Retry specific symbols
python market_sync.py FAILED_SYMBOL --force

# Check API health
curl http://localhost:8000/health
```

## 📚 API Documentation

When the API server is running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 🎯 Best Practices

### Performance Optimization

1. **Use Appropriate Batch Sizes**: 10-20 symbols for most operations
2. **Enable Chunked Sync**: For periods >90 days
3. **Monitor Memory Usage**: Adjust batch sizes for available RAM
4. **Schedule Off-Peak**: Run large operations during low-traffic periods

### Data Quality

1. **Regular Health Checks**: Monitor API and database status
2. **Incremental Updates**: Use daily incremental syncs
3. **Error Monitoring**: Set up alerts for failed operations
4. **Data Validation**: Regularly audit data quality and completeness

### Security

1. **API Authentication**: Implement proper authentication for production
2. **Database Security**: Use appropriate file permissions
3. **Network Security**: Secure API endpoints in production
4. **Audit Logging**: Maintain comprehensive operation logs

## 🚀 Quick Start

### 1. Basic Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "import duckdb; conn = duckdb.connect('data/financial_data.duckdb'); conn.close()"

# Test basic sync
python market_sync.py TCS
```

### 2. Full System Setup

```bash
# Start API server
python sync_api.py &

# Start dashboard
streamlit run sync_dashboard.py &

# Run comprehensive sync
python market_sync.py --all-symbols --chunked-sync --historical-days 180
```

### 3. Production Deployment

```bash
# API server with production settings
uvicorn sync_api:app --host 0.0.0.0 --port 8000 --workers 4

# Set up monitoring
# Configure log rotation, health checks, and alerting
```

---

## 📞 Support and Documentation

- **API Documentation**: http://localhost:8000/docs
- **Examples**: See `sync_examples.py`
- **Configuration**: Refer to `config.yaml` template
- **Troubleshooting**: Check logs in `logs/` directory

---

*Market Data Sync Service v1.0.0 - Enhanced with 90-day API limitation handling*


