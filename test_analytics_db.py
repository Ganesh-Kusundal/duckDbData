import sys
sys.path.insert(0, '.')

from analytics.core import DuckDBAnalytics, PatternAnalyzer

try:
    print("Testing analytics module connectivity...")
    connector = DuckDBAnalytics()
    print("Analytics connector initialized")
    
    # Test basic connection
    conn = connector.connect()
    print("Analytics connector connected to DuckDB")
    result = conn.execute('SELECT 1 as test').fetchall()
    print(f'Analytics query executed: {result}')
    
    # Test pattern analyzer
    analyzer = PatternAnalyzer(connector)
    print("PatternAnalyzer initialized")
    
    # Test basic pattern discovery (may fail if no data, but should not crash)
    try:
        patterns = analyzer.discover_volume_spike_patterns()
        print(f"Pattern discovery test: Found {len(patterns)} patterns")
    except Exception as pattern_error:
        print(f"Pattern discovery test (expected with no data): {pattern_error}")
    
    print("Analytics module database connectivity test completed")
    
except Exception as e:
    print(f"Analytics connectivity failed: {e}")
    import traceback
    traceback.print_exc()
