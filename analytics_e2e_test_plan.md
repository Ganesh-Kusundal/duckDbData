# Analytics Module E2E Test Plan

## 🎯 Executive Summary

This document outlines a comprehensive End-to-End (E2E) testing strategy for the TraderX Analytics module. The goal is to verify the complete workflow from database connectivity through pattern discovery, rule processing, dashboard rendering, and user interactions. The E2E tests will ensure system reliability, performance targets, and user experience quality across the entire analytics pipeline.

## 📋 Test Scope and Objectives

### Primary Objectives
1. **End-to-End Workflow Validation**: Verify complete user journey from data loading to actionable insights
2. **Performance Verification**: Ensure <2s scan performance for 500-stock universe
3. **Database Integration**: Confirm analytics module uses working infrastructure database layer
4. **Dashboard Functionality**: Test all UI components, interactions, and data visualization
5. **Error Handling**: Validate graceful degradation and user feedback for failures
6. **Export Capabilities**: Verify data export functionality for patterns and signals

### Test Scope
- **Database Layer**: Connectivity, schema initialization, data loading
- **Analytics Core**: Pattern discovery, rule engine, data processing
- **Dashboard UI**: Streamlit components, user interactions, visualizations
- **Integration Points**: ConfigManager, infrastructure adapters, external data sources
- **Performance**: Load testing, response times, memory usage

## 🏗️ Test Architecture

### 1. Test Data Setup

#### 1.1 Sample Data Generation
```python
# analytics/tests/e2e/data/setup_data.py
import duckdb
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

class TestDataGenerator:
    """Generate realistic test data for E2E testing."""
    
    @staticmethod
    def create_sample_market_data(num_stocks=50, days=30):
        """Create sample market data for NIFTY-50 like universe."""
        data = []
        base_date = datetime(2024, 1, 1)
        
        for stock_id in range(1, num_stocks + 1):
            symbol = f"STOCK{stock_id:03d}"
            for day in range(days):
                date = base_date + timedelta(days=day)
                # Generate realistic OHLCV data
                open_price = 100 + np.random.normal(0, 20)
                high = open_price * (1 + abs(np.random.normal(0, 0.02)))
                low = open_price * (1 - abs(np.random.normal(0, 0.02)))
                close = low + np.random.uniform(0, high - low)
                volume = np.random.randint(100000, 10000000)
                
                data.append({
                    'symbol': symbol,
                    'timestamp': date,
                    'open': round(open_price, 2),
                    'high': round(high, 2),
                    'low': round(low, 2),
                    'close': round(close, 2),
                    'volume': volume,
                    'timeframe': '1D',
                    'date_partition': date.date()
                })
        
        return pd.DataFrame(data)
    
    @staticmethod
    def create_pattern_data():
        """Create data with known breakout patterns for testing."""
        # Generate specific volume spike and breakout patterns
        # This will create predictable test scenarios
        pass
```

#### 1.2 Database Setup Fixture
```python
# analytics/tests/conftest.py
import pytest
import tempfile
import os
from pathlib import Path
from src.infrastructure.adapters.duckdb_adapter import DuckDBAdapter
from analytics.core import DuckDBAnalytics

@pytest.fixture(scope="session")
def test_database():
    """Create test database with sample data."""
    # Create temporary database
    db_path = tempfile.mkdtemp() / "test_analytics.db"
    
    # Initialize with sample data
    adapter = DuckDBAdapter(database_path=str(db_path))
    with adapter.get_connection() as conn:
        # Create schema
        adapter._initialize_schema()
        
        # Load test data
        test_data = TestDataGenerator.create_sample_market_data()
        # Insert data into market_data table
        
    yield str(db_path)
    
    # Cleanup
    if os.path.exists(str(db_path)):
        os.remove(str(db_path))

@pytest.fixture(scope="session")
def analytics_connector(test_database):
    """Create analytics connector with test database."""
    return DuckDBAnalytics(db_path=str(test_database))
```

### 2. E2E Test Categories

#### 2.1 Database Integration Tests

**File**: `analytics/tests/e2e/test_database_integration.py`

```python
import pytest
from analytics.core import DuckDBAnalytics, PatternAnalyzer
from src.infrastructure.config.config_manager import ConfigManager

class TestDatabaseIntegration:
    """E2E tests for database connectivity and data operations."""
    
    def test_complete_database_workflow(self, analytics_connector):
        """Test complete database workflow from connection to query."""
        # 1. Verify connection
        with analytics_connector.connect() as conn:
            assert conn is not None
            
            # 2. Test schema existence
            tables = conn.execute("SHOW TABLES").fetchall()
            required_tables = ['market_data', 'symbols', 'scanner_results']
            for table in required_tables:
                assert any(table_name == table for table_name, *_ in tables)
            
            # 3. Test data operations
            # Insert test record
            conn.execute("""
                INSERT INTO symbols (symbol, name, sector) 
                VALUES ('TEST001', 'Test Stock', 'Technology')
            """)
            
            # Verify insertion
            result = conn.execute("SELECT * FROM symbols WHERE symbol = 'TEST001'").fetchall()
            assert len(result) == 1
            
            # 4. Test analytics query
            analytics_result = analytics_connector.execute_analytics_query(
                "SELECT COUNT(*) as symbol_count FROM symbols"
            )
            assert not analytics_result.empty
            assert analytics_result['symbol_count'].iloc[0] >= 1
    
    def test_config_manager_integration(self):
        """Test analytics with ConfigManager integration."""
        config = ConfigManager()
        connector = DuckDBAnalytics(config_manager=config)
        
        with connector.connect():
            # Verify config-driven path resolution
            assert connector._adapter.database_path.endswith('financial_data.duckdb')
            
            # Test config-driven analytics query
            result = connector.execute_analytics_query(
                "SELECT 1 as config_test"
            )
            assert not result.empty
```

#### 2.2 Pattern Discovery E2E Tests

**File**: `analytics/tests/e2e/test_pattern_discovery.py`

```python
import pytest
from datetime import datetime, timedelta
from analytics.core import PatternAnalyzer
from analytics.tests.e2e.data.setup_data import TestDataGenerator

class TestPatternDiscoveryE2E:
    """E2E tests for complete pattern discovery workflow."""
    
    @pytest.fixture
    def pattern_data_connector(self, analytics_connector):
        """Connector with pattern test data."""
        # Load pattern-specific test data
        test_data = TestDataGenerator.create_pattern_data()
        # Insert into database
        with analytics_connector.connect() as conn:
            # Clear existing data
            conn.execute("DELETE FROM market_data")
            # Insert test patterns
            # ... data insertion logic
        
        return analytics_connector
    
    def test_volume_spike_discovery_complete(self, pattern_data_connector):
        """Test complete volume spike discovery workflow."""
        analyzer = PatternAnalyzer(pattern_data_connector)
        
        # 1. Execute pattern discovery
        patterns = analyzer.discover_volume_spike_patterns(
            min_volume_multiplier=1.5,
            time_window_minutes=60
        )
        
        # 2. Verify results structure
        assert isinstance(patterns, list)
        assert len(patterns) > 0  # Should find test patterns
        
        first_pattern = patterns[0]
        assert hasattr(first_pattern, 'symbol')
        assert hasattr(first_pattern, 'volume_multiplier')
        assert first_pattern.volume_multiplier >= 1.5
        
        # 3. Verify database integration
        assert first_pattern.symbol in ['TEST_STOCK_001', 'TEST_STOCK_002']  # Test symbols
        
        # 4. Test pattern scoring
        scores = analyzer.get_pattern_summary_table(patterns)
        assert not scores.empty
        assert 'confidence_score' in scores.columns
    
    def test_time_window_pattern_discovery(self, pattern_data_connector):
        """Test time window pattern discovery end-to-end."""
        analyzer = PatternAnalyzer(pattern_data_connector)
        
        # 1. Execute time window analysis
        time_patterns = analyzer.discover_time_window_patterns(
            start_time='09:30',
            end_time='11:00'
        )
        
        # 2. Verify time-based filtering
        assert len(time_patterns) > 0
        for pattern in time_patterns:
            assert hasattr(pattern, 'trade_time')
            # Verify time window filtering
            trade_time = pattern.trade_time.time()
            assert time(9, 30) <= trade_time <= time(11, 0)
        
        # 3. Test success rate analysis
        stats = analyzer.analyze_pattern_success_rates(time_patterns)
        assert hasattr(stats, 'total_occurrences')
        assert stats.total_occurrences == len(time_patterns)
    
    def test_pattern_discovery_performance(self, pattern_data_connector):
        """Test pattern discovery performance targets."""
        import time
        
        analyzer = PatternAnalyzer(pattern_data_connector)
        start_time = time.time()
        
        # Execute full pattern discovery
        volume_patterns = analyzer.discover_volume_spike_patterns()
        time_patterns = analyzer.discover_time_window_patterns()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance assertion (<2s target)
        assert duration < 2.0, f"Pattern discovery took {duration:.2f}s, expected <2s"
        print(f"✅ Pattern discovery performance: {duration:.2f}s")
```

#### 2.3 Rule Engine E2E Tests

**File**: `analytics/tests/e2e/test_rule_engine.py`

```python
import pytest
import json
from analytics.rules import RuleEngine, TradingRule
from analytics.core import PatternAnalyzer

class TestRuleEngineE2E:
    """E2E tests for rule engine integration with pattern discovery."""
    
    @pytest.fixture
    def complete_analytics_system(self, analytics_connector):
        """Complete analytics system with database and rules."""
        analyzer = PatternAnalyzer(analytics_connector)
        rule_engine = RuleEngine()
        
        # Load default rules
        with open('analytics/rules/default_rules.json', 'r') as f:
            rules_config = json.load(f)
        
        for rule_data in rules_config['rules']:
            rule = TradingRule.from_dict(rule_data)
            rule_engine.add_rule(rule)
        
        return analyzer, rule_engine
    
    def test_complete_signal_generation_workflow(self, complete_analytics_system):
        """Test complete workflow from patterns to trading signals."""
        analyzer, rule_engine = complete_analytics_system
        
        # 1. Discover patterns
        patterns = analyzer.discover_volume_spike_patterns()
        
        # 2. Apply rules
        signals = rule_engine.evaluate_patterns(patterns)
        
        # 3. Verify signal generation
        assert isinstance(signals, list)
        assert len(signals) <= len(patterns)  # Rules may filter patterns
        
        # 4. Test signal quality
        if signals:
            first_signal = signals[0]
            assert hasattr(first_signal, 'symbol')
            assert hasattr(first_signal, 'signal_strength')
            assert first_signal.signal_strength > 0
        
        print(f"✅ Generated {len(signals)} signals from {len(patterns)} patterns")
    
    def test_rule_configuration_integration(self, complete_analytics_system):
        """Test rule configuration loading and application."""
        analyzer, rule_engine = complete_analytics_system
        
        # Verify rules loaded
        assert len(rule_engine.rules) > 0
        
        # Test specific rule types
        volume_spike_rules = [r for r in rule_engine.rules if 'volume_spike' in r.name.lower()]
        assert len(volume_spike_rules) >= 1
        
        # Test rule evaluation
        patterns = analyzer.discover_volume_spike_patterns()
        evaluated = rule_engine.evaluate_patterns(patterns)
        
        # Verify rule statistics
        stats = rule_engine.get_rule_statistics()
        assert 'total_evaluations' in stats
        assert stats['total_evaluations'] == len(patterns)
```

#### 2.4 Dashboard E2E Tests

**File**: `analytics/tests/e2e/test_dashboard_integration.py`

Since Streamlit E2E testing requires special tools, create integration tests for the dashboard logic:

```python
import pytest
import streamlit as st
from unittest.mock import patch, MagicMock
from analytics.dashboard.app import get_config_manager, create_pattern_analyzer

class TestDashboardIntegration:
    """Integration tests for dashboard functionality."""
    
    def test_dashboard_initialization(self):
        """Test dashboard initialization and component setup."""
        with patch('streamlit.set_page_config') as mock_set_page:
            with patch('streamlit.title') as mock_title:
                # Import triggers dashboard initialization
                import analytics.dashboard.app
                
                mock_set_page.assert_called_once()
                mock_title.assert_called_with("🚀 TraderX — 500-Stock Descriptive Analytics Dashboard")
    
    def test_analytics_components_initialization(self):
        """Test analytics components are properly initialized in dashboard."""
        config_manager = get_config_manager()
        assert config_manager is not None
        
        # Test pattern analyzer creation
        analyzer = create_pattern_analyzer()
        assert isinstance(analyzer, PatternAnalyzer)
        
        # Verify database connectivity in dashboard context
        with analyzer.db.connect():
            result = analyzer.db.execute_analytics_query("SELECT 1")
            assert not result.empty
    
    @pytest.mark.parametrize("scan_type", ["volume_spike", "time_window", "momentum"])
    def test_scan_workflows(self, scan_type):
        """Test different scan workflows in dashboard context."""
        # This would use Streamlit testing framework or component testing
        # For now, test the underlying analytics functions
        analyzer = create_pattern_analyzer()
        
        if scan_type == "volume_spike":
            patterns = analyzer.discover_volume_spike_patterns()
        elif scan_type == "time_window":
            patterns = analyzer.discover_time_window_patterns()
        else:  # momentum
            patterns = analyzer.get_momentum_leaders()
        
        assert isinstance(patterns, list)
        print(f"✅ {scan_type} scan workflow: {len(patterns)} results")
    
    def test_export_functionality(self):
        """Test data export capabilities."""
        analyzer = create_pattern_analyzer()
        patterns = analyzer.discover_volume_spike_patterns()
        
        # Test export to CSV
        export_data = analyzer.get_pattern_summary_table(patterns)
        assert not export_data.empty
        
        # Verify export columns
        required_columns = ['symbol', 'confidence_score', 'volume_multiplier']
        for col in required_columns:
            assert col in export_data.columns
        
        print(f"✅ Export functionality verified: {len(export_data)} rows")
```

### 3. Performance and Load Testing

#### 3.1 Performance Test Suite

**File**: `analytics/tests/e2e/test_performance.py`

```python
import pytest
import time
from analytics.core import PatternAnalyzer
from analytics.dashboard.app import create_pattern_analyzer

class TestPerformanceE2E:
    """E2E performance tests for analytics workflows."""
    
    @pytest.mark.performance
    def test_full_universe_scan_performance(self):
        """Test 500-stock universe scan performance (<2s target)."""
        analyzer = create_pattern_analyzer()
        
        start_time = time.time()
        
        # Execute full scan
        patterns = analyzer.discover_volume_spike_patterns(
            min_volume_multiplier=1.2  # Lower threshold for more results
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance assertion
        assert duration < 2.0, f"Full scan took {duration:.2f}s, expected <2s"
        
        # Verify reasonable result count
        assert len(patterns) >= 10, f"Expected at least 10 patterns, got {len(patterns)}"
        
        print(f"✅ Full universe scan: {duration:.2f}s, {len(patterns)} patterns")
    
    @pytest.mark.performance
    def test_concurrent_pattern_discovery(self):
        """Test concurrent pattern discovery performance."""
        import asyncio
        import concurrent.futures
        
        analyzer = create_pattern_analyzer()
        
        def run_pattern_discovery(pattern_type):
            if pattern_type == "volume":
                return analyzer.discover_volume_spike_patterns()
            elif pattern_type == "time":
                return analyzer.discover_time_window_patterns()
            else:
                return analyzer.get_momentum_leaders()
        
        # Run concurrent discoveries
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(run_pattern_discovery, "volume"),
                executor.submit(run_pattern_discovery, "time"),
                executor.submit(run_pattern_discovery, "momentum")
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Verify concurrent performance
        assert duration < 3.0, f"Concurrent scans took {duration:.2f}s, expected <3s"
        
        # Verify all results valid
        for i, result in enumerate(results):
            assert isinstance(result, list), f"Result {i} not a list"
            print(f"✅ Concurrent scan {i}: {len(result)} patterns")
    
    @pytest.mark.performance
    def test_dashboard_load_performance(self):
        """Test dashboard loading performance."""
        import streamlit as st
        
        # This would require Streamlit testing framework
        # For now, test the data loading components
        analyzer = create_pattern_analyzer()
        
        start_time = time.time()
        
        # Simulate dashboard data loading
        kpi_data = analyzer.get_market_kpis()
        heatmap_data = analyzer.get_heatmap_data()
        patterns = analyzer.discover_volume_spike_patterns()
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert duration < 1.5, f"Dashboard data load took {duration:.2f}s, expected <1.5s"
        print(f"✅ Dashboard load performance: {duration:.2f}s")
```

### 4. E2E Test Execution Strategy

#### 4.1 Test Environment Setup

**Docker Compose for E2E Testing**:
```yaml
# docker-compose.e2e.yml
version: '3.8'
services:
  e2e-test:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - .:/app
    environment:
      - PYTHONPATH=/app
      - DUCKDB_PATH=/tmp/test_analytics.db
    command: pytest analytics/tests/e2e -v --tb=short -m e2e
    depends_on:
      - data-generator
    
  data-generator:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - .:/app
    command: python analytics/tests/e2e/data/setup_data.py
```

#### 4.2 CI/CD Integration

**GitHub Actions Workflow**:
```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -r analytics/requirements.txt
        pip install pytest pytest-cov
    
    - name: Run E2E Tests
      run: |
        cd analytics
        pytest tests/e2e -v --cov=analytics --cov-report=xml -m e2e
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### 5. Test Scenarios and Coverage

#### 5.1 Happy Path Scenarios

1. **Complete User Journey**:
   - Database connection → Pattern discovery → Rule evaluation → Dashboard display → Export results
   
2. **Performance Critical Path**:
   - 500-stock scan <2s → Real-time KPI updates → Interactive filtering
   
3. **Data Pipeline**:
   - Raw data → Technical indicators → Pattern detection → Signal generation

#### 5.2 Error Scenarios

1. **Database Connectivity Failures**:
   - Invalid database path
   - Permission denied
   - Network timeouts (for future distributed)
   
2. **Data Quality Issues**:
   - Missing columns in parquet files
   - Corrupted data
   - Empty datasets
   
3. **Configuration Errors**:
   - Invalid config values
   - Missing config sections
   - Path resolution failures

#### 5.3 Edge Cases

1. **Large Dataset Handling**:
   - 10+ years of 1-minute data
   - High-volume spike days
   - Market crash scenarios
   
2. **Concurrent Usage**:
   - Multiple dashboard sessions
   - Simultaneous pattern discovery
   - Parallel data exports

### 6. Monitoring and Reporting

#### 6.1 Test Metrics

**Performance Metrics**:
- Pattern discovery time (<2s)
- Dashboard load time (<1.5s)
- Memory usage (<500MB)
- CPU utilization (<80%)

**Reliability Metrics**:
- Test pass rate (95%+)
- Database connection success rate (100%)
- Error recovery rate (90%+)

**Coverage Metrics**:
- E2E test coverage (80%+ of critical paths)
- Integration test coverage (90%+)
- Unit test coverage (95%+)

#### 6.2 Automated Reporting

**Test Dashboard** (using existing analytics infrastructure):
- Real-time test results visualization
- Performance trend analysis
- Failure pattern detection
- Coverage reports

## 🚀 Implementation Roadmap

### Week 1: Foundation
- [ ] Create test data generation utilities
- [ ] Implement database integration E2E tests
- [ ] Set up test fixtures and conftest.py
- [ ] Basic connectivity and workflow tests

### Week 2: Core Functionality
- [ ] Pattern discovery E2E tests with real data
- [ ] Rule engine integration tests
- [ ] Performance testing framework
- [ ] Load testing scenarios

### Week 3: Dashboard Testing
- [ ] Streamlit component integration tests
- [ ] User interaction workflow tests
- [ ] Export functionality verification
- [ ] Error handling scenarios

### Week 4: Advanced & Production
- [ ] CI/CD pipeline integration
- [ ] Performance monitoring and alerting
- [ ] Test data management strategy
- [ ] Documentation and maintenance plan

## 📊 Expected Outcomes

After implementation:
- ✅ **Complete E2E Coverage**: 100% critical path coverage
- ✅ **Performance Validation**: Automated <2s scan verification
- ✅ **Reliability Assurance**: 95%+ test pass rate in CI
- ✅ **Regression Protection**: Automated detection of functionality breaks
- ✅ **Production Confidence**: Verified workflows before deployment

This E2E test plan ensures the TraderX Analytics module delivers reliable, performant, and production-ready functionality across the complete user journey.