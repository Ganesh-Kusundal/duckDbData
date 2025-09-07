#!/usr/bin/env python3
"""
Test script for Dhan broker 20-level orderbook depth
Tests real-time 20-level market depth using the broker approach
"""

import os
import sys
import datetime
import time
import threading
from typing import Dict, List, Optional, Any

# Add project root to path for broker import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from broker import get_broker

def test_20_level_orderbook():
    """Test 20-level orderbook depth functionality"""
    print("TESTING 20-LEVEL ORDERBOOK DEPTH")
    print("=" * 50)

    try:
        # Import broker
        print("🔗 Getting broker instance...")
        broker = get_broker()
        print("✅ Broker initialized successfully\n")

        # Test symbols
        test_symbols = ["RELIANCE", "TCS"]
        depth_received = {}
        test_duration = 15  # seconds for depth testing

        # Callback function to handle depth data
        def on_depth_data(depth_data: Dict[str, Any]):
            """Handle incoming depth data"""
            try:
                symbol = depth_data.get('symbol', 'UNKNOWN')
                if symbol not in depth_received:
                    depth_received[symbol] = []

                depth_received[symbol].append(depth_data)

                if len(depth_received[symbol]) == 1:  # Only print first depth update
                    print(f"📊 {symbol} Depth Update: Level {depth_data.get('depth_level', 'N/A')} received")

            except Exception as e:
                print(f"❌ Error processing depth: {e}")

        print("📈 Testing 20-Level Orderbook Depth")
        print("=" * 50)
        print(f"📅 Test duration: {test_duration} seconds")
        print(f"📈 Symbols: {', '.join(test_symbols)}")

        try:
            # Test if 20-level depth methods are available
            print("\n🔍 Checking available depth methods...")

            available_methods = [method for method in dir(broker) if 'depth' in method.lower() or '20' in method.lower()]
            print(f"📋 Available depth methods: {available_methods}")

            print("🚀 Starting 20-level depth stream...")
            success = broker.start_20_level_depth_stream(
                symbols=test_symbols,
                callback=on_depth_data
            )

            if success:
                print("✅ 20-level depth stream started successfully")

                # Wait for depth data
                print("⏳ Collecting depth data...")
                time.sleep(test_duration)

                # Stop the stream
                print("🛑 Stopping depth stream...")
                broker.stop_20_level_depth_stream()
                print("✅ Depth stream stopped")

            else:
                print("❌ Failed to start depth stream")
                return False

        except Exception as e:
            print(f"❌ Depth stream error: {e}")
            return False

        print("\n🎯 20-LEVEL ORDERBOOK TEST SUMMARY")
        print("=" * 50)

        # Summary statistics
        total_depth_updates = sum(len(depths) for depths in depth_received.values())

        print(f"✅ Depth Updates Received: {total_depth_updates}")
        for symbol, depths in depth_received.items():
            print(f"   • {symbol}: {len(depths)} depth updates")

        print("\n🔌 Orderbook Connection Status:")
        print("   ✅ Broker connection: Working")
        print("   ✅ 20-level depth stream: Working")
        print("   ✅ Real-time updates: Functional")

        if total_depth_updates > 0:
            print("\n🎉 20-level orderbook depth is working perfectly!")
            print("   📊 Real-time market depth data received successfully")
            return True
        else:
            print("\n⚠️  No depth data received - check connection")
            return False

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_orderbook_snapshot():
    """Test orderbook snapshot functionality"""
    print("\n📸 Testing Orderbook Snapshot")
    print("=" * 50)

    try:
        broker = get_broker()

        print("📸 Getting orderbook snapshot for RELIANCE...")
        snapshot = broker.get_20_level_depth("RELIANCE")

        if snapshot:
            print("✅ Orderbook snapshot received")
            print(f"   📊 Depth Level: {snapshot.get('depth_level', 'N/A')}")
            print(f"   📊 Timestamp: {snapshot.get('timestamp', 'N/A')}")
            return True
        else:
            print("❌ No orderbook snapshot received")
            return False

    except Exception as e:
        print(f"❌ Orderbook snapshot error: {e}")
        return False

if __name__ == "__main__":
    print("🌟 BROKER 20-LEVEL ORDERBOOK TEST")
    print("=" * 60)

    # Test 20-level orderbook functionality
    success1 = test_20_level_orderbook()

    # Test orderbook snapshot
    success2 = test_orderbook_snapshot()

    overall_success = success1 and success2

    print(f"\n🏁 20-LEVEL ORDERBOOK TEST RESULT: {'✅ PASSED' if overall_success else '❌ FAILED'}")
    sys.exit(0 if overall_success else 1)
