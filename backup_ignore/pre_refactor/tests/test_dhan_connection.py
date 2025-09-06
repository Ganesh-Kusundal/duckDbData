#!/usr/bin/env python3
"""
Test Dhan API Connection
Simple script to test if Dhan API credentials are working
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, date, timedelta

# Add project root to path
sys.path.append(str(Path(__file__).parent))

try:
    from Dhan_Tradehull import Tradehull
    print("✅ Tradehull library imported successfully")
except ImportError as e:
    print(f"❌ Failed to import Tradehull: {e}")
    sys.exit(1)

def test_dhan_connection():
    """Test Dhan API connection with current credentials"""
    
    print("🔍 Testing Dhan API Connection...")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv('config/.env')
    
    client_id = os.getenv('DHAN_CLIENT_ID', '').strip()
    access_token = os.getenv('DHAN_API_TOKEN', '').strip()
    
    print(f"Client ID: {'*' * (len(client_id) - 4) + client_id[-4:] if len(client_id) > 4 else 'NOT SET'}")
    print(f"Access Token: {'*' * (len(access_token) - 4) + access_token[-4:] if len(access_token) > 4 else 'NOT SET'}")
    
    if not client_id or not access_token:
        print("❌ ERROR: Dhan credentials not found in config/.env")
        print("Please update config/.env with your DHAN_CLIENT_ID and DHAN_API_TOKEN")
        return False
    
    try:
        # Initialize Dhan client
        print("\n🔄 Initializing Dhan client...")
        dhan_client = Tradehull(client_id, access_token)
        print("✅ Dhan client initialized successfully")
        
        # Test with a simple API call - get historical data for a popular stock
        print("\n🔄 Testing API call with RELIANCE...")
        test_symbol = "RELIANCE"
        
        # Get data for yesterday (to ensure market was open)
        yesterday = date.today() - timedelta(days=1)
        
        data = dhan_client.get_historical_data(
            tradingsymbol=test_symbol,
            exchange='NSE',
            timeframe='1',  # 1-minute data
            start_date=yesterday.strftime('%Y-%m-%d'),
            end_date=yesterday.strftime('%Y-%m-%d')
        )
        
        if data is not None:
            # Handle both DataFrame and list responses
            if hasattr(data, 'empty'):  # DataFrame
                if not data.empty:
                    print(f"✅ SUCCESS! Retrieved {len(data)} records for {test_symbol}")
                    print(f"📊 DataFrame columns: {list(data.columns)}")
                    return True
            elif isinstance(data, list) and len(data) > 0:
                print(f"✅ SUCCESS! Retrieved {len(data)} records for {test_symbol}")
                print(f"📊 Sample data: {data[0]}")
                return True
        
        if data is None or (hasattr(data, 'empty') and data.empty) or (isinstance(data, list) and len(data) == 0):
            print(f"⚠️ WARNING: No data returned for {test_symbol} on {yesterday}")
            print("This might be normal if yesterday was a holiday/weekend")
            
            # Try with a different date (last Friday)
            print("\n🔄 Trying with last Friday...")
            last_friday = yesterday
            while last_friday.weekday() != 4:  # Friday is 4
                last_friday -= timedelta(days=1)
            
            data = dhan_client.get_historical_data(
                tradingsymbol=test_symbol,
                exchange='NSE',
                timeframe='1',
                start_date=last_friday.strftime('%Y-%m-%d'),
                end_date=last_friday.strftime('%Y-%m-%d')
            )
            
            if data is not None:
                if hasattr(data, 'empty'):  # DataFrame
                    if not data.empty:
                        print(f"✅ SUCCESS! Retrieved {len(data)} records for {test_symbol} on {last_friday}")
                        return True
                elif isinstance(data, list) and len(data) > 0:
                    print(f"✅ SUCCESS! Retrieved {len(data)} records for {test_symbol} on {last_friday}")
                    return True
            
            print(f"❌ No data returned even for {last_friday}")
            return False
                
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to Dhan API")
        print(f"Error details: {e}")
        
        # Check if it's an authentication error
        if "Invalid_Authentication" in str(e) or "DH-901" in str(e):
            print("\n💡 This looks like an authentication error.")
            print("Please check your DHAN_CLIENT_ID and DHAN_API_TOKEN in config/.env")
        
        return False

def main():
    """Main function"""
    print("🚀 Dhan API Connection Test")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    success = test_dhan_connection()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 CONNECTION TEST PASSED!")
        print("✅ Your Dhan API credentials are working correctly")
        print("✅ You can now run the real-time pipeline")
    else:
        print("❌ CONNECTION TEST FAILED!")
        print("Please check your credentials and try again")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
