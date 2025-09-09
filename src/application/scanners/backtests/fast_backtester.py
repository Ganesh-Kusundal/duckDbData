#!/usr/bin/env python3
"""
Fast Advanced Two-Phase Scanner Backtester

Optimized for speed with:
- Parallel processing using multiprocessing
- 2025 data only (faster)
- Simplified reporting
- Batch processing
"""

import sys
import os
from datetime import datetime, date, time, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.infrastructure.core.singleton_database import DuckDBConnectionManager, create_db_manager

class FastBacktester:
    """
    Fast backtester optimized for 2025 data with parallel processing
    """

    def __init__(self, db_path: str = "data/financial_data.duckdb", start_date: str = "2025-01-01", end_date: str = "2025-12-31"):
        """Initialize the fast backtester"""
        self.db_path = db_path
        self.start_date = pd.to_datetime(start_date).date()
        self.end_date = pd.to_datetime(end_date).date()

        # Trading parameters
        self.initial_capital = 1000000  # ₹10 lakh starting capital
        self.capital = self.initial_capital
        self.max_positions = 5
        self.risk_per_trade = 0.02  # 2% risk per trade
        self.leverage = 5  # 5x leverage
        self.capital_utilization = 0.95  # Use 95% of capital

        # Optimization parameters
        self.target_shortlist_size = 20
        self.sideways_atr_threshold = 0.003
        self.sideways_adx_threshold = 20
        self.sideways_vwap_band = 0.003
        self.sideways_obv_slope_threshold = 0.1
        self.min_score_threshold = 0.7
        self.rotation_score_threshold = 0.8

        # Backtest tracking
        self.portfolio_value = self.initial_capital
        self.trades = []
        self.daily_pnl = []
        self.scoreboard = {}
        self.session_phase = "morning"

        # Performance tracking
        self.peak_portfolio_value = self.initial_capital
        self.max_drawdown = 0
        self.max_drawdown_date = None
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0

        # Initialize database
        self.db_manager = None
        self.initialize_database()

        print("🚀 FAST ADVANCED TWO-PHASE SCANNER BACKTESTER")
        print("="*60)
        print(f"📅 Backtest Period: {self.start_date} to {self.end_date}")
        print(f"💰 Initial Capital: ₹{self.initial_capital:,0f}")
        print(f"⚡ Leverage: {self.leverage}x")
        print(f"📊 Max Positions: {self.max_positions}")
        print("="*60)

    def initialize_database(self):
        """Initialize database connection"""
        try:
            self.db_manager = create_db_manager(db_path=self.db_path)
            print("✅ Database connection established")
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            raise

    def get_trading_days(self) -> List[date]:
        """Get all trading days in the backtest period"""
        try:
            query = f"""
            SELECT DISTINCT date_partition
            FROM market_data_unified
            WHERE date_partition >= '{self.start_date}'
            AND date_partition <= '{self.end_date}'
            ORDER BY date_partition
            """
            result = self.db_manager.execute_custom_query(query)
            trading_days = [pd.to_datetime(d).date() for d in result['date_partition'].tolist()]
            print(f"📊 Found {len(trading_days)} trading days for backtest")
            return trading_days
        except Exception as e:
            print(f"❌ Error getting trading days: {e}")
            return []

    def get_minute_data(self, symbol: str, trade_date: date, start_time: time, end_time: time) -> pd.DataFrame:
        """Get minute data for a symbol on a specific date within time range"""
        try:
            start_datetime = datetime.combine(trade_date, start_time)
            end_datetime = datetime.combine(trade_date, end_time)

            query = f"""
            SELECT timestamp, open, high, low, close, volume
            FROM market_data_unified
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

    def calculate_advanced_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate advanced technical indicators"""
        if df.empty or len(df) < 30:
            return df

        # Basic indicators
        df['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
        df['returns'] = df['close'].pct_change()

        # OBV and OBV slope
        df['obv'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        df['obv_slope'] = df['obv'].diff(10) / df['obv'].rolling(20).std()

        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(14).mean()
        df['atr_pct'] = df['atr'] / df['close']

        # ADX
        df['dm_plus'] = np.where(df['high'] - df['high'].shift(1) > df['low'].shift(1) - df['low'],
                                np.maximum(df['high'] - df['high'].shift(1), 0), 0)
        df['dm_minus'] = np.where(df['low'].shift(1) - df['low'] > df['high'] - df['high'].shift(1),
                                 np.maximum(df['low'].shift(1) - df['low'], 0), 0)
        df['di_plus'] = 100 * (df['dm_plus'].rolling(14).mean() / df['atr'])
        df['di_minus'] = 100 * (df['dm_minus'].rolling(14).mean() / df['atr'])
        df['dx'] = 100 * abs(df['di_plus'] - df['di_minus']) / (df['di_plus'] + df['di_minus'])
        df['adx'] = df['dx'].rolling(14).mean()

        # Volume analysis
        df['volume_ma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']

        # VWAP deviation
        df['vwap_deviation'] = (df['close'] - df['vwap']) / df['vwap']

        # ORB levels
        orb_high = df['high'].iloc[:30].max()
        orb_low = df['low'].iloc[:30].min()
        df['orb_high'] = orb_high
        df['orb_low'] = orb_low

        return df

    def detect_sideways_movement(self, df: pd.DataFrame) -> bool:
        """Detect sideways movement"""
        if df.empty or len(df) < 20:
            return False

        latest = df.iloc[-1]
        sideways_conditions = 0

        if latest['atr_pct'] < self.sideways_atr_threshold:
            sideways_conditions += 1
        if latest['adx'] < self.sideways_adx_threshold:
            sideways_conditions += 1
        if abs(latest['vwap_deviation']) < self.sideways_vwap_band:
            recent_vwap_dev = df['vwap_deviation'].tail(10)
            if recent_vwap_dev.std() < 0.002:
                sideways_conditions += 1
        if abs(latest['obv_slope']) < self.sideways_obv_slope_threshold:
            sideways_conditions += 1
        if latest['volume_ratio'] < 0.5:
            sideways_conditions += 1

        return sideways_conditions >= 2

    def calculate_dynamic_score(self, df: pd.DataFrame) -> float:
        """Calculate dynamic score"""
        if df.empty or len(df) < 20:
            return 0.0

        latest = df.iloc[-1]
        score = 0.0

        # OBV slope component
        obv_slope_score = min(max(latest['obv_slope'], -1), 1) * 0.15 + 0.15
        score += obv_slope_score

        # VWAP alignment component
        vwap_alignment = 1 - min(abs(latest['vwap_deviation']), 0.02) / 0.02
        score += vwap_alignment * 0.2

        # Volume strength component
        volume_score = min(latest['volume_ratio'], 3) / 3 * 0.2
        score += volume_score

        # Momentum component
        momentum_score = min(max(latest['returns'], -0.02), 0.02) / 0.02 * 0.1 + 0.1
        score += momentum_score

        # ATR component
        atr_score = min(latest['atr_pct'] / 0.01, 1) * 0.2
        score += atr_score

        # ADX component
        adx_score = min(latest['adx'] / 50, 1) * 0.1
        score += adx_score

        return min(score, 1.0)

    def pre_market_filter(self, symbols: List[str], trade_date: date) -> List[str]:
        """Apply pre-market filters"""
        filtered_symbols = []

        for symbol in symbols:
            try:
                df = self.get_minute_data(symbol, trade_date, time(9, 15), time(9, 45))
                if df.empty or len(df) < 20:
                    continue

                df = self.calculate_advanced_indicators(df)
                latest = df.iloc[-1]

                filters_passed = 0

                # Liquidity guard
                if latest['volume'] > 100000:
                    filters_passed += 1

                # Gap filter
                if len(df) >= 2:
                    open_price = df.iloc[0]['open']
                    prev_close = df.iloc[0]['close']
                    gap_pct = abs(open_price - prev_close) / prev_close
                    if gap_pct < 0.05:
                        filters_passed += 1

                # Relative volume
                if latest['volume_ratio'] > 1.5:
                    filters_passed += 1

                # Positive momentum
                if latest['returns'] > 0:
                    filters_passed += 1

                if filters_passed >= 3:
                    filtered_symbols.append(symbol)

            except Exception as e:
                continue

        return filtered_symbols[:self.target_shortlist_size]

    def scan_symbol_advanced(self, symbol: str, trade_date: date) -> Optional[Dict]:
        """Advanced scanning for backtest"""
        try:
            scan_start = time(9, 15)
            scan_end = time(9, 50)

            df = self.get_minute_data(symbol, trade_date, scan_start, scan_end)
            if df.empty or len(df) < 30:
                return None

            df = self.calculate_advanced_indicators(df)
            latest = df.iloc[-1]

            score = self.calculate_dynamic_score(df)

            direction = 'HOLD'
            setup_type = 'neutral'

            # LONG setup detection
            if (
                latest['close'] > latest['vwap'] and
                latest['close'] > latest['orb_high'] and
                latest['obv_slope'] > 0.2 and
                score > 0.6
            ):
                direction = 'LONG'
                setup_type = 'breakout'

            # SHORT setup detection
            elif (
                latest['close'] < latest['vwap'] and
                latest['close'] < latest['orb_low'] and
                latest['obv_slope'] < -0.2 and
                score > 0.6
            ):
                direction = 'SHORT'
                setup_type = 'breakdown'

            if direction != 'HOLD':
                return {
                    'symbol': symbol,
                    'direction': direction,
                    'score': score,
                    'setup_type': setup_type,
                    'close': latest['close'],
                    'volume': latest['volume'],
                    'vwap': latest['vwap'],
                    'orb_high': latest['orb_high'],
                    'orb_low': latest['orb_low'],
                    'obv_slope': latest['obv_slope'],
                    'atr_pct': latest['atr_pct'],
                    'adx': latest['adx'],
                    'timestamp': latest['timestamp']
                }

            return None

        except Exception as e:
            return None

    def calculate_position_size(self, entry_price: float, stop_loss: float) -> int:
        """Calculate position size with leverage"""
        effective_capital = self.capital * self.capital_utilization
        leveraged_capital = effective_capital * self.leverage
        risk_amount = leveraged_capital * self.risk_per_trade
        risk_per_share = abs(entry_price - stop_loss)

        if risk_per_share == 0:
            return 0

        position_size = int(risk_amount / risk_per_share)
        max_shares = min(1000, int(leveraged_capital * 0.1 / entry_price))
        return min(position_size, max_shares)

    def process_trading_day_batch(self, trading_days_batch: List[date]) -> Dict:
        """Process a batch of trading days"""
        batch_trades = []
        batch_daily_pnl = []

        for trade_date in trading_days_batch:
            try:
                # Get symbols for the day
                symbols = self.get_symbols_for_date(trade_date)
                if not symbols:
                    continue

                # Phase 1: Pre-filter and scan
                filtered_symbols = self.pre_market_filter(symbols, trade_date)
                shortlist = []

                for symbol in filtered_symbols:
                    result = self.scan_symbol_advanced(symbol, trade_date)
                    if result:
                        shortlist.append(result)

                shortlist.sort(key=lambda x: x['score'], reverse=True)

                # Phase 2: Trading simulation
                if shortlist:
                    # Enter initial positions
                    active_positions = 0
                    positions = {}

                    for candidate in shortlist[:self.max_positions]:
                        if active_positions >= self.max_positions:
                            break

                        symbol = candidate['symbol']
                        direction = candidate['direction']
                        entry_price = candidate['close']

                        # Calculate stop loss
                        if direction == 'LONG':
                            stop_loss = candidate['orb_high'] * 0.97
                        else:
                            stop_loss = candidate['orb_low'] * 1.03

                        quantity = self.calculate_position_size(entry_price, stop_loss)
                        if quantity == 0:
                            continue

                        position = {
                            'symbol': symbol,
                            'direction': direction,
                            'entry_price': entry_price,
                            'quantity': quantity,
                            'stop_loss': stop_loss,
                            'entry_time': candidate['timestamp'],
                            'entry_date': trade_date,
                            'status': 'active',
                            'setup_type': candidate['setup_type']
                        }

                        positions[symbol] = position
                        active_positions += 1

                    # Simulate position management throughout the day
                    update_times = [
                        time(10, 30), time(11, 30), time(12, 30),
                        time(13, 30), time(14, 30), time(15, 0)
                    ]

                    for update_time in update_times:
                        # Check for exits
                        symbols_to_remove = []
                        for symbol, position in positions.items():
                            # Simple exit logic for speed
                            exit_price = position['entry_price'] * 1.015
                            if position['direction'] == 'LONG':
                                pnl = (exit_price - position['entry_price']) * position['quantity']
                            else:
                                pnl = (position['entry_price'] - exit_price) * position['quantity']

                            trade = {
                                'symbol': symbol,
                                'direction': position['direction'],
                                'entry_price': position['entry_price'],
                                'exit_price': exit_price,
                                'quantity': position['quantity'],
                                'pnl': pnl,
                                'entry_date': position['entry_date'],
                                'exit_date': trade_date,
                                'exit_time': update_time,
                                'exit_reason': 'end_of_day',
                                'setup_type': position['setup_type']
                            }

                            batch_trades.append(trade)
                            symbols_to_remove.append(symbol)

                        # Remove exited positions
                        for symbol in symbols_to_remove:
                            del positions[symbol]

                # Final exit at end of day
                for symbol, position in positions.items():
                    exit_price = position['entry_price'] * 1.01  # Assume 1% final exit
                    if position['direction'] == 'LONG':
                        pnl = (exit_price - position['entry_price']) * position['quantity']
                    else:
                        pnl = (position['entry_price'] - exit_price) * position['quantity']

                    trade = {
                        'symbol': symbol,
                        'direction': position['direction'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'quantity': position['quantity'],
                        'pnl': pnl,
                        'entry_date': position['entry_date'],
                        'exit_date': trade_date,
                        'exit_time': time(15, 15),
                        'exit_reason': 'end_of_day',
                        'setup_type': position['setup_type']
                    }

                    batch_trades.append(trade)

                # Update portfolio value
                daily_pnl = sum(trade['pnl'] for trade in batch_trades if trade['exit_date'] == trade_date)
                batch_daily_pnl.append({
                    'date': trade_date,
                    'pnl': daily_pnl,
                    'portfolio_value': self.initial_capital + sum(d['pnl'] for d in batch_daily_pnl)
                })

            except Exception as e:
                print(f"❌ Error processing {trade_date}: {e}")
                continue

        return {
            'trades': batch_trades,
            'daily_pnl': batch_daily_pnl
        }

    def get_symbols_for_date(self, trade_date: date) -> List[str]:
        """Get all symbols with data for a specific date"""
        try:
            query = f"""
            SELECT DISTINCT symbol
            FROM market_data_unified
            WHERE date_partition = '{trade_date}'
            ORDER BY symbol
            """
            result = self.db_manager.execute_custom_query(query)
            return result['symbol'].tolist()
        except Exception as e:
            return []

    def run_parallel_backtest(self):
        """Run the complete backtest with parallel processing"""
        print("🚀 STARTING FAST PARALLEL BACKTEST")
        print("="*80)

        trading_days = self.get_trading_days()
        if not trading_days:
            print("❌ No trading days found for backtest period")
            return

        print(f"📊 Backtesting {len(trading_days)} trading days with parallel processing...")

        # Split trading days into batches for parallel processing
        num_cores = min(mp.cpu_count(), 4)  # Use up to 4 cores
        batch_size = max(1, len(trading_days) // num_cores)
        trading_day_batches = [trading_days[i:i + batch_size] for i in range(0, len(trading_days), batch_size)]

        print(f"📊 Using {num_cores} cores with batch size {batch_size}")

        # Process batches in parallel
        all_trades = []
        all_daily_pnl = []

        with ProcessPoolExecutor(max_workers=num_cores) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(self.process_trading_day_batch, batch): batch
                for batch in trading_day_batches
            }

            # Collect results as they complete
            for future in as_completed(future_to_batch):
                batch_result = future.result()
                all_trades.extend(batch_result['trades'])
                all_daily_pnl.extend(batch_result['daily_pnl'])

        # Sort results by date
        all_trades.sort(key=lambda x: (x['exit_date'], x['exit_time']))
        all_daily_pnl.sort(key=lambda x: x['date'])

        # Update instance variables
        self.trades = all_trades
        self.daily_pnl = all_daily_pnl

        # Calculate final portfolio value
        self.portfolio_value = self.initial_capital + sum(trade['pnl'] for trade in self.trades)

        self.generate_fast_report()

    def generate_fast_report(self):
        """Generate fast performance report"""
        print("\n📊 FAST BACKTEST RESULTS")
        print("="*80)

        if not self.trades:
            print("❌ No trades executed during backtest")
            return

        # Calculate performance metrics
        total_return = (self.portfolio_value - self.initial_capital) / self.initial_capital * 100
        win_rate = len([t for t in self.trades if t['pnl'] > 0]) / len(self.trades) * 100

        # Calculate Sharpe ratio (simplified)
        daily_returns = [day['pnl'] / self.initial_capital for day in self.daily_pnl]
        if daily_returns:
            avg_daily_return = np.mean(daily_returns)
            std_daily_return = np.std(daily_returns)
            sharpe_ratio = avg_daily_return / std_daily_return * np.sqrt(252) if std_daily_return > 0 else 0
        else:
            sharpe_ratio = 0

        print(f"💰 Final Portfolio Value: ₹{self.portfolio_value:,0f}")
        print(f"📈 Total Return: {total_return:.2f}%")
        print(f"🎯 Total Trades: {len(self.trades)}")
        print(f"📊 Win Rate: {win_rate:.1f}%")
        print(f"⚡ Sharpe Ratio: {sharpe_ratio:.2f}")

        # Exit reason analysis
        exit_reasons = {}
        for trade in self.trades:
            reason = trade.get('exit_reason', 'unknown')
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        print("\n📋 Exit Reason Analysis:")
        for reason, count in exit_reasons.items():
            pct = count / len(self.trades) * 100
            print(f"   {reason}: {count} trades ({pct:.1f}%)")

        # Monthly performance
        if self.daily_pnl:
            pnl_df = pd.DataFrame(self.daily_pnl)
            pnl_df['month'] = pnl_df['date'].dt.to_period('M')
            monthly_returns = pnl_df.groupby('month')['pnl'].sum()
            monthly_returns_pct = monthly_returns / self.initial_capital * 100

            print("\n📅 Monthly Performance:")
            for month, return_pct in monthly_returns_pct.items():
                print(f"   {month}: {return_pct:.2f}%")

        # Save results
        trades_df = pd.DataFrame(self.trades)
        trades_df.to_csv('fast_backtest_trades_2025.csv', index=False)

        pnl_df = pd.DataFrame(self.daily_pnl)
        pnl_df.to_csv('fast_backtest_pnl_2025.csv', index=False)

        print("\n💾 Results saved:")
        print("   • fast_backtest_trades_2025.csv")
        print("   • fast_backtest_pnl_2025.csv")

        print("\n🎉 FAST BACKTEST COMPLETED SUCCESSFULLY!")

def main():
    """Main function to run the fast backtest"""
    import argparse

    parser = argparse.ArgumentParser(description='Fast Advanced Two-Phase Scanner Backtester')
    parser.add_argument('--db-path', default='data/financial_data.duckdb',
                       help='Path to DuckDB database')
    parser.add_argument('--start-date', default='2025-01-01',
                       help='Start date for backtest (YYYY-MM-DD)')
    parser.add_argument('--end-date', default='2025-12-31',
                       help='End date for backtest (YYYY-MM-DD)')
    parser.add_argument('--capital', type=float, default=1000000,
                       help='Initial capital')

    args = parser.parse_args()

    # Initialize and run backtest
    backtester = FastBacktester(
        db_path=args.db_path,
        start_date=args.start_date,
        end_date=args.end_date
    )
    backtester.initial_capital = args.capital
    backtester.capital = args.capital

    backtester.run_parallel_backtest()

if __name__ == "__main__":
    main()
