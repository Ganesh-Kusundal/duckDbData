# 🤖 Advanced Trading System

A **production-ready, enterprise-grade trading system** built with modern Python architecture following Clean Architecture principles, CQRS pattern, and Domain-Driven Design.

[![Architecture](https://img.shields.io/badge/Architecture-Clean%20Architecture-blue)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
[![Pattern](https://img.shields.io/badge/Pattern-CQRS%20%2B%20DDD-red)](https://martinfowler.com/bliki/CQRS.html)
[![Database](https://img.shields.io/badge/Database-DuckDB-green)](https://duckdb.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/)

---

## 📊 **System Overview**

This trading system provides comprehensive market analysis, trading operations, risk management, and multi-broker integration capabilities. Built with a modular, scalable architecture that supports real-time trading workflows.

### **🎯 Key Features**

- **📈 Market Scanning**: Advanced breakout, CRP, and technical indicator analysis
- **💰 Trading Operations**: Complete order lifecycle management with position tracking
- **🛡️ Risk Management**: Comprehensive portfolio risk assessment and limits
- **📊 Analytics**: Real-time technical indicators and performance analytics
- **🔗 Multi-Broker Support**: Integration with Interactive Brokers, Alpaca, and more
- **🎛️ Rich CLI**: Interactive command-line interface with progress indicators
- **🌐 REST API**: FastAPI-based RESTful API with OpenAPI documentation
- **📡 WebSocket**: Real-time data streaming and live updates
- **📊 Dashboard**: Web-based trading dashboard with charts and analytics

---

## 🏗️ **Architecture**

### **Clean Architecture Layers**

```
┌─────────────────────────────────────────┐
│             PRESENTATION LAYER          │
│  ┌─────────────────────────────────────┐ │
│  │        REST API (FastAPI)          │ │
│  │        CLI (Typer + Rich)          │ │
│  │        WebSocket Server            │ │
│  │        Web Dashboard               │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│           APPLICATION LAYER             │
│  ┌─────────────────────────────────────┐ │
│  │        CQRS Commands               │ │
│  │        CQRS Queries                │ │
│  │        Command Handlers            │ │
│  │        Query Handlers              │ │
│  │        Application Services        │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│             DOMAIN LAYER                │
│  ┌─────────────────────────────────────┐ │
│  │        ENTITIES                    │ │
│  │        VALUE OBJECTS               │ │
│  │        DOMAIN SERVICES             │ │
│  │        REPOSITORIES                │ │
│  │        DOMAIN EVENTS               │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│          INFRASTRUCTURE LAYER           │
│  ┌─────────────────────────────────────┐ │
│  │        Database (DuckDB)           │ │
│  │        External APIs               │ │
│  │        Message Bus                 │ │
│  │        Caching                     │ │
│  │        Monitoring                  │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### **CQRS Pattern Implementation**

The system implements **Command Query Responsibility Segregation (CQRS)** for optimal read/write operations:

- **Commands**: Write operations that change application state
- **Queries**: Read operations that retrieve data
- **Events**: Domain events for state changes and integration
- **Handlers**: Process commands and queries
- **Buses**: Route commands/queries to appropriate handlers

---

## 🚀 **Quick Start**

### **Prerequisites**

- Python 3.11+
- pip
- git

### **Installation**

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd trading-system
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-test.txt  # For testing
   ```

3. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize the system**
   ```bash
   python -m src.interfaces.cli.main status
   ```

### **Basic Usage**

#### **CLI Commands**

```bash
# System status
python -m src.interfaces.cli.main status

# Run market scanner
python -m src.interfaces.cli.main scanner run --symbol AAPL --date 2024-09-05

# Backtest strategy
python -m src.interfaces.cli.main trading backtest --strategy breakout --symbol AAPL

# Show portfolio
python -m src.interfaces.cli.main trading portfolio

# List trading rules
python -m src.interfaces.cli.main trading rules
```

#### **API Usage**

```bash
# Start API server
uvicorn src.interfaces.api.main:app --host 0.0.0.0 --port 8000

# API endpoints
GET  /health          # Health check
GET  /market-data     # Market data queries
POST /orders          # Place orders
GET  /portfolio       # Portfolio information
WS   /ws/market-data  # Real-time market data
```

---

## 📁 **Project Structure**

```
trading-system/
├── src/
│   ├── domain/                    # Domain layer (business logic)
│   │   ├── trading/              # Trading domain
│   │   ├── analytics/            # Analytics domain
│   │   ├── scanning/             # Scanning domain
│   │   ├── risk_management/      # Risk management domain
│   │   └── broker_integration/   # Broker integration domain
│   │
│   ├── application/              # Application layer (CQRS)
│   │   ├── commands/            # Command definitions and handlers
│   │   ├── queries/             # Query definitions and handlers
│   │   └── cqrs_registry.py     # CQRS registry
│   │
│   ├── infrastructure/           # Infrastructure layer
│   │   ├── database/            # Database adapters
│   │   ├── external/            # External service integrations
│   │   ├── messaging/           # Event store and messaging
│   │   ├── caching/             # Caching layer
│   │   └── monitoring/          # Metrics and monitoring
│   │
│   └── interfaces/               # Presentation layer
│       ├── api/                 # REST API (FastAPI)
│       ├── cli/                 # Command-line interface
│       ├── websocket/           # WebSocket server
│       └── presentation_manager.py # Unified presentation layer
│
├── tests/                       # Comprehensive test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   ├── e2e/                    # End-to-end tests
│   ├── performance/            # Performance tests
│   └── conftest.py             # Test configuration
│
├── scripts/                     # Utility scripts
│   ├── organize_tests.py       # Test organization script
│   └── setup.py               # Setup and deployment scripts
│
├── docs/                       # Documentation
│   ├── api/                   # API documentation
│   ├── architecture/          # Architecture documentation
│   └── user-guides/           # User guides
│
├── docker/                     # Docker configuration
├── kubernetes/                 # Kubernetes manifests
├── requirements.txt            # Python dependencies
├── pytest.ini                 # Test configuration
├── docker-compose.yml         # Docker Compose setup
└── README.md                  # This file
```

---

## 🔧 **Configuration**

### **Environment Variables**

```bash
# Database
DATABASE_PATH=./data/financial_data.duckdb
DATABASE_CONNECTION_POOL_MIN=1
DATABASE_CONNECTION_POOL_MAX=10

# API
API_HOST=0.0.0.0
API_PORT=8000
API_CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Broker Integration
BROKER_TYPE=interactive_brokers
BROKER_API_KEY=your_api_key
BROKER_API_SECRET=your_api_secret

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s

# Cache
CACHE_TYPE=redis
CACHE_HOST=localhost
CACHE_PORT=6379
CACHE_TTL=3600
```

### **Configuration Files**

- `.env` - Environment-specific configuration
- `config/settings.py` - Application settings
- `config/logging.yaml` - Logging configuration
- `config/brokers.yaml` - Broker configurations

---

## 🧪 **Testing**

### **Test Categories**

```bash
# Run all tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# End-to-end tests only
pytest tests/e2e/

# Performance tests only
pytest tests/performance/

# Run with coverage
pytest --cov=src --cov-report=html
```

### **Test Coverage**

- **Overall**: 80%+
- **Domain Layer**: 90%+
- **Application Layer**: 85%+
- **Infrastructure Layer**: 75%+
- **Presentation Layer**: 70%+

---

## 📊 **Key Components**

### **Domain Layer**

#### **Trading Domain**
- **Order Management**: Complete order lifecycle (create, modify, cancel, fill)
- **Position Tracking**: Real-time position management with P&L calculation
- **Portfolio Management**: Multi-asset portfolio tracking and rebalancing

#### **Analytics Domain**
- **Technical Indicators**: RSI, MACD, Bollinger Bands, SMA, EMA
- **Signal Generation**: Automated signal detection and scoring
- **Performance Analytics**: Historical performance analysis and reporting

#### **Scanning Domain**
- **Rule Engine**: Flexible rule-based market scanning
- **Pattern Recognition**: Breakout, CRP, and custom pattern detection
- **Real-time Alerts**: Configurable alert system for market events

#### **Risk Management Domain**
- **Risk Assessment**: Portfolio risk calculation and stress testing
- **Position Limits**: Configurable position size and exposure limits
- **Risk Monitoring**: Real-time risk monitoring and alerts

#### **Broker Integration Domain**
- **Multi-Broker Support**: Interactive Brokers, Alpaca, and custom brokers
- **Order Execution**: Automated order routing and execution
- **Account Management**: Multi-account management and synchronization

### **Application Layer (CQRS)**

#### **Commands**
- `SubmitOrderCommand` - Submit new trading orders
- `ExecuteMarketScanCommand` - Run market scanning operations
- `AssessPortfolioRiskCommand` - Perform risk assessments
- `EstablishBrokerConnectionCommand` - Connect to broker APIs

#### **Queries**
- `GetOrderByIdQuery` - Retrieve specific orders
- `GetScanResultsQuery` - Get scanning results
- `GetPortfolioSummaryQuery` - Portfolio summaries
- `GetRiskAssessmentByIdQuery` - Risk assessment details

### **Infrastructure Layer**

#### **Database Layer**
- **DuckDB Integration**: High-performance analytical database
- **Connection Pooling**: Efficient connection management
- **Schema Management**: Automated schema migration

#### **External Integrations**
- **Broker APIs**: REST and WebSocket connections to broker platforms
- **Market Data Feeds**: Real-time and historical market data
- **Third-party Services**: Integration with external data providers

#### **Monitoring & Observability**
- **Metrics Collection**: System and business metrics
- **Health Checks**: Comprehensive system health monitoring
- **Logging**: Structured logging with correlation IDs

---

## 🚀 **Deployment**

### **Docker Deployment**

```bash
# Build Docker image
docker build -t trading-system .

# Run with Docker Compose
docker-compose up -d

# Scale services
docker-compose up -d --scale api=3 --scale scanner=2
```

### **Kubernetes Deployment**

```bash
# Deploy to Kubernetes
kubectl apply -f kubernetes/

# Check deployment status
kubectl get pods
kubectl get services
```

### **Production Checklist**

- [ ] Environment variables configured
- [ ] Database initialized and migrated
- [ ] SSL certificates installed
- [ ] Monitoring and alerting configured
- [ ] Backup strategy implemented
- [ ] Load balancer configured
- [ ] Security hardening applied

---

## 📚 **Documentation**

### **API Documentation**
- **OpenAPI/Swagger**: Interactive API documentation at `/docs`
- **REST Endpoints**: Complete endpoint reference with examples
- **WebSocket Streams**: Real-time data streaming documentation

### **User Guides**
- **Getting Started**: Quick start guide for new users
- **CLI Reference**: Complete command-line interface documentation
- **Configuration**: Detailed configuration options and examples
- **Troubleshooting**: Common issues and solutions

### **Developer Documentation**
- **Architecture Guide**: Detailed system architecture explanation
- **API Reference**: Internal API documentation
- **Contributing Guide**: Development workflow and standards
- **Testing Guide**: Testing strategies and best practices

---

## 🤝 **Contributing**

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit your changes**: `git commit -m 'Add amazing feature'`
4. **Push to the branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### **Development Standards**

- **Code Style**: Black formatting, isort imports
- **Testing**: 80%+ coverage required
- **Documentation**: All public APIs documented
- **Type Hints**: Full type annotation coverage
- **Linting**: pylint with zero errors

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 **Acknowledgments**

- **Clean Architecture**: Inspired by Uncle Bob's Clean Architecture principles
- **CQRS Pattern**: Based on Greg Young's CQRS and Event Sourcing patterns
- **Domain-Driven Design**: Following Vaughn Vernon's DDD principles
- **DuckDB**: High-performance analytical database
- **FastAPI**: Modern Python web framework
- **Typer**: Intuitive command-line interface framework

---

## 📞 **Support**

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **Documentation**: [Full Documentation](https://your-docs-site.com)

---

**🎯 Built with ❤️ for serious traders and developers**
