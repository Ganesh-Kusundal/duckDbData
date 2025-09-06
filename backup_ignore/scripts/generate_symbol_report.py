#!/usr/bin/env python3
"""
Symbol Data Coverage Report Generator
====================================

Generates a comprehensive report showing the last available candle date
for all symbols in the database.
"""

import sys
import os
from datetime import datetime, date
from pathlib import Path
import pandas as pd

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.duckdb_infra import DuckDBManager

def generate_symbol_report():
    """Generate comprehensive symbol data coverage report."""
    
    print("📊 GENERATING SYMBOL DATA COVERAGE REPORT")
    print("="*60)
    
    # Initialize database manager
    db_manager = DuckDBManager()
    
    try:
        # Get comprehensive symbol information
        print("🔍 Analyzing data coverage for all symbols...")
        
        symbol_coverage_query = """
        SELECT 
            symbol,
            MIN(date_partition) as first_date,
            MAX(date_partition) as last_date,
            COUNT(DISTINCT date_partition) as trading_days,
            COUNT(*) as total_records,
            ROUND(AVG(volume), 0) as avg_daily_volume,
            ROUND(AVG(close), 2) as avg_price,
            MIN(close) as min_price,
            MAX(close) as max_price,
            MAX(timestamp) as last_timestamp
        FROM market_data 
        GROUP BY symbol 
        ORDER BY symbol
        """
        
        print("📈 Executing comprehensive analysis...")
        symbol_data = db_manager.execute_custom_query(symbol_coverage_query)
        
        if symbol_data.empty:
            print("❌ No data found in database")
            return
        
        # Get overall database statistics
        print("📊 Calculating database statistics...")
        
        overall_stats_query = """
        SELECT 
            COUNT(DISTINCT symbol) as total_symbols,
            COUNT(DISTINCT date_partition) as total_trading_days,
            COUNT(*) as total_records,
            MIN(date_partition) as earliest_date,
            MAX(date_partition) as latest_date,
            SUM(volume) as total_volume,
            ROUND(AVG(close), 2) as avg_market_price
        FROM market_data
        """
        
        overall_stats = db_manager.execute_custom_query(overall_stats_query)
        
        # Calculate data freshness
        today = date.today()
        latest_date_str = str(overall_stats.iloc[0]['latest_date'])
        if ' ' in latest_date_str:
            latest_date_str = latest_date_str.split(' ')[0]
        latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d').date()
        days_behind = (today - latest_date).days
        
        # Generate markdown report
        print("📝 Generating markdown report...")
        
        report_content = f"""# Symbol Data Coverage Report
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 Database Overview

| Metric | Value |
|--------|-------|
| **Total Symbols** | {overall_stats.iloc[0]['total_symbols']:,} |
| **Total Trading Days** | {overall_stats.iloc[0]['total_trading_days']:,} |
| **Total Records** | {overall_stats.iloc[0]['total_records']:,} |
| **Date Range** | {overall_stats.iloc[0]['earliest_date']} to {overall_stats.iloc[0]['latest_date']} |
| **Total Volume** | {overall_stats.iloc[0]['total_volume']:,.0f} shares |
| **Average Market Price** | ₹{overall_stats.iloc[0]['avg_market_price']:,.2f} |
| **Data Freshness** | {days_behind} days behind current date |

## 📈 Symbol-wise Data Coverage

### Summary Statistics

- **Most Recent Data**: {latest_date}
- **Symbols with Current Data**: {len(symbol_data[symbol_data['last_date'] == overall_stats.iloc[0]['latest_date']])}
- **Average Records per Symbol**: {symbol_data['total_records'].mean():,.0f}
- **Average Trading Days per Symbol**: {symbol_data['trading_days'].mean():.0f}

### 🔍 Detailed Symbol Analysis

| Symbol | First Date | Last Date | Trading Days | Total Records | Avg Volume | Avg Price | Price Range | Last Update |
|--------|------------|-----------|--------------|---------------|------------|-----------|-------------|-------------|
"""
        
        # Add detailed symbol information
        for _, row in symbol_data.iterrows():
            # Format dates
            first_date = str(row['first_date']).split(' ')[0] if pd.notna(row['first_date']) else 'N/A'
            last_date = str(row['last_date']).split(' ')[0] if pd.notna(row['last_date']) else 'N/A'
            last_timestamp = str(row['last_timestamp']).split(' ')[1][:5] if pd.notna(row['last_timestamp']) else 'N/A'
            
            # Format numbers
            avg_volume = f"{row['avg_daily_volume']:,.0f}" if pd.notna(row['avg_daily_volume']) else 'N/A'
            avg_price = f"₹{row['avg_price']:,.2f}" if pd.notna(row['avg_price']) else 'N/A'
            price_range = f"₹{row['min_price']:.2f} - ₹{row['max_price']:.2f}" if pd.notna(row['min_price']) and pd.notna(row['max_price']) else 'N/A'
            
            report_content += f"| **{row['symbol']}** | {first_date} | {last_date} | {row['trading_days']:,} | {row['total_records']:,} | {avg_volume} | {avg_price} | {price_range} | {last_timestamp} |\n"
        
        # Add data quality analysis
        report_content += f"""

## 📊 Data Quality Analysis

### Coverage Distribution

"""
        
        # Analyze data coverage patterns
        coverage_analysis_query = """
        SELECT 
            CASE 
                WHEN trading_days >= 250 THEN 'Excellent (250+ days)'
                WHEN trading_days >= 100 THEN 'Good (100-249 days)'
                WHEN trading_days >= 50 THEN 'Fair (50-99 days)'
                ELSE 'Limited (<50 days)'
            END as coverage_category,
            COUNT(*) as symbol_count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT symbol) FROM market_data), 1) as percentage
        FROM (
            SELECT 
                symbol,
                COUNT(DISTINCT date_partition) as trading_days
            FROM market_data 
            GROUP BY symbol
        ) coverage_stats
        GROUP BY coverage_category
        ORDER BY 
            CASE coverage_category
                WHEN 'Excellent (250+ days)' THEN 1
                WHEN 'Good (100-249 days)' THEN 2
                WHEN 'Fair (50-99 days)' THEN 3
                ELSE 4
            END
        """
        
        coverage_analysis = db_manager.execute_custom_query(coverage_analysis_query)
        
        report_content += "| Coverage Level | Symbol Count | Percentage |\n"
        report_content += "|----------------|--------------|------------|\n"
        
        for _, row in coverage_analysis.iterrows():
            report_content += f"| {row['coverage_category']} | {row['symbol_count']} | {row['percentage']}% |\n"
        
        # Add volume analysis
        report_content += f"""

### Volume Analysis

"""
        
        volume_analysis_query = """
        SELECT 
            CASE 
                WHEN avg_volume >= 1000000 THEN 'High Volume (1M+)'
                WHEN avg_volume >= 100000 THEN 'Medium Volume (100K-1M)'
                WHEN avg_volume >= 10000 THEN 'Low Volume (10K-100K)'
                ELSE 'Very Low Volume (<10K)'
            END as volume_category,
            COUNT(*) as symbol_count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT symbol) FROM market_data), 1) as percentage
        FROM (
            SELECT 
                symbol,
                ROUND(AVG(volume), 0) as avg_volume
            FROM market_data 
            GROUP BY symbol
        ) volume_stats
        GROUP BY volume_category
        ORDER BY 
            CASE volume_category
                WHEN 'High Volume (1M+)' THEN 1
                WHEN 'Medium Volume (100K-1M)' THEN 2
                WHEN 'Low Volume (10K-100K)' THEN 3
                ELSE 4
            END
        """
        
        volume_analysis = db_manager.execute_custom_query(volume_analysis_query)
        
        report_content += "| Volume Category | Symbol Count | Percentage |\n"
        report_content += "|-----------------|--------------|------------|\n"
        
        for _, row in volume_analysis.iterrows():
            report_content += f"| {row['volume_category']} | {row['symbol_count']} | {row['percentage']}% |\n"
        
        # Add recent activity analysis
        report_content += f"""

## 🕐 Recent Activity Analysis

### Symbols by Last Update Date

"""
        
        recent_activity_query = """
        SELECT 
            last_date,
            COUNT(*) as symbol_count
        FROM (
            SELECT 
                symbol,
                MAX(date_partition) as last_date
            FROM market_data 
            GROUP BY symbol
        ) last_dates
        GROUP BY last_date
        ORDER BY last_date DESC
        LIMIT 10
        """
        
        recent_activity = db_manager.execute_custom_query(recent_activity_query)
        
        report_content += "| Date | Symbols Updated |\n"
        report_content += "|------|----------------|\n"
        
        for _, row in recent_activity.iterrows():
            date_str = str(row['last_date']).split(' ')[0]
            report_content += f"| {date_str} | {row['symbol_count']} |\n"
        
        # Add recommendations
        report_content += f"""

## 💡 Recommendations

### Data Maintenance
- **Current Status**: Database is {days_behind} days behind current date
- **Action Required**: {'✅ Data is current' if days_behind <= 1 else '⚠️ Consider updating data' if days_behind <= 7 else '❌ Data update urgently needed'}

### Symbol Coverage
- **Well Covered**: {len(symbol_data[symbol_data['trading_days'] >= 100])} symbols with 100+ trading days
- **Needs Attention**: {len(symbol_data[symbol_data['trading_days'] < 50])} symbols with limited data

### Volume Quality
- **High Liquidity**: {len(symbol_data[symbol_data['avg_daily_volume'] >= 100000])} symbols suitable for active trading
- **Low Liquidity**: {len(symbol_data[symbol_data['avg_daily_volume'] < 10000])} symbols with limited trading activity

---

*Report generated by DuckDB Financial Data Infrastructure*  
*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        # Save report to file
        report_filename = f"symbol_coverage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_path = Path(report_filename)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"✅ Report generated successfully!")
        print(f"📄 Report saved to: {report_path.absolute()}")
        print(f"📊 Analyzed {len(symbol_data)} symbols")
        print(f"📅 Data range: {overall_stats.iloc[0]['earliest_date']} to {overall_stats.iloc[0]['latest_date']}")
        print(f"📈 Total records: {overall_stats.iloc[0]['total_records']:,}")
        
        return report_path
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        db_manager.close()

if __name__ == "__main__":
    generate_symbol_report()
