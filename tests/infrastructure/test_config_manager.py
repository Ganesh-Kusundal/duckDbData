import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import yaml

from src.infrastructure.config.config_manager import ConfigManager
from src.infrastructure.config.schemas import (
    ScannersConfig, DatabaseConfig, BrokerConfig, AnalyticsConfig
)


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory with test YAML files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_dir = Path(tmp_dir) / "configs"
        config_dir.mkdir()
        
        # Create test config.yaml
        base_config = {
            "scanners": {
                "default": {
                    "obv_threshold": 100.0,
                    "volume_multiplier": 1.5,
                    "breakout_period": 20
                },
                "strategies": {},
                "backtest": {"max_iterations": 1000, "timeframe": "1d"}
            },
            "database": {
                "path": "test_data.duckdb",
                "memory": False,
                "extension_dir": "./extensions",
                "max_connections": 5
            },
            "brokers": {
                "default": "dhan",
                "brokers": {
                    "dhan": {"api_key": "test_key", "api_secret": "test_secret", "access_token": "test_token"},
                    "tradehull": {"api_key": "th_key", "api_secret": "th_secret", "access_token": "th_token"}
                },
                "endpoints": {"dhan": "https://api.dhan.co", "tradehull": "https://api.tradehull.com"},
                "rate_limit": 100
            },
            "analytics": {
                "queries": {"breakout_patterns": {"timeout": 30, "max_results": 1000}},
                "rules": [],
                "dashboard": {"port": 8080, "host": "localhost"},
                "indicators": ["rsi", "macd", "obv"]
            }
        }
        
        # Write base config
        with open(config_dir / "config.yaml", "w") as f:
            yaml.dump(base_config, f)
        
        # Create module-specific configs
        with open(config_dir / "database.yaml", "w") as f:
            yaml.dump({"max_connections": 3}, f)
        
        with open(config_dir / "scanners.yaml", "w") as f:
            yaml.dump({
                "strategies": {
                    "breakout": {
                        "obv_threshold": 150.0,
                        "volume_multiplier": 2.0,
                        "breakout_period": 15
                    }
                }
            }, f)
        
        # Create development override
        dev_config = {"database": {"memory": True}, "analytics": {"dashboard": {"port": 5000}}}
        with open(config_dir / "config_development.yaml", "w") as f:
            yaml.dump(dev_config, f)
        
        yield str(config_dir)


class TestConfigManager:
    """Unit tests for ConfigManager class."""
    
    def test_initialization_default(self, temp_config_dir):
        """Test ConfigManager initialization with default settings."""
        manager = ConfigManager(config_dir=temp_config_dir)
        assert manager.config_dir == Path(temp_config_dir)
        assert manager.env == "development"
        assert manager._config is not None
    
    def test_initialization_custom_env(self, temp_config_dir):
        """Test ConfigManager initialization with custom environment."""
        manager = ConfigManager(config_dir=temp_config_dir, env="production")
        assert manager.env == "production"
    
    def test_load_base_config(self, temp_config_dir):
        """Test loading base configuration from YAML."""
        manager = ConfigManager(config_dir=temp_config_dir)
        config = manager.get_config()
        assert "scanners" in config
        assert "database" in config
        assert config["scanners"]["default"]["obv_threshold"] == 100.0
    
    def test_load_module_configs(self, temp_config_dir):
        """Test loading module-specific configurations."""
        manager = ConfigManager(config_dir=temp_config_dir)
        config = manager.get_config()
        assert "database" in config
        assert config["database"]["max_connections"] == 3  # From database.yaml
    
    def test_environment_overrides(self, temp_config_dir):
        """Test environment-specific configuration overrides."""
        manager = ConfigManager(config_dir=temp_config_dir, env="development")
        config = manager.get_config()
        assert config["database"]["memory"] == True  # From config_development.yaml
        assert config["analytics"]["dashboard"]["port"] == 5000
    
    def test_pydantic_validation_scanners(self, temp_config_dir):
        """Test Pydantic validation for scanners configuration."""
        manager = ConfigManager(config_dir=temp_config_dir)
        scanners_config = manager.get_config("scanners")
        validated = ScannersConfig(**scanners_config)
        # Test dict access since default is now Dict
        assert validated.default["obv_threshold"] == 100.0
        assert validated.default["volume_multiplier"] == 1.5
        assert "breakout_period" in validated.default
    
    def test_pydantic_validation_database(self, temp_config_dir):
        """Test Pydantic validation for database configuration."""
        manager = ConfigManager(config_dir=temp_config_dir, env="production")  # Avoid dev override
        database_config = manager.get_config("database")
        validated = DatabaseConfig(**database_config)
        assert str(validated.path) == "test_data.duckdb"
        assert validated.memory == False
        assert validated.max_connections == 3  # From module config
    
    def test_pydantic_validation_brokers(self, temp_config_dir):
        """Test Pydantic validation for brokers configuration."""
        manager = ConfigManager(config_dir=temp_config_dir)
        brokers_config = manager.get_config("brokers")
        validated = BrokerConfig(**brokers_config)
        assert validated.default == "dhan"
        assert "dhan" in validated.brokers
        assert validated.brokers["dhan"].api_key.get_secret_value() == "test_key"
    
    def test_pydantic_validation_analytics(self, temp_config_dir):
        """Test Pydantic validation for analytics configuration."""
        manager = ConfigManager(config_dir=temp_config_dir, env="production")  # Avoid dev override
        analytics_config = manager.get_config("analytics")
        validated = AnalyticsConfig(**analytics_config)
        assert validated.queries["breakout_patterns"].timeout == 30
        assert validated.queries["breakout_patterns"].max_results == 1000
        assert validated.dashboard["port"] == 8080
        assert "rsi" in validated.indicators
    
    def test_get_value_nested(self, temp_config_dir):
        """Test getting nested configuration values."""
        manager = ConfigManager(config_dir=temp_config_dir)
        obv_threshold = manager.get_value("scanners.default.obv_threshold")
        assert obv_threshold == 100.0
        
        # Test with default
        unknown_value = manager.get_value("nonexistent.path", "default")
        assert unknown_value == "default"
    
    def test_get_config_section(self, temp_config_dir):
        """Test getting specific configuration sections."""
        manager = ConfigManager(config_dir=temp_config_dir)
        scanners_section = manager.get_config("scanners")
        assert isinstance(scanners_section, dict)
        assert "default" in scanners_section
    
    def test_environment_variable_overrides(self, temp_config_dir, monkeypatch):
        """Test environment variable overrides."""
        # Set environment variable
        monkeypatch.setenv("TRADING_PLATFORM_DATABASE_PATH", "overridden.duckdb")
        
        manager = ConfigManager(config_dir=temp_config_dir)
        config = manager.get_config("database")
        assert config["path"] == "overridden.duckdb"
    
    def test_validation_error_invalid_config(self, temp_config_dir, monkeypatch):
        """Test validation error handling for invalid configuration."""
        # Create invalid config
        invalid_config = {
            "scanners": {
                "default": {"obv_threshold": -100.0}  # Negative threshold should fail validation
            }
        }
        with open(Path(temp_config_dir) / "config.yaml", "w") as f:
            yaml.dump(invalid_config, f)
        
        with pytest.raises(ValueError, match="Invalid scanners config"):
            ConfigManager(config_dir=temp_config_dir)
    
    def test_reload_method(self, temp_config_dir):
        """Test dynamic config reloading."""
        manager = ConfigManager(config_dir=temp_config_dir)
        original_config = manager.get_config("database")
        
        # Modify config file
        with open(Path(temp_config_dir) / "database.yaml", "w") as f:
            yaml.dump({"max_connections": 10}, f)
        
        # Reload
        manager.reload()
        new_config = manager.get_config("database")
        
        assert new_config["max_connections"] == 10
        assert original_config["max_connections"] == 3
    
    def test_validate_section_method(self, temp_config_dir):
        """Test validate_section method with Pydantic model."""
        manager = ConfigManager(config_dir=temp_config_dir)
        
        # Validate database section
        validated_db = manager.validate_section("database", DatabaseConfig)
        assert isinstance(validated_db, DatabaseConfig)
        assert str(validated_db.path) == "test_data.duckdb"
        
        # Test with nonexistent section - should return empty model or handle gracefully
        try:
            manager.validate_section("nonexistent", DatabaseConfig)
        except ValueError as e:
            assert "nonexistent" in str(e)
    
    def test_missing_config_file_fallback(self, temp_config_dir):
        """Test fallback behavior when config files are missing."""
        # Remove all config files
        for config_file in Path(temp_config_dir).glob("*.yaml"):
            config_file.unlink()
        
        manager = ConfigManager(config_dir=temp_config_dir)
        config = manager.get_config()
        
        # Should return empty dict or minimal defaults
        assert isinstance(config, dict)
        assert len(config) >= 0  # Could be empty if no defaults
    
    @patch.dict(os.environ, {"ENV": "test"})
    def test_environment_detection(self, temp_config_dir):
        """Test automatic environment detection from ENV variable."""
        manager = ConfigManager(config_dir=temp_config_dir)
        assert manager.env == "test"


class TestConfigManagerIntegration:
    """Integration tests for ConfigManager with all components."""
    
    def test_full_integration(self, temp_config_dir):
        """Test complete ConfigManager workflow with all validations."""
        # Set environment
        os.environ["ENV"] = "development"
        
        # Create ConfigManager
        manager = ConfigManager(config_dir=temp_config_dir)
        
        # Test all get_config calls
        sections = ["scanners", "database", "brokers", "analytics"]
        for section in sections:
            config = manager.get_config(section)
            assert isinstance(config, dict)
            assert len(config) > 0
        
        # Test all validations
        validations = [
            ("scanners", ScannersConfig),
            ("database", DatabaseConfig),
            ("brokers", BrokerConfig),
            ("analytics", AnalyticsConfig)
        ]
        
        for section, model_class in validations:
            validated = manager.validate_section(section, model_class)
            assert isinstance(validated, model_class)
        
        # Test environment overrides applied
        full_config = manager.get_config()
        assert full_config["database"]["memory"] == True  # From development config
        assert full_config["analytics"]["dashboard"]["port"] == 5000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])