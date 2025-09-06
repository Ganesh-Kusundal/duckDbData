#!/usr/bin/env python3
"""
Pipeline Status Monitor
======================

Comprehensive status monitoring for the real-time data pipeline.
Shows detailed information about pipeline health, rate limiting, data processing, and system performance.

Author: AI Assistant
Date: 2025-09-04
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
import requests
from typing import Dict, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

def get_pipeline_status() -> Optional[Dict]:
    """Get status from the pipeline scheduler API"""
    try:
        response = requests.get('http://localhost:8001/status', timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API returned status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to connect to pipeline API: {e}")
        return None

def get_health_status() -> Optional[Dict]:
    """Get health status from the pipeline"""
    try:
        response = requests.get('http://localhost:8001/health', timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.exceptions.RequestException:
        return None

def get_metrics() -> Optional[Dict]:
    """Get detailed metrics from the pipeline"""
    try:
        response = requests.get('http://localhost:8001/metrics', timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.exceptions.RequestException:
        return None

def format_duration(seconds: float) -> str:
    """Format duration in human readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def format_rate(rate: float) -> str:
    """Format rate in human readable format"""
    if rate >= 1:
        return f"{rate:.1f}/s"
    else:
        return f"{rate*60:.1f}/min"

def print_status_header():
    """Print status header"""
    print("=" * 80)
    print("📊 REAL-TIME PIPELINE STATUS MONITOR")
    print("=" * 80)
    print(f"🕐 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def print_system_status(status: Dict):
    """Print system status"""
    print("🔧 SYSTEM STATUS")
    print("-" * 40)
    
    scheduler = status.get('scheduler', {})
    pipeline = status.get('pipeline', {})
    market = status.get('market', {})
    
    # System running status
    system_running = scheduler.get('running', False)
    print(f"System Running: {'✅ Yes' if system_running else '❌ No'}")
    
    # Market status
    market_open = market.get('is_open', False)
    print(f"Market Status: {'🟢 Open' if market_open else '🔴 Closed'}")
    
    if market_open:
        next_close = market.get('next_close')
        if next_close:
            close_time = datetime.fromisoformat(next_close.replace('Z', '+00:00'))
            time_until_close = close_time - datetime.now()
            print(f"Time until close: {format_duration(time_until_close.total_seconds())}")
    
    # Uptime
    if 'stats' in scheduler:
        start_time = datetime.fromisoformat(scheduler['stats']['start_time'].replace('Z', '+00:00'))
        uptime = datetime.now() - start_time
        print(f"System Uptime: {format_duration(uptime.total_seconds())}")
    
    print()

def print_rate_limiting_status(status: Dict):
    """Print rate limiting status"""
    print("🚦 RATE LIMITING")
    print("-" * 40)
    
    rate_limiting = status.get('rate_limiting', {})
    if rate_limiting:
        max_rate = rate_limiting.get('max_requests_per_second', 0)
        current_rate = rate_limiting.get('current_rate', 0)
        requests_in_window = rate_limiting.get('requests_in_window', 0)
        
        print(f"Max Rate: {max_rate} requests/second")
        print(f"Current Rate: {format_rate(current_rate)}")
        print(f"Requests in Window: {requests_in_window}")
        
        # Rate utilization
        if max_rate > 0:
            utilization = (current_rate / max_rate) * 100
            if utilization < 50:
                status_icon = "🟢"
            elif utilization < 80:
                status_icon = "🟡"
            else:
                status_icon = "🔴"
            print(f"Rate Utilization: {status_icon} {utilization:.1f}%")
    else:
        print("❌ Rate limiting data not available")
    
    print()

def print_pipeline_stats(status: Dict):
    """Print pipeline statistics"""
    print("📈 PIPELINE STATISTICS")
    print("-" * 40)
    
    pipeline = status.get('pipeline', {})
    stats = pipeline.get('stats', {})
    
    # Update counts
    data_updates = stats.get('data_updates', 0)
    indicator_updates = stats.get('indicator_updates', 0)
    errors = stats.get('errors', 0)
    
    print(f"Data Updates: {data_updates}")
    print(f"Indicator Updates: {indicator_updates}")
    print(f"Errors: {errors}")
    
    # Processing stats
    symbols_processed = stats.get('symbols_processed', 0)
    records_processed = stats.get('records_processed', 0)
    
    print(f"Symbols Processed: {symbols_processed}")
    print(f"Records Processed: {records_processed}")
    
    # Last update times
    last_data_update = stats.get('last_data_update')
    last_indicator_update = stats.get('last_indicator_update')
    
    if last_data_update:
        last_data_time = datetime.fromisoformat(last_data_update.replace('Z', '+00:00'))
        time_since_data = datetime.now() - last_data_time
        print(f"Last Data Update: {format_duration(time_since_data.total_seconds())} ago")
    
    if last_indicator_update:
        last_indicator_time = datetime.fromisoformat(last_indicator_update.replace('Z', '+00:00'))
        time_since_indicator = datetime.now() - last_indicator_time
        print(f"Last Indicator Update: {format_duration(time_since_indicator.total_seconds())} ago")
    
    print()

def print_symbols_status(status: Dict):
    """Print symbols status"""
    print("📋 SYMBOLS STATUS")
    print("-" * 40)
    
    pipeline = status.get('pipeline', {})
    
    total_symbols = pipeline.get('symbols_count', 0)
    priority_symbols = pipeline.get('priority_symbols', [])
    failed_symbols_count = pipeline.get('failed_symbols_count', 0)
    
    print(f"Total Symbols: {total_symbols}")
    print(f"Priority Symbols: {len(priority_symbols)}")
    print(f"Failed Symbols: {failed_symbols_count}")
    
    if priority_symbols:
        print(f"Priority List: {', '.join(priority_symbols[:10])}")
        if len(priority_symbols) > 10:
            print(f"              ... and {len(priority_symbols) - 10} more")
    
    print()

def print_configuration(status: Dict):
    """Print configuration summary"""
    print("⚙️ CONFIGURATION")
    print("-" * 40)
    
    pipeline = status.get('pipeline', {})
    config = pipeline.get('config', {})
    
    # Market hours
    market_open_time = config.get('market_open_time', '09:15:00')
    market_close_time = config.get('market_close_time', '15:30:00')
    print(f"Market Hours: {market_open_time} - {market_close_time}")
    
    # Update intervals
    data_interval = config.get('data_update_interval', 60)
    indicators_interval = config.get('indicators_update_interval', 60)
    print(f"Data Update Interval: {data_interval}s")
    print(f"Indicators Update Interval: {indicators_interval}s")
    
    # Performance settings
    max_workers_data = config.get('max_workers_data', 8)
    max_workers_indicators = config.get('max_workers_indicators', 4)
    batch_size = config.get('batch_size', 50)
    print(f"Max Workers (Data): {max_workers_data}")
    print(f"Max Workers (Indicators): {max_workers_indicators}")
    print(f"Batch Size: {batch_size}")
    
    print()

def print_health_indicators(status: Dict):
    """Print health indicators"""
    print("🏥 HEALTH INDICATORS")
    print("-" * 40)
    
    scheduler = status.get('scheduler', {})
    pipeline = status.get('pipeline', {})
    
    # Scheduler health
    scheduler_health = scheduler.get('health_status', 'unknown')
    health_icon = "🟢" if scheduler_health == "healthy" else "🔴"
    print(f"Scheduler Health: {health_icon} {scheduler_health}")
    
    # Pipeline health
    pipeline_running = pipeline.get('running', False)
    pipeline_icon = "🟢" if pipeline_running else "🔴"
    print(f"Pipeline Running: {pipeline_icon} {'Yes' if pipeline_running else 'No'}")
    
    # Error rate
    stats = pipeline.get('stats', {})
    errors = stats.get('errors', 0)
    data_updates = stats.get('data_updates', 1)  # Avoid division by zero
    
    if data_updates > 0:
        error_rate = (errors / data_updates) * 100
        if error_rate < 5:
            error_icon = "🟢"
        elif error_rate < 10:
            error_icon = "🟡"
        else:
            error_icon = "🔴"
        print(f"Error Rate: {error_icon} {error_rate:.1f}%")
    
    # Restart attempts
    restart_attempts = scheduler.get('stats', {}).get('pipeline_restarts', 0)
    if restart_attempts > 0:
        print(f"Restart Attempts: {restart_attempts}")
    
    print()

def print_recent_activity(status: Dict):
    """Print recent activity summary"""
    print("📊 RECENT ACTIVITY")
    print("-" * 40)
    
    pipeline = status.get('pipeline', {})
    stats = pipeline.get('stats', {})
    
    # Activity summary
    data_updates = stats.get('data_updates', 0)
    indicator_updates = stats.get('indicator_updates', 0)
    symbols_processed = stats.get('symbols_processed', 0)
    records_processed = stats.get('records_processed', 0)
    
    if data_updates > 0:
        print(f"✅ Data updates running ({data_updates} cycles)")
    else:
        print("⚠️ No data updates yet")
    
    if indicator_updates > 0:
        print(f"✅ Indicator updates running ({indicator_updates} cycles)")
    else:
        print("⚠️ No indicator updates yet")
    
    if symbols_processed > 0:
        print(f"✅ Symbols being processed ({symbols_processed} total)")
    else:
        print("⚠️ No symbols processed yet")
    
    if records_processed > 0:
        print(f"✅ Records being stored ({records_processed} total)")
    else:
        print("⚠️ No records stored yet")
    
    print()

def print_data_directory_status():
    """Print data directory status"""
    print("📁 DATA DIRECTORY STATUS")
    print("-" * 40)
    
    data_dir = Path("data/2025/09")
    if data_dir.exists():
        days = [d for d in data_dir.iterdir() if d.is_dir()]
        days.sort()
        
        print(f"Data directory: {data_dir}")
        print(f"Days with data: {len(days)}")
        
        if days:
            latest_day = days[-1]
            print(f"Latest data: {latest_day.name}")
            
            # Check if today's data exists
            today = datetime.now().strftime("%d")
            if today in [d.name for d in days]:
                print("✅ Today's data directory exists")
            else:
                print("⚠️ Today's data directory not found")
        else:
            print("⚠️ No data directories found")
    else:
        print("❌ Data directory not found")
    
    print()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Pipeline Status Monitor')
    parser.add_argument('--refresh', type=int, default=0, 
                       help='Auto-refresh interval in seconds (0 = no refresh)')
    parser.add_argument('--json', action='store_true', 
                       help='Output status as JSON')
    parser.add_argument('--simple', action='store_true', 
                       help='Show simplified status')
    
    args = parser.parse_args()
    
    if args.json:
        # JSON output mode
        status = get_pipeline_status()
        if status:
            print(json.dumps(status, indent=2))
        else:
            print(json.dumps({"error": "Failed to get status"}, indent=2))
        return
    
    if args.simple:
        # Simple status mode
        status = get_pipeline_status()
        if status:
            pipeline = status.get('pipeline', {})
            running = pipeline.get('running', False)
            market_open = status.get('market', {}).get('is_open', False)
            data_updates = pipeline.get('stats', {}).get('data_updates', 0)
            symbols_processed = pipeline.get('stats', {}).get('symbols_processed', 0)
            
            print(f"Pipeline: {'✅ Running' if running else '❌ Stopped'}")
            print(f"Market: {'🟢 Open' if market_open else '🔴 Closed'}")
            print(f"Data Updates: {data_updates}")
            print(f"Symbols Processed: {symbols_processed}")
        else:
            print("❌ Failed to get status")
        return
    
    # Full status mode
    while True:
        # Clear screen (works on most terminals)
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print_status_header()
        
        status = get_pipeline_status()
        if status:
            print_system_status(status)
            print_rate_limiting_status(status)
            print_pipeline_stats(status)
            print_symbols_status(status)
            print_configuration(status)
            print_health_indicators(status)
            print_recent_activity(status)
            print_data_directory_status()
        else:
            print("❌ Failed to connect to pipeline API")
            print("Make sure the pipeline is running: python scripts/start_realtime_system.py")
            print()
        
        if args.refresh > 0:
            print(f"🔄 Auto-refreshing in {args.refresh} seconds... (Ctrl+C to stop)")
            try:
                time.sleep(args.refresh)
            except KeyboardInterrupt:
                print("\n👋 Status monitoring stopped")
                break
        else:
            break

if __name__ == "__main__":
    main()

