#!/usr/bin/env python3
"""
Test Rate Limiting
Test the rate limiting functionality in the real-time pipeline
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from scripts.realtime_data_pipeline import RateLimiter

def test_rate_limiter():
    """Test the rate limiter functionality"""
    print("🧪 Testing Rate Limiter")
    print("=" * 50)
    
    # Test with 10 requests per second
    rate_limiter = RateLimiter(max_requests=10, time_window=1.0)
    
    print(f"Rate limit: {rate_limiter.max_requests} requests per {rate_limiter.time_window} second")
    print()
    
    # Test rapid requests
    print("📊 Testing rapid requests (should be rate limited):")
    start_time = time.time()
    
    for i in range(15):
        request_start = time.time()
        rate_limiter.wait_if_needed()
        request_end = time.time()
        
        current_rate = rate_limiter.get_current_rate()
        print(f"Request {i+1:2d}: {request_end - request_start:.3f}s | Current rate: {current_rate:.1f} req/s")
    
    total_time = time.time() - start_time
    print(f"\n⏱️ Total time for 15 requests: {total_time:.2f} seconds")
    print(f"📈 Average rate: {15/total_time:.1f} requests/second")
    
    # Test rate over time
    print("\n📊 Testing rate over time:")
    time.sleep(2)  # Wait for window to clear
    
    for i in range(5):
        rate_limiter.wait_if_needed()
        current_rate = rate_limiter.get_current_rate()
        print(f"Request {i+1}: Current rate: {current_rate:.1f} req/s")
        time.sleep(0.2)
    
    print("\n✅ Rate limiter test completed!")

if __name__ == "__main__":
    test_rate_limiter()
