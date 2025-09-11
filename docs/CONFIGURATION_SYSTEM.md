# 🔧 Configuration System Documentation

## Overview

The DuckDB Financial Infrastructure now includes a comprehensive, centralized configuration system that allows easy customization of all system parameters without code changes.

## 🎯 Key Features

- **Centralized YAML Configuration**: All parameters in `configs/scanners.yaml`
- **Runtime Configuration Updates**: Change settings while system is running
- **Type-Safe Access**: Proper validation and error handling
- **Automatic Persistence**: Changes saved automatically to disk
- **Easy Parameter Tuning**: Modify cutoff times, thresholds, etc. instantly

## 📁 Configuration Files

### Primary Configuration File: `configs/scanners.yaml`

```yaml
# Rule-based backtesting configuration
rules:
  # Signal generation timing
  cutoff_time: "09:45"
  signal_time_window_start: "09:15"
  signal_time_window_end: "09:45"

  # Performance measurement timing
  performance_start_time: "09:45"
  performance_end_time: "15:15"

  # Breakout rule defaults
  breakout:
    volume_multiplier_min: 1.2
    volume_multiplier_max: 3.0
    price_move_pct_min: 0.5
    price_move_pct_max: 5.0
    breakout_strength_threshold: 2.0
    time_window_minutes: 30
    volume_comparison_period: 10
    min_price: 50
    max_price: 10000
    min_volume: 1000

  # CRP rule defaults
  crp:
    close_threshold_pct: 2.0
    range_threshold_pct: 3.0
    consolidation_period: 5
    min_price: 50
    max_price: 10000
    min_volume: 1000

  # Technical rule defaults
  technical:
    rsi_oversold: 30
    rsi_overbought: 70
    macd_threshold: 0.1
    bb_deviation: 1.5
    min_price: 50
    max_price: 10000
    min_volume: 1000

  # Volume rule defaults
  volume:
    volume_multiplier_min: 1.5
    volume_multiplier_max: 5.0
    min_price: 50
    max_price: 10000
    min_volume: 1000

  # Backtesting parameters
  backtesting:
    max_parallel_rules: 4
    database_connection_pool: true
    query_cache_enabled: true
    query_cache_ttl: 300
    performance_monitoring: true
    metrics_collection: true

  # Optimization parameters
  optimization:
    default_algorithm: "grid_search"
    max_evaluations: 50
    parallel_workers: 2
    train_validation_split: 0.7
    fitness_metric: "intraday_win_rate"
    early_stopping_threshold: 0.001
```

## 🔧 Configuration Management

### Python API Usage

```python
from src.rules.config.rule_config import get_rule_config

# Get configuration instance
config = get_rule_config()

# Access configuration values
cutoff_time = config.get_cutoff_time()  # "09:45"
volume_min = config.get_breakout_volume_multiplier_min()  # 1.2
max_price = config.get_breakout_max_price()  # 10000

# Modify configuration at runtime
config.set_config_value('cutoff_time', '09:30')
config.set_config_value('breakout.volume_multiplier_min', 1.5)

# Save changes to disk
config.save_config()
```

### Direct YAML Editing

Edit `configs/scanners.yaml` directly:

```yaml
# Change cutoff time
cutoff_time: "09:30"

# Adjust breakout parameters
breakout:
  volume_multiplier_min: 1.5
  price_move_pct_min: 0.3
```

## 📊 Configurable Parameters

### Timing Parameters
- `cutoff_time`: Signal generation cutoff time (default: "09:45")
- `signal_time_window_start`: Start of signal scanning window
- `signal_time_window_end`: End of signal scanning window
- `performance_start_time`: When to start measuring performance
- `performance_end_time`: When to end measuring performance

### Rule Parameters
- **Breakout Rules**: Volume multipliers, price move thresholds, time windows
- **CRP Rules**: Close thresholds, consolidation periods, range thresholds
- **Technical Rules**: RSI levels, MACD thresholds, Bollinger Band settings
- **Volume Rules**: Volume multiplier ranges, price/volume filters

### System Parameters
- **Backtesting**: Parallel processing, caching, monitoring settings
- **Optimization**: Algorithm selection, evaluation limits, validation splits

## 🚀 Usage Examples

### Change Cutoff Time
```python
config = get_rule_config()
config.set_config_value('cutoff_time', '09:30')
config.save_config()
# Now all rules use 09:30 as cutoff time
```

### Adjust Breakout Sensitivity
```python
config.set_config_value('breakout.volume_multiplier_min', 1.1)
config.set_config_value('breakout.price_move_pct_min', 0.3)
config.save_config()
# Rules now trigger on smaller volume/price movements
```

### Configure Optimization
```python
config.set_config_value('optimization.max_evaluations', 100)
config.set_config_value('optimization.parallel_workers', 4)
config.save_config()
# Optimization runs longer with more parallel workers
```

## 🔍 Configuration Validation

The system includes automatic validation:

- **Type Checking**: Ensures parameters are correct types
- **Range Validation**: Validates parameter values are within acceptable ranges
- **Dependency Checking**: Ensures related parameters are consistent
- **Error Handling**: Graceful handling of invalid configurations

## 📈 Benefits

1. **Easy Tuning**: Adjust parameters without code changes
2. **Experimentation**: Quickly test different parameter combinations
3. **Production Safety**: Runtime changes without restarts
4. **Version Control**: Configuration changes tracked in git
5. **Documentation**: Self-documenting parameter names and defaults

## 🛠️ Implementation Details

### Configuration Classes

- `RuleConfig`: Main configuration manager class
- `get_rule_config()`: Global configuration instance getter
- `reload_rule_config()`: Reload configuration from disk

### Integration Points

- **Query Builder**: Uses `config.get_cutoff_time_obj()` for time filtering
- **Rule Templates**: Initialize with `config.get_breakout_*()` methods
- **Backtester**: Configures time windows from configuration
- **Optimizer**: Uses configured algorithm and evaluation parameters

### File Structure

```
configs/
├── scanners.yaml          # Main configuration file
└── ...

src/rules/config/
├── rule_config.py         # Configuration manager
└── ...

# Integration throughout codebase
src/rules/engine/query_builder.py     # Uses cutoff_time
src/rules/templates/breakout_rules.py # Uses rule parameters
scanner/backtesting/rule_backtester.py # Uses timing config
```

## 🎯 Best Practices

1. **Test Changes**: Always test configuration changes in development
2. **Backup Configs**: Keep backups of working configurations
3. **Document Changes**: Comment why specific values were chosen
4. **Version Control**: Track configuration changes in git
5. **Gradual Changes**: Make small adjustments and test incrementally

## 🔄 Runtime Configuration

The system supports runtime configuration updates:

```python
# Load current config
config = get_rule_config()

# Make changes
config.set_config_value('cutoff_time', '09:40')

# Apply changes immediately (no restart needed)
config.save_config()

# All subsequent rule executions use new cutoff time
```

This enables dynamic parameter tuning during backtesting and optimization without interrupting the workflow.
