#!/usr/bin/env python3
"""
Intraday Stock Scanner for DuckDB Financial Infrastructure
=========================================================

Advanced stock scanner for intraday trading opportunities.
Identifies stocks with unusual volume patterns, price movements, and other criteria.

Key Features:
- Relative volume analysis (e.g., 5x average by 9:50 AM)
- Price gap analysis
- Momentum scanning
- Volume profile analysis
- Real-time filtering capabilities

Usage:
    python scripts/intraday_scanner.py --scan-date 2024-01-15 --cutoff-time "09:50"
"""

import sys
import os
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.duckdb_infra import DuckDBManager, QueryAPI, TimeFrame


class IntradayScanner:
    """Advanced intraday stock scanner with multiple filtering criteria."""
    
    def __init__(self, db_manager: DuckDBManager):
        """Initialize the scanner with database manager."""
        self.db_manager = db_manager
        self.query_api = QueryAPI(db_manager)
        
    def calculate_relative_volume(
        self,
        scan_date: date,
        cutoff_time: str = "09:50",
        lookback_days: int = 14,
        min_relative_volume: float = 5.0,
        min_avg_volume: int = 100000
    ) -> pd.DataFrame:
        """
        Calculate relative volume for all stocks by a specific time.
        
        Args:
            scan_date: Date to scan
            cutoff_time: Time cutoff (e.g., "09:50")
            lookback_days: Days to look back for average calculation
            min_relative_volume: Minimum relative volume multiplier
            min_avg_volume: Minimum average daily volume filter
            
        Returns:
            DataFrame with relative volume analysis
        """
        print(f"🔍 Scanning for relative volume >= {min_relative_volume}x by {cutoff_time} on {scan_date}")
        
        # Calculate date range for historical average
        end_date = scan_date - timedelta(days=1)  # Previous day
        start_date = end_date - timedelta(days=lookback_days + 10)  # Buffer for weekends
        
        # Get available symbols
        symbols = self.db_manager.get_available_symbols()
        print(f"📊 Analyzing {len(symbols)} symbols...")
        
        # SQL query to calculate relative volume
        relative_volume_query = """
        WITH historical_volume AS (
            -- Calculate average volume by time for historical period
            SELECT 
                symbol,
                strftime('%H:%M', timestamp) as time_slot,
                AVG(volume) as avg_volume_at_time,
                COUNT(*) as sample_days
            FROM market_data 
            WHERE date_partition BETWEEN ? AND ?
                AND strftime('%H:%M', timestamp) <= ?
                AND strftime('%H:%M', timestamp) >= '09:15'
            GROUP BY symbol, time_slot
            HAVING COUNT(*) >= ?  -- Minimum sample days
        ),
        
        historical_daily_avg AS (
            -- Calculate average daily volume for filtering
            SELECT 
                symbol,
                AVG(daily_volume) as avg_daily_volume
            FROM (
                SELECT 
                    symbol,
                    date_partition,
                    SUM(volume) as daily_volume
                FROM market_data 
                WHERE date_partition BETWEEN ? AND ?
                GROUP BY symbol, date_partition
            ) daily_totals
            GROUP BY symbol
            HAVING AVG(daily_volume) >= ?  -- Minimum average volume filter
        ),
        
        current_day_volume AS (
            -- Calculate cumulative volume for scan date up to cutoff time
            SELECT 
                symbol,
                SUM(volume) as current_volume,
                COUNT(*) as current_ticks,
                MIN(timestamp) as first_tick,
                MAX(timestamp) as last_tick,
                AVG(close) as avg_price,
                MAX(high) as day_high,
                MIN(low) as day_low,
                (SELECT close FROM market_data m2 
                 WHERE m2.symbol = m1.symbol 
                   AND m2.date_partition = ?
                   AND m2.timestamp = MIN(m1.timestamp)) as open_price,
                (SELECT close FROM market_data m2 
                 WHERE m2.symbol = m1.symbol 
                   AND m2.date_partition = ?
                   AND m2.timestamp = MAX(m1.timestamp)) as current_price
            FROM market_data m1
            WHERE date_partition = ?
                AND strftime('%H:%M', timestamp) <= ?
                AND strftime('%H:%M', timestamp) >= '09:15'
            GROUP BY symbol
        ),
        
        expected_volume AS (
            -- Calculate expected volume based on historical average
            SELECT 
                h.symbol,
                SUM(h.avg_volume_at_time) as expected_volume_by_cutoff,
                COUNT(*) as time_slots_covered
            FROM historical_volume h
            WHERE h.time_slot <= ?
            GROUP BY h.symbol
        )
        
        SELECT 
            c.symbol,
            c.current_volume,
            e.expected_volume_by_cutoff,
            ROUND(c.current_volume / NULLIF(e.expected_volume_by_cutoff, 0), 2) as relative_volume,
            h.avg_daily_volume,
            c.current_ticks,
            c.open_price,
            c.current_price,
            c.day_high,
            c.day_low,
            ROUND(((c.current_price - c.open_price) / c.open_price) * 100, 2) as price_change_pct,
            ROUND(((c.day_high - c.day_low) / c.open_price) * 100, 2) as intraday_range_pct,
            c.first_tick,
            c.last_tick,
            e.time_slots_covered
        FROM current_day_volume c
        JOIN expected_volume e ON c.symbol = e.symbol
        JOIN historical_daily_avg h ON c.symbol = h.symbol
        WHERE c.current_volume / NULLIF(e.expected_volume_by_cutoff, 0) >= ?
            AND e.expected_volume_by_cutoff > 0
            AND c.current_ticks >= 10  -- Minimum ticks for reliability
        ORDER BY relative_volume DESC
        """
        
        # Parameters for the query
        min_sample_days = max(5, lookback_days // 3)  # At least 5 days of data
        
        params = [
            start_date, end_date, cutoff_time, min_sample_days,  # historical_volume
            start_date, end_date, min_avg_volume,  # historical_daily_avg  
            scan_date, scan_date, scan_date, cutoff_time,  # current_day_volume
            cutoff_time,  # expected_volume
            min_relative_volume  # final filter
        ]
        
        try:
            result = self.db_manager.execute_custom_query(relative_volume_query, params)
            
            if result.empty:
                print(f"⚠️  No stocks found with relative volume >= {min_relative_volume}x")
                return pd.DataFrame()
            
            # Add additional calculated fields
            result['volume_ratio_text'] = result['relative_volume'].apply(
                lambda x: f"{x:.1f}x" if pd.notna(x) else "N/A"
            )
            
            result['price_momentum'] = result.apply(
                lambda row: self._classify_momentum(row['price_change_pct'], row['intraday_range_pct']), 
                axis=1
            )
            
            print(f"✅ Found {len(result)} stocks meeting criteria")
            return result
            
        except Exception as e:
            print(f"❌ Error in relative volume calculation: {e}")
            return pd.DataFrame()
    
    def scan_price_gaps(
        self,
        scan_date: date,
        min_gap_percent: float = 2.0,
        gap_direction: str = "both"  # "up", "down", "both"
    ) -> pd.DataFrame:
        """
        Scan for stocks with significant price gaps.
        
        Args:
            scan_date: Date to scan
            min_gap_percent: Minimum gap percentage
            gap_direction: Direction of gap to scan for
            
        Returns:
            DataFrame with gap analysis
        """
        print(f"🔍 Scanning for price gaps >= {min_gap_percent}% on {scan_date}")
        
        # Get previous trading day
        prev_date = scan_date - timedelta(days=1)
        
        gap_query = """
        WITH previous_close AS (
            SELECT 
                symbol,
                close as prev_close
            FROM market_data 
            WHERE date_partition = ?
                AND timestamp = (
                    SELECT MAX(timestamp) 
                    FROM market_data m2 
                    WHERE m2.symbol = market_data.symbol 
                      AND m2.date_partition = ?
                )
        ),
        
        current_open AS (
            SELECT 
                symbol,
                open as current_open,
                close as current_price,
                high as day_high,
                low as day_low,
                volume,
                timestamp
            FROM market_data 
            WHERE date_partition = ?
                AND timestamp = (
                    SELECT MIN(timestamp) 
                    FROM market_data m2 
                    WHERE m2.symbol = market_data.symbol 
                      AND m2.date_partition = ?
                )
        )
        
        SELECT 
            c.symbol,
            p.prev_close,
            c.current_open,
            c.current_price,
            c.day_high,
            c.day_low,
            c.volume as opening_volume,
            ROUND(((c.current_open - p.prev_close) / p.prev_close) * 100, 2) as gap_percent,
            ROUND(((c.current_price - c.current_open) / c.current_open) * 100, 2) as move_after_open,
            CASE 
                WHEN c.current_open > p.prev_close THEN 'GAP_UP'
                WHEN c.current_open < p.prev_close THEN 'GAP_DOWN'
                ELSE 'NO_GAP'
            END as gap_direction,
            c.timestamp as open_time
        FROM current_open c
        JOIN previous_close p ON c.symbol = p.symbol
        WHERE ABS((c.current_open - p.prev_close) / p.prev_close * 100) >= ?
        ORDER BY ABS(gap_percent) DESC
        """
        
        params = [prev_date, prev_date, scan_date, scan_date, min_gap_percent]
        
        try:
            result = self.db_manager.execute_custom_query(gap_query, params)
            
            # Filter by gap direction if specified
            if gap_direction == "up":
                result = result[result['gap_percent'] > 0]
            elif gap_direction == "down":
                result = result[result['gap_percent'] < 0]
            
            if result.empty:
                print(f"⚠️  No stocks found with gaps >= {min_gap_percent}%")
                return pd.DataFrame()
            
            print(f"✅ Found {len(result)} stocks with significant gaps")
            return result
            
        except Exception as e:
            print(f"❌ Error in gap scanning: {e}")
            return pd.DataFrame()
    
    def scan_momentum_breakouts(
        self,
        scan_date: date,
        cutoff_time: str = "09:50",
        min_price_change: float = 3.0,
        min_volume_ratio: float = 2.0
    ) -> pd.DataFrame:
        """
        Scan for momentum breakouts with volume confirmation.
        
        Args:
            scan_date: Date to scan
            cutoff_time: Time cutoff for analysis
            min_price_change: Minimum price change percentage
            min_volume_ratio: Minimum volume ratio vs average
            
        Returns:
            DataFrame with momentum analysis
        """
        print(f"🚀 Scanning for momentum breakouts by {cutoff_time} on {scan_date}")
        
        momentum_query = """
        WITH current_stats AS (
            SELECT 
                symbol,
                MIN(CASE WHEN strftime('%H:%M', timestamp) = '09:15' THEN close END) as open_price,
                MAX(CASE WHEN strftime('%H:%M', timestamp) <= ? THEN close END) as current_price,
                MAX(CASE WHEN strftime('%H:%M', timestamp) <= ? THEN high END) as period_high,
                MIN(CASE WHEN strftime('%H:%M', timestamp) <= ? THEN low END) as period_low,
                SUM(CASE WHEN strftime('%H:%M', timestamp) <= ? THEN volume ELSE 0 END) as period_volume,
                COUNT(CASE WHEN strftime('%H:%M', timestamp) <= ? THEN 1 END) as period_ticks
            FROM market_data 
            WHERE date_partition = ?
                AND strftime('%H:%M', timestamp) >= '09:15'
            GROUP BY symbol
        ),
        
        avg_volume AS (
            SELECT 
                symbol,
                AVG(period_volume) as avg_period_volume
            FROM (
                SELECT 
                    symbol,
                    date_partition,
                    SUM(CASE WHEN strftime('%H:%M', timestamp) <= ? THEN volume ELSE 0 END) as period_volume
                FROM market_data 
                WHERE date_partition BETWEEN ? AND ?
                    AND strftime('%H:%M', timestamp) >= '09:15'
                GROUP BY symbol, date_partition
            ) daily_volumes
            GROUP BY symbol
            HAVING COUNT(*) >= 5  -- At least 5 days of data
        )
        
        SELECT 
            c.symbol,
            c.open_price,
            c.current_price,
            c.period_high,
            c.period_low,
            c.period_volume,
            a.avg_period_volume,
            ROUND(((c.current_price - c.open_price) / c.open_price) * 100, 2) as price_change_pct,
            ROUND(((c.period_high - c.period_low) / c.open_price) * 100, 2) as range_pct,
            ROUND(c.period_volume / NULLIF(a.avg_period_volume, 0), 2) as volume_ratio,
            c.period_ticks,
            CASE 
                WHEN c.current_price > c.open_price THEN 'BULLISH'
                WHEN c.current_price < c.open_price THEN 'BEARISH'
                ELSE 'NEUTRAL'
            END as momentum_direction
        FROM current_stats c
        JOIN avg_volume a ON c.symbol = a.symbol
        WHERE ABS((c.current_price - c.open_price) / c.open_price * 100) >= ?
            AND c.period_volume / NULLIF(a.avg_period_volume, 0) >= ?
            AND c.period_ticks >= 10
        ORDER BY ABS(price_change_pct) DESC
        """
        
        # Calculate date range for average
        end_date = scan_date - timedelta(days=1)
        start_date = end_date - timedelta(days=20)
        
        params = [
            cutoff_time, cutoff_time, cutoff_time, cutoff_time, cutoff_time, scan_date,  # current_stats
            cutoff_time, start_date, end_date,  # avg_volume
            min_price_change, min_volume_ratio  # filters
        ]
        
        try:
            result = self.db_manager.execute_custom_query(momentum_query, params)
            
            if result.empty:
                print(f"⚠️  No momentum breakouts found")
                return pd.DataFrame()
            
            print(f"✅ Found {len(result)} momentum breakouts")
            return result
            
        except Exception as e:
            print(f"❌ Error in momentum scanning: {e}")
            return pd.DataFrame()
    
    def comprehensive_scan(
        self,
        scan_date: date,
        cutoff_time: str = "09:50",
        criteria: Dict = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Run comprehensive scan with multiple criteria.
        
        Args:
            scan_date: Date to scan
            cutoff_time: Time cutoff
            criteria: Dictionary of scanning criteria
            
        Returns:
            Dictionary of scan results by type
        """
        if criteria is None:
            criteria = {
                'relative_volume': {'min_relative_volume': 5.0, 'min_avg_volume': 100000},
                'price_gaps': {'min_gap_percent': 2.0, 'gap_direction': 'both'},
                'momentum': {'min_price_change': 3.0, 'min_volume_ratio': 2.0}
            }
        
        print(f"🔍 Running comprehensive intraday scan for {scan_date} (cutoff: {cutoff_time})")
        print("="*70)
        
        results = {}
        
        # 1. Relative Volume Scan
        if 'relative_volume' in criteria:
            print("\n📊 RELATIVE VOLUME SCAN:")
            rv_criteria = criteria['relative_volume']
            results['relative_volume'] = self.calculate_relative_volume(
                scan_date=scan_date,
                cutoff_time=cutoff_time,
                **rv_criteria
            )
        
        # 2. Price Gap Scan
        if 'price_gaps' in criteria:
            print("\n📈 PRICE GAP SCAN:")
            gap_criteria = criteria['price_gaps']
            results['price_gaps'] = self.scan_price_gaps(
                scan_date=scan_date,
                **gap_criteria
            )
        
        # 3. Momentum Breakout Scan
        if 'momentum' in criteria:
            print("\n🚀 MOMENTUM BREAKOUT SCAN:")
            momentum_criteria = criteria['momentum']
            results['momentum'] = self.scan_momentum_breakouts(
                scan_date=scan_date,
                cutoff_time=cutoff_time,
                **momentum_criteria
            )
        
        return results
    
    def _classify_momentum(self, price_change: float, range_pct: float) -> str:
        """Classify momentum based on price change and range."""
        if pd.isna(price_change) or pd.isna(range_pct):
            return "UNKNOWN"
        
        if abs(price_change) >= 5 and range_pct >= 3:
            return "STRONG_MOMENTUM"
        elif abs(price_change) >= 3 and range_pct >= 2:
            return "MODERATE_MOMENTUM"
        elif abs(price_change) >= 1 and range_pct >= 1:
            return "WEAK_MOMENTUM"
        else:
            return "LOW_MOMENTUM"
    
    def export_scan_results(
        self, 
        results: Dict[str, pd.DataFrame], 
        output_dir: str = "scan_results"
    ) -> None:
        """Export scan results to CSV files."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for scan_type, df in results.items():
            if not df.empty:
                filename = f"{scan_type}_scan_{timestamp}.csv"
                filepath = output_path / filename
                df.to_csv(filepath, index=False)
                print(f"📁 Exported {scan_type} results to: {filepath}")


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description="Intraday Stock Scanner")
    parser.add_argument("--scan-date", type=str, required=True, 
                       help="Date to scan (YYYY-MM-DD)")
    parser.add_argument("--cutoff-time", type=str, default="09:50",
                       help="Cutoff time (HH:MM)")
    parser.add_argument("--relative-volume", type=float, default=5.0,
                       help="Minimum relative volume multiplier")
    parser.add_argument("--min-gap", type=float, default=2.0,
                       help="Minimum gap percentage")
    parser.add_argument("--momentum-change", type=float, default=3.0,
                       help="Minimum momentum price change")
    parser.add_argument("--export", action="store_true",
                       help="Export results to CSV")
    
    args = parser.parse_args()
    
    # Parse scan date
    try:
        scan_date = datetime.strptime(args.scan_date, "%Y-%m-%d").date()
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")
        return
    
    # Initialize scanner
    db_manager = DuckDBManager()
    scanner = IntradayScanner(db_manager)
    
    # Define scan criteria
    criteria = {
        'relative_volume': {
            'min_relative_volume': args.relative_volume,
            'min_avg_volume': 100000
        },
        'price_gaps': {
            'min_gap_percent': args.min_gap,
            'gap_direction': 'both'
        },
        'momentum': {
            'min_price_change': args.momentum_change,
            'min_volume_ratio': 2.0
        }
    }
    
    # Run comprehensive scan
    results = scanner.comprehensive_scan(
        scan_date=scan_date,
        cutoff_time=args.cutoff_time,
        criteria=criteria
    )
    
    # Display results
    print("\n" + "="*70)
    print("📋 SCAN RESULTS SUMMARY:")
    print("="*70)
    
    for scan_type, df in results.items():
        print(f"\n{scan_type.upper().replace('_', ' ')}:")
        if df.empty:
            print("   No results found")
        else:
            print(f"   Found {len(df)} stocks")
            if len(df) <= 10:
                # Show top results
                display_cols = ['symbol']
                if 'relative_volume' in df.columns:
                    display_cols.extend(['relative_volume', 'current_volume'])
                if 'gap_percent' in df.columns:
                    display_cols.extend(['gap_percent', 'gap_direction'])
                if 'price_change_pct' in df.columns:
                    display_cols.extend(['price_change_pct', 'momentum_direction'])
                
                available_cols = [col for col in display_cols if col in df.columns]
                print(df[available_cols].head(10).to_string(index=False))
    
    # Export if requested
    if args.export:
        scanner.export_scan_results(results)
    
    db_manager.close()
    print(f"\n✅ Scan completed for {scan_date}")


if __name__ == "__main__":
    main()
