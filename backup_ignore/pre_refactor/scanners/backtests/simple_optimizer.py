#!/usr/bin/env python3
"""
Simple Parameter Optimizer for Trading Strategies

Focuses on key parameters that drive performance:
- Score thresholds
- Risk management
- Position sizing
- Market timing
"""

import sys
import os
from datetime import datetime, date, time, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import pandas as pd
import numpy as np
import json

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class SimpleOptimizer:
    """
    Simple but effective parameter optimizer
    """

    def __init__(self, db_path: str = "../data/financial_data.duckdb",
                 start_date: str = "2020-01-01", end_date: str = "2025-12-31"):
        """Initialize the optimizer"""
        self.db_path = db_path
        self.start_date = pd.to_datetime(start_date).date()
        self.end_date = pd.to_datetime(end_date).date()

        # Database connection
        self.db_manager = None
        self.initialize_database()

        print("🔧 SIMPLE PARAMETER OPTIMIZER")
        print("="*50)
        print(f"📅 Optimization Period: {self.start_date} to {self.end_date}")
        print("="*50)

    def initialize_database(self):
        """Initialize database connection"""
        try:
            from core.duckdb_infra import DuckDBManager
            self.db_manager = DuckDBManager()
            print("✅ Database connection established")
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            raise

    def optimize_score_threshold(self):
        """Optimize the minimum score threshold"""
        print("\n🎯 OPTIMIZING SCORE THRESHOLD")
        print("-" * 30)

        thresholds = [0.4, 0.5, 0.6, 0.7, 0.8]
        results = []

        for threshold in thresholds:
            print(f"   Testing threshold: {threshold}")

            # Run backtest with this threshold
            result = self.test_score_threshold(threshold)
            results.append({
                'threshold': threshold,
                'return': result.get('total_return', 0),
                'trades': result.get('total_trades', 0),
                'win_rate': result.get('win_rate', 0),
                'sharpe': result.get('sharpe_ratio', 0)
            })

            print(f"      📊 Return: {result.get('total_return', 0):.2f}%, Trades: {result.get('total_trades', 0)}, Win Rate: {result.get('win_rate', 0):.1f}%")

        # Find best threshold
        best_result = max(results, key=lambda x: x['return'])
        print(f"\n✅ Best Score Threshold: {best_result['threshold']} (Return: {best_result['return']:.2f}%)")

        return best_result['threshold']

    def optimize_risk_per_trade(self):
        """Fix risk per trade at 95%"""
        print("\n🎯 RISK PER TRADE FIXED AT 95%")
        print("-" * 30)
        print("   Skipping risk optimization as requested")
        print("   Using fixed risk per trade: 95%")

        return 0.95  # Fixed 95% risk per trade

    def optimize_leverage(self):
        """Skip leverage optimization - use fixed leverage"""
        print("\n🎯 LEVERAGE FIXED AT 5x")
        print("-" * 30)
        print("   Skipping leverage optimization as requested")
        print("   Using fixed leverage: 5x")

        return 5  # Fixed leverage

    def optimize_max_positions(self):
        """Optimize maximum positions"""
        print("\n🎯 OPTIMIZING MAX POSITIONS")
        print("-" * 30)

        position_limits = [2, 3, 4, 5, 6, 7, 8]
        results = []

        for max_pos in position_limits:
            print(f"   Testing max positions: {max_pos}")

            result = self.test_max_positions(max_pos)
            results.append({
                'max_positions': max_pos,
                'return': result.get('total_return', 0),
                'trades': result.get('total_trades', 0),
                'win_rate': result.get('win_rate', 0),
                'sharpe': result.get('sharpe_ratio', 0)
            })

            print(f"      📊 Return: {result.get('total_return', 0):.2f}%, Trades: {result.get('total_trades', 0)}")

        # Find optimal position limit
        best_result = max(results, key=lambda x: x['sharpe'])
        print(f"\n✅ Best Max Positions: {best_result['max_positions']} (Sharpe: {best_result['sharpe']:.2f})")

        return best_result['max_positions']

    def test_score_threshold(self, threshold: float) -> Dict:
        """Test a specific score threshold"""
        return self.run_parameter_test({'min_score_threshold': threshold})

    def test_risk_level(self, risk: float) -> Dict:
        """Test a specific risk level"""
        return self.run_parameter_test({'risk_per_trade': risk})

    def test_leverage(self, leverage: int) -> Dict:
        """Test a specific leverage level"""
        return self.run_parameter_test({'leverage': leverage})

    def test_max_positions(self, max_pos: int) -> Dict:
        """Test a specific max positions limit"""
        return self.run_parameter_test({'max_positions': max_pos})

    def run_parameter_test(self, test_params: Dict) -> Dict:
        """Run a parameter test"""
        try:
            # Create parameter set with defaults + test parameter
            default_params = {
                'min_score_threshold': 0.6,
                'obv_slope_threshold': 0.2,
                'vwap_deviation_band': 0.02,
                'risk_per_trade': 0.02,
                'leverage': 5,
                'max_positions': 5,
                'atr_threshold': 0.01,
                'volume_ratio_threshold': 1.5
            }

            # Update with test parameters
            default_params.update(test_params)

            # Run quick backtest
            backtester = QuickBacktester(
                db_manager=self.db_manager,
                start_date=self.start_date,
                end_date=self.end_date,
                parameters=default_params
            )

            return backtester.run_quick_backtest()

        except Exception as e:
            print(f"❌ Parameter test failed: {e}")
            return {'error': str(e)}

    def run_complete_optimization(self):
        """Run complete optimization sequence"""
        print("🚀 STARTING COMPLETE PARAMETER OPTIMIZATION")
        print("="*60)

        # Optimize each parameter sequentially
        optimal_score_threshold = self.optimize_score_threshold()
        optimal_risk = self.optimize_risk_per_trade()
        optimal_leverage = self.optimize_leverage()
        optimal_max_positions = self.optimize_max_positions()

        # Create optimal parameter set
        optimal_parameters = {
            'min_score_threshold': optimal_score_threshold,
            'obv_slope_threshold': 0.2,  # Keep default
            'vwap_deviation_band': 0.02,  # Keep default
            'risk_per_trade': optimal_risk,
            'leverage': optimal_leverage,
            'max_positions': optimal_max_positions,
            'atr_threshold': 0.01,  # Keep default
            'volume_ratio_threshold': 1.5  # Keep default
        }

        print("\n🎯 OPTIMAL PARAMETER SET")
        print("="*40)
        for param, value in optimal_parameters.items():
            print(f"   {param}: {value}")

        # Run final validation
        print("\n🔬 FINAL VALIDATION")
        print("-" * 20)

        final_backtester = QuickBacktester(
            db_manager=self.db_manager,
            start_date=self.start_date,
            end_date=self.end_date,
            parameters=optimal_parameters
        )

        final_result = final_backtester.run_quick_backtest()

        print("\n📊 OPTIMIZATION RESULTS")
        print("="*40)
        print(f"💰 Final Portfolio: ₹{final_result.get('final_portfolio', 1000000):,.0f}")
        print(f"📈 Total Return: {final_result.get('total_return', 0):.2f}%")
        print(f"🎯 Total Trades: {final_result.get('total_trades', 0)}")
        print(f"📊 Win Rate: {final_result.get('win_rate', 0):.1f}%")
        print(f"⚡ Sharpe Ratio: {final_result.get('sharpe_ratio', 0):.2f}")
        print(f"📉 Max Drawdown: {final_result.get('max_drawdown', 0)*100:.2f}%")

        # Save optimal parameters
        with open('optimal_parameters_simple.json', 'w') as f:
            json.dump({
                'optimal_parameters': optimal_parameters,
                'final_results': final_result,
                'optimization_date': str(datetime.now())
            }, f, indent=2, default=str)

        print("\n💾 Optimal parameters saved to: optimal_parameters_simple.json")

        return optimal_parameters, final_result


class QuickBacktester:
    """
    Quick backtester for parameter optimization
    """

    def __init__(self, db_manager, start_date: date, end_date: date, parameters: Dict):
        """Initialize quick backtester"""
        self.db_manager = db_manager
        self.start_date = start_date
        self.end_date = end_date
        self.params = parameters

        # Initialize with parameters
        self.initial_capital = 1000000
        self.capital = self.initial_capital
        self.portfolio_value = self.initial_capital

        # Apply parameters
        self.min_score_threshold = parameters.get('min_score_threshold', 0.6)
        self.obv_slope_threshold = parameters.get('obv_slope_threshold', 0.2)
        self.vwap_deviation_band = parameters.get('vwap_deviation_band', 0.02)
        self.risk_per_trade = parameters.get('risk_per_trade', 0.02)
        self.leverage = parameters.get('leverage', 5)
        self.max_positions = parameters.get('max_positions', 5)
        self.atr_threshold = parameters.get('atr_threshold', 0.01)
        self.volume_ratio_threshold = parameters.get('volume_ratio_threshold', 1.5)

    def run_quick_backtest(self) -> Dict:
        """Run quick backtest"""
        try:
            # Get trading days (sample for speed)
            trading_days = self.get_trading_days()
            if not trading_days:
                return {'error': 'No trading days found'}

            trades = []
            daily_pnl = []
            max_drawdown = 0
            peak_value = self.initial_capital

            # Process every 3rd day for speed
            test_days = trading_days[::3][:30]  # 30 days max

            for trade_date in test_days:
                day_trades = self.process_trading_day(trade_date)
                trades.extend(day_trades)

                # Update portfolio
                day_pnl = sum(trade.get('pnl', 0) for trade in day_trades)
                self.portfolio_value += day_pnl

                daily_pnl.append({
                    'date': trade_date,
                    'pnl': day_pnl,
                    'portfolio_value': self.portfolio_value
                })

                # Update drawdown
                if self.portfolio_value > peak_value:
                    peak_value = self.portfolio_value
                else:
                    current_dd = (peak_value - self.portfolio_value) / peak_value
                    max_drawdown = max(max_drawdown, current_dd)

            # Calculate metrics
            total_return = (self.portfolio_value - self.initial_capital) / self.initial_capital * 100
            win_rate = len([t for t in trades if t.get('pnl', 0) > 0]) / len(trades) * 100 if trades else 0

            # Calculate Sharpe ratio
            if daily_pnl and len(daily_pnl) > 1:
                returns = [day['pnl'] / self.initial_capital for day in daily_pnl]
                avg_return = np.mean(returns)
                std_return = np.std(returns)
                sharpe_ratio = avg_return / std_return * np.sqrt(252) if std_return > 0 else 0
            else:
                sharpe_ratio = 0

            return {
                'total_return': total_return,
                'total_trades': len(trades),
                'win_rate': win_rate,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'final_portfolio': self.portfolio_value
            }

        except Exception as e:
            print(f"❌ Backtest error: {e}")
            return {'error': str(e)}

    def get_trading_days(self) -> List[date]:
        """Get trading days"""
        try:
            query = f"""
            SELECT DISTINCT date_partition
            FROM market_data
            WHERE date_partition >= '{self.start_date}'
            AND date_partition <= '{self.end_date}'
            ORDER BY date_partition
            """
            result = self.db_manager.execute_custom_query(query)
            return [pd.to_datetime(d).date() for d in result['date_partition'].tolist()]
        except:
            return []

    def process_trading_day(self, trade_date: date) -> List[Dict]:
        """Process trading day"""
        trades = []

        try:
            symbols = self.get_symbols_for_date(trade_date)
            if not symbols:
                return trades

            # Scan top symbols
            for symbol in symbols[:15]:  # Limit for speed
                trade = self.scan_symbol(symbol, trade_date)
                if trade:
                    trades.append(trade)

        except Exception as e:
            pass

        return trades[:self.max_positions]  # Limit positions

    def get_symbols_for_date(self, trade_date: date) -> List[str]:
        """Get symbols for date"""
        try:
            query = f"""
            SELECT DISTINCT symbol
            FROM market_data
            WHERE date_partition = '{trade_date}'
            ORDER BY volume DESC
            """
            result = self.db_manager.execute_custom_query(query)
            return result['symbol'].tolist()[:30]  # Top 30 by volume
        except:
            return []

    def scan_symbol(self, symbol: str, trade_date: date) -> Optional[Dict]:
        """Scan symbol for trade opportunity"""
        try:
            df = self.get_minute_data(symbol, trade_date, time(9, 15), time(9, 50))
            if df.empty or len(df) < 20:
                return None

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            # Calculate score
            score = 0

            # Volume strength
            if latest['volume'] > self.volume_ratio_threshold * df['volume'].mean():
                score += 0.25

            # Price momentum
            if latest['close'] > prev['close']:
                score += 0.25

            # OBV momentum
            if len(df) > 5:
                obv_recent = (df['close'] * df['volume']).tail(5).sum()
                obv_earlier = (df['close'] * df['volume']).iloc[-10:-5].sum()
                if obv_recent > obv_earlier * (1 + self.obv_slope_threshold):
                    score += 0.3

            # VWAP alignment
            if len(df) > 10:
                vwap = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
                if abs(latest['close'] - vwap.iloc[-1]) / vwap.iloc[-1] < self.vwap_deviation_band:
                    score += 0.2

            # Generate trade if score meets threshold
            if score >= self.min_score_threshold:
                direction = 'LONG' if latest['close'] > prev['close'] else 'SHORT'
                quantity = int((self.capital * self.risk_per_trade * self.leverage) / latest['close'])

                # Simulate exit
                exit_price = latest['close'] * 1.008 if direction == 'LONG' else latest['close'] * 0.992
                pnl = (exit_price - latest['close']) * quantity if direction == 'LONG' else (latest['close'] - exit_price) * quantity

                return {
                    'symbol': symbol,
                    'direction': direction,
                    'entry_price': latest['close'],
                    'exit_price': exit_price,
                    'quantity': quantity,
                    'pnl': pnl,
                    'entry_date': trade_date,
                    'exit_date': trade_date
                }

        except Exception as e:
            pass

        return None

    def get_minute_data(self, symbol: str, trade_date: date, start_time: time, end_time: time) -> pd.DataFrame:
        """Get minute data"""
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


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Simple Parameter Optimizer')
    parser.add_argument('--db-path', default='../data/financial_data.duckdb',
                       help='Path to DuckDB database')
    parser.add_argument('--start-date', default='2020-01-01',
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', default='2025-12-31',
                       help='End date (YYYY-MM-DD)')

    args = parser.parse_args()

    # Run optimization
    optimizer = SimpleOptimizer(
        db_path=args.db_path,
        start_date=args.start_date,
        end_date=args.end_date
    )

    optimal_params, final_results = optimizer.run_complete_optimization()

    print("\n🎉 OPTIMIZATION COMPLETED!")
    print("="*50)
    print("✅ Sequential parameter optimization")
    print("✅ Risk-adjusted parameter selection")
    print("✅ Optimal parameters identified")
    print("✅ Results saved to optimal_parameters_simple.json")

if __name__ == "__main__":
    main()
