# Database Integration Plan for Analytics Module

## 🎯 Executive Summary

This document outlines the architectural plan to resolve the analytics module database connectivity issues by integrating with the proven infrastructure database layer. The goal is to ensure seamless connectivity between the analytics components (PatternAnalyzer, DuckDBAnalytics) and the working database infrastructure while maintaining backward compatibility and performance.

## 📋 Current Status

### ✅ Working Components
- **Infrastructure Database Layer**: `src/infrastructure/adapters/duckdb_adapter.py` connects successfully and creates/initializes the database
- **Core Tests**: 77/92 analytics tests pass, confirming pattern discovery logic works
- **Pattern Analysis**: `discover_volume_spike_patterns()` and `discover_time_window_patterns()` tests pass with mocked data

### ❌ Issues to Resolve
- **Analytics Connector Path Resolution**: `analytics/core/duckdb_connector.py` uses incorrect fallback path `../data/financial_data.duckdb`
- **ConfigManager Integration**: Analytics components don't receive ConfigManager instance
- **Module Isolation**: Analytics has separate database logic instead of using shared infrastructure
- **Retry Decorators**: Instance method binding issues (temporarily bypassed)

## 🏗️ Architectural Solution

### Phase 1: Analytics Connector Refactoring

#### 1.1 Replace Custom Connection Logic

**File**: `analytics/core/duckdb_connector.py`

**Current Issue**:
```python
# Lines 41-44 - Incorrect fallback
self.db_path = db_path or "../data/financial_data.duckdb"  # Wrong path
```

**Solution**: Delegate to infrastructure adapter

```python
from src.infrastructure.adapters.duckdb_adapter import DuckDBAdapter
from src.infrastructure.config.config_manager import ConfigManager

class DuckDBAnalytics:
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager
        # Use infrastructure adapter with same config
        self._adapter = DuckDBAdapter(config_manager=config_manager)
        self._connection = None
        
        # Load analytics-specific paths from config
        self.data_paths = self._load_data_paths()
    
    def _load_data_paths(self) -> Dict[str, str]:
        """Load analytics-specific data paths from config."""
        if self.config_manager:
            try:
                analytics_config = self.config_manager.get_config('analytics')
                return {
                    'parquet_base': analytics_config.get('data_paths', {}).get('parquet_base', './data/'),
                    'indicators': analytics_config.get('data_paths', {}).get('indicators', './data/technical_indicators/'),
                    'processed': analytics_config.get('data_paths', {}).get('processed', './data/processed/')
                }
            except Exception as e:
                logger.warning(f"Failed to load analytics config: {e}")
        
        # Fallback paths
        return {
            'parquet_base': './data/',
            'indicators': './data/technical_indicators/',
            'processed': './data/processed/'
        }
```

#### 1.2 Update Connection Methods

**Replace custom connect() with infrastructure delegation**:

```python
def connect(self):
    """Connect using infrastructure adapter."""
    try:
        with self._adapter.get_connection() as conn:
            self._connection = conn
            logger.info(f"Analytics connected via infrastructure adapter")
            return conn
    except Exception as e:
        error_msg = f"Analytics connection failed via infrastructure adapter: {str(e)}"
        context = {'operation': 'connect_analytics', 'config_manager': bool(self.config_manager)}
        exc = DatabaseConnectionError(error_msg, 'connect_analytics', context=context)
        logger.error("Analytics connection failed", extra=exc.to_dict())
        raise exc

def execute_analytics_query(self, query: str, **params) -> pd.DataFrame:
    """Execute analytics query using infrastructure connection."""
    try:
        with self._adapter.get_connection() as conn:
            # Format query with parameters (maintain existing logic)
            formatted_query = query
            for key, value in params.items():
                if isinstance(value, str):
                    formatted_query = formatted_query.replace(f"{{{key}}}", f"'{value}'")
                else:
                    formatted_query = formatted_query.replace(f"{{{key}}}", str(value))
            
            logger.debug(f"Executing analytics query: {formatted_query[:100]}...")
            result = conn.execute(formatted_query).df()  # Use .df() for pandas compatibility
            logger.info(f"Analytics query returned {len(result)} rows")
            return result
            
    except Exception as e:
        error_msg = f"Analytics query execution failed: {str(e)}"
        context = {
            'query': query[:200] + '...' if len(query) > 200 else query,
            'params_count': len(params),
            'formatted_query_length': len(formatted_query)
        }
        exc = DatabaseConnectionError(error_msg, 'execute_analytics_query', context=context)
        logger.error("Analytics query execution failed", extra=exc.to_dict())
        raise exc
```

### Phase 2: ConfigManager Integration

#### 2.1 Update PatternAnalyzer Initialization

**File**: `analytics/core/pattern_analyzer.py`

**Current**:
```python
class PatternAnalyzer:
    def __init__(self, db_connector: DuckDBAnalytics):
        self.db = db_connector
```

**Enhanced with ConfigManager**:
```python
class PatternAnalyzer:
    def __init__(self, db_connector: Optional[DuckDBAnalytics] = None, config_manager: Optional[ConfigManager] = None):
        """
        Initialize PatternAnalyzer with optional database connector and config.
        
        Args:
            db_connector: DuckDBAnalytics instance (legacy support)
            config_manager: ConfigManager for centralized configuration
        """
        self.config_manager = config_manager
        
        # Backward compatibility
        if db_connector:
            self.db = db_connector
        else:
            # Create connector with config manager
            self.db = DuckDBAnalytics(config_manager=config_manager)
        
        self.discovered_patterns = []
        self._load_pattern_config()
    
    def _load_pattern_config(self):
        """Load pattern discovery parameters from config."""
        if self.config_manager:
            try:
                analytics_config = self.config_manager.get_config('analytics')
                pattern_config = analytics_config.get('patterns', {})
                self.min_volume_multiplier = pattern_config.get('min_volume_multiplier', 1.5)
                self.time_window_minutes = pattern_config.get('time_window_minutes', 10)
                self.min_price_move = pattern_config.get('min_price_move', 0.03)
            except Exception as e:
                logger.warning(f"Failed to load pattern config: {e}")
                # Use defaults
                self.min_volume_multiplier = 1.5
                self.time_window_minutes = 10
                self.min_price_move = 0.03
        else:
            # Default values
            self.min_volume_multiplier = 1.5
            self.time_window_minutes = 10
            self.min_price_move = 0.03
```

### Phase 3: Dashboard Integration

#### 3.1 Update Dashboard App Configuration

**File**: `analytics/dashboard/app.py`

**Add ConfigManager initialization**:
```python
import streamlit as st
from src.infrastructure.config.config_manager import ConfigManager
from analytics.core import DuckDBAnalytics, PatternAnalyzer

# Initialize config manager
@st.cache_resource
def get_config_manager():
    """Get shared ConfigManager instance."""
    return ConfigManager()

# Initialize analytics components with config
config_manager = get_config_manager()
analytics_connector = DuckDBAnalytics(config_manager=config_manager)
pattern_analyzer = PatternAnalyzer(config_manager=config_manager)

# Dashboard title and configuration
st.set_page_config(
    page_title="TraderX Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🚀 TraderX — 500-Stock Descriptive Analytics Dashboard")
```

### Phase 4: Retry Decorator Enhancement

#### 4.1 Fix Instance Method Binding

**File**: `src/infrastructure/utils/retry.py`

**Current Issue**: `@tenacity_retry` decorator interferes with method binding

**Solution**: Use descriptor pattern for proper method preservation

```python
from functools import wraps, update_wrapper
from types import MethodType

class RetryDescriptor:
    """Descriptor that applies retry decorator while preserving method binding."""
    
    def __init__(self, func, retry_config):
        self.func = func
        self.retry_config = retry_config
        update_wrapper(self, func)
    
    def __get__(self, instance, owner):
        if instance is None:
            return self
        
        # Create bound method with retry wrapper
        def bound_method(*args, **kwargs):
            # Apply retry logic to the original method
            tenacity_retry = retry(
                stop=stop_after_attempt(self.retry_config["max_retries"]),
                wait=wait_exponential(
                    min=self.retry_config["initial_backoff"],
                    max=self.retry_config["max_backoff"],
                    multiplier=self.retry_config["backoff_multiplier"]
                ),
                retry=retry_if_exception_type(DatabaseConnectionError),
                before=before_log(logger, logging.INFO),
                reraise=True
            )
            
            @wraps(self.func)
            @tenacity_retry
            def wrapper(*w_args, **w_kwargs):
                print(f"DEBUG RETRY METHOD: {self.func.__name__} called")
                return self.func(instance, *w_args, **w_kwargs)
            
            return wrapper(*args, **kwargs)
        
        return MethodType(bound_method, instance)

def retry_db_operation(config_manager: Optional[ConfigManager] = None, **kwargs) -> Callable:
    """Enhanced retry decorator that preserves method binding."""
    retry_config = get_retry_config(config_manager, "database.retry")
    retry_config.update(kwargs)
    
    def decorator(func: Callable) -> Callable:
        return RetryDescriptor(func, retry_config)
    
    return decorator
```

### Phase 5: Verification and Testing

#### 5.1 Integration Test Script

**File**: `analytics/tests/integration/test_db_integration.py`

```python
import pytest
from src.infrastructure.config.config_manager import ConfigManager
from analytics.core import DuckDBAnalytics, PatternAnalyzer

class TestAnalyticsDatabaseIntegration:
    """Integration tests for analytics database connectivity."""
    
    @pytest.fixture
    def config_manager(self):
        return ConfigManager()
    
    def test_analytics_connector_with_config(self, config_manager):
        """Test analytics connector with proper config integration."""
        connector = DuckDBAnalytics(config_manager=config_manager)
        with connector.connect():
            result = connector.execute_analytics_query("SELECT 1 as test")
            assert not result.empty
            assert len(result) == 1
    
    def test_pattern_analyzer_integration(self, config_manager):
        """Test PatternAnalyzer with database connectivity."""
        connector = DuckDBAnalytics(config_manager=config_manager)
        analyzer = PatternAnalyzer(connector)
        
        # Test pattern discovery (may return empty if no data, but shouldn't crash)
        patterns = analyzer.discover_volume_spike_patterns()
        assert isinstance(patterns, list)  # Should return list even if empty
        
        # Test time window patterns
        time_patterns = analyzer.discover_time_window_patterns()
        assert isinstance(time_patterns, list)
    
    def test_query_execution_with_data_paths(self, config_manager):
        """Test analytics queries with proper data paths."""
        connector = DuckDBAnalytics(config_manager=config_manager)
        
        # Test parquet scanning if data exists
        query = "SELECT COUNT(*) as file_count FROM parquet_scan('{parquet_base}**/*.parquet')"
        try:
            result = connector.execute_analytics_query(query)
            print(f"Found {result['file_count'].iloc[0] if not result.empty else 0} parquet files")
        except Exception as e:
            # Expected if no data files exist
            print(f"No parquet files found (expected in development): {e}")
```

#### 5.2 Runtime Verification Commands

```bash
# Test complete integration
python -c "
import sys; sys.path.insert(0, '.')
from src.infrastructure.config.config_manager import ConfigManager
from analytics.core import DuckDBAnalytics, PatternAnalyzer

config = ConfigManager()
connector = DuckDBAnalytics(config_manager=config)
analyzer = PatternAnalyzer(connector)

print('✅ Analytics integration test started')
with connector.connect():
    print('✅ Database connection successful')
    result = connector.execute_analytics_query('SELECT 1')
    print(f'✅ Query result: {len(result)} rows')

patterns = analyzer.discover_volume_spike_patterns()
print(f'✅ Pattern discovery: {len(patterns)} patterns found')
print('✅ Full integration successful')
"
```

### Phase 6: Deployment and Monitoring

#### 6.1 Configuration Management

**Update configs/analytics.yaml**:
```yaml
analytics:
  data_paths:
    parquet_base: './data/'
    indicators: './data/technical_indicators/'
    processed: './data/processed/'
  patterns:
    min_volume_multiplier: 1.5
    time_window_minutes: 10
    min_price_move: 0.03
  queries:
    volume_spike:
      min_volume_multiplier: 1.5
      time_window_minutes: 60
      min_price_move: 0.02
  dashboard:
    analysis_start_time: "09:35"
    analysis_end_time: "09:50"
```

#### 6.2 Performance Monitoring

**Add to dashboard/app.py**:
```python
import time
from contextlib import contextmanager

@contextmanager
def track_query_performance(name: str):
    """Track query performance for monitoring."""
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        st.metric(f"{name} Query Time", f"{duration:.2f}s")
        logger.info(f"{name} executed in {duration:.2f}s")

# Usage in analytics methods
with track_query_performance("Volume Spike Discovery"):
    patterns = analyzer.discover_volume_spike_patterns()
```

## 🎯 Implementation Priority

### Immediate (Phase 1 - This Sprint)
1. **Update DuckDBAnalytics** to use infrastructure adapter [High Priority]
2. **Fix path resolution** in analytics connector [High Priority]
3. **Integration tests** for connector + PatternAnalyzer [High Priority]

### Short Term (Phase 2 - Next Sprint)
1. **ConfigManager integration** throughout analytics [Medium Priority]
2. **Retry decorator enhancement** for instance methods [Medium Priority]
3. **Dashboard configuration** updates [Medium Priority]

### Long Term (Phase 3 - Future)
1. **Performance monitoring** and optimization [Low Priority]
2. **Advanced caching** strategies [Low Priority]
3. **Distributed query** support [Low Priority]

## 📊 Expected Outcomes

After implementation:
- ✅ **100% Test Coverage**: All analytics tests passing with real database connectivity
- ✅ **<2s Query Performance**: 500-stock universe scans within performance targets  
- ✅ **Zero Path Issues**: Consistent database connectivity across environments
- ✅ **Config-Driven**: Centralized configuration management
- ✅ **Production Ready**: Proper error handling and monitoring

## 🚨 Rollback Plan

If integration issues occur:
1. **Revert to mocked tests** (current working state)
2. **Use in-memory database** for development
3. **Gradual migration** - keep both connectors temporarily
4. **Feature flags** for database adapter selection

## 📅 Timeline

- **Week 1**: Connector refactoring and basic integration
- **Week 2**: ConfigManager integration and test coverage
- **Week 3**: Performance optimization and monitoring
- **Week 4**: Documentation and deployment preparation

This plan ensures the analytics module will have robust, production-ready database connectivity while maintaining the existing functionality and test coverage.