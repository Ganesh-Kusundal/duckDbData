#!/usr/bin/env python3
"""
Test script for breakout scanner with optimal settings.
Generated for testing on 2025-09-05 00:00:00
"""

import sys
from pathlib import Path
from datetime import date, time
import pandas as pd

# Setup path
current_dir = Path.cwd()
if current_dir.name == 'scanner':
    project_root = current_dir.parent.parent
elif current_dir.name == 'notebook':
    project_root = current_dir.parent
else:
    project_root = current_dir

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(project_root / 'src') not in sys.path:
    sys.path.insert(0, str(project_root / 'src'))

from src.infrastructure.logging import setup_logging
from src.application.scanners.strategies.breakout_scanner import BreakoutScanner
from src.infrastructure.core.database import DuckDBManager
from src.infrastructure.config.settings import get_settings

# Setup
setup_logging()
settings = get_settings()

# Initialize with optimal database
db_manager = DuckDBManager(db_path=str(project_root / "data" / "financial_data.duckdb"))
db_manager.create_schema()

# Initialize scanner with relaxed config
scanner = BreakoutScanner(db_manager=db_manager)

# Apply relaxed configuration
scanner.config.update({'resistance_break_pct': 0.5, 'breakout_volume_ratio': 1.5, 'consolidation_range_pct': 8.0, 'min_price': 50, 'max_price': 2000, 'consolidation_period': 5, 'max_results': 50})

print("🎯 Testing breakout scanner on 2025-09-05")
print("📊 Using relaxed configuration for better results")

# Test the scanner
test_date = date(2025, 9, 5)
cutoff_time = time(9, 50)

results = scanner.scan(test_date, cutoff_time)

if not results.empty:
    print(f"\n✅ Success! Found {len(results)} breakout candidates")
    print("\n📈 Top results:")
    display_cols = ['symbol', 'current_price', 'breakout_score', 'breakout_pct', 'volume_ratio']
    print(results[display_cols].head(10).to_string(index=False))

    # Save results
    results.to_csv('optimal_scanner_results.csv', index=False)
    print("\n💾 Results saved to optimal_scanner_results.csv")
else:
    print("\n⚠️  No breakout patterns found - try further relaxing criteria")

# Close database
db_manager.close()
