import sys
from datetime import date, time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.application.use_cases.scan_market import ScanMarketUseCase, ScanRequest
from src.application.scanners.strategies.breakout_scanner import BreakoutScanner
from src.application.scanners.strategies.technical_scanner import TechnicalScanner
from src.infrastructure.config.config_manager import ConfigManager
from src.infrastructure.adapters.duckdb_adapter import DuckDBAdapter

# Simple mocks for services that may not be essential for basic scan
class MockDataSyncService:
    def __init__(self, db_adapter):
        self.db_adapter = db_adapter

class MockEventBus:
    def publish(self, event):
        print(f"Published event: {event['event_type']}")

# Initialize components with real config and DB
config_dir = "configs"
config_manager = ConfigManager(config_dir=config_dir)

db_adapter = DuckDBAdapter(config_manager=config_manager)
market_data_repo = db_adapter  # Use adapter as repository
data_sync_service = MockDataSyncService(db_adapter)
event_bus = MockEventBus()

use_case = ScanMarketUseCase(
    market_data_repo=market_data_repo,
    data_sync_service=data_sync_service,
    event_bus=event_bus,
    config_manager=config_manager
)

# Register scanners
use_case.register_scanner_strategy('breakout', BreakoutScanner)
use_case.register_scanner_strategy('technical', TechnicalScanner)

# Create scan request for a past date with data (2015-03-02 from data directory)
request = ScanRequest(
    scan_date=date(2015, 3, 2),
    cutoff_time=time(10, 0),
    scanner_types=['breakout', 'technical']
)

try:
    print("Running real market scan with actual DB data...")
    result = use_case.execute(request)
    
    print(f"\nScan completed successfully!")
    print(f"Total stocks found: {result.total_stocks_found}")
    print(f"Successful scanners: {result.successful_scanners}")
    print(f"Execution time: {result.execution_time_seconds:.2f}s")
    
    if result.pattern_stats:
        print(f"Pattern stats: {result.pattern_stats}")
    
    for scanner_name, df in result.scanner_results.items():
        if not df.empty:
            print(f"\n{scanner_name.upper()} results:")
            print(df.head().to_string())
            print(f"Total {len(df)} symbols found")
        else:
            print(f"\n{scanner_name.upper()}: No results")
    
    print("\nFeatures working: Scanners executed without errors using real data.")
    
except Exception as e:
    print(f"Scan failed: {e}")
    import traceback
    traceback.print_exc()
    print("Features not working: Error during execution with real data.")