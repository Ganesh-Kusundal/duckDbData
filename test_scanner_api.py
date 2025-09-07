#!/usr/bin/env python3
"""
Scanner API Test Script
======================

Test script to verify the Scanner API functionality.
Run this script to test all major API endpoints.
"""

import requests
import json
import time
from datetime import date, datetime
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1/scanner"
TEST_SYMBOLS = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ITC"]

def test_api_health() -> bool:
    """Test API health endpoint."""
    print("🔍 Testing API Health...")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Health: {data['status']} - {data['available_symbols']} symbols available")
            return True
        else:
            print(f"❌ API Health Check Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API Health Check Error: {e}")
        return False

def test_get_scanners() -> bool:
    """Test get available scanners endpoint."""
    print("\n🔍 Testing Get Available Scanners...")
    try:
        response = requests.get(f"{API_BASE_URL}/scanners", timeout=10)
        if response.status_code == 200:
            scanners = response.json()
            print(f"✅ Found {len(scanners)} available scanners:")
            for scanner in scanners:
                status = "🟢" if scanner['is_available'] else "🔴"
                print(f"   {status} {scanner['scanner_name']} - Success Rate: {scanner['success_rate']}%")
            return True
        else:
            print(f"❌ Get Scanners Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Get Scanners Error: {e}")
        return False

def test_market_overview() -> bool:
    """Test market overview endpoint."""
    print("\n🔍 Testing Market Overview...")
    try:
        response = requests.get(f"{API_BASE_URL}/market-overview", timeout=10)
        if response.status_code == 200:
            overview = response.json()
            print(f"✅ Market Overview:")
            print(f"   📊 Total Symbols: {overview['total_symbols']}")
            print(f"   📈 Advancing: {overview['advancing_count']}")
            print(f"   📉 Declining: {overview['declining_count']}")
            print(f"   🚀 Breakout Candidates: {overview['breakout_candidates']}")
            print(f"   💹 Market Sentiment: {overview['market_sentiment']}")
            print(f"   🎯 Top Sector: {overview['top_sector']}")
            return True
        else:
            print(f"❌ Market Overview Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Market Overview Error: {e}")
        return False

def test_get_symbols() -> bool:
    """Test get symbols endpoint."""
    print("\n🔍 Testing Get Symbols...")
    try:
        response = requests.get(f"{API_BASE_URL}/symbols?limit=10", timeout=10)
        if response.status_code == 200:
            symbols = response.json()
            print(f"✅ Retrieved {len(symbols)} symbols: {', '.join(symbols[:5])}...")
            return True
        else:
            print(f"❌ Get Symbols Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Get Symbols Error: {e}")
        return False

def test_default_config() -> bool:
    """Test get default configuration endpoint."""
    print("\n🔍 Testing Default Configuration...")
    try:
        response = requests.get(f"{API_BASE_URL}/config/default", timeout=10)
        if response.status_code == 200:
            config = response.json()
            print(f"✅ Default Configuration:")
            print(f"   📅 Consolidation Period: {config['consolidation_period']} days")
            print(f"   📊 Volume Ratio: {config['breakout_volume_ratio']}x")
            print(f"   💰 Price Range: ₹{config['min_price']} - ₹{config['max_price']}")
            print(f"   🎯 Max Results: {config['max_results_per_day']}")
            return True
        else:
            print(f"❌ Default Config Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Default Config Error: {e}")
        return False

def test_validate_config() -> bool:
    """Test configuration validation endpoint."""
    print("\n🔍 Testing Configuration Validation...")
    try:
        test_config = {
            "consolidation_period": 5,
            "breakout_volume_ratio": 1.5,
            "resistance_break_pct": 0.5,
            "min_price": 50,
            "max_price": 2000,
            "max_results_per_day": 3,
            "min_volume": 10000,
            "min_probability_score": 10.0
        }
        
        response = requests.post(
            f"{API_BASE_URL}/config/validate",
            json=test_config,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['valid']:
                print(f"✅ Configuration Validation: {result['message']}")
                return True
            else:
                print(f"❌ Configuration Invalid: {result['message']}")
                return False
        else:
            print(f"❌ Config Validation Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Config Validation Error: {e}")
        return False

def test_single_day_scan() -> Dict[str, Any]:
    """Test single day scan endpoint."""
    print("\n🔍 Testing Single Day Scan...")
    try:
        scan_request = {
            "scanner_type": "enhanced_breakout",
            "scan_date": date.today().isoformat(),
            "cutoff_time": "09:50:00",
            "symbols": TEST_SYMBOLS,
            "config": {
                "max_results_per_day": 5,
                "min_probability_score": 10.0
            }
        }
        
        print(f"   📅 Scanning date: {scan_request['scan_date']}")
        print(f"   🎯 Symbols: {', '.join(TEST_SYMBOLS)}")
        
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/scan",
            json=scan_request,
            timeout=30
        )
        execution_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Scan Completed:")
            print(f"   🆔 Scan ID: {result['scan_id']}")
            print(f"   📊 Total Results: {result['total_results']}")
            print(f"   ✅ Successful Breakouts: {result['successful_breakouts']}")
            print(f"   📈 Success Rate: {result['success_rate']}%")
            print(f"   💹 Avg Price Change: {result['avg_price_change']}%")
            print(f"   🎯 Avg Probability Score: {result['avg_probability_score']}")
            print(f"   ⏱️  Execution Time: {result['execution_time_ms']}ms (API: {execution_time:.0f}ms)")
            
            if result['results']:
                print(f"   🏆 Top Result: {result['results'][0]['symbol']} - {result['results'][0]['probability_score']:.1f}%")
            
            return result
        else:
            print(f"❌ Single Day Scan Failed: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   Error: {error_detail.get('detail', 'Unknown error')}")
            except:
                print(f"   Raw response: {response.text}")
            return {}
    except Exception as e:
        print(f"❌ Single Day Scan Error: {e}")
        return {}

def test_date_range_scan() -> Dict[str, Any]:
    """Test date range scan endpoint."""
    print("\n🔍 Testing Date Range Scan...")
    try:
        from datetime import timedelta
        
        end_date = date.today()
        start_date = end_date - timedelta(days=2)  # 3-day range
        
        scan_request = {
            "scanner_type": "enhanced_breakout",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "cutoff_time": "09:50:00",
            "end_of_day_time": "15:15:00",
            "symbols": TEST_SYMBOLS[:3],  # Limit to 3 symbols for faster testing
            "config": {
                "max_results_per_day": 2,
                "min_probability_score": 5.0
            }
        }
        
        print(f"   📅 Date Range: {start_date} to {end_date}")
        print(f"   🎯 Symbols: {', '.join(TEST_SYMBOLS[:3])}")
        
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/scan",
            json=scan_request,
            timeout=60  # Longer timeout for date range
        )
        execution_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Date Range Scan Completed:")
            print(f"   🆔 Scan ID: {result['scan_id']}")
            print(f"   📊 Total Results: {result['total_results']}")
            print(f"   ✅ Successful Breakouts: {result['successful_breakouts']}")
            print(f"   📈 Success Rate: {result['success_rate']}%")
            print(f"   💹 Avg Price Change: {result['avg_price_change']}%")
            print(f"   ⏱️  Execution Time: {result['execution_time_ms']}ms (API: {execution_time:.0f}ms)")
            
            return result
        else:
            print(f"❌ Date Range Scan Failed: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   Error: {error_detail.get('detail', 'Unknown error')}")
            except:
                print(f"   Raw response: {response.text}")
            return {}
    except Exception as e:
        print(f"❌ Date Range Scan Error: {e}")
        return {}

def test_performance_stats() -> bool:
    """Test performance statistics endpoint."""
    print("\n🔍 Testing Performance Statistics...")
    try:
        response = requests.get(f"{API_BASE_URL}/stats/performance?days=30", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Performance Statistics (30 days):")
            print(f"   📊 Total Scans: {stats['total_scans']}")
            print(f"   🎯 Breakouts Found: {stats['total_breakouts_found']}")
            print(f"   📈 Overall Success Rate: {stats['overall_success_rate']}%")
            print(f"   💹 Avg Price Change: {stats['avg_price_change']}%")
            print(f"   🏆 Top Symbols: {', '.join(stats['top_symbols'])}")
            print(f"   ⏱️  Avg Execution Time: {stats['avg_execution_time_ms']}ms")
            return True
        else:
            print(f"❌ Performance Stats Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Performance Stats Error: {e}")
        return False

def test_batch_scan() -> bool:
    """Test batch scan endpoint."""
    print("\n🔍 Testing Batch Scan...")
    try:
        from datetime import timedelta
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        batch_requests = [
            {
                "scanner_type": "enhanced_breakout",
                "scan_date": today.isoformat(),
                "cutoff_time": "09:50:00",
                "symbols": TEST_SYMBOLS[:2],
                "config": {"max_results_per_day": 2}
            },
            {
                "scanner_type": "enhanced_breakout",
                "scan_date": yesterday.isoformat(),
                "cutoff_time": "09:50:00",
                "symbols": TEST_SYMBOLS[:2],
                "config": {"max_results_per_day": 2}
            }
        ]
        
        print(f"   📅 Batch scanning 2 dates with {len(TEST_SYMBOLS[:2])} symbols each")
        
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/batch-scan?max_concurrent=2",
            json=batch_requests,
            timeout=60
        )
        execution_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            results = response.json()
            print(f"✅ Batch Scan Completed:")
            print(f"   📊 Completed Scans: {len(results)}")
            print(f"   ⏱️  Total Execution Time: {execution_time:.0f}ms")
            
            for i, result in enumerate(results):
                print(f"   📋 Scan {i+1}: {result['total_results']} results, {result['execution_time_ms']}ms")
            
            return True
        else:
            print(f"❌ Batch Scan Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Batch Scan Error: {e}")
        return False

def run_all_tests():
    """Run all API tests."""
    print("🚀 Starting Scanner API Tests")
    print("=" * 50)
    
    test_results = []
    
    # Basic functionality tests
    test_results.append(("API Health", test_api_health()))
    test_results.append(("Get Scanners", test_get_scanners()))
    test_results.append(("Market Overview", test_market_overview()))
    test_results.append(("Get Symbols", test_get_symbols()))
    test_results.append(("Default Config", test_default_config()))
    test_results.append(("Validate Config", test_validate_config()))
    
    # Core scanning tests
    single_scan_result = test_single_day_scan()
    test_results.append(("Single Day Scan", bool(single_scan_result)))
    
    date_range_result = test_date_range_scan()
    test_results.append(("Date Range Scan", bool(date_range_result)))
    
    # Additional functionality tests
    test_results.append(("Performance Stats", test_performance_stats()))
    test_results.append(("Batch Scan", test_batch_scan()))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! Scanner API is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the API server and database connection.")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)