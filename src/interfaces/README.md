# Unified Presentation Layer

The **Unified Presentation Layer** provides a consolidated interface system for the Trading System, offering multiple ways to interact with the application through a single, coordinated architecture.

## 🎯 Overview

The presentation layer unifies four distinct interfaces into a cohesive system:

- **🌐 REST API** - FastAPI-based RESTful web service
- **💻 CLI** - Rich command-line interface with Typer
- **🖥️ Dashboard** - Web-based graphical interface
- **🔌 WebSocket** - Real-time data streaming server

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 PRESENTATION LAYER                       │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   REST API  │  │     CLI     │  │  DASHBOARD  │     │
│  │  (FastAPI)  │  │   (Typer)   │  │  (FastAPI)  │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                         │
│  ┌─────────────┐                                        │
│  │ WEBSOCKET   │                                        │
│  │  (FastAPI)  │                                        │
│  └─────────────┘                                        │
├─────────────────────────────────────────────────────────┤
│           PRESENTATION MANAGER                          │
│  • Service Coordination                                 │
│  • Health Monitoring                                    │
│  • Configuration Management                             │
│  • Lifecycle Management                                 │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Running All Services

```bash
# Run the complete unified system
python src/interfaces/unified_main.py

# Or run from project root
python -m src.interfaces.unified_main
```

### Running Individual Services

```bash
# Run only the API
python src/interfaces/unified_main.py --service api

# Run only the dashboard
python src/interfaces/unified_main.py --service dashboard

# Run specific services
python src/interfaces/unified_main.py --services api websocket
```

### Development Mode

```bash
# Enable auto-reload and debug logging
python src/interfaces/unified_main.py --reload --debug

# Custom ports
python src/interfaces/unified_main.py --api-port 8080 --dashboard-port 8081
```

## 📋 Service Endpoints

### REST API
- **Base URL**: `http://localhost:8000`
- **Documentation**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

### Dashboard
- **URL**: `http://localhost:8080`
- **Features**: Market data visualization, scanner controls, system monitoring

### WebSocket
- **URL**: `ws://localhost:8081`
- **Stats**: `http://localhost:8081/stats`
- **Endpoints**:
  - `/ws/market-data` - Real-time market data
  - `/ws/scanner` - Scanner signals
  - `/ws/trading` - Trading events

### CLI
```bash
# Show system status
python -m src.interfaces.cli.main status

# Show version
python -m src.interfaces.cli.main version

# Access CLI help
python -m src.interfaces.cli.main --help
```

## ⚙️ Configuration

### Configuration File

Create a configuration file at one of these locations:
- `config/presentation.yaml`
- `config/presentation.yml`
- `config/presentation.json`
- `presentation.yaml`
- `.presentation.yaml`

### Example Configuration (YAML)

```yaml
version: "2.0.0"
environment: "development"
log_level: "INFO"

api:
  host: "0.0.0.0"
  port: 8000
  enable_docs: true
  reload: false
  cors_origins: ["*"]

cli:
  enable_completion: true
  rich_output: true

dashboard:
  host: "0.0.0.0"
  port: 8080
  theme: "dark"
  refresh_interval: 30

websocket:
  host: "0.0.0.0"
  port: 8081
  max_connections: 1000

health:
  enabled: true
  check_interval: 60

metrics:
  enabled: true
  collection_interval: 60

security:
  enable_ssl: false
  enable_auth: false
  enable_rate_limiting: true

enabled_services:
  - api
  - cli
  - dashboard
  - websocket
```

### Environment Variables

```bash
# API Configuration
export API_HOST="0.0.0.0"
export API_PORT="8000"
export API_ENABLE_DOCS="true"

# Dashboard Configuration
export DASHBOARD_HOST="0.0.0.0"
export DASHBOARD_PORT="8080"

# WebSocket Configuration
export WEBSOCKET_HOST="0.0.0.0"
export WEBSOCKET_PORT="8081"

# Global Settings
export ENVIRONMENT="production"
export LOG_LEVEL="INFO"
```

## 🔧 API Reference

### Core Endpoints

#### Health Check
```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "services": ["market_data", "analytics", "scanner", "trading"]
}
```

#### System Status
```http
GET /api/v1/system/status
```

#### Market Data
```http
GET /api/v1/market-data/{symbol}
GET /api/v1/market-data/{symbol}/history?start=2024-01-01&end=2024-12-31
```

#### Analytics
```http
GET /api/v1/analytics/indicators/{symbol}
POST /api/v1/analytics/scan
```

#### Trading
```http
GET /api/v1/trading/orders
POST /api/v1/trading/orders
GET /api/v1/trading/positions
```

## 🔌 WebSocket API

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8081/ws/market-data');

// Subscribe to market data
ws.send(JSON.stringify({
  type: 'subscribe',
  symbol: 'AAPL',
  channels: ['price', 'volume']
}));

// Handle incoming data
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

### Message Types

#### Market Data
```json
{
  "type": "market_data",
  "symbol": "AAPL",
  "price": 150.25,
  "volume": 1000000,
  "timestamp": "2024-09-05T10:30:00Z"
}
```

#### Scanner Signals
```json
{
  "type": "scanner_signal",
  "symbol": "AAPL",
  "signal_type": "BUY",
  "strength": 0.85,
  "criteria": ["volume_breakout", "price_momentum"]
}
```

#### Trading Events
```json
{
  "type": "order_filled",
  "order_id": "ord_001",
  "symbol": "AAPL",
  "quantity": 100,
  "price": 150.25,
  "timestamp": "2024-09-05T10:30:00Z"
}
```

## 💻 CLI Commands

### System Commands
```bash
# Show system status
trading-system status

# Show version information
trading-system version

# Get help
trading-system --help
```

### Market Data Commands
```bash
# Get current market data
trading-system market-data get AAPL

# Show market data history
trading-system market-data history AAPL --days 30

# Stream market data
trading-system market-data stream AAPL
```

### Scanner Commands
```bash
# Run scanner
trading-system scanner run breakout

# Show scanner results
trading-system scanner results --limit 20

# Configure scanner
trading-system scanner config breakout --threshold 0.8
```

### Analytics Commands
```bash
# Calculate indicators
trading-system analytics indicators AAPL --indicators rsi,macd

# Show technical analysis
trading-system analytics ta AAPL

# Generate signals
trading-system analytics signals AAPL
```

## 🖥️ Dashboard Features

### Main Dashboard
- **Market Overview**: Real-time market data and indices
- **Portfolio Summary**: Current positions and P&L
- **Active Orders**: Open orders and status
- **System Health**: Service status and metrics

### Market Data View
- **Price Charts**: Interactive candlestick charts
- **Volume Analysis**: Volume histograms and indicators
- **Technical Indicators**: RSI, MACD, Bollinger Bands
- **News Feed**: Market news and alerts

### Scanner Interface
- **Scanner Configuration**: Customize scan parameters
- **Real-time Results**: Live scanning results
- **Signal History**: Historical signals and performance
- **Alert Management**: Configure signal alerts

### System Monitoring
- **Service Health**: All system services status
- **Performance Metrics**: CPU, memory, network usage
- **Error Logs**: Recent errors and warnings
- **Configuration**: System settings management

## 🔒 Security Features

### Authentication
- JWT-based authentication for API and dashboard
- Session management with configurable timeouts
- Role-based access control (RBAC)

### Authorization
- API key authentication for programmatic access
- OAuth2 support for third-party integrations
- Fine-grained permissions system

### Security Headers
- HTTPS enforcement in production
- CORS configuration for cross-origin requests
- Security headers (HSTS, CSP, X-Frame-Options)

## 📊 Monitoring & Health

### Health Checks
- **Service Health**: Individual service health status
- **Dependency Health**: Database, cache, external services
- **System Resources**: CPU, memory, disk usage
- **Custom Health Checks**: Application-specific health metrics

### Metrics Collection
- **Performance Metrics**: Response times, throughput
- **Business Metrics**: Orders processed, signals generated
- **System Metrics**: Resource usage, error rates
- **Custom Metrics**: Application-specific KPIs

### Alerting
- **Health Alerts**: Service down/unhealthy notifications
- **Performance Alerts**: High latency, error rate thresholds
- **Business Alerts**: Trading signals, market events
- **Integration**: Webhook, email, Slack notifications

## 🚀 Deployment

### Development
```bash
# Run with auto-reload
python src/interfaces/unified_main.py --reload --debug

# Use development configuration
export ENVIRONMENT=development
python src/interfaces/unified_main.py
```

### Production
```bash
# Use production configuration
export ENVIRONMENT=production
python src/interfaces/unified_main.py --services api dashboard websocket

# Run behind reverse proxy (nginx)
# Configure nginx to proxy to:
# - API: localhost:8000
# - Dashboard: localhost:8080
# - WebSocket: localhost:8081
```

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000 8080 8081

CMD ["python", "-m", "src.interfaces.unified_main"]
```

## 🔧 Development

### Project Structure
```
src/interfaces/
├── api/                 # REST API implementation
├── cli/                 # CLI implementation
├── dashboard/           # Web dashboard
├── websocket/           # WebSocket server
├── config/             # Configuration management
├── presentation_manager.py  # Unified manager
├── unified_main.py     # Main entry point
└── README.md          # This file
```

### Adding New Endpoints

#### API Endpoint
```python
# src/interfaces/api/routes/custom_routes.py
from fastapi import APIRouter
from ..dependencies import get_cqrs_registry

router = APIRouter()

@router.get("/custom/endpoint")
async def custom_endpoint():
    # Your endpoint logic here
    return {"message": "Custom endpoint"}
```

#### CLI Command
```python
# src/interfaces/cli/commands/custom_commands.py
import typer

custom_app = typer.Typer()

@custom_app.command("custom")
def custom_command(name: str):
    """Custom CLI command."""
    typer.echo(f"Hello {name}!")
```

#### WebSocket Handler
```python
# src/interfaces/websocket/handlers/custom_handlers.py
async def handle_custom_message(websocket, data):
    """Handle custom WebSocket message."""
    await websocket.send_json({
        "type": "custom_response",
        "data": data
    })
```

## 📈 Performance

### Optimization Features
- **Async/Await**: Fully asynchronous request handling
- **Connection Pooling**: Efficient database and external service connections
- **Caching**: Multi-level caching for improved performance
- **Compression**: Response compression for reduced bandwidth
- **Rate Limiting**: Configurable rate limits to prevent abuse

### Scalability
- **Horizontal Scaling**: Stateless design supports multiple instances
- **Load Balancing**: Compatible with load balancers and reverse proxies
- **Database Sharding**: Support for database partitioning
- **CDN Integration**: Static asset delivery optimization

## 🐛 Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Check what's using ports
lsof -i :8000
lsof -i :8080
lsof -i :8081

# Change ports in configuration
python src/interfaces/unified_main.py --api-port 8001 --dashboard-port 8081
```

#### Service Startup Failures
```bash
# Check logs
tail -f logs/trading_system.log

# Run with debug logging
python src/interfaces/unified_main.py --debug

# Test individual services
python src/interfaces/unified_main.py --service api
```

#### WebSocket Connection Issues
```bash
# Check WebSocket server status
curl http://localhost:8081/stats

# Test WebSocket connection
python -c "
import websockets
async def test():
    async with websockets.connect('ws://localhost:8081/ws/market-data') as ws:
        print('WebSocket connected successfully')
"
```

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python src/interfaces/unified_main.py --debug

# Check health status
curl http://localhost:8000/health

# View metrics
curl http://localhost:8000/metrics
```

## 🤝 Contributing

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd trading-system

# Install dependencies
pip install -r requirements.txt

# Run in development mode
python src/interfaces/unified_main.py --reload --debug
```

### Testing
```bash
# Run all tests
pytest

# Run interface tests
pytest tests/interfaces/

# Run with coverage
pytest --cov=src/interfaces --cov-report=html
```

### Code Style
- Follow PEP 8 style guidelines
- Use type hints for all function parameters
- Write comprehensive docstrings
- Include unit tests for new functionality

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Documentation
- **API Docs**: `http://localhost:8000/docs`
- **Configuration Guide**: See `config/presentation.yaml`
- **CLI Help**: `python -m src.interfaces.cli.main --help`

### Community
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Wiki**: Project Wiki

### Professional Support
- **Enterprise Support**: Available for production deployments
- **Training**: Custom training sessions available
- **Consulting**: Architecture and implementation consulting

---

**🎯 The Unified Presentation Layer provides a complete, production-ready interface system for the Trading System, supporting multiple interaction patterns while maintaining consistency and performance.**