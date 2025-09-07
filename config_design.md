# Configuration System Design

## Overview

The configuration system introduces a centralized ConfigManager in the infrastructure layer to replace scattered config usage across the trading platform. This addresses identified issues in the architecture analysis: lack of validation, environment support, and dynamic loading in the current [`settings.py`](src/infrastructure/config/settings.py). The system supports YAML files for structured configs and environment variables for sensitive/dynamic values, with Pydantic for validation. It enables hierarchical overrides (global → module → environment) for flexibility in development, testing, and production.

The ConfigManager will be injectable into use cases, scanners, adapters, and services, promoting clean architecture principles by abstracting config access.

## ConfigManager Class Specification

### Location
- File: `src/infrastructure/config/config_manager.py`

### Key Features
- **Loading Sources**:
  - YAML files: Primary source for structured configs (e.g., `config.yaml` in project root or `configs/` directory).
  - Environment variables: Override YAML values (prefixed e.g., `TRADING_PLATFORM_`).
  - Default values: Fallbacks defined in code via Pydantic models.
- **Validation**: Uses Pydantic BaseModel for schema validation, ensuring type safety and required fields.
- **Hierarchical Overrides**:
  - Global: Base config for the entire application.
  - Module-specific: Overrides for scanners, database, brokers, etc.
  - Environment-specific: Loaded based on `os.getenv('ENV', 'development')`, e.g., `config_dev.yaml` overrides base.
- **Dynamic Loading**: Supports reloading configs at runtime (e.g., for hot-reloading in development) and caching for performance.
- **Access Patterns**: Singleton-like instance for global access, but injectable via dependency injection (e.g., in FastAPI or use cases).
- **Error Handling**: Raises descriptive exceptions for invalid configs (e.g., missing required fields, type mismatches).
- **Security**: Environment vars for secrets (API keys); YAML for non-sensitive defaults.

### Class Structure (Pseudo-Code)

```python
from typing import Dict, Any, Optional
from pathlib import Path
import os
import yaml
from pydantic import BaseModel, ValidationError

class ConfigManager:
    def __init__(self, config_dir: str = "configs", env: str = None):
        self.config_dir = Path(config_dir)
        self.env = env or os.getenv("ENV", "development")
        self._config: Optional[Dict[str, Any]] = None
        self._load_config()
    
    def _load_config(self):
        """Load and merge configs hierarchically."""
        base_config = self._load_yaml("config.yaml")
        env_config = self._load_yaml(f"config_{self.env}.yaml") if self._config_dir.exists() / f"config_{self.env}.yaml" else {}
        module_configs = self._load_module_configs()  # e.g., scanners.yaml, database.yaml
        
        # Merge with overrides: global -> module -> env
        self._config = {**base_config, **module_configs, **env_config}
        
        # Override with env vars
        self._apply_env_overrides()
        
        # Validate using Pydantic schemas
        self._validate_config()
    
    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load YAML file, return empty dict if not found."""
        file_path = self.config_dir / filename
        if file_path.exists():
            with open(file_path, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def _load_module_configs(self) -> Dict[str, Any]:
        """Load module-specific YAML files (e.g., scanners.yaml)."""
        module_configs = {}
        for module_file in self.config_dir.glob("*.yaml"):
            if module_file.stem != "config" and not module_file.stem.endswith(f"_{self.env}"):
                module_name = module_file.stem
                module_configs[module_name] = self._load_yaml(module_file.name)
        return module_configs
    
    def _apply_env_overrides(self):
        """Override config values with environment variables (e.g., TRADING_PLATFORM_DB_PATH)."""
        for key, value in self._config.items():
            env_key = f"TRADING_PLATFORM_{key.upper().replace('.', '_')}"
            if env_key in os.environ:
                self._config[key] = os.getenv(env_key, value)
    
    def _validate_config(self):
        """Validate the entire config or sections using Pydantic models."""
        # Example: Validate scanners section with ScannersConfig model
        if "scanners" in self._config:
            ScannersConfig(**self._config["scanners"])  # Raises ValidationError if invalid
    
    def get_config(self, section: str = None) -> Dict[str, Any]:
        """Get config section or full config."""
        if section:
            return self._config.get(section, {})
        return self._config.copy()
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get nested value, e.g., 'database.path'."""
        keys = key.split(".")
        value = self._config
        for k in keys:
            value = value.get(k, default)
            if value is None:
                return default
        return value
    

## Pydantic Config Schemas

Schemas will be defined in `src/infrastructure/config/schemas.py` using Pydantic BaseModels. These provide validation and type hints for ConfigManager sections. Example schemas for key components:

### ScannersConfig
```python
from pydantic import BaseModel, Field
from typing import Dict, Any

class ScannerThresholds(BaseModel):
    obv_threshold: float = Field(..., gt=0, description="On-Balance Volume threshold for signals")
    volume_multiplier: float = Field(1.5, ge=1.0, description="Relative volume multiplier")
    breakout_period: int = Field(20, ge=5, description="Lookback period for breakout detection")

class ScannersConfig(BaseModel):
    default: ScannerThresholds = Field(default_factory=ScannerThresholds)
    strategies: Dict[str, ScannerThresholds] = {}  # e.g., {"breakout": {...}, "obv": {...}}
    backtest: Dict[str, Any] = Field({"max_iterations": 1000, "timeframe": "1d"})
```

### DatabaseConfig
```python
from pydantic import BaseModel, Field
from pathlib import Path

class DatabaseConfig(BaseModel):
    path: Path = Field("financial_data.duckdb", description="DuckDB database file path")
    memory: bool = Field(False, description="Use in-memory database")
    extension_dir: Path = Field("./extensions", description="DuckDB extensions directory")
    max_connections: int = Field(5, ge=1, description="Maximum concurrent connections")
```

### BrokersConfig
```python
from pydantic import BaseModel, Field, SecretStr
from typing import Dict, List

class BrokerCredentials(BaseModel):
    api_key: SecretStr = Field(..., description="Broker API key")
    api_secret: SecretStr = Field(..., description="Broker API secret")
    access_token: SecretStr = Field(..., description="Access token")

class BrokerConfig(BaseModel):
    default: str = Field("dhan", description="Default broker")
    brokers: Dict[str, BrokerCredentials] = Field(
        {"dhan": BrokerCredentials(), "tradehull": BrokerCredentials()},
        description="Credentials for each broker"
    )
    endpoints: Dict[str, str] = Field(
        {"dhan": "https://api.dhan.co", "tradehull": "https://api.tradehull.com"},
        description="API endpoints"
    )
    rate_limit: int = Field(100, ge=1, description="Requests per minute")
```

### AnalyticsConfig
```python
from pydantic import BaseModel, Field
from typing import Dict, List

class QueryConfig(BaseModel):
    timeout: int = Field(30, ge=1, description="Query timeout in seconds")
    max_results: int = Field(1000, ge=1, description="Maximum query results")

class RuleConfig(BaseModel):
    name: str
    pattern: str
    params: Dict[str, Any] = {}

class AnalyticsConfig(BaseModel):
    queries: Dict[str, QueryConfig] = Field(
        {"breakout_patterns": QueryConfig()},
        description="Query configurations"
    )
    rules: List[RuleConfig] = Field([], description="Rule engine configurations")
    dashboard: Dict[str, Any] = Field({"port": 8080, "host": "localhost"})
    indicators: List[str] = Field(["rsi", "macd", "obv"], description="Enabled technical indicators")
```

### Usage in ConfigManager
In `_validate_config()`, instantiate models like:
```python
ScannersConfig(**self._config.get("scanners", {}))
DatabaseConfig(**self._config.get("database", {}))
BrokersConfig(**self._config.get("brokers", {}))
AnalyticsConfig(**self._config.get("analytics", {}))
```

These schemas ensure runtime validation and provide IDE support for config access.
    def reload(self):
        """Reload configs dynamically."""
        self._load_config()
    
    def validate_section(self, section: str, model_class: type[BaseModel]):
        """Validate a specific section with a Pydantic model."""
        section_config = self.get_config(section)
        try:
            return model_class(**section_config)
        except ValidationError as e:
            raise ValueError(f"Invalid config for {section}: {e}")
```

### Integration Points
- **Dependency Injection**: In use cases (e.g., [`ScanMarketUseCase`](src/application/use_cases/scan_market.py:48)), inject `ConfigManager` to access scanner configs instead of hardcoded `_get_default_config()`.
- **Adapters**: [`DuckDBAdapter`](src/infrastructure/adapters/duckdb_adapter.py) uses ConfigManager for `db_path`.
- **Scanners**: BaseScanner and strategies (e.g., [`BreakoutScanner`](src/application/scanners/strategies/breakout_scanner.py:14)) inject config for thresholds.
- **Brokers**: [`BrokerAdapter`](src/infrastructure/adapters/broker_adapter.py) for API keys.
- **Analytics**: Queries and rules load params from config.
- **Global Access**: Singleton instance in `src/infrastructure/config/__init__.py`: `config_manager = ConfigManager()`.

### Dependencies
- `pydantic>=2.0` for validation.
- `pyyaml>=6.0` for YAML parsing.
- Environment: `ENV` var for environment selection.

## Next Steps
- Define Pydantic schemas in a separate section/file.
- Update architecture diagram.
- Migration plan.