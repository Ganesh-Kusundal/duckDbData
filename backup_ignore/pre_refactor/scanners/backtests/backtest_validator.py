#!/usr/bin/env python3
"""
Backtest Validation Framework

Validates backtest results for common biases and provides realistic adjustments:
- Look-ahead bias detection
- Survivorship bias analysis
- Selection bias checks
- Liquidity bias validation
- Execution bias simulation
- Universe change bias detection
- Market impact bias estimation
"""

import sys
import os
from datetime import datetime, date, time, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class BacktestValidator:
    """
    Comprehensive backtest validation framework
    """

    def __init__(self, trades_csv: str = "../fast_backtest_trades_2025.csv",
                 pnl_csv: str = "../fast_backtest_pnl_2025.csv",
                 db_path: str = "../data/financial_data.duckdb"):
        """Initialize the validator"""
        self.trades_csv = trades_csv
        self.pnl_csv = pnl_csv
        self.db_path = db_path

        # Validation results
        self.validation_report = {}
        self.adjusted_trades = []
        self.bias_scores = {}

        # Initialize database
        self.db_manager = None
        self.initialize_database()

        print("🔍 BACKTEST VALIDATION FRAMEWORK")
        print("="*60)
        print("Validating for common quantitative biases...")
        print("="*60)

    def initialize_database(self):
        """Initialize database connection"""
        try:
            from core.duckdb_infra import DuckDBManager
            self.db_manager = DuckDBManager()
            print("✅ Database connection established")
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            raise

    def load_backtest_data(self):
        """Load backtest results"""
        try:
            self.trades_df = pd.read_csv(self.trades_csv)
            self.pnl_df = pd.read_csv(self.pnl_csv)
            print(f"✅ Loaded {len(self.trades_df)} trades and {len(self.pnl_df)} P&L records")
        except Exception as e:
            print(f"❌ Error loading backtest data: {e}")
            return False
        return True

    def validate_look_ahead_bias(self) -> Dict:
        """Validate for look-ahead bias"""
        print("\n🔍 VALIDATING LOOK-AHEAD BIAS")
        print("-" * 40)

        look_ahead_issues = []
        total_checks = 0
        issues_found = 0

        for idx, trade in self.trades_df.iterrows():
            total_checks += 1
            entry_date = pd.to_datetime(trade['entry_date']).date()
            entry_time = pd.to_datetime(trade['entry_time']).time()

            # Check if VWAP calculation uses future data
            symbol = trade['symbol']

            # Get data up to entry time
            actual_data = self.get_minute_data(symbol, entry_date, time(9, 15), entry_time)

            if actual_data.empty or len(actual_data) < 10:
                issues_found += 1
                look_ahead_issues.append({
                    'trade_id': idx,
                    'symbol': symbol,
                    'date': entry_date,
                    'issue': 'insufficient_data_for_indicators'
                })
                continue

            # Calculate VWAP using only available data
            actual_vwap = (actual_data['close'] * actual_data['volume']).cumsum() / actual_data['volume'].cumsum()
            actual_vwap_latest = actual_vwap.iloc[-1]

            # Check if the trade decision could be made with available data
            # This is a simplified check - in practice you'd recalculate all indicators
            if len(actual_data) < 30:  # Need enough bars for reliable indicators
                issues_found += 1
                look_ahead_issues.append({
                    'trade_id': idx,
                    'symbol': symbol,
                    'date': entry_date,
                    'issue': 'insufficient_bars_for_indicators'
                })

        look_ahead_bias_score = (issues_found / total_checks) * 100 if total_checks > 0 else 0

        result = {
            'bias_type': 'look_ahead',
            'issues_found': issues_found,
            'total_checks': total_checks,
            'bias_score': look_ahead_bias_score,
            'issues': look_ahead_issues[:10],  # Show first 10 issues
            'status': 'LOW_RISK' if look_ahead_bias_score < 5 else 'MEDIUM_RISK' if look_ahead_bias_score < 15 else 'HIGH_RISK'
        }

        print(f"📊 Look-ahead bias score: {look_ahead_bias_score:.2f}%")
        print(f"🎯 Status: {result['status']}")
        print(f"❌ Issues found: {issues_found}/{total_checks}")

        return result

    def validate_survivorship_bias(self) -> Dict:
        """Validate for survivorship bias"""
        print("\n🔍 VALIDATING SURVIVORSHIP BIAS")
        print("-" * 40)

        # Get unique symbols in backtest
        backtest_symbols = set(self.trades_df['symbol'].unique())

        # Check how many symbols from historical universe are missing
        # This is a simplified check - in practice you'd check against historical index membership
        total_historical_symbols = len(backtest_symbols) * 1.5  # Estimate
        survivorship_rate = (len(backtest_symbols) / total_historical_symbols) * 100

        survivorship_bias_score = 100 - survivorship_rate

        result = {
            'bias_type': 'survivorship',
            'backtest_symbols': len(backtest_symbols),
            'estimated_historical_symbols': int(total_historical_symbols),
            'survivorship_rate': survivorship_rate,
            'bias_score': survivorship_bias_score,
            'status': 'LOW_RISK' if survivorship_bias_score < 10 else 'MEDIUM_RISK' if survivorship_bias_score < 25 else 'HIGH_RISK'
        }

        print(f"📊 Survivorship bias score: {survivorship_bias_score:.2f}%")
        print(f"🎯 Status: {result['status']}")
        print(f"📈 Survivorship rate: {survivorship_rate:.1f}%")

        return result

    def validate_selection_bias(self) -> Dict:
        """Validate for selection bias"""
        print("\n🔍 VALIDATING SELECTION BIAS")
        print("-" * 40)

        # Check if we're only trading certain types of stocks
        trade_directions = self.trades_df['direction'].value_counts()
        setup_types = self.trades_df['setup_type'].value_counts()

        # Check for concentration in specific stocks
        symbol_counts = self.trades_df['symbol'].value_counts()
        top_symbol_pct = (symbol_counts.iloc[0] / len(self.trades_df)) * 100 if len(symbol_counts) > 0 else 0

        # Check for directional bias
        long_trades = trade_directions.get('LONG', 0)
        short_trades = trade_directions.get('SHORT', 0)
        direction_bias = abs(long_trades - short_trades) / (long_trades + short_trades) * 100

        selection_bias_score = (top_symbol_pct + direction_bias) / 2

        result = {
            'bias_type': 'selection',
            'top_symbol_concentration': top_symbol_pct,
            'direction_bias': direction_bias,
            'bias_score': selection_bias_score,
            'status': 'LOW_RISK' if selection_bias_score < 15 else 'MEDIUM_RISK' if selection_bias_score < 30 else 'HIGH_RISK'
        }

        print(f"📊 Selection bias score: {selection_bias_score:.2f}%")
        print(f"🎯 Status: {result['status']}")
        print(f"🏆 Top symbol concentration: {top_symbol_pct:.1f}%")
        print(f"📊 Direction bias: {direction_bias:.1f}%")

        return result

    def validate_liquidity_bias(self) -> Dict:
        """Validate for liquidity bias"""
        print("\n🔍 VALIDATING LIQUIDITY BIAS")
        print("-" * 40)

        liquidity_issues = []
        total_checks = 0
        issues_found = 0

        for idx, trade in self.trades_df.iterrows():
            total_checks += 1
            symbol = trade['symbol']
            entry_date = pd.to_datetime(trade['entry_date']).date()

            # Check volume at entry time
            entry_data = self.get_minute_data(symbol, entry_date, time(9, 15), time(9, 50))

            if not entry_data.empty:
                avg_volume = entry_data['volume'].mean()
                latest_volume = entry_data['volume'].iloc[-1]

                # Check if volume is sufficient
                if avg_volume < 50000:  # Less than 50k average volume
                    issues_found += 1
                    liquidity_issues.append({
                        'trade_id': idx,
                        'symbol': symbol,
                        'date': entry_date,
                        'avg_volume': avg_volume,
                        'issue': 'low_volume'
                    })

                # Check for volume spikes (potential manipulation)
                if latest_volume > avg_volume * 5:
                    issues_found += 1
                    liquidity_issues.append({
                        'trade_id': idx,
                        'symbol': symbol,
                        'date': entry_date,
                        'volume_ratio': latest_volume / avg_volume,
                        'issue': 'volume_spike'
                    })

        liquidity_bias_score = (issues_found / total_checks) * 100 if total_checks > 0 else 0

        result = {
            'bias_type': 'liquidity',
            'issues_found': issues_found,
            'total_checks': total_checks,
            'bias_score': liquidity_bias_score,
            'issues': liquidity_issues[:10],
            'status': 'LOW_RISK' if liquidity_bias_score < 10 else 'MEDIUM_RISK' if liquidity_bias_score < 25 else 'HIGH_RISK'
        }

        print(f"📊 Liquidity bias score: {liquidity_bias_score:.2f}%")
        print(f"🎯 Status: {result['status']}")
        print(f"❌ Liquidity issues: {issues_found}/{total_checks}")

        return result

    def validate_execution_bias(self) -> Dict:
        """Validate for execution bias (slippage, tick size)"""
        print("\n🔍 VALIDATING EXECUTION BIAS")
        print("-" * 40)

        # Simulate realistic execution with slippage and tick size
        adjusted_pnl = []
        total_slippage_cost = 0

        for idx, trade in self.trades_df.iterrows():
            entry_price = trade['entry_price']
            exit_price = trade['exit_price']
            quantity = trade['quantity']

            # Add realistic slippage (0.1-0.2% of price)
            slippage_pct = 0.0015  # 0.15% average slippage
            slippage_amount = entry_price * slippage_pct

            # Apply tick size rounding (₹0.05 for most stocks)
            tick_size = 0.05
            adjusted_entry = round(entry_price / tick_size) * tick_size
            adjusted_exit = round(exit_price / tick_size) * tick_size

            # Add slippage to entry
            if trade['direction'] == 'LONG':
                adjusted_entry += slippage_amount
                pnl = (adjusted_exit - adjusted_entry) * quantity
            else:  # SHORT
                adjusted_entry -= slippage_amount
                pnl = (adjusted_entry - adjusted_exit) * quantity

            adjusted_pnl.append(pnl)
            total_slippage_cost += abs(pnl - trade['pnl'])

        original_total_pnl = self.trades_df['pnl'].sum()
        adjusted_total_pnl = sum(adjusted_pnl)
        execution_impact = (original_total_pnl - adjusted_total_pnl) / abs(original_total_pnl) * 100

        result = {
            'bias_type': 'execution',
            'original_pnl': original_total_pnl,
            'adjusted_pnl': adjusted_total_pnl,
            'total_slippage_cost': total_slippage_cost,
            'execution_impact_pct': execution_impact,
            'bias_score': abs(execution_impact),
            'status': 'LOW_RISK' if abs(execution_impact) < 5 else 'MEDIUM_RISK' if abs(execution_impact) < 15 else 'HIGH_RISK'
        }

        print(f"📊 Execution bias score: {abs(execution_impact):.2f}%")
        print(f"🎯 Status: {result['status']}")
        print(f"💰 Original P&L: ₹{original_total_pnl:,.0f}")
        print(f"💰 Adjusted P&L: ₹{adjusted_total_pnl:,.0f}")
        print(f"📉 Execution impact: {execution_impact:.2f}%")

        return result

    def validate_universe_change_bias(self) -> Dict:
        """Validate for universe change bias (splits, dividends, etc.)"""
        print("\n🔍 VALIDATING UNIVERSE CHANGE BIAS")
        print("-" * 40)

        # Check for potential corporate actions
        # This is a simplified check - in practice you'd check against corporate action databases
        universe_issues = []
        total_checks = 0
        issues_found = 0

        # Check for price anomalies that might indicate splits/dividends
        for symbol in self.trades_df['symbol'].unique():
            symbol_trades = self.trades_df[self.trades_df['symbol'] == symbol]
            prices = symbol_trades['entry_price'].values

            if len(prices) > 1:
                total_checks += 1
                # Check for sudden price changes (potential splits)
                price_changes = np.diff(prices) / prices[:-1]
                max_change = np.max(np.abs(price_changes))

                if max_change > 0.5:  # 50% price change
                    issues_found += 1
                    universe_issues.append({
                        'symbol': symbol,
                        'max_price_change': max_change,
                        'issue': 'potential_corporate_action'
                    })

        universe_bias_score = (issues_found / total_checks) * 100 if total_checks > 0 else 0

        result = {
            'bias_type': 'universe_change',
            'issues_found': issues_found,
            'total_checks': total_checks,
            'bias_score': universe_bias_score,
            'issues': universe_issues,
            'status': 'LOW_RISK' if universe_bias_score < 5 else 'MEDIUM_RISK' if universe_bias_score < 15 else 'HIGH_RISK'
        }

        print(f"📊 Universe change bias score: {universe_bias_score:.2f}%")
        print(f"🎯 Status: {result['status']}")
        print(f"❌ Universe issues: {issues_found}/{total_checks}")

        return result

    def validate_market_impact_bias(self) -> Dict:
        """Validate for market impact bias"""
        print("\n🔍 VALIDATING MARKET IMPACT BIAS")
        print("-" * 40)

        impact_issues = []
        total_checks = 0
        issues_found = 0

        for idx, trade in self.trades_df.iterrows():
            total_checks += 1
            symbol = trade['symbol']
            entry_date = pd.to_datetime(trade['entry_date']).date()
            quantity = trade['quantity']
            entry_price = trade['entry_price']

            # Estimate market impact based on trade size relative to average volume
            entry_data = self.get_minute_data(symbol, entry_date, time(9, 15), time(9, 50))

            if not entry_data.empty:
                avg_volume = entry_data['volume'].mean()
                trade_size_pct = (quantity / avg_volume) * 100

                # Estimate impact cost
                if trade_size_pct > 10:  # Trade size > 10% of average volume
                    impact_cost_pct = min(trade_size_pct * 0.01, 2.0)  # Up to 2% impact
                    issues_found += 1
                    impact_issues.append({
                        'trade_id': idx,
                        'symbol': symbol,
                        'date': entry_date,
                        'trade_size_pct': trade_size_pct,
                        'estimated_impact': impact_cost_pct,
                        'issue': 'large_trade_size'
                    })

        market_impact_bias_score = (issues_found / total_checks) * 100 if total_checks > 0 else 0

        result = {
            'bias_type': 'market_impact',
            'issues_found': issues_found,
            'total_checks': total_checks,
            'bias_score': market_impact_bias_score,
            'issues': impact_issues[:10],
            'status': 'LOW_RISK' if market_impact_bias_score < 5 else 'MEDIUM_RISK' if market_impact_bias_score < 15 else 'HIGH_RISK'
        }

        print(f"📊 Market impact bias score: {market_impact_bias_score:.2f}%")
        print(f"🎯 Status: {result['status']}")
        print(f"❌ Impact issues: {issues_found}/{total_checks}")

        return result

    def get_minute_data(self, symbol: str, trade_date: date, start_time: time, end_time: time) -> pd.DataFrame:
        """Get minute data for validation"""
        try:
            start_datetime = datetime.combine(trade_date, start_time)
            end_datetime = datetime.combine(trade_date, end_time)

            query = f"""
            SELECT timestamp, open, high, low, close, volume
            FROM market_data
            WHERE symbol = '{symbol}'
            AND date_partition = '{trade_date}'
            AND timestamp >= '{start_datetime}'
            AND timestamp <= '{end_datetime}'
            ORDER BY timestamp
            """

            result = self.db_manager.execute_custom_query(query)
            if result.empty:
                return pd.DataFrame()

            result['timestamp'] = pd.to_datetime(result['timestamp'])
            return result

        except Exception as e:
            return pd.DataFrame()

    def run_validation(self):
        """Run complete validation suite"""
        print("🚀 STARTING COMPREHENSIVE BACKTEST VALIDATION")
        print("="*80)

        if not self.load_backtest_data():
            return

        # Run all validations
        validations = [
            self.validate_look_ahead_bias,
            self.validate_survivorship_bias,
            self.validate_selection_bias,
            self.validate_liquidity_bias,
            self.validate_execution_bias,
            self.validate_universe_change_bias,
            self.validate_market_impact_bias
        ]

        validation_results = {}
        for validation_func in validations:
            try:
                result = validation_func()
                validation_results[result['bias_type']] = result
            except Exception as e:
                print(f"❌ Error in {validation_func.__name__}: {e}")

        self.validation_report = validation_results
        self.generate_validation_report()

    def generate_validation_report(self):
        """Generate comprehensive validation report"""
        print("\n📊 COMPREHENSIVE VALIDATION REPORT")
        print("="*80)

        # Overall risk assessment
        bias_scores = [result['bias_score'] for result in self.validation_report.values()]
        overall_risk_score = np.mean(bias_scores)

        risk_levels = [result['status'] for result in self.validation_report.values()]
        high_risk_count = risk_levels.count('HIGH_RISK')
        medium_risk_count = risk_levels.count('MEDIUM_RISK')

        if high_risk_count > 0:
            overall_status = 'HIGH_RISK'
        elif medium_risk_count > 2:
            overall_status = 'MEDIUM_RISK'
        else:
            overall_status = 'LOW_RISK'

        print(f"🎯 OVERALL VALIDATION STATUS: {overall_status}")
        print(f"📊 Overall Risk Score: {overall_risk_score:.2f}%")
        print(f"🔴 High Risk Biases: {high_risk_count}")
        print(f"🟡 Medium Risk Biases: {medium_risk_count}")
        print(f"🟢 Low Risk Biases: {risk_levels.count('LOW_RISK')}")

        print("\n" + "="*80)
        print("BIAS VALIDATION SUMMARY:")
        print("="*80)

        for bias_type, result in self.validation_report.items():
            status_emoji = {
                'LOW_RISK': '🟢',
                'MEDIUM_RISK': '🟡',
                'HIGH_RISK': '🔴'
            }[result['status']]

            print(f"\n{status_emoji} {bias_type.upper().replace('_', ' ')} BIAS")
            print(f"   Risk Score: {result['bias_score']:.2f}%")
            print(f"   Status: {result['status']}")

            # Show key metrics
            if bias_type == 'look_ahead':
                print(f"   Issues Found: {result['issues_found']}/{result['total_checks']}")
            elif bias_type == 'survivorship':
                print(f"   Survivorship Rate: {result['survivorship_rate']:.1f}%")
            elif bias_type == 'selection':
                print(f"   Top Symbol Concentration: {result['top_symbol_concentration']:.1f}%")
                print(f"   Direction Bias: {result['direction_bias']:.1f}%")
            elif bias_type == 'liquidity':
                print(f"   Liquidity Issues: {result['issues_found']}/{result['total_checks']}")
            elif bias_type == 'execution':
                print(f"   Execution Impact: {result['execution_impact_pct']:.2f}%")
                print(f"   Slippage Cost: ₹{result['total_slippage_cost']:,.0f}")
            elif bias_type == 'universe_change':
                print(f"   Universe Issues: {result['issues_found']}/{result['total_checks']}")
            elif bias_type == 'market_impact':
                print(f"   Impact Issues: {result['issues_found']}/{result['total_checks']}")

        print("\n" + "="*80)
        print("VALIDATION RECOMMENDATIONS:")
        print("="*80)

        recommendations = []

        for bias_type, result in self.validation_report.items():
            if result['status'] == 'HIGH_RISK':
                if bias_type == 'look_ahead':
                    recommendations.append("• Fix look-ahead bias: Ensure all indicators use only historical data up to decision time")
                elif bias_type == 'survivorship':
                    recommendations.append("• Address survivorship bias: Test on historical universe including delisted stocks")
                elif bias_type == 'selection':
                    recommendations.append("• Reduce selection bias: Define universe rules upfront, avoid cherry-picking")
                elif bias_type == 'liquidity':
                    recommendations.append("• Improve liquidity filters: Add minimum volume/turnover requirements")
                elif bias_type == 'execution':
                    recommendations.append("• Add execution realism: Include slippage, tick size, and market impact costs")
                elif bias_type == 'universe_change':
                    recommendations.append("• Handle corporate actions: Use split/dividend adjusted data")
                elif bias_type == 'market_impact':
                    recommendations.append("• Reduce market impact: Limit position sizes for illiquid stocks")

        if recommendations:
            print("\n".join(recommendations))
        else:
            print("✅ No critical issues found! Backtest appears robust.")

        print("\n" + "="*80)
        print("VALIDATION COMPLETE")
        print("="*80)

        # Save validation report
        validation_summary = {
            'overall_status': overall_status,
            'overall_risk_score': overall_risk_score,
            'validation_results': self.validation_report,
            'recommendations': recommendations
        }

        import json
        with open('backtest_validation_report.json', 'w') as f:
            json.dump(validation_summary, f, indent=2, default=str)

        print("💾 Validation report saved to: backtest_validation_report.json")

def main():
    """Main function to run validation"""
    import argparse

    parser = argparse.ArgumentParser(description='Backtest Validation Framework')
    parser.add_argument('--trades-csv', default='fast_backtest_trades_2025.csv',
                       help='Path to trades CSV file')
    parser.add_argument('--pnl-csv', default='fast_backtest_pnl_2025.csv',
                       help='Path to P&L CSV file')
    parser.add_argument('--db-path', default='data/financial_data.duckdb',
                       help='Path to DuckDB database')

    args = parser.parse_args()

    # Initialize and run validation
    validator = BacktestValidator(
        trades_csv=args.trades_csv,
        pnl_csv=args.pnl_csv,
        db_path=args.db_path
    )

    validator.run_validation()

if __name__ == "__main__":
    main()
