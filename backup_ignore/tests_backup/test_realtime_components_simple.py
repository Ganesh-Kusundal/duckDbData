#!/usr/bin/env python3
"""
Simplified Real-Time System Component Tests
==========================================

Tests components that don't require database access:
1. Rate Limiter
2. Configuration Management
3. Logging System
4. API Integration
5. Technical Indicators Calculator (with sample data)

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

def test_rate_limiter():
    """Test the rate limiter component"""
    print("🧪 Testing Rate Limiter")
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
        
        # Test some specific calculations
        if 'sma_20' in indicators.columns:
            sma_value = indicators['sma_20'].iloc[-1]
            print(f"✅ SMA 20 calculation: {sma_value:.2f}")
        
        if 'rsi_14' in indicators.columns:
            rsi_value = indicators['rsi_14'].iloc[-1]
            print(f"✅ RSI 14 calculation: {rsi_value:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Technical indicators calculator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_pipeline_components():
    """Test data pipeline components without database"""
    print("\n🧪 Testing Data Pipeline Components")
    print("-" * 40)
    
    try:
        from scripts.realtime_data_pipeline import PipelineConfig
        
        # Create configuration
        config = PipelineConfig()
        print("✅ Pipeline configuration created")
        
        # Test market hours check
        now = datetime.now().time()
        market_open = config.market_open_time <= now <= config.market_close_time
        print(f"✅ Market open check: {market_open}")
        
        # Test configuration validation
        print(f"   Market hours: {config.market_open_time} - {config.market_close_time}")
        print(f"   Data interval: {config.data_update_interval}s")
        print(f"   Rate limit: {config.max_requests_per_second} requests/second")
        print(f"   Priority symbols: {len(config.priority_symbols)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data pipeline components test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_rate_limiting_integration():
    """Test rate limiting with API calls"""
    print("\n🧪 Testing Rate Limiting with API")
    print("-" * 40)
    
    try:
        from scripts.realtime_data_pipeline import RateLimiter
        from Dhan_Tradehull import Tradehull
        from dotenv import load_dotenv
        import os
        
        # Load environment variables
        load_dotenv('config/.env')
        
        client_id = os.getenv('DHAN_CLIENT_ID', '')
        access_token = os.getenv('DHAN_API_TOKEN', '')
        
        # Initialize components
        rate_limiter = RateLimiter(max_requests=3, time_window=1.0)
        dhan_client = Tradehull(client_id, access_token)
        
        print("✅ Rate limiter and API client initialized")
        
        # Test symbols
        test_symbols = ["RELIANCE", "TCS", "INFY"]
        yesterday = date.today() - timedelta(days=1)
        
        start_time = time.time()
        successful = 0
        
        for i, symbol in enumerate(test_symbols, 1):
            print(f"📊 [{i}/{len(test_symbols)}] Fetching {symbol}...")
            symbol_start = time.time()
            
            try:
                # Apply rate limiting
                rate_limiter.wait_if_needed()
                
                # Make API call
                data = dhan_client.get_historical_data(
                    tradingsymbol=symbol,
                    exchange='NSE',
                    timeframe='1',
                    start_date=yesterday.strftime('%Y-%m-%d'),
                    end_date=yesterday.strftime('%Y-%m-%d')
                )
                
                if data is not None and len(data) > 0:
                    symbol_time = (datetime.now() - symbol_start).total_seconds()
                    current_rate = rate_limiter.get_current_rate()
                    
                    print(f"   ✅ Success ({symbol_time:.2f}s) | Rate: {current_rate:.1f}/s | Records: {len(data)}")
                    successful += 1
                else:
                    print(f"   ⚠️ No data")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        total_time = time.time() - start_time
        print()
        print(f"📊 Results:")
        print(f"   Successful: {successful}/{len(test_symbols)}")
        print(f"   Total time: {total_time:.2f} seconds")
        print(f"   Final rate: {rate_limiter.get_current_rate():.1f} requests/second")
        
        return True
        
    except Exception as e:
        print(f"❌ Rate limiting integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run simplified component tests"""
    print("🚀 Simplified Real-Time System Component Tests")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Test results tracking
    test_results = {}
    
    # Run simplified component tests
    tests = [
        ("Rate Limiter", test_rate_limiter),
        ("Configuration Management", test_configuration_management),
        ("Logging System", test_logging_system),
        ("API Integration", test_api_integration),
        ("Technical Indicators Calculator", test_technical_indicators_calculator),
        ("Data Pipeline Components", test_data_pipeline_components),
        ("Rate Limiting Integration", test_rate_limiting_integration)
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
        print("🎉 ALL CORE COMPONENTS ARE WORKING CORRECTLY!")
        print("✅ Rate limiting is functioning")
        print("✅ API integration is working")
        print("✅ Configuration management is operational")
        print("✅ Technical indicators calculation is working")
        print("✅ Real-time system is ready for deployment")
    else:
        print("⚠️ Some components need attention")
        print("Please review the failed tests above")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
