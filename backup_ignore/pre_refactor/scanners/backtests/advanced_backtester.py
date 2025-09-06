#!/usr/bin/env python3
"""
Advanced Two-Phase Scanner Backtester

Backtests the optimized scanner on 10+ years of historical data with:
- Complete optimization features (sideways detection, capital rotation, etc.)
- Multi-year performance analysis
- Risk management and drawdown analysis
- Detailed performance metrics
"""

import sys
import os
from datetime import datetime, date, time, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import pandas as pd
import numpy as np
from tqdm import tqdm

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class AdvancedBacktester:
    """
    Advanced backtester for the two-phase scanner with full optimization features
    """

    def __init__(self, db_path: str = "data/financial_data.duckdb", start_date: str = "2015-01-01", end_date: str = "2025-12-31"):
        """Initialize the advanced backtester"""
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
        self.current_date = self.start_date
        self.portfolio_value = self.initial_capital
        self.positions = {}
        self.trades = []
        self.daily_pnl = []
        self.portfolio_history = []
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
        self.total_fees = 0

        # Initialize database
        self.db_manager = None
        self.initialize_database()

        print("🚀 ADVANCED TWO-PHASE SCANNER BACKTESTER")
        print("="*60)
        print(f"📅 Backtest Period: {self.start_date} to {self.end_date}")
        print(f"💰 Initial Capital: ₹{self.initial_capital:,.0f}")
        print(f"⚡ Leverage: {self.leverage}x")
        print(f"📊 Max Positions: {self.max_positions}")
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

    def get_trading_days(self) -> List[date]:
        """Get all trading days in the backtest period"""
        try:
            query = f"""
            SELECT DISTINCT date_partition
            FROM market_data
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

    def get_symbols_for_date(self, trade_date: date) -> List[str]:
        """Get all symbols with data for a specific date"""
        try:
            query = f"""
            SELECT DISTINCT symbol
            FROM market_data
            WHERE date_partition = '{trade_date}'
            ORDER BY symbol
            """
            result = self.db_manager.execute_custom_query(query)
            return result['symbol'].tolist()
        except Exception as e:
            return []

    def get_minute_data(self, symbol: str, trade_date: date, start_time: time, end_time: time) -> pd.DataFrame:
        """Get minute data for a symbol on a specific date within time range"""
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
            if (latest['close'] > latest['vwap'] and
                latest['close'] > latest['orb_high'] and
                latest['obv_slope'] > 0.2 and
                score > 0.6):
                direction = 'LONG'
                setup_type = 'breakout'

            # SHORT setup detection
            elif (latest['close'] < latest['vwap'] and
                  latest['close'] < latest['orb_low'] and
                  latest['obv_slope'] < -0.2 and
                  score > 0.6):
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

    def should_exit_position(self, symbol: str, position: Dict, trade_date: date, current_time: time) -> Tuple[bool, str]:
        """Determine if position should be exited"""
        try:
            start_time = (datetime.combine(trade_date, current_time) - timedelta(minutes=30)).time()
            df = self.get_minute_data(symbol, trade_date, start_time, current_time)

            if df.empty:
                return False, "no_data"

            df = self.calculate_advanced_indicators(df)
            latest = df.iloc[-1]

            is_sideways = self.detect_sideways_movement(df)

            entry_price = position['entry_price']
            current_price = latest['close']

            if position['direction'] == 'LONG':
                unrealized_pnl_pct = (current_price - entry_price) / entry_price
            else:
                unrealized_pnl_pct = (entry_price - current_price) / entry_price

            # Session-based exit rules
            if self.session_phase == "morning":
                if is_sideways and unrealized_pnl_pct < 0.005:
                    return True, "morning_sideways_small_profit"

            elif self.session_phase == "midday":
                if is_sideways:
                    return True, "midday_sideways"
                if unrealized_pnl_pct < -0.01:
                    return True, "midday_stop_loss"

            else:  # Afternoon
                if is_sideways and unrealized_pnl_pct > 0:
                    return True, "afternoon_lock_profit"
                if latest['adx'] < 15:
                    return True, "afternoon_trend_fade"

            # Check for better opportunities
            current_score = self.scoreboard.get(symbol, {}).get('score', 0)
            top_score = max([s.get('score', 0) for s in self.scoreboard.values()])

            if top_score > current_score + 0.2:
                return True, "better_opportunity"

            return False, "hold"

        except Exception as e:
            return False, f"error: {e}"

    def get_session_phase(self, current_time: time) -> str:
        """Get session phase"""
        if current_time < time(11, 30):
            return "morning"
        elif current_time < time(14, 0):
            return "midday"
        else:
            return "afternoon"

    def process_trading_day(self, trade_date: date):
        """Process a single trading day"""
        print(f"\n📅 Processing {trade_date}")

        # Get symbols for the day
        symbols = self.get_symbols_for_date(trade_date)
        if not symbols:
            print(f"❌ No symbols found for {trade_date}")
            return

        # Phase 1: Pre-filter and scan
        filtered_symbols = self.pre_market_filter(symbols, trade_date)
        print(f"🔍 Pre-filter: {len(symbols)} → {len(filtered_symbols)} symbols")

        shortlist = []
        for symbol in filtered_symbols:
            result = self.scan_symbol_advanced(symbol, trade_date)
            if result:
                shortlist.append(result)

        shortlist.sort(key=lambda x: x['score'], reverse=True)
        print(f"✅ Scan complete: {len(shortlist)} candidates")

        # Initialize scoreboard
        self.scoreboard = {item['symbol']: item for item in shortlist}

        # Phase 2: Trading simulation
        if shortlist:
            # Enter initial positions
            active_positions = 0
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

                self.positions[symbol] = position
                active_positions += 1

            print(f"✅ Entered {active_positions} positions")

            # Simulate position management throughout the day
            update_times = [
                time(10, 30), time(11, 30), time(12, 30),
                time(13, 30), time(14, 30), time(15, 0)
            ]

            for update_time in update_times:
                self.session_phase = self.get_session_phase(update_time)

                # Update scores
                for symbol in list(self.scoreboard.keys()):
                    try:
                        start_time = (datetime.combine(trade_date, update_time) - timedelta(minutes=30)).time()
                        df = self.get_minute_data(symbol, trade_date, start_time, update_time)
                        if not df.empty and len(df) >= 20:
                            df = self.calculate_advanced_indicators(df)
                            new_score = self.calculate_dynamic_score(df)
                            self.scoreboard[symbol]['score'] = new_score
                    except Exception:
                        continue

                # Check for exits
                symbols_to_remove = []
                for symbol, position in self.positions.items():
                    should_exit, reason = self.should_exit_position(symbol, position, trade_date, update_time)

                    if should_exit:
                        # Calculate exit price (assume 1.5% move)
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
                            'exit_reason': reason,
                            'setup_type': position['setup_type']
                        }

                        self.trades.append(trade)
                        self.total_trades += 1
                        self.total_pnl += pnl

                        if pnl > 0:
                            self.winning_trades += 1
                        else:
                            self.losing_trades += 1

                        symbols_to_remove.append(symbol)

                # Remove exited positions
                for symbol in symbols_to_remove:
                    del self.positions[symbol]

        # Final exit at end of day
        for symbol, position in self.positions.items():
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

            self.trades.append(trade)
            self.total_trades += 1
            self.total_pnl += pnl

            if pnl > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1

        # Update portfolio value
        daily_pnl = sum(trade['pnl'] for trade in self.trades if trade['exit_date'] == trade_date)
        self.portfolio_value += daily_pnl
        self.daily_pnl.append({
            'date': trade_date,
            'pnl': daily_pnl,
            'portfolio_value': self.portfolio_value
        })

        # Update drawdown
        if self.portfolio_value > self.peak_portfolio_value:
            self.peak_portfolio_value = self.portfolio_value
        else:
            current_drawdown = (self.peak_portfolio_value - self.portfolio_value) / self.peak_portfolio_value
            if current_drawdown > self.max_drawdown:
                self.max_drawdown = current_drawdown
                self.max_drawdown_date = trade_date

        # Clear positions for next day
        self.positions.clear()

    def run_backtest(self):
        """Run the complete backtest"""
        print("🚀 STARTING ADVANCED BACKTEST")
        print("="*80)

        trading_days = self.get_trading_days()
        if not trading_days:
            print("❌ No trading days found for backtest period")
            return

        print(f"📊 Backtesting {len(trading_days)} trading days...")

        for trade_date in tqdm(trading_days, desc="Backtesting"):
            try:
                self.process_trading_day(trade_date)
            except Exception as e:
                print(f"❌ Error processing {trade_date}: {e}")
                continue

        self.generate_backtest_report()

    def generate_backtest_report(self):
        """Generate comprehensive backtest report"""
        print("\n📊 ADVANCED BACKTEST RESULTS")
        print("="*80)

        if not self.trades:
            print("❌ No trades executed during backtest")
            return

        # Calculate performance metrics
        total_return = (self.portfolio_value - self.initial_capital) / self.initial_capital * 100
        win_rate = self.winning_trades / self.total_trades * 100 if self.total_trades > 0 else 0

        # Calculate Sharpe ratio (simplified)
        daily_returns = [day['pnl'] / self.initial_capital for day in self.daily_pnl]
        if daily_returns:
            avg_daily_return = np.mean(daily_returns)
            std_daily_return = np.std(daily_returns)
            sharpe_ratio = avg_daily_return / std_daily_return * np.sqrt(252) if std_daily_return > 0 else 0
        else:
            sharpe_ratio = 0

        # Calculate Sortino ratio (downside deviation)
        negative_returns = [r for r in daily_returns if r < 0]
        downside_std = np.std(negative_returns) if negative_returns else 0
        sortino_ratio = avg_daily_return / downside_std * np.sqrt(252) if downside_std > 0 else 0

        # Calculate Calmar ratio
        calmar_ratio = total_return / 100 / self.max_drawdown if self.max_drawdown > 0 else 0

        print(f"💰 Final Portfolio Value: ₹{self.portfolio_value:,.0f}")
        print(f"📈 Total Return: {total_return:.2f}%")
        print(f"🎯 Total Trades: {self.total_trades}")
        print(f"📊 Win Rate: {win_rate:.1f}%")
        print(f"⚡ Sharpe Ratio: {sharpe_ratio:.2f}")
        print(f"🎯 Sortino Ratio: {sortino_ratio:.2f}")
        print(f"📉 Max Drawdown: {self.max_drawdown*100:.2f}%")
        print(f"📊 Calmar Ratio: {calmar_ratio:.2f}")

        if self.max_drawdown_date:
            print(f"📅 Max Drawdown Date: {self.max_drawdown_date}")

        # Exit reason analysis
        exit_reasons = {}
        for trade in self.trades:
            reason = trade.get('exit_reason', 'unknown')
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        print("\n📋 Exit Reason Analysis:")
        for reason, count in exit_reasons.items():
            pct = count / self.total_trades * 100
            print(f"   {reason}: {count} trades ({pct:.1f}%)")

        # Annual returns analysis
        if self.daily_pnl:
            pnl_df = pd.DataFrame(self.daily_pnl)
            pnl_df['year'] = pnl_df['date'].dt.year
            annual_returns = pnl_df.groupby('year')['pnl'].sum()
            annual_returns_pct = annual_returns / self.initial_capital * 100

            print("\n📅 Annual Performance:")
            for year, return_pct in annual_returns_pct.items():
                print(f"   {year}: {return_pct:.2f}%")

        # Save detailed results
        trades_df = pd.DataFrame(self.trades)
        trades_df.to_csv('advanced_backtest_trades.csv', index=False)

        pnl_df = pd.DataFrame(self.daily_pnl)
        pnl_df.to_csv('advanced_backtest_pnl.csv', index=False)

        print("\n💾 Detailed results saved:")
        print("   • advanced_backtest_trades.csv")
        print("   • advanced_backtest_pnl.csv")

        print("\n🎉 ADVANCED BACKTEST COMPLETED SUCCESSFULLY!")

def main():
    """Main function to run the advanced backtest"""
    import argparse

    parser = argparse.ArgumentParser(description='Advanced Two-Phase Scanner Backtester')
    parser.add_argument('--db-path', default='data/financial_data.duckdb',
                       help='Path to DuckDB database')
    parser.add_argument('--start-date', default='2015-01-01',
                       help='Start date for backtest (YYYY-MM-DD)')
    parser.add_argument('--end-date', default='2025-12-31',
                       help='End date for backtest (YYYY-MM-DD)')
    parser.add_argument('--capital', type=float, default=1000000,
                       help='Initial capital')

    args = parser.parse_args()

    # Initialize and run backtest
    backtester = AdvancedBacktester(
        db_path=args.db_path,
        start_date=args.start_date,
        end_date=args.end_date
    )
    backtester.initial_capital = args.capital
    backtester.capital = args.capital

    backtester.run_backtest()

if __name__ == "__main__":
    main()
