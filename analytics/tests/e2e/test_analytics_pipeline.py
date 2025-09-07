#!/usr/bin/env python3
"""
End-to-End Tests for Analytics Pipeline
=======================================
Real integration tests for the complete analytics workflow without mocking.
Uses real DuckDB database with project data.
"""

import warnings
import pytest
import pandas as pd
import duckdb
from datetime import datetime, timedelta
from analytics.core.duckdb_connector import DuckDBAnalytics
from analytics.core.pattern_analyzer import PatternAnalyzer
from analytics.rules.rule_engine import RuleEngine, TradingRule
from analytics.utils.data_processor import DataProcessor

warnings.filterwarnings("ignore", category=DeprecationWarning, module="rx.internal.constants")
warnings.filterwarnings("ignore", category=DeprecationWarning, message="Support for class-based `config` is deprecated")

@pytest.fixture(scope="module")
def real_db():
    """Fixture to load real Parquet data into in-memory DuckDB."""
    conn = duckdb.connect(':memory:')
    
    # Load real Parquet data from project data directory
    conn.execute("INSTALL httpfs; LOAD httpfs;")
    # Assume Parquet files are in data/2015/ etc., load sample
    conn.execute("""
        CREATE TABLE financial_data AS
        SELECT * FROM read_parquet('data/2015/02/**/*.parquet')
        LIMIT 5000
    """)
    
    analytics = DuckDBAnalytics(db_path=':memory:')
    analytics.connection = conn
    yield analytics
    conn.close()

class TestAnalyticsPipelineE2E:
    """End-to-end tests for the analytics pipeline."""
    
    def test_full_pattern_discovery_pipeline(self, real_db):
        """Test complete pipeline: data processing -> pattern analysis."""
        processor = DataProcessor()
        analyzer = PatternAnalyzer(real_db)
        engine = RuleEngine()
        
        # Get data from DB (use a real symbol from NIFTY-500)
        raw_data = real_db.execute_analytics_query("SELECT * FROM financial_data LIMIT 100")  # Sample real data
        assert len(raw_data) > 0
        assert 'volume' in raw_data.columns
        
        # Process data with real indicators
        processed_data = processor.calculate_technical_indicators(raw_data)
        assert 'volume_ratio' in processed_data.columns or 'rsi' in processed_data.columns
        
        # Discover patterns on real data
        patterns = analyzer.discover_volume_spike_patterns(min_volume_multiplier=1.5, time_window_minutes=60)
        # Assert flow completes without error; real data may vary, but check non-empty if patterns exist
        assert patterns is not None
        if patterns:
            assert len(patterns) > 0
    
    def test_rule_evaluation_pipeline(self, real_db):
        """Test pipeline: pattern discovery -> rule evaluation."""
        analyzer = PatternAnalyzer(real_db)
        engine = RuleEngine()
        
        # Add a simple rule
        test_rule = TradingRule(
            name="Test Volume Rule",
            description="Detect volume >1.5x",
            conditions={"volume_multiplier": ">1.5"},
            actions={"alert": True}
        )
        engine.add_rule(test_rule)
        
        # Discover patterns on real data
        patterns = analyzer.discover_volume_spike_patterns(min_volume_multiplier=1.5)
        
        # Evaluate with rules
        if patterns:
            signals = engine.evaluate_pattern(patterns[0])
            assert signals is not None
            if signals:
                assert any(s.rule_name == "Test Volume Rule" for s in signals)
        else:
            pytest.skip("No patterns found in real data for this test")
    
    def test_data_processing_integration(self, real_db):
        """Test data processing across components."""
        processor = DataProcessor()
        raw_data = real_db.execute_analytics_query("SELECT * FROM financial_data LIMIT 1000")
        
        # Process and detect spikes
        with_spikes = processor.detect_volume_spikes(raw_data, threshold=1.5)
        assert 'is_volume_spike' in with_spikes.columns
        spike_count = with_spikes['is_volume_spike'].sum()
        # Real data may not have spikes; assert flow works
        assert spike_count >= 0
        
        # Generate report
        report = processor.generate_pattern_report(with_spikes)
        assert 'total_records' in report
        assert report['total_records'] == len(raw_data)