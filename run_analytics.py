#!/usr/bin/env python3
"""
Analytics Runner for OHLC Data
==============================

Runs analytics and scanners on the verified OHLC data from parquet files.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, date
import pandas as pd
import duckdb
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OHLCDataAnalytics:
    """Analytics runner for OHLC data from parquet files."""

    def __init__(self):
        self.conn = duckdb.connect()
        self.data_path = Path('./data')
        logger.info("Initialized OHLC Analytics Runner")

    def get_sample_symbols(self, limit=10) -> list[str]:
        """Get a sample of available symbols."""
        try:
            # Get all parquet files and extract symbols
            all_files = list(self.data_path.rglob('*.parquet'))
            symbols = set()

            for file_path in all_files[:1000]:  # Sample first 1000 files
                filename = file_path.name
                if '_minute_' in filename:
                    symbol = filename.split('_minute_')[0]
                    symbols.add(symbol)
                    if len(symbols) >= limit:
                        break

            return list(symbols)[:limit]

        except Exception as e:
            logger.error(f"Error getting sample symbols: {e}")
            return []

    def run_volume_analysis(self, symbols: list[str], date_str: str = "2024-01-01") -> pd.DataFrame:
        """Run volume analysis on specified symbols for a given date."""
        logger.info(f"Running volume analysis for {len(symbols)} symbols on {date_str}")

        results = []

        for symbol in symbols:
            try:
                # Find files for this symbol on the specified date
                pattern = f"{symbol}_minute_{date_str}.parquet"
                files = list(self.data_path.rglob(pattern))

                if not files:
                    logger.warning(f"No files found for {symbol} on {date_str}")
                    continue

                file_path = files[0]
                logger.info(f"Analyzing {symbol}: {file_path}")

                # Run volume analysis query
                query = f"""
                SELECT
                    COUNT(*) as total_records,
                    AVG(volume) as avg_volume,
                    MAX(volume) as max_volume,
                    MIN(volume) as min_volume,
                    SUM(volume) as total_volume,
                    STDDEV(volume) as volume_stddev,
                    AVG(close) as avg_price,
                    MIN(close) as min_price,
                    MAX(close) as max_price,
                    (MAX(close) - MIN(close)) / MIN(close) * 100 as daily_range_pct,
                    (MAX(high) - MIN(low)) / MIN(low) * 100 as true_range_pct
                FROM read_parquet('{file_path}')
                WHERE volume > 0
                """

                df = self.conn.execute(query).fetchdf()

                if not df.empty:
                    result = df.iloc[0].to_dict()
                    result['symbol'] = symbol
                    result['date'] = date_str
                    result['file_path'] = str(file_path)
                    results.append(result)

                    logger.info(f"✅ {symbol}: {result['total_records']} records, "
                              f"avg volume: {result['avg_volume']:,.0f}, "
                              f"daily range: {result['daily_range_pct']:.2f}%")

            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")

        return pd.DataFrame(results)

    def run_price_action_analysis(self, symbols: list[str], date_str: str = "2024-01-01") -> pd.DataFrame:
        """Run price action analysis to identify breakout patterns."""
        logger.info(f"Running price action analysis for {len(symbols)} symbols on {date_str}")

        results = []

        for symbol in symbols:
            try:
                pattern = f"{symbol}_minute_{date_str}.parquet"
                files = list(self.data_path.rglob(pattern))

                if not files:
                    continue

                file_path = files[0]

                # Analyze price action patterns
                query = f"""
                WITH price_action AS (
                    SELECT
                        close,
                        high,
                        low,
                        volume,
                        -- Price movement indicators
                        (close - LAG(close, 1) OVER (ORDER BY close)) / LAG(close, 1) OVER (ORDER BY close) * 100 as price_change_pct,
                        (high - low) / low * 100 as range_pct,
                        -- Volume analysis
                        volume / AVG(volume) OVER (ORDER BY close ROWS BETWEEN 5 PRECEDING AND CURRENT ROW) as volume_ratio,
                        -- Moving averages
                        AVG(close) OVER (ORDER BY close ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) as ma10,
                        AVG(close) OVER (ORDER BY close ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as ma20
                    FROM read_parquet('{file_path}')
                    WHERE volume > 0
                )
                SELECT
                    COUNT(*) as data_points,
                    AVG(price_change_pct) as avg_price_change,
                    STDDEV(price_change_pct) as volatility,
                    AVG(range_pct) as avg_range_pct,
                    AVG(volume_ratio) as avg_volume_ratio,
                    MIN(price_change_pct) as min_change,
                    MAX(price_change_pct) as max_change,
                    SUM(CASE WHEN price_change_pct > 2.0 THEN 1 ELSE 0 END) as up_moves_2pct,
                    SUM(CASE WHEN price_change_pct < -2.0 THEN 1 ELSE 0 END) as down_moves_2pct,
                    AVG(CASE WHEN close > ma10 THEN 1 ELSE 0 END) as above_ma10_pct
                FROM price_action
                WHERE price_change_pct IS NOT NULL
                """

                df = self.conn.execute(query).fetchdf()

                if not df.empty and df.iloc[0]['data_points'] > 0:
                    result = df.iloc[0].to_dict()
                    result['symbol'] = symbol
                    result['date'] = date_str
                    results.append(result)

                    logger.info(f"✅ {symbol}: volatility: {result['volatility']:.2f}%, "
                              f"up moves >2%: {result['up_moves_2pct']}, "
                              f"above MA10: {result['above_ma10_pct']:.1f}%")

            except Exception as e:
                logger.error(f"Error in price action analysis for {symbol}: {e}")

        return pd.DataFrame(results)

    def find_breakout_candidates(self, symbols: list[str], date_str: str = "2024-01-01") -> pd.DataFrame:
        """Find potential breakout candidates based on volume and price action."""
        logger.info(f"Finding breakout candidates for {len(symbols)} symbols on {date_str}")

        breakout_results = []

        for symbol in symbols:
            try:
                pattern = f"{symbol}_minute_{date_str}.parquet"
                files = list(self.data_path.rglob(pattern))

                if not files:
                    continue

                file_path = files[0]

                # Look for breakout patterns
                query = f"""
                WITH breakout_analysis AS (
                    SELECT
                        close,
                        high,
                        low,
                        volume,
                        ROW_NUMBER() OVER (ORDER BY close) as minute_number,
                        -- Pre-breakout consolidation (first 30 minutes)
                        AVG(close) OVER (ORDER BY close ROWS BETWEEN 30 PRECEDING AND CURRENT ROW) as consolidation_price,
                        STDDEV(close) OVER (ORDER BY close ROWS BETWEEN 30 PRECEDING AND CURRENT ROW) as consolidation_volatility,
                        AVG(volume) OVER (ORDER BY close ROWS BETWEEN 30 PRECEDING AND CURRENT ROW) as avg_volume_pre,
                        -- Post-breakout performance (next 30 minutes)
                        MAX(high) OVER (ORDER BY close ROWS BETWEEN CURRENT ROW AND 29 FOLLOWING) as max_high_next_30,
                        MIN(low) OVER (ORDER BY close ROWS BETWEEN CURRENT ROW AND 29 FOLLOWING) as min_low_next_30
                    FROM read_parquet('{file_path}')
                    WHERE volume > 0
                ),
                breakout_signals AS (
                    SELECT
                        *,
                        -- Breakout conditions
                        CASE
                            WHEN consolidation_volatility < 0.01
                                 AND volume > avg_volume_pre * 1.5
                                 AND max_high_next_30 > consolidation_price * 1.02
                            THEN 'BULLISH_BREAKOUT'
                            WHEN consolidation_volatility < 0.01
                                 AND volume > avg_volume_pre * 1.5
                                 AND min_low_next_30 < consolidation_price * 0.98
                            THEN 'BEARISH_BREAKOUT'
                            ELSE 'NO_BREAKOUT'
                        END as breakout_type,
                        (max_high_next_30 - consolidation_price) / consolidation_price * 100 as potential_upside,
                        (consolidation_price - min_low_next_30) / consolidation_price * 100 as potential_downside
                    FROM breakout_analysis
                    WHERE minute_number > 30  -- Only after consolidation period
                )
                SELECT
                    breakout_type,
                    COUNT(*) as breakout_count,
                    AVG(volume / avg_volume_pre) as avg_volume_multiplier,
                    AVG(potential_upside) as avg_upside,
                    AVG(potential_downside) as avg_downside,
                    MAX(potential_upside) as max_upside,
                    MAX(potential_downside) as max_downside
                FROM breakout_signals
                WHERE breakout_type != 'NO_BREAKOUT'
                GROUP BY breakout_type
                """

                df = self.conn.execute(query).fetchdf()

                if not df.empty:
                    for _, row in df.iterrows():
                        result = row.to_dict()
                        result['symbol'] = symbol
                        result['date'] = date_str
                        breakout_results.append(result)

                        logger.info(f"🎯 {symbol}: {result['breakout_type']} "
                                  f"({result['breakout_count']} signals, "
                                  f"vol x{result['avg_volume_multiplier']:.1f})")

            except Exception as e:
                logger.error(f"Error in breakout analysis for {symbol}: {e}")

        return pd.DataFrame(breakout_results)

    def run_comprehensive_analysis(self, sample_size=20, date_str="2024-01-01"):
        """Run comprehensive analysis on OHLC data."""
        print("🚀 COMPREHENSIVE OHLC DATA ANALYTICS")
        print("=" * 60)

        # Get sample symbols
        print("📊 Getting sample symbols...")
        symbols = self.get_sample_symbols(sample_size)
        print(f"✅ Selected {len(symbols)} symbols for analysis: {symbols[:5]}{'...' if len(symbols) > 5 else ''}")

        # Run volume analysis
        print("\n📈 Running Volume Analysis...")
        volume_results = self.run_volume_analysis(symbols, date_str)

        # Run price action analysis
        print("\n💹 Running Price Action Analysis...")
        price_results = self.run_price_action_analysis(symbols, date_str)

        # Find breakout candidates
        print("\n🎯 Finding Breakout Candidates...")
        breakout_results = self.find_breakout_candidates(symbols, date_str)

        # Generate summary report
        self.generate_summary_report(volume_results, price_results, breakout_results, date_str)

        return {
            'volume_analysis': volume_results,
            'price_analysis': price_results,
            'breakout_analysis': breakout_results
        }

    def generate_summary_report(self, volume_df, price_df, breakout_df, date_str):
        """Generate a comprehensive summary report."""
        print("\n📋 ANALYTICS SUMMARY REPORT")
        print("=" * 60)
        print(f"Analysis Date: {date_str}")
        print(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if not volume_df.empty:
            print("\n📊 VOLUME ANALYSIS SUMMARY:")
            print(f"  Symbols Analyzed: {len(volume_df)}")
            print(f"  Average Daily Volume: {volume_df['avg_volume'].mean():,.0f}")
            print(f"  Average Daily Range: {volume_df['daily_range_pct'].mean():.2f}%")
            print(f"  Highest Volume Symbol: {volume_df.loc[volume_df['total_volume'].idxmax(), 'symbol']} "
                  f"({volume_df['total_volume'].max():,.0f})")

        if not price_df.empty:
            print("\n💹 PRICE ACTION SUMMARY:")
            print(f"  Average Volatility: {price_df['volatility'].mean():.2f}%")
            print(f"  Average Intraday Range: {price_df['avg_range_pct'].mean():.2f}%")
            print(f"  Most Volatile Symbol: {price_df.loc[price_df['volatility'].idxmax(), 'symbol']} "
                  f"({price_df['volatility'].max():.2f}%)")

            bullish_symbols = price_df[price_df['above_ma10_pct'] > 0.6]
            if not bullish_symbols.empty:
                print(f"  Bullish Trend Symbols (>60% above MA10): {len(bullish_symbols)}")

        if not breakout_df.empty:
            print("\n🎯 BREAKOUT ANALYSIS SUMMARY:")
            breakout_types = breakout_df['breakout_type'].value_counts()
            for breakout_type, count in breakout_types.items():
                print(f"  {breakout_type}: {count} signals")

            if 'BULLISH_BREAKOUT' in breakout_df['breakout_type'].values:
                bullish = breakout_df[breakout_df['breakout_type'] == 'BULLISH_BREAKOUT']
                print(f"  Average Bullish Upside: {bullish['avg_upside'].mean():.2f}%")
                print(f"  Best Bullish Symbol: {bullish.loc[bullish['avg_upside'].idxmax(), 'symbol']}")

        print("\n✅ ANALYSIS COMPLETE!")
        print("💡 Insights:")
        print("  - High volume symbols indicate strong market interest")
        print("  - Low volatility periods often precede breakouts")
        print("  - Breakout patterns can signal trading opportunities")
        print("  - Volume confirmation is crucial for pattern validity")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def main():
    """Main function to run analytics."""
    # Change to project directory
    os.chdir('/Users/apple/Downloads/duckDbData')

    analytics = OHLCDataAnalytics()

    try:
        # Run comprehensive analysis
        results = analytics.run_comprehensive_analysis(
            sample_size=30,  # Analyze 30 symbols
            date_str="2024-01-01"  # Use this date for analysis
        )

        print("\n💾 Results saved in memory. Access via results dictionary:")
        print("  - results['volume_analysis']: Volume analysis DataFrame")
        print("  - results['price_analysis']: Price action analysis DataFrame")
        print("  - results['breakout_analysis']: Breakout analysis DataFrame")

        return results

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        analytics.close()


if __name__ == "__main__":
    main()
