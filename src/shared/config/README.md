# Configuration System

The Configuration System provides a unified, hierarchical, and validated approach to managing all application settings. It consolidates scattered configuration files into a single source of truth with environment-specific overrides.

## 🏗️ Architecture Overview

```
Configuration Hierarchy
├── consolidated_config.yaml       # Base configuration (all environments)
├── environments/
│   ├── development.yaml          # Development overrides
│   ├── staging.yaml              # Staging overrides
│   ├── production.yaml           # Production overrides
│   └── testing.yaml              # Testing overrides
└── migration.py                  # Migration utilities
```

## 📁 Directory Structure

```
src/shared/config/
├── __init__.py                   # Package exports
├── config_manager.py             # Main configuration manager
├── settings.py                   # Pydantic settings classes
├── loaders.py                    # Configuration file loaders
├── validators.py                 # Configuration validators
├── migration.py                  # Migration utilities
├── consolidated_config.yaml      # Main configuration file
├── environments/                 # Environment-specific configs
│   ├── development.yaml
│   ├── staging.yaml
│   ├── production.yaml
│   └── testing.yaml
└── README.md
```

## 🔧 Core Components

### 1. Configuration Manager (`ConfigManager`)

The central orchestrator that handles loading, validation, and caching of configurations:

```python
from src.shared.config import get_config_manager

# Get configuration manager
config_manager = get_config_manager()

# Load configuration
database_config = config_manager.get_config("database")

# Get typed settings
from src.shared.config import AppSettings
app_settings = config_manager.get_settings(AppSettings)
```

### 2. Settings Classes (Pydantic)

Type-safe configuration classes with validation:

```python
from src.shared.config import DatabaseSettings, APISettings

# Database settings with validation
db_settings = DatabaseSettings(
    path="data/financial_data.duckdb",
    max_connections=10
)

# API settings with validation
api_settings = APISettings(
    host="0.0.0.0",
    port=8000,
    secret_key="your-secret-key"
)
```

### 3. Configuration Loaders

Support for multiple file formats and sources:

```python
from src.shared.config.loaders import ConfigLoader

loader = ConfigLoader()

# Load YAML file
config = loader.load_config("config/database.yaml")

# Load from environment variables
env_config = loader.load_from_environment(prefix="TRADING_")

# Merge configurations
merged = loader.merge_configs(base_config, override_config)
```

### 4. Configuration Validators

Validate configuration data against schemas and business rules:

```python
from src.shared.config.validators import ConfigValidator

validator = ConfigValidator()

# Validate configuration
is_valid = validator.validate_config("database", config)

# Get validation errors
errors = validator.get_validation_errors("database", config)
```

## 📋 Configuration Files

### Main Configuration (`consolidated_config.yaml`)

Contains all base configuration settings that apply to all environments:

```yaml
# Application metadata
name: "Trading System"
version: "2.0.0"
environment: development

# Core components
database:
  path: "data/financial_data.duckdb"
  max_connections: 5

api:
  host: "0.0.0.0"
  port: 8000

brokers:
  default: "dhan"
  brokers:
    dhan:
      api_key: "dummy_key"
      # ... other settings
```

### Environment-Specific Configurations

Override settings for specific environments:

#### Development (`environments/development.yaml`)
```yaml
environment: development

api:
  host: "127.0.0.1"  # Localhost only
  port: 8000

database:
  path: "data/financial_data_dev.duckdb"  # Separate DB

logging:
  level: "DEBUG"  # More verbose logging
```

#### Production (`environments/production.yaml`)
```yaml
environment: production

api:
  host: "0.0.0.0"
  port: 8000
  secret_key: "${API_SECRET_KEY}"  # Environment variable

security:
  enable_ssl: true
  ssl_cert_path: "/etc/ssl/certs/trading-system.crt"

logging:
  level: "WARNING"  # Less verbose
```

## 🚀 Usage Examples

### Basic Usage

```python
from src.shared.config import get_config_manager, AppSettings

# Get configuration manager
config_manager = get_config_manager()

# Load database configuration
db_config = config_manager.get_config("database")
print(f"Database path: {db_config['path']}")

# Get typed application settings
app_settings = config_manager.get_settings(AppSettings)
print(f"API host: {app_settings.api.host}")
print(f"Database path: {app_settings.database.path}")
```

### Environment-Specific Loading

```python
import os
from src.shared.config import get_config_manager

# Set environment
os.environ["TRADING_ENV"] = "production"

# Configuration manager automatically loads production settings
config_manager = get_config_manager()
api_config = config_manager.get_config("api")
# Returns production API configuration
```

### Hot Reload

```python
from src.shared.config import get_config_manager

config_manager = get_config_manager()

# Load configuration (cached)
config1 = config_manager.get_config("database")

# Force reload from disk
config2 = config_manager.get_config("database", reload=True)

# Reload all configurations
config_manager.reload_all()
```

### Validation

```python
from src.shared.config import get_config_manager

config_manager = get_config_manager()

# Validate configuration
is_valid = config_manager.validate_config("database")
if not is_valid:
    print("Database configuration is invalid")
```

## 🔄 Migration from Old System

### Preview Migration

```bash
cd src/shared/config
python migration.py preview
```

### Run Migration

```bash
# Create backup and migrate
python migration.py migrate

# Migrate without backup (not recommended)
python migration.py migrate --no-backup
```

### Rollback Migration

```bash
# Rollback to original configuration
python migration.py rollback
```

### Migration Report

After migration, check the migration summary:

```bash
cat configs/migration_summary.yaml
```

## 🔧 Advanced Features

### Environment Variable Substitution

Use environment variables in configuration files:

```yaml
database:
  path: "${DATABASE_PATH}"
  password: "${DB_PASSWORD}"

api:
  secret_key: "${API_SECRET_KEY}"
```

### Configuration Templates

Generate configuration templates:

```python
from src.shared.config.loaders import ConfigLoader

loader = ConfigLoader()
template = loader.get_config_template("database")
print(template)
```

### Custom Validators

Add custom validation rules:

```python
from src.shared.config.validators import ConfigValidator

class CustomValidator(ConfigValidator):
    def _validate_custom_config(self, config):
        # Custom validation logic
        if "custom_field" not in config:
            return False
        return True
```

## 📊 Configuration Sections

### Database Configuration
```yaml
database:
  path: "data/financial_data.duckdb"
  memory: false
  max_connections: 5
  connection_pool_size: 10
  query_cache_enabled: true
  schema: {...}  # Database schema definitions
```

### API Configuration
```yaml
api:
  host: "0.0.0.0"
  port: 8000
  cors_origins: ["http://localhost:3000"]
  rate_limit: "100/minute"
  docs_url: "/docs"
  secret_key: "your-secret-key"
```

### Broker Configuration
```yaml
brokers:
  default: "dhan"
  rate_limit: 100
  brokers:
    dhan:
      api_key: "${DHAN_API_KEY}"
      api_secret: "${DHAN_API_SECRET}"
    tradehull:
      api_key: "${TRADEHULL_API_KEY}"
  endpoints:
    dhan: "https://api.dhan.co"
```

### Scanner Configuration
```yaml
scanners:
  default:
    breakout_period: 20
    volume_multiplier: 1.5
  rules:
    breakout: {...}
    volume: {...}
  strategies:
    breakout: {...}
    technical: {...}
```

### Trade Engine Configuration
```yaml
trade_engine:
  mode: "backtest"
  universe: "NIFTY500"
  time:
    warmup_start: "09:15"
    eod_flat: "15:15"
  risk:
    per_trade_r_pct: 0.75
    k_atr_initial: 1.6
  telemetry:
    log_level: "INFO"
    metrics:
      enable_pnl_tracking: true
```

## 🔒 Security Considerations

### Production Configuration
- Never commit secrets to version control
- Use environment variables for sensitive data
- Enable SSL in production
- Use restrictive CORS origins
- Implement proper access controls

### Environment Variables
```bash
# Database
export DATABASE_PATH="/var/lib/trading/data.duckdb"
export DB_PASSWORD="secure_password"

# API
export API_SECRET_KEY="your-256-bit-secret"
export JWT_SECRET="your-jwt-secret"

# Brokers
export DHAN_API_KEY="your_dhan_api_key"
export DHAN_API_SECRET="your_dhan_secret"
```

## 🧪 Testing Configuration

### Unit Tests
```python
import pytest
from src.shared.config import get_config_manager, DatabaseSettings

def test_database_config():
    config_manager = get_config_manager()
    db_config = config_manager.get_config("database")

    assert "path" in db_config
    assert db_config["max_connections"] > 0

def test_settings_validation():
    # This should raise validation error
    with pytest.raises(ValueError):
        DatabaseSettings(max_connections=-1)
```

### Integration Tests
```python
def test_config_loading():
    config_manager = get_config_manager()
    config = config_manager.get_config("api")

    assert config["host"] in ["127.0.0.1", "0.0.0.0"]
    assert 1000 <= config["port"] <= 9999
```

### Environment Tests
```python
def test_environment_override():
    import os
    os.environ["TRADING_ENV"] = "testing"

    config_manager = get_config_manager()
    api_config = config_manager.get_config("api")

    # Should load testing configuration
    assert api_config["host"] == "127.0.0.1"
```

## 📈 Performance & Caching

### Configuration Caching
- Configurations are cached in memory
- Automatic reload on file changes
- Environment-specific cache keys
- Thread-safe operations

### Performance Optimizations
```python
# Pre-load frequently used configurations
config_manager = get_config_manager()
database_config = config_manager.get_config("database")  # Cached
api_config = config_manager.get_config("api")           # Cached

# Force reload when needed
config_manager.reload_all()
```

## 🔍 Monitoring & Debugging

### Configuration Info
```python
config_manager = get_config_manager()
info = config_manager.get_environment_info()

print(f"Environment: {info['environment']}")
print(f"Available configs: {info['available_configs']}")
print(f"Cache size: {info['cache_size']}")
```

### Debug Logging
```python
import logging
logging.getLogger("src.shared.config").setLevel(logging.DEBUG)

# Now you'll see detailed configuration loading logs
config_manager = get_config_manager()
config = config_manager.get_config("database")
```

## 🚦 Best Practices

### 1. Configuration Hierarchy
- Use base configuration for common settings
- Override only what needs to change per environment
- Keep sensitive data in environment variables

### 2. Validation
- Always validate configurations after loading
- Use type-safe settings classes
- Implement custom validators for business rules

### 3. Security
- Never commit secrets to version control
- Use strong encryption for sensitive data
- Implement proper access controls

### 4. Testing
- Test configuration loading in all environments
- Validate configuration changes
- Use separate test configurations

### 5. Documentation
- Document all configuration options
- Provide examples for each environment
- Keep configuration schema up to date

## 🎯 Migration Guide

### From Scattered Files to Consolidated

1. **Backup existing configurations**
   ```bash
   cp -r configs configs.backup
   ```

2. **Preview migration**
   ```bash
   cd src/shared/config
   python migration.py preview
   ```

3. **Run migration**
   ```bash
   python migration.py migrate
   ```

4. **Update application code**
   ```python
   # Old way
   import yaml
   with open("configs/database.yaml") as f:
       config = yaml.safe_load(f)

   # New way
   from src.shared.config import get_config_manager
   config_manager = get_config_manager()
   config = config_manager.get_config("database")
   ```

5. **Test thoroughly**
   - Run all tests
   - Verify application functionality
   - Check logs for configuration errors

### Environment Variable Migration

```bash
# Old way
DATABASE_PATH=/var/lib/trading/data.duckdb

# New way (with defaults)
export DATABASE_PATH="${DATABASE_PATH:-data/financial_data.duckdb}"
export TRADING_ENV="${TRADING_ENV:-development}"
```

This unified configuration system provides a robust, scalable, and maintainable approach to managing application settings across all environments! 🎉
