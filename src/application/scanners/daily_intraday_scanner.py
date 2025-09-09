#!/usr/bin/env python3
"""
Daily Intraday Scanner System
================================

Automated scanner that runs at 09:50 every trading day to select stocks
for intraday trading based on technical and volume criteria.

Features:
- Multiple scanner strategies (relative volume, momentum, technical)
- Real-time scanning at 09:50 AM
- Automated execution and result storage
- Integration with existing DuckDB database

Usage:
    # Run once for today
    python scanners/daily_intraday_scanner.py

    # Run for specific date
    python scanners/daily_intraday_scanner.py --scan-date 2024-01-15
"""

import sys
import os
import argparse
import pandas as pd
from datetime import datetime, date, time
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

def import_technical_scanner():
    try:
        from src.application.scanners.strategies.technical_scanner import TechnicalScanner
        return TechnicalScanner
    except ImportError:
        print("⚠️  Technical scanner not available, will use only relative volume scanner")
        return None

from src.infrastructure.singleton_database import DuckDBConnectionManager, create_db_manager

class DailyIntradayScanner:
    """Main scanner system for daily intraday stock selection."""

    def __init__(self, db_manager: DuckDBConnectionManager = None):
        """Initialize scanner system."""
        self.db_manager = db_manager or create_db_manager()

        # Initialize scanner strategies
        from src.application.scanners.strategies.relative_volume_scanner import RelativeVolumeScanner
        self.scanners = {'relative_volume': RelativeVolumeScanner(self.db_manager)}

        # Add technical scanner if available
        TechnicalScanner = import_technical_scanner()
        if TechnicalScanner:
            self.scanners['technical'] = TechnicalScanner(self.db_manager)

        # Ensure results directory exists
        self.results_dir = Path("scanners/results")
        self.results_dir.mkdir(exist_ok=True)

        print(f"🚀 Daily Intraday Scanner initialized with {len(self.scanners)} strategies")

    def scan_today_at_9_50(self) -> Dict[str, pd.DataFrame]:
        """
        Run all scanner strategies for today at 09:50 cutoff time.

        Returns:
            Dictionary of scanner results by strategy
        """
        scan_date = date.today()
        cutoff_time = time(9, 50)

        print(f"🔍 Running daily scanner for {scan_date} at {cutoff_time}")

        marketplace_results = {}

        for scanner_name, scanner in self.scanners.items():
            print(f"\n{'='*60}")
            print(f"📊 RUNNING: {scanner_name.upper().replace('_', ' ')} SCANNER")
            print('=' * 60)

            # Run scanner
            results = scanner.scan(scan_date, cutoff_time)

            if not results.empty:
                # Save results
                filename = scanner.save_results(results)

                # Add metadata
                results_copy = results.copy()
                results_copy['scan_type'] = scanner_name
                results_copy['scan_date'] = scan_date
                results_copy['cutoff_time'] = cutoff_time
                results_copy['scan_timestamp'] = datetime.now()

                marketplace_results[scanner_name] = results_copy

                # Print summary
                self._print_scanner_summary(scanner_name, results)
            else:
                marketplace_results[scanner_name] = pd.DataFrame()
                print(f"⚠️  No results from {scanner_name} scanner")

        # Generate comprehensive report
        self._generate_daily_report(marketplace_results, scan_date, cutoff_time)

        return marketplace_results

    def run_specialized_scan(
                           scan_date: date,
                           cutoff_time: time,
                           scanners: List[str] = None,
                           config_override: Dict[str, Any] = None) -> Dict[str, pd.DataFrame]:
        """
        Run specialized scan with custom parameters.

        Args:
            scan_date: Date to scan
            cutoff_time: Time cutoff for scanning
            scanners: List of scanner names to run (default: all)
            config_override: Configuration overrides for scanners

        Returns:
            Dictionary of scanner results
        """
        if scanners is None:
            scanners = list(self.scanners.keys())

        results = {}

        print(f"🔍 Running specialized scan for {scan_date} at {cutoff_time}")

        for scanner_name in scanners:
            if scanner_name not in self.scanners:
                print(f"❌ Scanner '{scanner_name}' not found")
                continue

            scanner = self.scanners[scanner_name]

            # Apply configuration overrides
            if config_override and scanner_name in config_override:
                scanner.config.update(config_override[scanner_name])

            print(f"\n📊 Running {scanner_name} scanner...")

            scan_results = scanner.scan(scan_date, cutoff_time)

            if not scan_results.empty:
                # Save results
                scanner.save_results(scan_results)
                results[scanner_name] = scan_results
                self._print_scanner_summary(scanner_name, scan_results)
            else:
                results[scanner_name] = pd.DataFrame()
                print(f"⚠️  No results from {scanner_name} scanner")

        return results

    def _print_scanner_summary(self, scanner_name: str, results: pd.DataFrame):
        """Print summary of scanner results."""
        print(f"\n📋 {scanner_name.upper().replace('_', ' ')} RESULTS SUMMARY:")
        print(f"   Found: {len(results)} stocks")

        if len(results) > 0:
            # Print top 5 results
            print(f"   Top {min(5, len(results))} stocks:")
            print("-" * 60)

            display_cols = ['symbol', 'relative_volume', 'price_change_pct']

            available_cols = [col for col in display_cols if col in results.columns]
            if not available_cols:
                available_cols = list(results.columns)[:3]

            for _, row in results.head(5).iterrows():
                values = []
                for col in available_cols:
                    if col == 'relative_volume' and col in results.columns:
                        values.append(f"{row[col]:.1f}x")
                    elif col == 'price_change_pct' and col in results.columns:
                        values.append(f"{row[col]:.2f}%")
                    else:
                        values.append(str(row[col]))

                print(f"   {' | '.join(values[:3])}")

    def _generate_daily_report(self,
                             results: Dict[str, pd.DataFrame],
                             scan_date: date,
                             cutoff_time: time):
        """Generate comprehensive daily report."""
        report_path = self.results_dir / f"daily_scan_{scan_date.strftime('%Y%m%d')}.txt"

        with open(report_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write(f"DAILY INTRADAY SCAN RESULTS - {scan_date}\n")
            f.write(f"Cutoff Time: {cutoff_time}\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write("=" * 80 + "\n\n")

            total_stocks = 0

            for scanner_name, df in results.items():
                f.write(f"{scanner_name.upper().replace('_', ' ')} SCANNER:\n")
                f.write("-" * 40 + "\n")

                if df.empty:
                    f.write("No stocks found\n\n")
                else:
                    f.write(f"Total stocks: {len(df)}\n\n")

                    # Write detailed results
                    for _, row in df.iterrows():
                        f.write(f"Symbol: {row['symbol']}\n")
                        if 'relative_volume' in row:
                            f.write(f"Relative Volume: {row['relative_volume']:.1f}x\n")
                        if 'price_change_pct' in row:
                            f.write(f"Price Change: {row['price_change_pct']:.2f}%\n")
                        if 'current_volume' in row:
                            f.write(f"Current Volume: {row['current_volume']:,}\n")
                        f.write("\n")

                    total_stocks += len(df)

            f.write("=" * 80 + "\n")
            f.write(f"GRAND TOTAL: {total_stocks} stocks from {len(results)} scanners\n")
            f.write("=" * 80 + "\n")

        print(f"\n📄 Daily report saved to: {report_path}")


def main():
    """Main function for command-line execution."""
    parser = argparse.ArgumentParser(description="Daily Intraday Stock Scanner")
    parser.add_argument("--scan-date", type=str,
                       help="Specific date to scan (YYYY-MM-DD, default: today)")
    parser.add_argument("--cutoff-time", type=str, default="09:50",
                       help="Cutoff time (HH:MM)")
    parser.add_argument("--config", type=str,
                       help="JSON config file path")

    args = parser.parse_args()

    # Parse scan date
    if args.scan_date:
        try:
            scan_date = datetime.strptime(args.scan_date, "%Y-%m-%d").date()
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD")
            return
    else:
        scan_date = date.today()

    # Create scanner
    scanner = DailyIntradayScanner()

    # Load config if provided
    config_override = None
    if args.config and Path(args.config).exists():
        import json
        with open(args.config, 'r') as f:
            config_override = json.load(f)

    try:
        if scan_date == date.today() and args.cutoff_time == "09:50":
            # Run standard daily scan
            results = scanner.scan_today_at_9_50()
        else:
            # Run custom scan
            cutoff_time = datetime.strptime(args.cutoff_time, "%H:%M").time()
            results = scanner.run_specialized_scan(scan_date, cutoff_time, config_override=config_override)

        print(f"\n✅ Scan completed successfully for {scan_date}")

        # Print overall summary
        total_stocks = sum(len(df) for df in results.values() if not df.empty)
        successful_scanners = sum(1 for df in results.values() if not df.empty)

        print(f"📊 Total stocks found: {total_stocks}")
        print(f"🔧 Successful scanners: {successful_scanners}/{len(results)}")

    except Exception as e:
        print(f"❌ Error during scanning: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
