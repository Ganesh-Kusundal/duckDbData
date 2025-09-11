# 🤝 Contributing Guide

Welcome to the Trading System project! We're excited that you're interested in contributing. This guide will help you get started with development, understand our processes, and make meaningful contributions to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Guidelines](#code-guidelines)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Community](#community)

## 📜 Code of Conduct

### Our Pledge
We are committed to providing a welcoming and inclusive environment for all contributors. We pledge to:

- **Be respectful** of differing viewpoints and experiences
- **Be collaborative** and help each other learn and grow
- **Be constructive** in feedback and criticism
- **Show empathy** towards other community members
- **Focus on what is best** for the community and project

### Our Standards
Examples of behavior that contributes to a positive environment:

- ✅ Using welcoming and inclusive language
- ✅ Being respectful of differing viewpoints
- ✅ Gracefully accepting constructive criticism
- ✅ Focusing on what is best for the community
- ✅ Showing empathy towards other community members

Examples of unacceptable behavior:

- ❌ The use of sexualized language or imagery
- ❌ Personal or political attacks
- ❌ Trolling, insulting/derogatory comments
- ❌ Public or private harassment
- ❌ Publishing others' private information

## 🚀 Getting Started

### Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** installed
- **Git** for version control
- **Docker & Docker Compose** (recommended)
- **GitHub account** for contributing

### Quick Setup

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/trading-system.git
   cd trading-system
   ```
3. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Set up development environment** (see [Development Setup](#development-setup))
5. **Make your changes**
6. **Run tests** and ensure they pass
7. **Submit a pull request**

## 🛠️ Development Setup

### Option 1: Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/your-org/trading-system.git
cd trading-system

# Start development environment
docker-compose -f docker/docker-compose.dev.yml up -d

# Run tests
docker-compose exec api python -m pytest tests/

# Access services
# API: http://localhost:8000
# Dashboard: http://localhost:8080
# Docs: http://localhost:8000/docs
```

### Option 2: Local Python Environment

```bash
# Clone repository
git clone https://github.com/your-org/trading-system.git
cd trading-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup pre-commit hooks
pre-commit install

# Run database migrations
python scripts/setup.py

# Start development server
python -m src.interfaces.api.main --reload
```

### IDE Configuration

#### VS Code
Create `.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

#### PyCharm
1. Open project in PyCharm
2. Configure interpreter: `File → Settings → Project → Python Interpreter → Add → Virtualenv Environment`
3. Install requirements: `Tools → Sync Python Requirements`
4. Configure testing: `File → Settings → Tools → Python Integrated Tools → Testing → pytest`

## 🔄 Development Workflow

### 1. Choose an Issue

- Check [GitHub Issues](https://github.com/your-org/trading-system/issues) for open tasks
- Look for issues labeled `good first issue` or `help wanted`
- Comment on the issue to indicate you're working on it

### 2. Create a Branch

```bash
# Create and switch to feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-number-description

# Or for documentation
git checkout -b docs/update-contributing-guide
```

### 3. Make Changes

Follow our [Code Guidelines](#code-guidelines) while making changes.

### 4. Test Your Changes

```bash
# Run unit tests
python -m pytest tests/unit/ -v

# Run integration tests
python -m pytest tests/integration/ -v

# Run all tests
python -m pytest tests/ --cov=src --cov-report=html

# Check code quality
flake8 src/
black --check src/
mypy src/
```

### 5. Commit Changes

```bash
# Stage your changes
git add .

# Commit with descriptive message
git commit -m "feat: add market data validation

- Add OHLCV price validation in MarketData entity
- Add volume validation with historical comparison
- Add comprehensive error messages
- Update tests for validation scenarios

Closes #123"

# Follow conventional commit format
# Types: feat, fix, docs, style, refactor, test, chore
```

### 6. Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
# - Use PR template
# - Link to related issues
# - Add screenshots for UI changes
# - Request review from maintainers
```

## 📝 Code Guidelines

### Python Style Guide

We follow **PEP 8** with some modifications:

#### Code Formatting
```python
# Use Black for automatic formatting
# Line length: 88 characters
# String quotes: Double quotes preferred
# Trailing commas: Yes, for better git diffs

# Good
def calculate_sma(prices: List[float], period: int = 20) -> float:
    """Calculate Simple Moving Average."""
    if len(prices) < period:
        raise ValueError("Insufficient data for SMA calculation")

    return sum(prices[-period:]) / period

# Bad
def calculate_sma(prices, period=20):
    if len(prices) < period:
        raise ValueError("Insufficient data")
    return sum(prices[-period:]) / period
```

#### Type Hints
```python
# Always use type hints
from typing import List, Optional, Dict, Any

def process_market_data(
    symbol: str,
    data: List[Dict[str, Any]],
    validate: bool = True
) -> Optional[Dict[str, Any]]:
    """Process market data with validation."""
    pass

# Use Union for multiple types
from typing import Union
def get_price(symbol: str) -> Union[float, None]:
    pass
```

#### Naming Conventions
```python
# Classes: PascalCase
class MarketDataService:
    pass

# Functions/Methods: snake_case
def calculate_volatility(prices: List[float]) -> float:
    pass

# Constants: UPPER_CASE
MAX_CONNECTIONS = 10
DEFAULT_TIMEOUT = 30

# Private attributes: _single_underscore
class TradingService:
    def __init__(self):
        self._repository = None
        self._validator = None
```

#### Error Handling
```python
# Use custom exceptions
class TradingError(Exception):
    """Base trading exception."""
    pass

class ValidationError(TradingError):
    """Data validation error."""
    pass

class DatabaseError(TradingError):
    """Database operation error."""
    pass

# Handle exceptions properly
def get_market_data(symbol: str) -> MarketData:
    try:
        return repository.find_by_symbol(symbol)
    except DatabaseError as e:
        logger.error(f"Database error for {symbol}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error for {symbol}: {e}")
        raise TradingError(f"Failed to get market data for {symbol}") from e
```

### Architecture Guidelines

#### Clean Architecture
- **Domain Layer**: Pure business logic, no external dependencies
- **Infrastructure Layer**: External services and adapters
- **Application Layer**: Use cases and CQRS orchestration
- **Presentation Layer**: API, CLI, and UI interfaces

#### CQRS Pattern
```python
# Commands for write operations
@dataclass
class UpdateMarketDataCommand(Command):
    symbol: str
    market_data: MarketData

# Queries for read operations
@dataclass
class GetMarketDataQuery(Query):
    symbol: str
    timeframe: str = "1D"

# Separate handlers
class UpdateMarketDataCommandHandler(CommandHandler):
    async def handle(self, command: UpdateMarketDataCommand) -> CommandResult:
        # Write logic here
        pass

class GetMarketDataQueryHandler(QueryHandler):
    async def handle(self, query: GetMarketDataQuery) -> QueryResult:
        # Read logic here
        pass
```

#### Dependency Injection
```python
# Use dependency injection instead of direct instantiation
class MarketDataService:
    def __init__(self, repository: MarketDataRepository):
        self.repository = repository

# In composition root (main.py or dependency container)
def create_market_data_service() -> MarketDataService:
    repository = DuckDBMarketDataRepository()
    return MarketDataService(repository)
```

### Testing Guidelines

#### Unit Tests
```python
import pytest
from unittest.mock import Mock

def test_market_data_creation():
    """Test MarketData entity creation and validation."""
    ohlcv = OHLCV(open=100, high=105, low=95, close=102, volume=1000)
    market_data = MarketData(
        symbol="AAPL",
        timestamp="2024-01-01T10:00:00Z",
        timeframe="1D",
        ohlcv=ohlcv,
        date_partition="2024-01-01"
    )

    assert market_data.symbol == "AAPL"
    assert market_data.ohlcv.close == 102.0
    assert market_data.is_bullish() is True

def test_invalid_market_data():
    """Test MarketData validation."""
    with pytest.raises(ValueError, match="Low price cannot be higher than high price"):
        OHLCV(open=100, high=90, low=95, close=102, volume=1000)
```

#### Integration Tests
```python
@pytest.mark.asyncio
async def test_market_data_repository():
    """Test repository with actual database."""
    repository = DuckDBMarketDataRepository()

    market_data = create_test_market_data()
    result = await repository.save(market_data)
    assert result is True

    retrieved = await repository.find_latest_by_symbol("AAPL", "1D")
    assert retrieved is not None
    assert retrieved.symbol == "AAPL"
```

#### Test Coverage
- **Minimum Coverage**: 80% for new code
- **Branches**: Test both true/false branches
- **Edge Cases**: Test boundary conditions
- **Error Cases**: Test exception handling

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/unit/test_market_data.py

# Run tests with coverage
python -m pytest --cov=src --cov-report=html

# Run tests in verbose mode
python -m pytest -v

# Run tests matching pattern
python -m pytest -k "test_market_data"

# Run tests and stop on first failure
python -m pytest -x
```

### Writing Tests

#### Test Structure
```
tests/
├── unit/                    # Unit tests
│   ├── test_market_data.py
│   ├── test_ohlcv.py
│   └── test_commands.py
├── integration/            # Integration tests
│   ├── test_api.py
│   ├── test_database.py
│   └── test_websocket.py
├── functional/             # Functional tests
│   ├── test_trading_flow.py
│   └── test_scanner_flow.py
└── fixtures/               # Test fixtures
    ├── market_data.json
    └── test_database.db
```

#### Test Fixtures
```python
import pytest
from src.domain.market_data.entities.market_data import MarketData, OHLCV

@pytest.fixture
def sample_ohlcv():
    """Sample OHLCV data for testing."""
    return OHLCV(
        open=150.25,
        high=152.80,
        low=149.50,
        close=152.10,
        volume=45000000
    )

@pytest.fixture
def sample_market_data(sample_ohlcv):
    """Sample market data for testing."""
    return MarketData(
        symbol="AAPL",
        timestamp="2024-09-05T16:00:00Z",
        timeframe="1D",
        ohlcv=sample_ohlcv,
        date_partition="2024-09-05"
    )

@pytest.fixture
async def test_database():
    """Test database fixture."""
    # Setup test database
    db = DuckDBMarketDataRepository(":memory:")
    await db.initialize()

    yield db

    # Cleanup
    await db.close()
```

## 📚 Documentation

### Code Documentation

```python
class MarketDataService:
    """
    Domain service for market data operations.

    This service handles business logic related to market data processing,
    validation, and analysis. It orchestrates operations between the domain
    entities and infrastructure repositories.

    Attributes:
        repository: Market data repository for persistence operations

    Example:
        service = MarketDataService(repository)
        data = await service.get_price_history("AAPL", days=30)
    """

    def __init__(self, repository: MarketDataRepository):
        """
        Initialize market data service.

        Args:
            repository: Market data repository implementation
        """
        self.repository = repository

    async def get_price_history(
        self,
        symbol: str,
        timeframe: str = "1D",
        days: int = 30
    ) -> List[MarketData]:
        """
        Get price history for a symbol.

        Retrieves historical market data for the specified symbol and
        timeframe over the given number of days.

        Args:
            symbol: Trading symbol (e.g., 'AAPL', 'GOOGL')
            timeframe: Data timeframe ('1D', '1H', '30m', etc.)
            days: Number of days of history to retrieve

        Returns:
            List of MarketData objects in chronological order

        Raises:
            ValueError: If symbol or timeframe is invalid
            DatabaseError: If database operation fails

        Example:
            history = await service.get_price_history("AAPL", days=90)
            for data in history:
                print(f"{data.timestamp}: {data.ohlcv.close}")
        """
        pass
```

### API Documentation

```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

router = APIRouter()

class MarketDataResponse(BaseModel):
    """Market data API response model."""
    symbol: str = Field(..., description="Trading symbol")
    timestamp: str = Field(..., description="ISO timestamp")
    timeframe: str = Field(..., description="Data timeframe")
    ohlcv: dict = Field(..., description="OHLCV price data")
    date_partition: str = Field(..., description="Date partition")

    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "timestamp": "2024-09-05T16:00:00",
                "timeframe": "1D",
                "ohlcv": {
                    "open": 150.25,
                    "high": 152.80,
                    "low": 149.50,
                    "close": 152.10,
                    "volume": 45000000
                },
                "date_partition": "2024-09-05"
            }
        }

@router.get(
    "/current/{symbol}",
    response_model=MarketDataResponse,
    summary="Get Current Market Data",
    description="Retrieve the latest market data for a specific symbol."
)
async def get_current_market_data(
    symbol: str = Path(..., description="Trading symbol"),
    timeframe: str = Query("1D", description="Data timeframe")
):
    """Get current market data for a symbol."""
    pass
```

## 🔄 Pull Request Process

### PR Template

When creating a pull request, use this template:

```markdown
## Description
Brief description of the changes made.

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change
- [ ] Documentation update
- [ ] Refactoring

## How Has This Been Tested?
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Performance tests pass

## Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have added tests for new functionality
- [ ] I have updated documentation
- [ ] All tests pass
- [ ] I have tested manually

## Screenshots (if applicable)
Add screenshots for UI changes.

## Additional Notes
Any additional information or context.
```

### PR Review Process

1. **Automated Checks**: CI/CD runs tests and linting
2. **Peer Review**: At least one maintainer reviews the code
3. **Testing**: Reviewer tests the functionality
4. **Approval**: PR is approved and merged
5. **Deployment**: Changes are deployed to staging/production

### Code Review Guidelines

#### For Reviewers
- **Be constructive**: Focus on code quality and learning
- **Explain reasoning**: Provide context for suggestions
- **Suggest alternatives**: Offer solutions, not just problems
- **Check coverage**: Ensure adequate test coverage
- **Verify documentation**: Check that docs are updated

#### For Contributors
- **Address feedback**: Respond to all review comments
- **Make requested changes**: Implement suggested improvements
- **Ask questions**: Seek clarification when needed
- **Keep scope focused**: Don't expand PR scope unnecessarily
- **Test thoroughly**: Ensure changes work as expected

## 🐛 Issue Reporting

### Bug Reports

Use this template for bug reports:

```markdown
## Bug Report

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Environment:**
- OS: [e.g., Ubuntu 22.04]
- Python Version: [e.g., 3.11.0]
- Docker Version: [e.g., 24.0.0]
- Browser: [e.g., Chrome 115.0]

**Additional context**
Add any other context about the problem here.
```

### Feature Requests

Use this template for feature requests:

```markdown
## Feature Request

**Is your feature request related to a problem? Please describe.**
A clear and concise description of what the problem is.

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions.

**Additional context**
Add any other context or screenshots about the feature request here.
```

## 🌐 Community

### Getting Help

- **Documentation**: Check the [docs](../README.md) first
- **GitHub Issues**: Search existing issues and discussions
- **GitHub Discussions**: Ask questions in the Q&A section
- **Slack**: Join our community Slack workspace

### Communication Guidelines

- **Be respectful**: Treat everyone with respect and kindness
- **Be clear**: Write clear, concise messages
- **Be patient**: Allow time for responses
- **Be helpful**: Help others when you can
- **Stay on topic**: Keep discussions relevant to the project

### Recognition

Contributors are recognized in several ways:

- **Contributors List**: Added to [CONTRIBUTORS.md](../CONTRIBUTORS.md)
- **GitHub Recognition**: GitHub's contributor insights
- **Release Notes**: Mentioned in release notes
- **Community Calls**: Invited to community meetings

## 📜 License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project (MIT License).

## 🙏 Acknowledgments

Thank you for contributing to the Trading System! Your contributions help make this project better for everyone.

---

**Happy contributing! 🚀**
