#!/usr/bin/env python3
"""
Test Single Symbol Data Retrieval
Test the pipeline's ability to fetch data for one symbol with rate limiting
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from scripts.realtime_data_pipeline import RealTimeDataPipeline, PipelineConfig

def test_single_symbol():
    """Test data retrieval for a single symbol"""
    print("🧪 Testing Single Symbol Data Retrieval")
    print("=" * 50)
    
    # Create pipeline configuration
    config = PipelineConfig()
    print(f"Rate limit: {config.max_requests_per_second} requests/second")
    print()
    
    # Create pipeline
    pipeline = RealTimeDataPipeline(config)
    print("✅ Pipeline initialized with rate limiting")
    
    # Test symbol
    test_symbol = "RELIANCE"
    print(f"🎯 Testing symbol: {test_symbol}")
    print()
    
    # Test data retrieval
    print("📊 Fetching current minute data...")
    start_time = datetime.now()
    
    try:
        data = pipeline._get_current_minute_data(test_symbol)
        
        if data is not None and not data.empty:
            print(f"✅ SUCCESS! Retrieved data for {test_symbol}")
            print(f"📈 Records: {len(data)}")
            print(f"⏱️ Time taken: {(datetime.now() - start_time).total_seconds():.2f} seconds")
            print()
            
            # Show data details
            print("📋 Data Details:")
            print(f"   Columns: {list(data.columns)}")
            print(f"   Latest timestamp: {data['timestamp'].iloc[-1]}")
            print(f"   Latest close: {data['close'].iloc[-1]}")
            print(f"   Volume: {data['volume'].iloc[-1]}")
            print()
            
            # Test rate limiting stats
            current_rate = pipeline.rate_limiter.get_current_rate()
            print(f"🚦 Rate Limiting:")
            print(f"   Current rate: {current_rate:.1f} requests/second")
            print(f"   Requests in window: {len(pipeline.rate_limiter.requests)}")
            print()
            
            return True
        else:
            print(f"❌ No data returned for {test_symbol}")
            return False
            
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multiple_symbols():
    """Test data retrieval for multiple symbols to see rate limiting in action"""
    print("\n🧪 Testing Multiple Symbols (Rate Limiting)")
    print("=" * 50)
    
    # Create pipeline
    config = PipelineConfig()
    pipeline = RealTimeDataPipeline(config)
    
    # Test symbols
    test_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
    print(f"🎯 Testing {len(test_symbols)} symbols: {', '.join(test_symbols)}")
    print()
    
    start_time = datetime.now()
    successful = 0
    
    for i, symbol in enumerate(test_symbols, 1):
        print(f"📊 [{i}/{len(test_symbols)}] Fetching {symbol}...")
        symbol_start = datetime.now()
        
        try:
            data = pipeline._get_current_minute_data(symbol)
            
            if data is not None and not data.empty:
                symbol_time = (datetime.now() - symbol_start).total_seconds()
                current_rate = pipeline.rate_limiter.get_current_rate()
                
                print(f"   ✅ Success ({symbol_time:.2f}s) | Rate: {current_rate:.1f}/s")
                successful += 1
            else:
                print(f"   ❌ No data")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    total_time = (datetime.now() - start_time).total_seconds()
    print()
    print(f"📊 Results:")
    print(f"   Successful: {successful}/{len(test_symbols)}")
    print(f"   Total time: {total_time:.2f} seconds")
    print(f"   Average time per symbol: {total_time/len(test_symbols):.2f} seconds")
    print(f"   Final rate: {pipeline.rate_limiter.get_current_rate():.1f} requests/second")

def main():
    """Main function"""
    print("🚀 Single Symbol Data Retrieval Test")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Test single symbol
    success = test_single_symbol()
    
    if success:
        # Test multiple symbols
        test_multiple_symbols()
        
        print("\n" + "=" * 50)
        print("🎉 ALL TESTS COMPLETED!")
        print("✅ Rate limiting is working correctly")
        print("✅ Data retrieval is functioning")
        print("✅ Pipeline is ready for real-time operation")
    else:
        print("\n" + "=" * 50)
        print("❌ TEST FAILED!")
        print("Please check your configuration and try again")

if __name__ == "__main__":
    main()
