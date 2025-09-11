"""
Configuration Settings Classes
Type-safe configuration classes using Pydantic
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, validator

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older Pydantic versions
    from pydantic import BaseSettings
import os


class DatabaseSettings(BaseModel):
    """Database configuration settings"""

    path: str = Field(default="data/financial_data.duckdb", description="Database file path")
    memory: bool = Field(default=False, description="Use in-memory database")
    extension_dir: str = Field(default="./extensions", description="Database extensions directory")
    max_connections: int = Field(default=5, description="Maximum database connections")
    connection_pool_size: int = Field(default=10, description="Connection pool size")
    connection_pool_timeout: float = Field(default=30.0, description="Connection timeout in seconds")
    query_cache_enabled: bool = Field(default=True, description="Enable query caching")
    query_cache_ttl: int = Field(default=300, description="Query cache TTL in seconds")

    # Schema definitions
    schema: Dict[str, Any] = Field(default_factory=dict, description="Database schema definitions")

    @validator('path')
    def validate_database_path(cls, v):
        """Validate database path"""
        if not v:
            raise ValueError("Database path cannot be empty")
        return v

    @validator('max_connections')
    def validate_max_connections(cls, v):
        """Validate maximum connections"""
        if v < 1:
            raise ValueError("Maximum connections must be at least 1")
        return v


class BrokerSettings(BaseModel):
    """Broker configuration settings"""

    default: str = Field(default="dhan", description="Default broker")
    brokers: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Broker configurations")
    endpoints: Dict[str, str] = Field(default_factory=dict, description="Broker API endpoints")
    rate_limit: int = Field(default=100, description="API rate limit per minute")

    @validator('brokers')
    def validate_brokers(cls, v):
        """Validate broker configurations"""
        required_keys = ['api_key', 'api_secret', 'access_token']
        for broker_name, broker_config in v.items():
            for key in required_keys:
                if key not in broker_config:
                    raise ValueError(f"Broker {broker_name} missing required key: {key}")
        return v


class ScannerSettings(BaseModel):
    """Scanner configuration settings"""

    default: Dict[str, Any] = Field(default_factory=dict, description="Default scanner settings")
    rules: Dict[str, Any] = Field(default_factory=dict, description="Scanner rules configuration")
    strategies: Dict[str, Any] = Field(default_factory=dict, description="Scanner strategies")
    backtest: Dict[str, Any] = Field(default_factory=dict, description="Backtest configuration")
    optimization: Dict[str, Any] = Field(default_factory=dict, description="Optimization settings")

    # Time settings
    cutoff_time: str = Field(default="09:30", description="Scanner cutoff time")
    performance_start_time: str = Field(default="09:45", description="Performance start time")
    performance_end_time: str = Field(default="15:15", description="Performance end time")
    signal_time_window_start: str = Field(default="09:15", description="Signal window start")
    signal_time_window_end: str = Field(default="09:45", description="Signal window end")


class AnalyticsSettings(BaseModel):
    """Analytics configuration settings"""

    queries: Dict[str, Any] = Field(default_factory=dict, description="Query configurations")
    rules: List[Dict[str, Any]] = Field(default_factory=list, description="Analytics rules")
    dashboard: Dict[str, Any] = Field(default_factory=dict, description="Dashboard settings")
    indicators: List[str] = Field(default_factory=list, description="Available indicators")


class APISettings(BaseModel):
    """API configuration settings"""

    host: str = Field(default="0.0.0.0", description="API server host")
    port: int = Field(default=8000, description="API server port")
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://localhost:8080"], description="CORS allowed origins")
    rate_limit: str = Field(default="100/minute", description="API rate limit")
    docs_url: str = Field(default="/docs", description="API documentation URL")
    redoc_url: str = Field(default="/redoc", description="ReDoc documentation URL")
    openapi_url: str = Field(default="/openapi.json", description="OpenAPI JSON URL")

    # Security settings
    secret_key: str = Field(default_factory=lambda: os.getenv("SECRET_KEY", "your-secret-key-here"), description="API secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration")

    @validator('port')
    def validate_port(cls, v):
        """Validate port number"""
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v


class CLISettings(BaseModel):
    """CLI configuration settings"""

    rich_enabled: bool = Field(default=True, description="Enable Rich terminal formatting")
    log_level: str = Field(default="INFO", description="CLI logging level")
    progress_bar: bool = Field(default=True, description="Show progress bars")
    auto_completion: bool = Field(default=True, description="Enable command auto-completion")
    max_table_rows: int = Field(default=100, description="Maximum table rows to display")
    output_format: str = Field(default="table", description="Default output format")

    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v.upper()

    @validator('output_format')
    def validate_output_format(cls, v):
        """Validate output format"""
        valid_formats = ["table", "json", "csv", "text"]
        if v.lower() not in valid_formats:
            raise ValueError(f"Output format must be one of: {', '.join(valid_formats)}")
        return v.lower()


class DashboardSettings(BaseModel):
    """Dashboard configuration settings"""

    host: str = Field(default="0.0.0.0", description="Dashboard server host")
    port: int = Field(default=8080, description="Dashboard server port")
    reload: bool = Field(default=False, description="Enable auto-reload for development")
    static_dir: str = Field(default="static", description="Static files directory")
    template_dir: str = Field(default="templates", description="Template files directory")

    # Dashboard features
    real_time_updates: bool = Field(default=True, description="Enable real-time updates")
    websocket_enabled: bool = Field(default=True, description="Enable WebSocket connections")
    charts_enabled: bool = Field(default=True, description="Enable interactive charts")
    export_enabled: bool = Field(default=True, description="Enable data export features")

    # Security settings
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"], description="CORS allowed origins")
    session_timeout: int = Field(default=3600, description="Session timeout in seconds")

    @validator('port')
    def validate_port(cls, v):
        """Validate port number"""
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v


class WebSocketSettings(BaseModel):
    """WebSocket configuration settings"""

    host: str = Field(default="0.0.0.0", description="WebSocket server host")
    port: int = Field(default=8081, description="WebSocket server port")
    max_connections: int = Field(default=1000, description="Maximum concurrent connections")
    connection_timeout: int = Field(default=30, description="Connection timeout in seconds")
    heartbeat_interval: int = Field(default=30, description="Heartbeat interval in seconds")
    message_size_limit: int = Field(default=1048576, description="Maximum message size in bytes")

    # Subscription settings
    max_subscriptions_per_client: int = Field(default=100, description="Maximum subscriptions per client")
    subscription_rate_limit: int = Field(default=10, description="Subscription rate limit per second")

    # Data streaming
    data_stream_interval: float = Field(default=1.0, description="Data stream interval in seconds")
    batch_size: int = Field(default=100, description="Batch size for data streaming")

    @validator('port')
    def validate_port(cls, v):
        """Validate port number"""
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v


class PerformanceSettings(BaseModel):
    """Performance configuration settings"""

    fast_mode: bool = Field(default=False, description="Enable fast mode optimizations")
    connection_pool_enabled: bool = Field(default=True, description="Enable connection pooling")
    query_cache_enabled: bool = Field(default=True, description="Enable query caching")
    prepared_statements_enabled: bool = Field(default=True, description="Enable prepared statements")
    performance_monitoring: bool = Field(default=False, description="Enable performance monitoring")
    metrics_collection: bool = Field(default=False, description="Enable metrics collection")
    verification_timeout: float = Field(default=5.0, description="Verification timeout")
    essential_checks_only: bool = Field(default=False, description="Run only essential checks")
    skip_complex_verification: bool = Field(default=False, description="Skip complex verification")


class AppSettings(BaseModel):
    """Main application settings - aggregates all other settings"""

    # Environment
    environment: str = Field(default_factory=lambda: os.getenv("TRADING_ENV", "development"), description="Application environment")

    # Core components
    database: DatabaseSettings = Field(default_factory=DatabaseSettings, description="Database settings")
    brokers: BrokerSettings = Field(default_factory=BrokerSettings, description="Broker settings")
    scanners: ScannerSettings = Field(default_factory=ScannerSettings, description="Scanner settings")
    analytics: AnalyticsSettings = Field(default_factory=AnalyticsSettings, description="Analytics settings")

    # Interface components
    api: APISettings = Field(default_factory=APISettings, description="API settings")
    cli: CLISettings = Field(default_factory=CLISettings, description="CLI settings")
    dashboard: DashboardSettings = Field(default_factory=DashboardSettings, description="Dashboard settings")
    websocket: WebSocketSettings = Field(default_factory=WebSocketSettings, description="WebSocket settings")

    # Performance
    performance: PerformanceSettings = Field(default_factory=PerformanceSettings, description="Performance settings")

    # Application metadata
    name: str = Field(default="Trading System", description="Application name")
    version: str = Field(default="2.0.0", description="Application version")
    description: str = Field(default="Unified Trading System with CQRS Architecture", description="Application description")

    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment"""
        valid_environments = ["development", "staging", "production", "testing"]
        if v.lower() not in valid_environments:
            raise ValueError(f"Environment must be one of: {', '.join(valid_environments)}")
        return v.lower()

    def get_service_url(self, service: str) -> str:
        """
        Get service URL for a given service

        Args:
            service: Service name (api, dashboard, websocket)

        Returns:
            Service URL
        """
        if service == "api":
            return f"http://{self.api.host}:{self.api.port}"
        elif service == "dashboard":
            return f"http://{self.dashboard.host}:{self.dashboard.port}"
        elif service == "websocket":
            return f"ws://{self.websocket.host}:{self.websocket.port}"
        else:
            raise ValueError(f"Unknown service: {service}")

    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == "development"

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == "production"

    def get_log_level(self) -> str:
        """Get appropriate log level for environment"""
        if self.environment == "production":
            return "WARNING"
        elif self.environment == "testing":
            return "DEBUG"
        else:
            return "INFO"
