# Enhanced Scanner Framework

A comprehensive, production-ready scanner framework that provides unified functionality across CLI, API, and Streamlit interfaces with real-time scanning capabilities.

## 🚀 Overview

The Enhanced Scanner Framework builds upon the existing DDD architecture to provide:

- **Unified Interface**: Consistent scanner functionality across all interfaces
- **Real-time Streaming**: Live scanning with WebSocket support
- **Advanced Configuration**: Centralized configuration management
- **Production Ready**: Comprehensive error handling and validation
- **Extensible Design**: Easy addition of new scanner types and interfaces

## 🏗️ Architecture

### Core Components

```
src/
├── application/scanners/           # Domain scanner logic
├── interfaces/                     # Interface adapters
│   ├── cli/commands/scanners.py    # Enhanced CLI commands
│   ├── api/routes/scanner_api.py   # REST API endpoints
│   └── presentation/scanner/       # Streamlit dashboard
├── infrastructure/
│   ├── config/scanner_config_manager.py  # Unified configuration
│   └── database/                   # Data access layer
└── tests/test_enhanced_scanner_framework.py  # Comprehensive tests
```

### Design Patterns

- **Hexagonal Architecture**: Clean separation between domain and infrastructure
- **Dependency Injection**: Configurable scanner implementations
- **Observer Pattern**: Real-time updates via WebSocket
- **Strategy Pattern**: Pluggable scanner algorithms
- **Factory Pattern**: Scanner instantiation management

## 🎯 Features

### CLI Interface (`scanner` command)

#### Basic Usage
```bash
# Run single scan
scanner run --scanner-type breakout --date 2025-01-15

# Run with streaming output
scanner run --scanner-type breakout --stream --interval 30

# Use API backend
scanner run --scanner-type breakout --api-mode

# Load configuration from file
scanner run --scanner-type breakout --config-file config/scanner_config.json
```

#### Advanced Commands
```bash
# Configure scanner parameters
scanner config --scanner-type breakout --key min_price --value 100

# Monitor scanner performance
scanner monitor --scanner-type breakout --interval 30 --duration 300

# List available scanners
scanner list

# Run backtest
scanner backtest --scanner-type breakout --start-date 2025-01-01 --end-date 2025-01-31

# Optimize parameters
scanner optimize --scanner-type breakout
```

### API Interface

#### REST Endpoints

```http
# Run scan
POST /api/v1/scanner/scan
Content-Type: application/json

{
  "scanner_type": "breakout",
  "scan_date": "2025-01-15",
  "cutoff_time": "09:50",
  "config": {
    "min_price": 100,
    "max_price": 2000
  }
}

# Get scanner status
GET /api/v1/scanner/scanners

# Get market overview
GET /api/v1/scanner/market-overview

# Get available symbols
GET /api/v1/scanner/symbols?limit=100

# Export results
GET /api/v1/scanner/export/{scan_id}/csv
```

#### WebSocket Streaming

```javascript
// Connect to live scanning
const ws = new WebSocket('ws://localhost:8000/api/v1/scanner/ws/live-scan');

// Handle messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'scan_update') {
    console.log('New results:', data.results);
  }
};

// Connect to specific scanner
const scannerWs = new WebSocket('ws://localhost:8000/api/v1/scanner/ws/scanner/breakout');
```

### Streamlit Dashboard

#### Features
- **Real-time Dashboard**: Live scanning with auto-refresh
- **Interactive Configuration**: Adjust parameters in real-time
- **Performance Analytics**: Charts and statistics
- **Export Capabilities**: Download results in multiple formats
- **Multi-tab Interface**: Organized dashboard sections

#### Usage
```bash
# Start dashboard
streamlit run src/presentation/scanner/app.py

# Access at http://localhost:8501
```

## ⚙️ Configuration

### Configuration File Structure

```json
{
  "default": {
    "consolidation_period": 5,
    "breakout_volume_ratio": 1.5,
    "resistance_break_pct": 0.5,
    "min_price": 50,
    "max_price": 2000,
    "max_results_per_day": 3,
    "min_volume": 10000,
    "min_probability_score": 10.0,
    "timeout": 300,
    "retry_attempts": 3,
    "enable_caching": true,
    "cache_ttl": 300
  },
  "breakout": {
    "consolidation_period": 5,
    "breakout_volume_ratio": 1.5
  },
  "streaming": {
    "enabled": true,
    "interval_seconds": 30,
    "max_concurrent_scans": 3,
    "websocket_enabled": true,
    "auto_refresh_ui": true,
    "real_time_alerts": true
  },
  "api": {
    "host": "localhost",
    "port": 8000,
    "timeout": 300,
    "max_batch_size": 10,
    "enable_cors": true
  },
  "cli": {
    "verbose_logging": false,
    "progress_bars": true,
    "color_output": true,
    "default_format": "table",
    "auto_save_results": true,
    "results_directory": "scanner_results"
  },
  "streamlit": {
    "theme": "light",
    "auto_refresh_interval": 30,
    "max_chart_points": 1000,
    "enable_export": true,
    "default_scanner": "breakout",
    "dashboard_layout": "wide"
  }
}
```

### Configuration Management

```python
from src.infrastructure.config.scanner_config_manager import get_config_manager

# Get configuration manager
config_manager = get_config_manager()

# Get scanner configuration
scanner_config = config_manager.get_scanner_config("breakout")

# Update configuration
config_manager.update_config("default", "timeout", 600)
config_manager.save_config()
```

## 🔧 Setup & Installation

### Prerequisites
- Python 3.8+
- DuckDB database
- Required packages (see requirements files)

### Installation
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r src/presentation/scanner/requirements.txt

# Set up configuration
cp configs/scanner_config.json configs/scanner_config.local.json
# Edit configuration as needed
```

### Environment Setup
```bash
# Activate conda environment
conda activate duckDbData

# Start API server
python -m src.interfaces.api.app

# In another terminal, start Streamlit dashboard
streamlit run src/presentation/scanner/app.py
```

## 📊 Usage Examples

### CLI Examples

```bash
# Simple scan
scanner run --scanner-type breakout

# Streaming scan with custom interval
scanner run --scanner-type breakout --stream --interval 60

# Scan with custom configuration
scanner run --scanner-type breakout --config-file my_config.json

# Monitor scanner performance
scanner monitor --scanner-type breakout --duration 600

# Configure scanner parameters
scanner config --scanner-type breakout --key min_price --value 200
```

### API Examples

```python
import requests

# Run scan via API
response = requests.post("http://localhost:8000/api/v1/scanner/scan", json={
    "scanner_type": "breakout",
    "scan_date": "2025-01-15",
    "cutoff_time": "09:50"
})

results = response.json()
print(f"Found {len(results['results'])} results")
```

### Streamlit Usage

1. Start the dashboard
2. Select scanner type from sidebar
3. Configure parameters using sliders
4. Click "Start Live Scan" for real-time updates
5. View results in the dashboard tabs
6. Export results using the export button

## 🧪 Testing

### Running Tests
```bash
# Run all tests
pytest tests/test_enhanced_scanner_framework.py -v

# Run with coverage
pytest tests/test_enhanced_scanner_framework.py --cov=src --cov-report=html

# Run specific test
pytest tests/test_enhanced_scanner_framework.py::TestScannerConfigManager::test_get_scanner_config -v
```

### Test Coverage
- Configuration management
- API endpoint validation
- CLI command testing
- Integration testing
- Configuration validation

## 🔍 Scanner Types

### Breakout Scanner
- Identifies breakout patterns with volume confirmation
- Configurable consolidation periods and volume ratios
- Advanced probability scoring

### CRP Scanner
- Close-Range-Pattern analysis for intraday opportunities
- Optimized for short-term trading signals
- Real-time pattern recognition

### Technical Scanner
- RSI, MACD, Bollinger Bands analysis
- Multi-indicator combination scoring
- Trend and momentum analysis

### Relative Volume Scanner
- Volume-based anomaly detection
- Comparative volume analysis
- Liquidity and volatility assessment

## 📈 Performance & Monitoring

### Metrics
- Scan execution time
- Success rate by scanner type
- Result count trends
- Error rates and types
- API response times

### Monitoring
```bash
# CLI monitoring
scanner monitor --scanner-type breakout

# API health check
GET /api/v1/scanner/health

# Performance statistics
GET /api/v1/scanner/stats/performance
```

## 🚨 Error Handling

### Common Error Scenarios
- Database connection failures
- Invalid scanner parameters
- API timeout errors
- Configuration validation errors
- WebSocket connection issues

### Error Responses
```json
{
  "error": "Scanner execution failed",
  "detail": "Database connection timeout",
  "scanner_type": "breakout",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## 🔒 Security

### API Security
- Input validation on all endpoints
- Rate limiting configuration
- CORS configuration
- Request/response logging

### Configuration Security
- No hardcoded credentials
- Environment-specific configuration
- Secure configuration file handling

## 📚 API Reference

### Scanner Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/scanner/scan` | POST | Execute scanner |
| `/api/v1/scanner/scanners` | GET | List available scanners |
| `/api/v1/scanner/market-overview` | GET | Get market overview |
| `/api/v1/scanner/symbols` | GET | Get available symbols |
| `/api/v1/scanner/export/{scan_id}/csv` | GET | Export results to CSV |
| `/api/v1/scanner/stats/performance` | GET | Get performance statistics |

### WebSocket Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/v1/scanner/ws/live-scan` | Live scanning updates |
| `/api/v1/scanner/ws/scanner/{type}` | Scanner-specific streaming |

## 🤝 Contributing

### Adding New Scanner Types
1. Implement scanner class in `src/application/scanners/strategies/`
2. Add configuration in `scanner_config.json`
3. Update CLI choices and API validation
4. Add to Streamlit scanner selection
5. Update tests

### Adding New Interfaces
1. Follow hexagonal architecture principles
2. Use dependency injection for scanner instances
3. Implement unified configuration access
4. Add comprehensive error handling
5. Update documentation and tests

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the documentation in this README
- Review the test files for usage examples
- Check the configuration files for setup examples
- Review error logs for debugging information

## 🎯 Roadmap

### Planned Enhancements
- [ ] Advanced backtesting framework
- [ ] Machine learning-based scanners
- [ ] Multi-market support
- [ ] Real-time alerting system
- [ ] Performance optimization
- [ ] Additional export formats
- [ ] Mobile-responsive dashboard

---

**Built with ❤️ using Clean Architecture and Domain-Driven Design principles**


