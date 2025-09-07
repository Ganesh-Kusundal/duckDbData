# Configuration Migration Plan

## Overview

This plan outlines the steps to migrate from the current scattered configuration approach (e.g., hardcoded values in [`settings.py`](src/infrastructure/config/settings.py), `_get_default_config()` methods in scanners, hardcoded paths in adapters) to the new centralized ConfigManager system. The migration is incremental to minimize disruption, starting with infrastructure components and progressing to application layers. It assumes the ConfigManager and schemas from `config_design.md` are implemented first.

Key principles:
- **Backward Compatibility**: Initial implementation supports legacy config access via fallbacks.
- **Incremental Rollout**: Migrate one module at a time (e.g., database first, then scanners).
- **Testing**: Each step includes validation and unit tests.
- **Rollback**: Keep old config logic commented out during transition.

## Migration Steps

### Step 1: Implement ConfigManager and Schemas (Pre-Migration)
- Create `src/infrastructure/config/config_manager.py` and `schemas.py` based on `config_design.md`.
- Add dependencies: `pip install pydantic pyyaml`.
- Create initial YAML configs: `config.yaml` (global defaults), `config_development.yaml`, module-specific YAMLs (e.g., `database.yaml`, `scanners.yaml`).
- Test: Unit tests for loading, validation, and overrides.

### Step 2: Migrate Infrastructure Configs
- **Database**:
  - Update [`database.py`](src/infrastructure/core/database.py) or relevant files to inject ConfigManager instead of hardcoded `db_path`.
  - Extract current settings from `settings.py` to `database.yaml` (e.g., `path: financial_data.duckdb`).
  - Replace `db_path = "financial_data.duckdb"` with `config_manager.get_value("database.path")`.
  - Update [`DuckDBAdapter`](src/infrastructure/adapters/duckdb_adapter.py): Use `DatabaseConfig` schema for validation.
  - Test: Verify database connections in development environment.

- **Brokers**:
  - Update [`broker_adapter.py`](src/infrastructure/adapters/broker_adapter.py) to load API keys from `brokers.yaml` or ENV vars (e.g., `TRADING_PLATFORM_BROKERS_DHAN_API_KEY`).
  - Move hardcoded endpoints/credentials to `BrokersConfig`.
  - Ensure `SecretStr` handles sensitive data securely.
  - Test: Mock broker connections with config overrides.

### Step 3: Migrate Application Layer (Scanners and Use Cases)
- **BaseScanner**:
  - In [`base_scanner.py`](src/application/scanners/base_scanner.py), replace `_get_default_config()` with `ConfigManager.get_config("scanners")`.
  - Migrate defaults (e.g., thresholds) to `scanners.yaml` and validate with `ScannersConfig`.
  - Update subclasses like [`BreakoutScanner`](src/application/scanners/strategies/breakout_scanner.py:14) to use injected config.
  - Handle overrides for specific strategies (e.g., `strategies.breakout.obv_threshold`).

- **Use Cases**:
  - Inject ConfigManager into [`ScanMarketUseCase`](src/application/use_cases/scan_market.py:48) via dependency injection.
  - Replace any inline configs with `config_manager.get_value("scanners.default.obv_threshold")`.
  - Update `ScannerService` to pass config to scanners.

- **Analytics**:
  - Migrate query params in [`duckdb_connector.py`](analytics/core/duckdb_connector.py) to `AnalyticsConfig`.
  - Update rule engine configs in `rules/` to use `rules.yaml` loaded via ConfigManager.
  - Ensure dashboard settings (port, host) are configurable.

### Step 4: Global Migration and Cleanup
- **settings.py Refactor**:
  - Move all global settings to `config.yaml`.
  - Deprecate `settings.py` functions, redirect to ConfigManager.
  - Remove after full validation.

- **Environment Support**:
  - Set `ENV=development` for local testing.
  - Create `config_production.yaml` for deployment, with ENV vars for secrets.

- **Dynamic Loading**:
  - Implement `ConfigManager.reload()` for hot-reloading in development.
  - Update CLI commands (e.g., `python -m src.cli config reload`).

### Step 5: Testing and Validation
- **Unit Tests**:
  - Test each schema validation (e.g., invalid `obv_threshold` raises `ValidationError`).
  - Mock ConfigManager in scanner/backtester tests.
- **Integration Tests**:
  - End-to-end: Run scan_market with new config, verify outputs match old behavior.
  - Environment tests: Switch between dev/prod configs.
- **Performance**:
  - Benchmark config loading time (<100ms target).
- **Documentation**:
  - Update README.md with config setup instructions.
  - Add examples in `examples/config_example.yaml`.

### Potential Challenges and Mitigations
- **Breaking Changes**: Use versioned configs (e.g., `config_v1.yaml`) during transition.
- **Sensitive Data**: Ensure ENV vars are set in `.env` files (gitignored).
- **Validation Errors**: Add graceful fallbacks to old hardcoded values if schema fails.
- **Dependencies**: Pin Pydantic/YAML versions in requirements.txt.

### Timeline Estimate
- Step 1: 1 day
- Step 2: 2 days
- Step 3: 3 days
- Step 4: 1 day
- Step 5: 2 days
- Total: ~9 days, with parallel testing.

### Rollback Plan
- If issues arise, revert to old `_get_default_config()` methods.
- Keep old code in comments or feature branch.
- Use feature flags (e.g., `USE_NEW_CONFIG = False`) to toggle.

This plan ensures a smooth transition to the centralized configuration system while maintaining system stability.