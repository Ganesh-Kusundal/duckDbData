from typing import Dict, Any, Optional
from pathlib import Path
import os
import yaml
from pydantic import ValidationError

from .schemas import ScannersConfig, DatabaseConfig, BrokerConfig, AnalyticsConfig, ScannerThresholds

class ConfigManager:
    def __init__(self, config_dir: str = "configs", env: str = None):
        self.config_dir = Path(config_dir)
        self.env = env or os.getenv("ENV", "development")
        self._config: Optional[Dict[str, Any]] = None
        self._load_config()
    
    def _load_config(self):
        """Load and merge configs hierarchically."""
        base_config = self._load_yaml("config.yaml")
        env_config_path = self.config_dir / f"config_{self.env}.yaml"
        env_config = self._load_yaml(f"config_{self.env}.yaml") if env_config_path.exists() else {}
        module_configs = self._load_module_configs()
        
        # Merge with overrides: global -> module -> env (recursive merge)
        self._config = self._deep_merge(base_config, module_configs)
        self._config = self._deep_merge(self._config, env_config)
        
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
    
    def _deep_merge(self, base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge two dictionaries, with overrides taking precedence."""
        merged = base.copy()
        for key, value in overrides.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged
    
    def _validate_config(self):
        """Validate the entire config or sections using Pydantic models."""
        # Validate scanners section - validate threshold dicts directly
        if "scanners" in self._config:
            try:
                scanners_data = self._config["scanners"]
                # Validate default thresholds
                if "default" in scanners_data:
                    ScannerThresholds(**scanners_data["default"])
                # Validate strategy thresholds
                for strategy_name, strategy_config in scanners_data.get("strategies", {}).items():
                    ScannerThresholds(**strategy_config)
            except ValidationError as e:
                raise ValueError(f"Invalid scanners config: {e}")
        
        # Validate database section
        if "database" in self._config:
            try:
                DatabaseConfig(**self._config["database"])
            except ValidationError as e:
                raise ValueError(f"Invalid database config: {e}")
        
        # Validate brokers section
        if "brokers" in self._config:
            try:
                BrokerConfig(**self._config["brokers"])
            except ValidationError as e:
                raise ValueError(f"Invalid brokers config: {e}")
        
        # Validate analytics section
        if "analytics" in self._config:
            try:
                AnalyticsConfig(**self._config["analytics"])
            except ValidationError as e:
                raise ValueError(f"Invalid analytics config: {e}")
    
    def get_config(self, section: str = None) -> Dict[str, Any]:
        """Get config section or full config."""
        if section:
            return self._config.get(section, {}).copy()
        return self._config.copy()
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get nested value, e.g., 'database.path'."""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
            if value is None:
                return default
        return value
    
    def reload(self):
        """Reload configs dynamically."""
        self._load_config()
    
    def validate_section(self, section: str, model_class):
        """Validate a specific section with a Pydantic model."""
        section_config = self.get_config(section)
        try:
            return model_class(**section_config)
        except ValidationError as e:
            raise ValueError(f"Invalid config for {section}: {e}")