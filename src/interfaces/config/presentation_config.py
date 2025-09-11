"""
Presentation Layer Configuration

Centralized configuration management for all presentation interfaces:
- API server settings
- CLI options
- Dashboard settings
- WebSocket configuration
- Health monitoring
- Cross-service settings
"""

import os
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import yaml

from pydantic import BaseModel, Field, validator


class APISettings(BaseModel):
    """API server configuration."""
    host: str = Field(default="0.0.0.0", description="API server host")
    port: int = Field(default=8000, description="API server port")
    enable_docs: bool = Field(default=True, description="Enable API documentation")
    enable_redoc: bool = Field(default=True, description="Enable ReDoc documentation")
    reload: bool = Field(default=False, description="Enable auto-reload for development")
    workers: int = Field(default=1, description="Number of worker processes")
    cors_origins: List[str] = Field(default_factory=lambda: ["*"], description="CORS allowed origins")
    cors_credentials: bool = Field(default=True, description="CORS allow credentials")
    rate_limit: str = Field(default="100/minute", description="API rate limiting")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    log_level: str = Field(default="INFO", description="API logging level")


class CLISettings(BaseModel):
    """CLI configuration."""
    enable_completion: bool = Field(default=True, description="Enable shell completion")
    rich_output: bool = Field(default=True, description="Enable rich text output")
    max_table_rows: int = Field(default=100, description="Maximum rows in table output")
    table_style: str = Field(default="blue", description="Table style for rich output")
    progress_style: str = Field(default="blue", description="Progress bar style")
    spinner_style: str = Field(default="dots", description="Spinner style")
    log_level: str = Field(default="INFO", description="CLI logging level")


class DashboardSettings(BaseModel):
    """Dashboard configuration."""
    host: str = Field(default="0.0.0.0", description="Dashboard server host")
    port: int = Field(default=8080, description="Dashboard server port")
    reload: bool = Field(default=False, description="Enable auto-reload for development")
    static_dir: Optional[str] = Field(default=None, description="Static files directory")
    template_dir: Optional[str] = Field(default=None, description="Template files directory")
    theme: str = Field(default="dark", description="Dashboard theme")
    refresh_interval: int = Field(default=30, description="Data refresh interval in seconds")
    enable_auth: bool = Field(default=False, description="Enable authentication")
    session_timeout: int = Field(default=3600, description="Session timeout in seconds")
    log_level: str = Field(default="INFO", description="Dashboard logging level")


class WebSocketSettings(BaseModel):
    """WebSocket server configuration."""
    host: str = Field(default="0.0.0.0", description="WebSocket server host")
    port: int = Field(default=8081, description="WebSocket server port")
    reload: bool = Field(default=False, description="Enable auto-reload for development")
    ping_interval: int = Field(default=30, description="Ping interval in seconds")
    ping_timeout: int = Field(default=10, description="Ping timeout in seconds")
    max_connections: int = Field(default=1000, description="Maximum concurrent connections")
    message_queue_size: int = Field(default=1000, description="Message queue size")
    enable_compression: bool = Field(default=True, description="Enable message compression")
    heartbeat_interval: int = Field(default=60, description="Heartbeat interval in seconds")
    log_level: str = Field(default="INFO", description="WebSocket logging level")


class HealthSettings(BaseModel):
    """Health monitoring configuration."""
    enabled: bool = Field(default=True, description="Enable health monitoring")
    check_interval: int = Field(default=60, description="Health check interval in seconds")
    timeout: int = Field(default=10, description="Health check timeout in seconds")
    failure_threshold: int = Field(default=3, description="Failure threshold for alerts")
    recovery_threshold: int = Field(default=2, description="Recovery threshold")
    alert_enabled: bool = Field(default=False, description="Enable health alerts")
    alert_webhook: Optional[str] = Field(default=None, description="Alert webhook URL")
    alert_email: Optional[str] = Field(default=None, description="Alert email address")


class MetricsSettings(BaseModel):
    """Metrics collection configuration."""
    enabled: bool = Field(default=True, description="Enable metrics collection")
    collection_interval: int = Field(default=60, description="Metrics collection interval")
    retention_days: int = Field(default=30, description="Metrics retention period")
    enable_prometheus: bool = Field(default=False, description="Enable Prometheus metrics")
    prometheus_port: int = Field(default=9090, description="Prometheus metrics port")
    enable_statsd: bool = Field(default=False, description="Enable StatsD metrics")
    statsd_host: str = Field(default="localhost", description="StatsD host")
    statsd_port: int = Field(default=8125, description="StatsD port")


class SecuritySettings(BaseModel):
    """Security configuration."""
    enable_ssl: bool = Field(default=False, description="Enable SSL/TLS")
    ssl_cert_path: Optional[str] = Field(default=None, description="SSL certificate path")
    ssl_key_path: Optional[str] = Field(default=None, description="SSL key path")
    enable_auth: bool = Field(default=False, description="Enable authentication")
    auth_provider: str = Field(default="local", description="Authentication provider")
    jwt_secret: Optional[str] = Field(default=None, description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    session_secret: Optional[str] = Field(default=None, description="Session secret")
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Rate limit requests per window")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")


class UnifiedPresentationConfig(BaseModel):
    """Unified presentation layer configuration."""
    version: str = Field(default="2.0.0", description="Configuration version")

    # Service configurations
    api: APISettings = Field(default_factory=APISettings)
    cli: CLISettings = Field(default_factory=CLISettings)
    dashboard: DashboardSettings = Field(default_factory=DashboardSettings)
    websocket: WebSocketSettings = Field(default_factory=WebSocketSettings)

    # Cross-service configurations
    health: HealthSettings = Field(default_factory=HealthSettings)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    # Global settings
    environment: str = Field(default="development", description="Environment (development/production)")
    log_level: str = Field(default="INFO", description="Global log level")
    enable_all_services: bool = Field(default=True, description="Enable all services by default")
    shutdown_timeout: int = Field(default=30, description="Shutdown timeout in seconds")

    # Service selection
    enabled_services: List[str] = Field(
        default_factory=lambda: ["api", "cli", "dashboard", "websocket"],
        description="Enabled presentation services"
    )

    @validator('enabled_services')
    def validate_enabled_services(cls, v):
        """Validate enabled services."""
        valid_services = {"api", "cli", "dashboard", "websocket"}
        invalid_services = set(v) - valid_services
        if invalid_services:
            raise ValueError(f"Invalid services: {invalid_services}")
        return v

    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment."""
        if v not in {"development", "staging", "production"}:
            raise ValueError(f"Invalid environment: {v}")
        return v


class PresentationConfigManager:
    """
    Configuration manager for presentation layer.

    Handles loading, validation, and management of presentation configurations.
    """

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._find_config_file()
        self.config: Optional[UnifiedPresentationConfig] = None
        self._load_config()

    def _find_config_file(self) -> str:
        """Find configuration file in standard locations."""
        search_paths = [
            Path.cwd() / "config" / "presentation.yaml",
            Path.cwd() / "config" / "presentation.yml",
            Path.cwd() / "config" / "presentation.json",
            Path.cwd() / "presentation.yaml",
            Path.cwd() / "presentation.yml",
            Path.cwd() / "presentation.json",
            Path.cwd() / ".presentation.yaml",
            Path.cwd() / ".presentation.yml",
            Path.cwd() / ".presentation.json",
        ]

        for path in search_paths:
            if path.exists():
                return str(path)

        # Return default path if no config file found
        return "config/presentation.yaml"

    def _load_config(self):
        """Load configuration from file."""
        try:
            if not Path(self.config_file).exists():
                # Create default configuration
                self.config = UnifiedPresentationConfig()
                self.save_config()
                return

            with open(self.config_file, 'r', encoding='utf-8') as f:
                if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                    config_data = yaml.safe_load(f) or {}
                elif self.config_file.endswith('.json'):
                    config_data = json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {self.config_file}")

            self.config = UnifiedPresentationConfig(**config_data)

        except Exception as e:
            print(f"Warning: Failed to load config from {self.config_file}: {e}")
            print("Using default configuration...")
            self.config = UnifiedPresentationConfig()

    def save_config(self):
        """Save current configuration to file."""
        try:
            config_path = Path(self.config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            config_data = self.config.dict()

            with open(self.config_file, 'w', encoding='utf-8') as f:
                if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                elif self.config_file.endswith('.json'):
                    json.dump(config_data, f, indent=2)
                else:
                    raise ValueError(f"Unsupported config file format: {self.config_file}")

        except Exception as e:
            raise RuntimeError(f"Failed to save config to {self.config_file}: {e}")

    def get_config(self) -> UnifiedPresentationConfig:
        """Get current configuration."""
        return self.config

    def update_config(self, updates: Dict[str, Any]):
        """Update configuration with new values."""
        config_dict = self.config.dict()
        self._deep_update(config_dict, updates)
        self.config = UnifiedPresentationConfig(**config_dict)
        self.save_config()

    def _deep_update(self, base_dict: Dict[str, Any], update_dict: Dict[str, Any]):
        """Deep update dictionary."""
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def create_development_config(self) -> UnifiedPresentationConfig:
        """Create development configuration."""
        return UnifiedPresentationConfig(
            environment="development",
            log_level="DEBUG",
            api=APISettings(
                host="127.0.0.1",
                port=8000,
                reload=True,
                enable_docs=True
            ),
            dashboard=DashboardSettings(
                host="127.0.0.1",
                port=8080,
                reload=True
            ),
            websocket=WebSocketSettings(
                host="127.0.0.1",
                port=8081,
                reload=True
            ),
            health=HealthSettings(enabled=True),
            metrics=MetricsSettings(enabled=True)
        )

    def create_production_config(self) -> UnifiedPresentationConfig:
        """Create production configuration."""
        return UnifiedPresentationConfig(
            environment="production",
            log_level="WARNING",
            api=APISettings(
                host="0.0.0.0",
                port=8000,
                reload=False,
                enable_docs=False,
                workers=4
            ),
            dashboard=DashboardSettings(
                host="0.0.0.0",
                port=8080,
                reload=False,
                enable_auth=True
            ),
            websocket=WebSocketSettings(
                host="0.0.0.0",
                port=8081,
                reload=False,
                max_connections=5000
            ),
            security=SecuritySettings(
                enable_ssl=True,
                enable_auth=True,
                enable_rate_limiting=True
            ),
            health=HealthSettings(
                enabled=True,
                alert_enabled=True
            ),
            metrics=MetricsSettings(
                enabled=True,
                enable_prometheus=True
            )
        )

    def validate_config(self) -> List[str]:
        """Validate current configuration."""
        errors = []

        # Check service ports don't conflict
        ports = {}
        if "api" in self.config.enabled_services:
            ports[self.config.api.port] = "api"
        if "dashboard" in self.config.enabled_services:
            ports[self.config.dashboard.port] = "dashboard"
        if "websocket" in self.config.enabled_services:
            ports[self.config.websocket.port] = "websocket"

        port_conflicts = {}
        for port, service in ports.items():
            if port in port_conflicts:
                port_conflicts[port].append(service)
            else:
                port_conflicts[port] = [service]

        for port, services in port_conflicts.items():
            if len(services) > 1:
                errors.append(f"Port {port} is used by multiple services: {', '.join(services)}")

        # Check SSL configuration
        if self.config.security.enable_ssl:
            if not self.config.security.ssl_cert_path:
                errors.append("SSL enabled but ssl_cert_path not configured")
            if not self.config.security.ssl_key_path:
                errors.append("SSL enabled but ssl_key_path not configured")

        # Check authentication configuration
        if self.config.security.enable_auth and not self.config.security.jwt_secret:
            errors.append("Authentication enabled but jwt_secret not configured")

        return errors

    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """Get configuration for specific service."""
        if service_name == "api":
            return self.config.api.dict()
        elif service_name == "cli":
            return self.config.cli.dict()
        elif service_name == "dashboard":
            return self.config.dashboard.dict()
        elif service_name == "websocket":
            return self.config.websocket.dict()
        else:
            raise ValueError(f"Unknown service: {service_name}")

    def print_config_summary(self):
        """Print configuration summary."""
        print("📋 PRESENTATION CONFIGURATION SUMMARY")
        print("=" * 50)
        print(f"Environment: {self.config.environment}")
        print(f"Version: {self.config.version}")
        print(f"Log Level: {self.config.log_level}")
        print()

        print("🛠️  ENABLED SERVICES:")
        for service in self.config.enabled_services:
            print(f"  ✅ {service}")
        print()

        if "api" in self.config.enabled_services:
            api = self.config.api
            print("🌐 API SERVICE:"            print(f"  Host: {api.host}:{api.port}")
            print(f"  Docs: {'enabled' if api.enable_docs else 'disabled'}")
            print(f"  Reload: {'enabled' if api.reload else 'disabled'}")
            print()

        if "dashboard" in self.config.enabled_services:
            dash = self.config.dashboard
            print("🖥️  DASHBOARD SERVICE:"            print(f"  Host: {dash.host}:{dash.port}")
            print(f"  Theme: {dash.theme}")
            print(f"  Auth: {'enabled' if dash.enable_auth else 'disabled'}")
            print()

        if "websocket" in self.config.enabled_services:
            ws = self.config.websocket
            print("🔌 WEBSOCKET SERVICE:"            print(f"  Host: {ws.host}:{ws.port}")
            print(f"  Max Connections: {ws.max_connections}")
            print(f"  Compression: {'enabled' if ws.enable_compression else 'disabled'}")
            print()

        health = self.config.health
        print("🏥 HEALTH MONITORING:"        print(f"  Enabled: {health.enabled}")
        if health.enabled:
            print(f"  Check Interval: {health.check_interval}s")
            print(f"  Alerting: {'enabled' if health.alert_enabled else 'disabled'}")
        print()

        metrics = self.config.metrics
        print("📊 METRICS COLLECTION:"        print(f"  Enabled: {metrics.enabled}")
        if metrics.enabled:
            print(f"  Collection Interval: {metrics.collection_interval}s")
            print(f"  Prometheus: {'enabled' if metrics.enable_prometheus else 'disabled'}")
        print()

        security = self.config.security
        print("🔒 SECURITY:"        print(f"  SSL: {'enabled' if security.enable_ssl else 'disabled'}")
        print(f"  Authentication: {'enabled' if security.enable_auth else 'disabled'}")
        print(f"  Rate Limiting: {'enabled' if security.enable_rate_limiting else 'disabled'}")

        # Validation errors
        errors = self.validate_config()
        if errors:
            print("\n⚠️  CONFIGURATION ISSUES:")
            for error in errors:
                print(f"  ❌ {error}")


# Global configuration manager instance
_config_manager: Optional[PresentationConfigManager] = None


def get_config_manager(config_file: Optional[str] = None) -> PresentationConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = PresentationConfigManager(config_file)
    return _config_manager


def reset_config_manager():
    """Reset global configuration manager (mainly for testing)."""
    global _config_manager
    _config_manager = None


def load_config_from_env() -> UnifiedPresentationConfig:
    """Load configuration from environment variables."""
    config = UnifiedPresentationConfig()

    # API settings from environment
    config.api.host = os.getenv("API_HOST", config.api.host)
    config.api.port = int(os.getenv("API_PORT", config.api.port))
    config.api.enable_docs = os.getenv("API_ENABLE_DOCS", str(config.api.enable_docs)).lower() == "true"

    # Dashboard settings from environment
    config.dashboard.host = os.getenv("DASHBOARD_HOST", config.dashboard.host)
    config.dashboard.port = int(os.getenv("DASHBOARD_PORT", config.dashboard.port))

    # WebSocket settings from environment
    config.websocket.host = os.getenv("WEBSOCKET_HOST", config.websocket.host)
    config.websocket.port = int(os.getenv("WEBSOCKET_PORT", config.websocket.port))

    # Global settings from environment
    config.environment = os.getenv("ENVIRONMENT", config.environment)
    config.log_level = os.getenv("LOG_LEVEL", config.log_level)

    return config
