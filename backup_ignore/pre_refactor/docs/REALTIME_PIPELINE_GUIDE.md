# Real-Time Data Pipeline System

## Overview

A comprehensive real-time data pipeline system that continuously updates market data and technical indicators on 1-minute intervals. Built on top of the existing DuckDB infrastructure and technical indicators system.

## 🚀 Quick Start

### Start the Complete System
```bash
# Start everything (scheduler + pipeline + monitor)
python scripts/start_realtime_system.py

# Start with custom API port
python scripts/start_realtime_system.py --api-port 8002

# Start without monitoring
python scripts/start_realtime_system.py --no-monitor
```

### Check System Status
```bash
# Show current status
python scripts/start_realtime_system.py --status

# Check via API
curl http://localhost:8001/status
```

### Stop the System
```bash
# Graceful shutdown
python scripts/start_realtime_system.py --stop

# Or use Ctrl+C if running in foreground
```

## 📋 System Components

### 1. **Real-Time Data Pipeline** (`realtime_data_pipeline.py`)
- Fetches 1-minute market data from Dhan API
- Updates DuckDB database continuously
- Processes 487+ symbols with priority handling
- Market hours awareness (9:15 AM - 3:30 PM IST)

### 2. **Pipeline Scheduler** (`pipeline_scheduler.py`)
- Manages pipeline lifecycle
- Auto-start/stop based on market hours
- Health monitoring and recovery
- REST API for control and monitoring
- Automatic restart on failures

### 3. **Pipeline Monitor** (`pipeline_monitor.py`)
- Real-time health monitoring
- Performance metrics collection
- Alert system (Email/Slack)
- Automated reporting
- Health scoring (0-100)

### 4. **System Manager** (`start_realtime_system.py`)
- Unified system orchestration
- Process management
- Status monitoring
- Graceful shutdown handling

## 🔧 Configuration

### Main Configuration File: `config/realtime_config.json`

```json
{
  "pipeline": {
    "market_hours": {
      "open_time": "09:15",
      "close_time": "15:30"
    },
    "update_intervals": {
      "data_update_seconds": 60,
      "indicators_update_seconds": 60
    },
    "priority_symbols": [
      "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"
    ]
  }
}
```

### Environment Variables
```bash
# Dhan API credentials (required)
export DHAN_CLIENT_ID="your_client_id"
export DHAN_API_TOKEN="your_api_token"

# Email alerts (optional)
export SMTP_USERNAME="your_email@gmail.com"
export SMTP_PASSWORD="your_app_password"
export ALERT_EMAIL_RECIPIENTS="admin@company.com,trader@company.com"

# Slack alerts (optional)
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
```

## 📊 API Endpoints

The scheduler provides a REST API on port 8001:

### System Control
```bash
# Get system status
GET /status

# Start pipeline
POST /start

# Stop pipeline  
POST /stop

# Restart pipeline
POST /restart

# Health check
GET /health
```

### Monitoring
```bash
# Get metrics
GET /metrics

# Get configuration
GET /config

# API root
GET /
```

### Example API Usage
```bash
# Check if system is healthy
curl http://localhost:8001/health

# Get detailed status
curl http://localhost:8001/status | jq

# Start pipeline manually
curl -X POST http://localhost:8001/start

# Stop pipeline
curl -X POST http://localhost:8001/stop
```

## 🔍 Monitoring & Alerts

### Health Scoring (0-100)
- **Pipeline Running**: 30 points
- **Market Hours Compliance**: 20 points  
- **Error Rate**: 25 points
- **Data Freshness**: 15 points
- **Performance**: 10 points

### Alert Conditions
- Pipeline down during market hours
- High error rate (>5%)
- Stale data (>5 minutes old)
- Low health score (<50)
- Low update frequency

### Alert Channels
- **Email**: SMTP-based email alerts
- **Slack**: Webhook-based Slack notifications
- **Logs**: Detailed logging to files

## 📈 Performance Characteristics

### Data Processing
- **Update Frequency**: Every 60 seconds
- **Symbols Processed**: 487+ symbols
- **Priority Symbols**: 20 high-priority stocks updated first
- **Concurrent Workers**: 8 for data, 4 for indicators
- **Batch Size**: 50 symbols per batch

### Technical Indicators
- **Real-time Calculation**: 1-minute timeframe focus
- **99+ Indicators**: Complete technical analysis suite
- **Support/Resistance**: Dynamic level detection
- **Supply/Demand Zones**: Volume-weighted analysis

### System Resources
- **Memory Usage**: ~500MB typical
- **CPU Usage**: 10-20% during market hours
- **Storage**: ~1GB per month (compressed)
- **Network**: ~1MB/minute API calls

## 🛠️ Operations Guide

### Daily Operations

#### Morning Startup (Before 9:15 AM)
```bash
# Check system status
python scripts/start_realtime_system.py --status

# Start system if not running
python scripts/start_realtime_system.py

# Verify all components
curl http://localhost:8001/health
```

#### During Market Hours (9:15 AM - 3:30 PM)
```bash
# Monitor health score
curl http://localhost:8001/status | jq '.scheduler.health_status'

# Check recent updates
curl http://localhost:8001/metrics | jq '.pipeline_stats'

# View logs
tail -f logs/realtime_pipeline.log
```

#### Evening Shutdown (After 3:30 PM)
```bash
# System auto-stops, but can manually stop
python scripts/start_realtime_system.py --stop

# Generate daily report
python scripts/pipeline_monitor.py --report daily
```

### Troubleshooting

#### Pipeline Not Starting
```bash
# Check Dhan API credentials
echo $DHAN_CLIENT_ID
echo $DHAN_API_TOKEN

# Check database connectivity
python -c "from core.duckdb_infra.database import DuckDBManager; DuckDBManager().get_available_symbols()[:5]"

# Check logs
tail -50 logs/pipeline_scheduler.log
```

#### High Error Rate
```bash
# Check specific errors
curl http://localhost:8001/status | jq '.pipeline.stats.errors'

# Restart pipeline
curl -X POST http://localhost:8001/restart

# Check API rate limits
grep "rate limit" logs/realtime_pipeline.log
```

#### Stale Data
```bash
# Check last update time
curl http://localhost:8001/status | jq '.pipeline.stats.last_data_update'

# Force restart
curl -X POST http://localhost:8001/restart

# Check market status
curl http://localhost:8001/status | jq '.market'
```

### Maintenance

#### Weekly Maintenance
```bash
# Generate weekly report
python scripts/pipeline_monitor.py --report weekly

# Clean old logs (keep last 30 days)
find logs/ -name "*.log" -mtime +30 -delete

# Check disk space
df -h data/
```

#### Monthly Maintenance
```bash
# Update technical indicators for all symbols
python scripts/update_technical_indicators.py --force

# Backup configuration
cp -r config/ backups/config_$(date +%Y%m%d)/

# Review and optimize symbol lists
python scripts/analyze_symbol_performance.py
```

## 🔄 Integration with Existing Systems

### Technical Indicators Integration
The real-time pipeline automatically triggers technical indicators updates:

```python
# Indicators are updated in real-time for 1-minute timeframe
# Access via existing API:
from core.technical_indicators.storage import TechnicalIndicatorsStorage

storage = TechnicalIndicatorsStorage('data/technical_indicators')
latest_indicators = storage.load_indicators('RELIANCE', '1T', today, today)
```

### Database Integration
Real-time data flows into the existing DuckDB infrastructure:

```python
# Access real-time data via existing database manager
from core.duckdb_infra.database import DuckDBManager

db = DuckDBManager()
latest_data = db.get_market_data('RELIANCE', '1T', today, today)
```

### API Server Integration
The existing API server automatically serves real-time data:

```bash
# Get real-time resampled data
curl "http://localhost:8000/data/RELIANCE?timeframe=1T&start_date=2025-09-04"
```

## 📊 Monitoring Dashboard

### Key Metrics to Watch
1. **Health Score**: Should be >80 during market hours
2. **Update Frequency**: ~1 update per minute per priority symbol
3. **Error Rate**: Should be <2%
4. **Data Freshness**: <2 minutes old during market hours
5. **Symbol Coverage**: All 487+ symbols processed

### Performance Indicators
```bash
# Real-time metrics
curl http://localhost:8001/metrics | jq '{
  health_score: .pipeline_stats.health_score,
  symbols_processed: .pipeline_stats.symbols_processed,
  error_rate: .pipeline_stats.error_rate,
  last_update: .pipeline_stats.last_data_update
}'
```

## 🚨 Alerting Setup

### Email Alerts
```bash
# Set environment variables
export SMTP_USERNAME="alerts@yourcompany.com"
export SMTP_PASSWORD="your_app_password"
export ALERT_EMAIL_RECIPIENTS="admin@yourcompany.com,trader@yourcompany.com"

# Start monitor with email alerts
python scripts/pipeline_monitor.py --email-recipients "admin@yourcompany.com"
```

### Slack Alerts
```bash
# Set webhook URL
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Start monitor with Slack alerts
python scripts/pipeline_monitor.py --slack-webhook "$SLACK_WEBHOOK_URL"
```

## 🔒 Security Considerations

### API Security
- Run on localhost by default
- Use reverse proxy (nginx) for external access
- Implement authentication for production
- Rate limiting recommended

### Credentials Management
- Store API keys in environment variables
- Use `.env` files for development
- Consider using secrets management systems
- Rotate API keys regularly

### Network Security
- Firewall rules for API ports
- VPN access for remote monitoring
- SSL/TLS for external connections
- Monitor API access logs

## 📈 Scaling Considerations

### Horizontal Scaling
- Run multiple pipeline instances for different symbol groups
- Load balance API requests
- Distribute monitoring across regions
- Use message queues for coordination

### Vertical Scaling
- Increase worker threads for higher throughput
- Add more memory for larger symbol sets
- Use faster storage for better I/O
- Optimize database queries

### Performance Tuning
```json
{
  "performance": {
    "max_workers_data": 16,        // Increase for more symbols
    "max_workers_indicators": 8,   // Increase for faster indicators
    "batch_size": 100,             // Larger batches for efficiency
    "max_symbols_per_batch": 200   // Process more symbols per cycle
  }
}
```

## 🎯 Success Metrics

After successful deployment, you should see:

✅ **System Health**: >90% uptime during market hours  
✅ **Data Freshness**: <1 minute lag for priority symbols  
✅ **Error Rate**: <1% for API calls and processing  
✅ **Coverage**: All 487+ symbols updated every minute  
✅ **Performance**: <30 seconds for full update cycle  
✅ **Indicators**: Real-time technical analysis available  

The system is now ready for production trading operations! 🚀

---

**Need Help?** Check the logs in the `logs/` directory or use the API endpoints for detailed status information.
