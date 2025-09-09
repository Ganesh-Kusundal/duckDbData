#!/usr/bin/env python3
"""
Scanner Scheduler for automated 09:50 execution.
Automatically runs intraday scanners every trading day at 09:50 AM.
"""

import sys
import os
import time
import schedule
import threading
from datetime import datetime, date, time, timedelta
from pathlib import Path
import logging
from typing import Dict, Any, List, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..daily_intraday_scanner import DailyIntradayScanner
from src.infrastructure.singleton_database import DuckDBConnectionManager, create_db_manager


class ScannerScheduler:
    """
    Automated scheduler for daily 09:50 scanner execution.
    Runs on trading days at exactly 09:50 AM IST.
    """

    def __init__(self, db_manager: DuckDBConnectionManager = None):
        """Initialize the scanner scheduler."""
        self.db_manager = db_manager or create_db_manager()
        self.scanner = DailyIntradayScanner(self.db_manager)

        # Setup logging
        self._setup_logging()

        # Holiday and market schedule configuration
        self.holidays = [
            # Add major Indian holidays here
            date(2025, 1, 1),   # New Year
            date(2025, 1, 26),  # Republic Day
            date(2025, 3, 14),  # Holi
            date(2025, 3, 31),  # Ramzan Id
            date(2025, 4, 14),  # Dr. Ambedkar Jayanti
            date(2025, 5, 1),   # Labour Day
            date(2025, 8, 15),  # Independence Day
            date(2025, 8, 25),  # Raksha Bandhan
            date(2025, 10, 2),  # Gandhi Jayanti
            date(2025, 11, 5),  # Diwali
            date(2025, 12, 25)  # Christmas
        ]

        self.running = False
        self.last_scan_date = None
        self.scan_history = []

        self.logger.info("🚀 Scanner Scheduler initialized")

    def _setup_logging(self):
        """Setup logging for the scheduler."""
        log_file = Path("logs/scanner_scheduler.log")
        log_file.parent.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

        self.logger = logging.getLogger('ScannerScheduler')

    def start(self, daemon: bool = True):
        """
        Start the scheduler.

        Args:
            daemon: Whether to run in daemon thread
        """
        self.logger.info("📅 Starting scanner scheduler...")

        # Schedule the daily scan at 09:50 AM
        schedule.every().day.at("09:50").do(self._run_daily_scan)

        # Add a pre-scan check at 09:00 to verify market status
        schedule.every().day.at("09:00").do(self._pre_scan_check)

        self.running = True

        if daemon:
            # Run in background thread
            scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            scheduler_thread.start()
            self.logger.info(f"✅ Scheduler started in daemon mode (Thread: {scheduler_thread.name})")

            # Keep main thread alive
            try:
                while self.running:
                    time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                self.stop()
        else:
            # Run in foreground
            self.logger.info("✅ Scheduler started in foreground mode")
            self._run_scheduler()

    def stop(self):
        """Stop the scheduler."""
        self.logger.info("🛑 Stopping scanner scheduler...")
        self.running = False
        schedule.clear()
        self.logger.info("✅ Scanner scheduler stopped")

    def _run_scheduler(self):
        """Main scheduler loop."""
        self.logger.info("⏰ Scheduler loop started")

        while self.running:
            try:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.logger.error(f"❌ Error in scheduler loop: {e}")
                time.sleep(60)  # Pause longer on errors

    def _pre_scan_check(self):
        """Pre-scan verification at 09:00 AM."""
        today = date.today()

        if not self._is_trading_day(today):
            self.logger.info(f"📅 {today}: Holiday/weekend - skipping scan")
            return

        self.logger.info(f"🔍 Pre-scan check for {today}")

        # Check if we have sufficient data for scanning
        try:
            symbols = self.scanner.scanners['relative_volume'].get_available_symbols()
            self.logger.info(f"✅ Found {len(symbols)} available symbols for scanning")

            if len(symbols) < 100:
                self.logger.warning("⚠️  Low symbol count - database may need refresh")

        except Exception as e:
            self.logger.error(f"❌ Pre-scan data check failed: {e}")

    def _run_daily_scan(self):
        """Execute the actual daily scan at 09:50 AM."""
        scan_date = date.today()
        scan_time = datetime.now().time()

        self.logger.info(f"🚀 Starting daily scan for {scan_date} at {scan_time}")

        # Double-check market should be open
        if not self._is_trading_day(scan_date):
            self.logger.warning(f"⚠️  {scan_date} marked as trading day but is holiday/weekend")
            return

        try:
            # Run the daily scan
            start_time = time.time()
            results = self.scanner.scan_today_at_9_50()
            scan_duration = time.time() - start_time

            # Record scan results
            scan_record = {
                'date': scan_date,
                'time': scan_time,
                'duration_seconds': scan_duration,
                'results': self._summarize_scan_results(results),
                'total_stocks': sum(len(df) for df in results.values() if not df.empty),
                'successful_scanners': sum(1 for df in results.values() if not df.empty),
                'scan_status': 'SUCCESS'
            }

            self.scan_history.append(scan_record)
            self.last_scan_date = scan_date

            self.logger.info(f"✅ Daily scan completed in {scan_duration:.1f}s - {scan_record['total_stocks']} stocks found")

            # Trigger post-scan processing
            self._post_scan_processing(results, scan_date)

        except Exception as e:
            self.logger.error(f"❌ Daily scan failed: {e}")
            import traceback
            self.logger.error(f"Stack trace: {traceback.format_exc()}")

            # Record failed scan
            scan_record = {
                'date': scan_date,
                'time': scan_time,
                'duration_seconds': 0,
                'results': {},
                'total_stocks': 0,
                'successful_scanners': 0,
                'scan_status': 'FAILED',
                'error': str(e)
            }
            self.scan_history.append(scan_record)

    def _post_scan_processing(self, results: Dict[str, Any], scan_date: date):
        """
        Post-scan processing like report generation and notifications.

        Args:
            results: Scan results from all scanners
            scan_date: Date of scan
        """
        try:
            # Generate summary email/report
            summary = self._generate_scan_summary(results, scan_date)
            self.logger.info(f"📄 Scan summary generated: {summary.total_stocks} total stocks")

            # Could add email notifications here
            # self._send_notification_email(summary)

            # Store results in results directory for backtesting later
            self._archive_scan_results()

        except Exception as e:
            self.logger.error(f"❌ Post-scan processing failed: {e}")

    def _is_trading_day(self, check_date: date) -> bool:
        """
        Check if date is a valid trading day.
        Saturday, Sunday, and holidays are not trading days.

        Args:
            check_date: Date to check

        Returns:
            True if it's a trading day
        """
        # Weekend check
        if check_date.weekday() >= 5:  # Saturday=5, Sunday=6
            return False

        # Holiday check
        if check_date in self.holidays:
            return False

        return True

    def _summarize_scan_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Create summarized version of scan results for logging."""
        summary = {}
        for scanner_name, df in results.items():
            if not df.empty:
                summary[scanner_name] = {
                    'count': len(df),
                    'top_symbols': df.head(3)['symbol'].tolist() if 'symbol' in df.columns else []
                }
            else:
                summary[scanner_name] = {'count': 0, 'top_symbols': []}
        return summary

    def _generate_scan_summary(self, results: Dict[str, Any], scan_date: date) -> Dict[str, Any]:
        """Generate detailed scan summary."""
        summary = {
            'scan_date': scan_date,
            'timestamp': datetime.now(),
            'scanners': {},
            'total_stocks': 0,
            'unique_stocks': set()
        }

        for scanner_name, df in results.items():
            if not df.empty:
                scanner_summary = {
                    'stock_count': len(df),
                    'top_stocks': df.head(5).to_dict('records') if len(df) > 5 else df.to_dict('records')
                }
                summary['scanners'][scanner_name] = scanner_summary
                summary['total_stocks'] += len(df)

                if 'symbol' in df.columns:
                    summary['unique_stocks'].update(df['symbol'].tolist())

            else:
                summary['scanners'][scanner_name] = {'stock_count': 0, 'top_stocks': []}

        summary['unique_stocks'] = list(summary['unique_stocks'])
        return summary

    def _archive_scan_results(self):
        """Archive scan results for backtesting and analysis."""
        # This method could save results to persistent storage for later backtesting
        pass

    def get_scan_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get recent scan history.

        Args:
            days: Number of days of history to retrieve

        Returns:
            List of scan records
        """
        cutoff_date = date.today() - timedelta(days=days)
        return [record for record in self.scan_history if record['date'] >= cutoff_date]

    def get_scan_statistics(self) -> Dict[str, Any]:
        """Get scanner performance statistics."""
        if not self.scan_history:
            return {'total_scans': 0}

        successful_scans = sum(1 for record in self.scan_history if record['scan_status'] == 'SUCCESS')
        total_stocks_found = sum(record['total_stocks'] for record in self.scan_history)

        return {
            'total_scans': len(self.scan_history),
            'successful_scans': successful_scans,
            'success_rate': successful_scans / len(self.scan_history) * 100 if self.scan_history else 0,
            'total_stocks_found': total_stocks_found,
            'average_stocks_per_scan': total_stocks_found / len(self.scan_history) if self.scan_history else 0,
            'last_scan_date': self.last_scan_date
        }

    def manual_scan_now(self) -> Dict[str, Any]:
        """Manually trigger scan right now (for testing/debugging)."""
        self.logger.info("🔨 Manual scan triggering...")
        results = self.scanner.scan_today_at_9_50()
        self.logger.info(f"✅ Manual scan completed - {sum(len(df) for df in results.values() if not df.empty)} stocks found")
        return results


def main():
    """Main function for scheduler execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Scanner Scheduler")
    parser.add_argument("--test", action="store_true", help="Run in test mode")
    parser.add_argument("--manual", action="store_true", help="Trigger manual scan")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode")

    args = parser.parse_args()

    scheduler = ScannerScheduler()

    if args.manual:
        # Run manual scan
        print("🔨 Running manual scan...")
        results = scheduler.manual_scan_now()
        print(f"✅ Manual scan complete - {sum(len(df) for df in results.values() if not df.empty)} stocks found")

    elif args.test:
        # Test mode - run scan now
        print("🧪 Running test scan...")
        results = scheduler.manual_scan_now()

        # Show detailed results
        for scanner_name, df in results.items():
            print(f"\n📊 {scanner_name.upper().replace('_', ' ')} SCANNER:")
            if not df.empty:
                print(f"   Found {len(df)} stocks")
                print(df.head(3)[['symbol']].to_string(index=False))
            else:
                print("   No stocks found")

    else:
        # Production mode
        print("📅 Starting scanner scheduler...")
        try:
            scheduler.start(daemon=args.daemon)
        except KeyboardInterrupt:
            scheduler.stop()
            print("\n✅ Scheduler stopped")


if __name__ == "__main__":
    main()
