from pydantic import BaseModel, Field
from typing import Dict, Any, List
from pathlib import Path
from pydantic import SecretStr

class ScannerThresholds(BaseModel):
    obv_threshold: float = Field(..., gt=0, description="On-Balance Volume threshold for signals")
    volume_multiplier: float = Field(1.5, ge=1.0, description="Relative volume multiplier")
    breakout_period: int = Field(20, ge=5, description="Lookback period for breakout detection")

class ScannersConfig(BaseModel):
    default: Dict[str, Any] = Field({}, description="Default scanner thresholds")
    strategies: Dict[str, Dict[str, Any]] = Field({}, description="Strategy-specific thresholds")
    backtest: Dict[str, Any] = Field({"max_iterations": 1000, "timeframe": "1d"})
    
    @property
    def validated_default(self) -> ScannerThresholds:
        """Get validated default thresholds."""
        return ScannerThresholds(**self.default)
    
    @property
    def validated_strategies(self) -> Dict[str, ScannerThresholds]:
        """Get validated strategy thresholds."""
        return {name: ScannerThresholds(**thresholds) for name, thresholds in self.strategies.items()}

class DatabaseConfig(BaseModel):
    path: Path = Field("financial_data.duckdb", description="DuckDB database file path")
    memory: bool = Field(False, description="Use in-memory database")
    extension_dir: Path = Field("./extensions", description="DuckDB extensions directory")
    max_connections: int = Field(5, ge=1, description="Maximum concurrent connections")

class BrokerCredentials(BaseModel):
    api_key: SecretStr = Field(..., description="Broker API key")
    api_secret: SecretStr = Field(..., description="Broker API secret")
    access_token: SecretStr = Field(..., description="Access token")

class BrokerConfig(BaseModel):
    default: str = Field("dhan", description="Default broker")
    brokers: Dict[str, BrokerCredentials] = Field(
        {
            "dhan": BrokerCredentials(api_key=SecretStr("dummy_dhan_key"), api_secret=SecretStr("dummy_dhan_secret"), access_token=SecretStr("dummy_dhan_token")),
            "tradehull": BrokerCredentials(api_key=SecretStr("dummy_th_key"), api_secret=SecretStr("dummy_th_secret"), access_token=SecretStr("dummy_th_token"))
        },
        description="Credentials for each broker"
    )
    endpoints: Dict[str, str] = Field(
        {"dhan": "https://api.dhan.co", "tradehull": "https://api.tradehull.com"},
        description="API endpoints"
    )
    rate_limit: int = Field(100, ge=1, description="Requests per minute")

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