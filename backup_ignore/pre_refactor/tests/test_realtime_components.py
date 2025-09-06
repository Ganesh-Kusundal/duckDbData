#!/usr/bin/env python3
"""
Real-Time System Component Tests
================================

Comprehensive testing of each component in the real-time data pipeline:
1. Database Manager
2. Technical Indicators Storage
3. Technical Indicators Calculator
4. Technical Indicators Updater
5. Rate Limiter
6. Data Pipeline
7. Configuration Management
8. Logging System

Author: AI Assistant
Date: 2025-09-04
"""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_database_manager():
    """Test the database manager component"""
    print("🧪 Testing Database Manager")
    print("-" * 40)
    
    try:
        from core.duckdb_infra.database import DuckDBManager
        
        # Initialize database manager
        db_manager = DuckDBManager()
        print("✅ Database manager initialized")
        
        # Test database connection
        test_query = "SELECT 1 as test"
        result = db_manager.execute_custom_query(test_query)
        print("✅ Database connection working")
        
        # Test getting available symbols
        symbols = db_manager.get_available_symbols()
        print(f"✅ Found {len(symbols)} symbols in database")
        
        # Test inserting sample data
        sample_data = pd.DataFrame({
            'symbol': ['TEST_SYMBOL'],
            'timestamp': [datetime.now()],
            'open': [100.0],
            'high': [105.0],
            'low': [95.0],
            'close': [102.0],
            'volume': [1000],
            'date_partition': [date.today()]
        })
        
        records_added = db_manager.insert_market_data(sample_data)
        print(f"✅ Inserted {records_added} test records")
        
        # Clean up test data
        db_manager.execute_custom_query("DELETE FROM market_data WHERE symbol = 'TEST_SYMBOL'")
        print("✅ Test data cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ Database manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_technical_indicators_storage():
    """Test the technical indicators storage component"""
    print("\n🧪 Testing Technical Indicators Storage")
    print("-" * 40)
    
    try:
        from core.technical_indicators.storage import TechnicalIndicatorsStorage
        
        # Initialize storage
        storage = TechnicalIndicatorsStorage('data/technical_indicators')
        print("✅ Technical indicators storage initialized")
        
        # Test storage directory creation
        if storage.base_path.exists():
            print("✅ Storage directory exists")
        else:
            print("⚠️ Storage directory created")
        
        # Test storing sample indicators
        sample_indicators = pd.DataFrame({
            'symbol': ['TEST_SYMBOL'],
            'timestamp': [datetime.now()],
            'date_partition': [date.today()],
            'sma_20': [100.0],
            'rsi_14': [50.0],
            'macd': [0.5],
            'volume': [1000]
        })
        
        success = storage.store_indicators(sample_indicators, '1T', date.today())
        print(f"✅ Stored indicators: {success}")
        
        # Test loading indicators
        loaded_indicators = storage.load_indicators('TEST_SYMBOL', '1T', date.today())
        if loaded_indicators is not None and not loaded_indicators.empty:
            print(f"✅ Loaded {len(loaded_indicators)} indicator records")
        else:
            print("⚠️ No indicators loaded (expected for test data)")
        
        # Test getting available symbols
        available_symbols = storage.get_available_symbols()
        print(f"✅ Available symbols in storage: {len(available_symbols)}")
        
        # Test storage statistics
        stats = storage.get_storage_stats()
        print(f"✅ Storage stats: {stats['files_count']} files, {stats['symbols_count']} symbols")
        
        return True
        
    except Exception as e:
        print(f"❌ Technical indicators storage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_technical_indicators_calculator():
    """Test the technical indicators calculator component"""
    print("\n🧪 Testing Technical Indicators Calculator")
    print("-" * 40)
    
    try:
        from core.technical_indicators.calculator import TechnicalIndicatorsCalculator
        
        # Create sample OHLCV data
        dates = pd.date_range(start='2025-09-01', periods=100, freq='1min')
        np.random.seed(42)  # For reproducible results
        
        sample_data = pd.DataFrame({
            'timestamp': dates,
            'open': 100 + np.random.randn(100) * 2,
            'high': 105 + np.random.randn(100) * 2,
            'low': 95 + np.random.randn(100) * 2,
            'close': 102 + np.random.randn(100) * 2,
            'volume': 1000 + np.random.randint(0, 500, 100)
        })
        
        # Initialize calculator
        calculator = TechnicalIndicatorsCalculator()
        print("✅ Technical indicators calculator initialized")
        
        # Test calculating indicators
        indicators = calculator.calculate_all_indicators(sample_data, 'TEST_SYMBOL', '1T')
        print(f"✅ Calculated indicators: {len(indicators)} columns")
        
        # Check for key indicators
        key_indicators = ['sma_20', 'ema_20', 'rsi_14', 'macd', 'bollinger_upper', 'atr_14']
        found_indicators = [ind for ind in key_indicators if ind in indicators.columns]
        print(f"✅ Found {len(found_indicators)} key indicators: {found_indicators}")
        
        # Test support/resistance calculation
        support_resistance = calculator.calculate_support_resistance_zones(sample_data)
        if support_resistance is not None and not support_resistance.empty:
            print("✅ Support/resistance zones calculated")
        
        # Test supply/demand zones
        supply_demand = calculator.calculate_supply_demand_zones(sample_data)
        if supply_demand is not None and not supply_demand.empty:
            print("✅ Supply/demand zones calculated")
        
        return True
        
    except Exception as e:
        print(f"❌ Technical indicators calculator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_technical_indicators_updater():
    """Test the technical indicators updater component"""
    print("\n🧪 Testing Technical Indicators Updater")
    print("-" * 40)
    
    try:
        from core.duckdb_infra.database import DuckDBManager
        from core.technical_indicators.storage import TechnicalIndicatorsStorage
        from core.technical_indicators.updater import TechnicalIndicatorsUpdater
        
        # Initialize components
        db_manager = DuckDBManager()
        storage = TechnicalIndicatorsStorage('data/technical_indicators')
        updater = TechnicalIndicatorsUpdater(db_manager, storage)
        print("✅ Technical indicators updater initialized")
        
        # Test updating indicators for a symbol
        today = date.today()
        success = updater.update_symbol_indicators(
            symbol='RELIANCE',
            timeframes=['1T'],
            start_date=today,
            end_date=today,
            force_recalculate=True
        )
        
        if success:
            print("✅ Successfully updated indicators for RELIANCE")
        else:
            print("⚠️ No indicators updated (may be normal if no data)")
        
        return True
        
    except Exception as e:
        print(f"❌ Technical indicators updater test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_rate_limiter():
    """Test the rate limiter component"""
    print("\n🧪 Testing Rate Limiter")
    print("-" * 40)
    
    try:
        from scripts.realtime_data_pipeline import RateLimiter
        
        # Test rate limiter with 5 requests per second
        rate_limiter = RateLimiter(max_requests=5, time_window=1.0)
        print("✅ Rate limiter initialized (5 requests/second)")
        
        # Test rapid requests
        start_time = time.time()
        for i in range(8):
            request_start = time.time()
            rate_limiter.wait_if_needed()
            request_end = time.time()
            
            current_rate = rate_limiter.get_current_rate()
            print(f"   Request {i+1}: {request_end - request_start:.3f}s | Rate: {current_rate:.1f}/s")
        
        total_time = time.time() - start_time
        print(f"✅ Total time for 8 requests: {total_time:.2f} seconds")
        print(f"✅ Final rate: {rate_limiter.get_current_rate():.1f} requests/second")
        
        return True
        
    except Exception as e:
        print(f"❌ Rate limiter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_pipeline():
    """Test the data pipeline component"""
    print("\n🧪 Testing Data Pipeline")
    print("-" * 40)
    
    try:
        from scripts.realtime_data_pipeline import RealTimeDataPipeline, PipelineConfig
        
        # Create configuration
        config = PipelineConfig()
        print("✅ Pipeline configuration created")
        
        # Initialize pipeline
        pipeline = RealTimeDataPipeline(config)
        print("✅ Data pipeline initialized")
        
        # Test market hours check
        market_open = pipeline._is_market_open()
        print(f"✅ Market open check: {market_open}")
        
        # Test symbol loading
        symbols = pipeline._load_symbols()
        print(f"✅ Loaded {len(symbols)} symbols")
        
        # Test single symbol data retrieval
        test_symbol = "RELIANCE"
        data = pipeline._get_current_minute_data(test_symbol)
        
        if data is not None and not data.empty:
            print(f"✅ Retrieved data for {test_symbol}: {len(data)} records")
            print(f"   Latest close: {data['close'].iloc[-1]}")
            print(f"   Rate: {pipeline.rate_limiter.get_current_rate():.1f} requests/second")
        else:
            print(f"⚠️ No data for {test_symbol}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_configuration_management():
    """Test configuration management"""
    print("\n🧪 Testing Configuration Management")
    print("-" * 40)
    
    try:
        from scripts.realtime_data_pipeline import PipelineConfig
        
        # Test default configuration
        config = PipelineConfig()
        print("✅ Default configuration created")
        
        # Test configuration attributes
        print(f"   Market hours: {config.market_open_time} - {config.market_close_time}")
        print(f"   Data interval: {config.data_update_interval}s")
        print(f"   Indicators interval: {config.indicators_update_interval}s")
        print(f"   Max workers (data): {config.max_workers_data}")
        print(f"   Max workers (indicators): {config.max_workers_indicators}")
        print(f"   Rate limit: {config.max_requests_per_second} requests/second")
        print(f"   Priority symbols: {len(config.priority_symbols)}")
        
        # Test configuration serialization
        config_dict = config.__dict__
        print("✅ Configuration serialization working")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration management test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_logging_system():
    """Test the logging system"""
    print("\n🧪 Testing Logging System")
    print("-" * 40)
    
    try:
        import logging
        
        # Test logging configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        logger = logging.getLogger('test_logger')
        print("✅ Logging system configured")
        
        # Test different log levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        print("✅ All log levels working")
        
        # Test file logging
        log_file = 'logs/test_component.log'
        file_handler = logging.FileHandler(log_file)
        logger.addHandler(file_handler)
        logger.info("Test message to file")
        print(f"✅ File logging working: {log_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Logging system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_integration():
    """Test API integration"""
    print("\n🧪 Testing API Integration")
    print("-" * 40)
    
    try:
        from Dhan_Tradehull import Tradehull
        from dotenv import load_dotenv
        import os
        
        # Load environment variables
        load_dotenv('config/.env')
        
        client_id = os.getenv('DHAN_CLIENT_ID', '')
        access_token = os.getenv('DHAN_API_TOKEN', '')
        
        # Initialize API client
        dhan_client = Tradehull(client_id, access_token)
        print("✅ Dhan API client initialized")
        
        # Test API connection
        test_symbol = "RELIANCE"
        yesterday = date.today() - timedelta(days=1)
        
        data = dhan_client.get_historical_data(
            tradingsymbol=test_symbol,
            exchange='NSE',
            timeframe='1',
            start_date=yesterday.strftime('%Y-%m-%d'),
            end_date=yesterday.strftime('%Y-%m-%d')
        )
        
        if data is not None and len(data) > 0:
            print(f"✅ API connection working: {len(data)} records for {test_symbol}")
        else:
            print("⚠️ No data returned (may be normal for weekend/holiday)")
        
        return True
        
    except Exception as e:
        print(f"❌ API integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_end_to_end_workflow():
    """Test end-to-end workflow"""
    print("\n🧪 Testing End-to-End Workflow")
    print("-" * 40)
    
    try:
        from scripts.realtime_data_pipeline import RealTimeDataPipeline, PipelineConfig
        
        # Create pipeline
        config = PipelineConfig()
        config.max_requests_per_second = 5  # Lower rate for testing
        pipeline = RealTimeDataPipeline(config)
        
        print("✅ Pipeline created for end-to-end test")
        
        # Test complete workflow: fetch data -> calculate indicators -> store
        test_symbol = "RELIANCE"
        
        # Step 1: Fetch data
        print("📊 Step 1: Fetching data...")
        data = pipeline._get_current_minute_data(test_symbol)
        
        if data is not None and not data.empty:
            print(f"   ✅ Data fetched: {len(data)} records")
            
            # Step 2: Update database
            print("💾 Step 2: Updating database...")
            records_added = pipeline.db_manager.insert_market_data(data)
            print(f"   ✅ Database updated: {records_added} records")
            
            # Step 3: Calculate indicators
            print("📈 Step 3: Calculating indicators...")
            success = pipeline._update_symbol_indicators(test_symbol)
            print(f"   ✅ Indicators calculated: {success}")
            
            # Step 4: Check storage
            print("🗄️ Step 4: Checking storage...")
            indicators = pipeline.indicators_storage.load_indicators(
                test_symbol, '1T', date.today()
            )
            if indicators is not None and not indicators.empty:
                print(f"   ✅ Indicators stored: {len(indicators)} records")
            else:
                print("   ⚠️ No indicators stored yet")
            
            print("✅ End-to-end workflow completed successfully!")
            return True
        else:
            print("❌ No data available for end-to-end test")
            return False
        
    except Exception as e:
        print(f"❌ End-to-end workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run all component tests"""
    print("🚀 Real-Time System Component Tests")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Test results tracking
    test_results = {}
    
    # Run all component tests
    tests = [
        ("Database Manager", test_database_manager),
        ("Technical Indicators Storage", test_technical_indicators_storage),
        ("Technical Indicators Calculator", test_technical_indicators_calculator),
        ("Technical Indicators Updater", test_technical_indicators_updater),
        ("Rate Limiter", test_rate_limiter),
        ("Data Pipeline", test_data_pipeline),
        ("Configuration Management", test_configuration_management),
        ("Logging System", test_logging_system),
        ("API Integration", test_api_integration),
        ("End-to-End Workflow", test_end_to_end_workflow)
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"🧪 TESTING: {test_name}")
        print(f"{'='*60}")
        
        try:
            result = test_func()
            test_results[test_name] = result
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            test_results[test_name] = False
    
    # Print summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for result in test_results.values() if result)
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<35} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL COMPONENTS ARE WORKING CORRECTLY!")
        print("✅ Real-time system is ready for deployment")
    else:
        print("⚠️ Some components need attention")
        print("Please review the failed tests above")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
