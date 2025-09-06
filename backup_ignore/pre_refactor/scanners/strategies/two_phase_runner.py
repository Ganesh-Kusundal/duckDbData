#!/usr/bin/env python3
"""
Two-Phase Intraday Trading Runner

Phase 1: One-time scan at 09:50 IST → Generate shortlist of high-probability candidates
Phase 2: Rolling intraday mode → Trade only the shortlisted symbols from 09:50 → 15:15

Strategy: OBV + ORB + VWAP + Relative Strength + Volume Breakout
"""

import sys
import os
from datetime import datetime, date, time, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class TwoPhaseIntradayRunner:
    """
    Two-phase intraday trading system:
    Phase 1: 09:50 scan → shortlist candidates
    Phase 2: 09:50-15:15 → trade shortlisted symbols
    """

    def __init__(self, db_path: str = "data/financial_data.duckdb"):
        """Initialize the two-phase runner"""
        self.db_path = db_path
        self.today = date.today()
        self.scan_time = time(9, 50)  # 09:50 IST
        self.end_time = time(15, 15)  # 15:15 IST

        # Trading parameters
        self.min_volume = 100000  # Minimum volume threshold
        self.max_positions = 5  # Maximum concurrent positions
        self.risk_per_trade = 0.02  # 2% risk per trade
        self.capital = 100000  # Starting capital
        self.leverage = 5  # 5x leverage multiplier
        self.capital_utilization = 0.95  # Use 95% of capital

        # Strategy parameters
        self.orb_lookback = 30  # ORB calculation period (minutes)
        self.vwap_period = 30  # VWAP calculation period
        self.obv_threshold = 1.5  # OBV breakout threshold
        self.volume_threshold = 1.2  # Volume breakout threshold

        # Initialize components
        self.db_manager = None
        self.positions = {}
        self.trades = []
        self.shortlist = []

        print("🚀 Two-Phase Intraday Runner Initialized")
        print(f"📅 Trading Day: {self.today}")
        print(f"🕘 Scan Time: {self.scan_time}")
        print(f"🏁 End Time: {self.end_time}")

    def initialize_database(self):
        """Initialize database connection"""
        try:
            from core.duckdb_infra import DuckDBManager
            self.db_manager = DuckDBManager()
            print("✅ Database connection established")
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            raise

    def get_available_symbols(self) -> List[str]:
        """Get all symbols with data for today"""
        try:
            query = f"""
            SELECT DISTINCT symbol
            FROM market_data
            WHERE date_partition = '{self.today}'
            ORDER BY symbol
            """
            result = self.db_manager.execute_custom_query(query)
            symbols = result['symbol'].tolist()
            print(f"📊 Found {len(symbols)} symbols with data for {self.today}")
            return symbols
        except Exception as e:
            print(f"❌ Error getting symbols: {e}")
            return []

    def get_minute_data(self, symbol: str, start_time: time, end_time: time) -> pd.DataFrame:
        """Get minute data for a symbol within time range"""
        try:
            start_datetime = datetime.combine(self.today, start_time)
            end_datetime = datetime.combine(self.today, end_time)

            query = f"""
            SELECT timestamp, open, high, low, close, volume
            FROM market_data
            WHERE symbol = '{symbol}'
            AND date_partition = '{self.today}'
            AND timestamp >= '{start_datetime}'
            AND timestamp <= '{end_datetime}'
            ORDER BY timestamp
            """

            result = self.db_manager.execute_custom_query(query)
            if result.empty:
                return pd.DataFrame()

            # Ensure timestamp is datetime
            result['timestamp'] = pd.to_datetime(result['timestamp'])
            return result

        except Exception as e:
            print(f"❌ Error getting data for {symbol}: {e}")
            return pd.DataFrame()

    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for the strategy"""
        if df.empty or len(df) < self.orb_lookback:
            return df

        # VWAP calculation
        df['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()

        # OBV calculation
        df['obv'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()

        # ORB (Opening Range Breakout)
        orb_high = df['high'].iloc[:self.orb_lookback].max()
        orb_low = df['low'].iloc[:self.orb_lookback].min()
        df['orb_high'] = orb_high
        df['orb_low'] = orb_low

        # Volume moving average
        df['volume_ma'] = df['volume'].rolling(window=20).mean()

        # Relative Strength (vs market)
        # Using simple price momentum as proxy
        df['returns'] = df['close'].pct_change()
        df['cum_returns'] = (1 + df['returns']).cumprod()

        return df

    def scan_symbol(self, symbol: str) -> Optional[Dict]:
        """Scan a single symbol for both long and short trading opportunities"""
        try:
            # Get data from 09:15 to 09:50
            scan_start = time(9, 15)
            scan_end = time(9, 50)

            df = self.get_minute_data(symbol, scan_start, scan_end)
            if df.empty or len(df) < self.orb_lookback:
                return None

            # Calculate indicators
            df = self.calculate_technical_indicators(df)

            # Get latest data point
            latest = df.iloc[-1]

            # Check for LONG opportunities
            long_score = 0
            long_reasons = []

            # LONG criteria
            obv_ma = df['obv'].rolling(window=20).mean().iloc[-1]

            # 1. OBV Breakout (bullish)
            if latest['obv'] > obv_ma * self.obv_threshold:
                long_score += 2
                long_reasons.append("OBV Breakout")

            # 2. Volume Breakout
            if latest['volume'] > latest['volume_ma'] * self.volume_threshold:
                long_score += 1
                long_reasons.append("Volume Breakout")

            # 3. VWAP Alignment (above VWAP)
            if latest['close'] > latest['vwap']:
                long_score += 1
                long_reasons.append("Above VWAP")

            # 4. ORB Breakout (above opening range high)
            if latest['close'] > latest['orb_high']:
                long_score += 2
                long_reasons.append("ORB Breakout")

            # 5. Minimum volume check
            if latest['volume'] > self.min_volume:
                long_score += 1
                long_reasons.append("Volume Threshold")

            # 6. Positive momentum
            if latest['returns'] > 0:
                long_score += 1
                long_reasons.append("Positive Momentum")

            # Check for SHORT opportunities
            short_score = 0
            short_reasons = []

            # SHORT criteria
            # 1. OBV Breakdown (bearish)
            if latest['obv'] < obv_ma / self.obv_threshold:
                short_score += 2
                short_reasons.append("OBV Breakdown")

            # 2. Volume Breakout (can be on both sides)
            if latest['volume'] > latest['volume_ma'] * self.volume_threshold:
                short_score += 1
                short_reasons.append("Volume Breakout")

            # 3. VWAP Alignment (below VWAP)
            if latest['close'] < latest['vwap']:
                short_score += 1
                short_reasons.append("Below VWAP")

            # 4. ORB Breakdown (below opening range low)
            if latest['close'] < latest['orb_low']:
                short_score += 2
                short_reasons.append("ORB Breakdown")

            # 5. Minimum volume check
            if latest['volume'] > self.min_volume:
                short_score += 1
                short_reasons.append("Volume Threshold")

            # 6. Negative momentum
            if latest['returns'] < 0:
                short_score += 1
                short_reasons.append("Negative Momentum")

            # Determine the better opportunity
            if long_score >= 4 and long_score > short_score:
                # LONG opportunity
                return {
                    'symbol': symbol,
                    'direction': 'LONG',
                    'score': long_score,
                    'reasons': long_reasons,
                    'close': latest['close'],
                    'volume': latest['volume'],
                    'vwap': latest['vwap'],
                    'orb_high': latest['orb_high'],
                    'orb_low': latest['orb_low'],
                    'obv': latest['obv'],
                    'timestamp': latest['timestamp']
                }
            elif short_score >= 4 and short_score > long_score:
                # SHORT opportunity
                return {
                    'symbol': symbol,
                    'direction': 'SHORT',
                    'score': short_score,
                    'reasons': short_reasons,
                    'close': latest['close'],
                    'volume': latest['volume'],
                    'vwap': latest['vwap'],
                    'orb_high': latest['orb_high'],
                    'orb_low': latest['orb_low'],
                    'obv': latest['obv'],
                    'timestamp': latest['timestamp']
                }

            return None

        except Exception as e:
            print(f"❌ Error scanning {symbol}: {e}")
            return None

    def phase1_scan_at_0950(self) -> List[Dict]:
        """Phase 1: Scan all symbols at 09:50 and generate shortlist"""
        print("\n🔍 PHASE 1: SCANNING AT 09:50 IST")
        print("="*60)

        symbols = self.get_available_symbols()
        if not symbols:
            print("❌ No symbols found for today")
            return []

        print(f"📊 Scanning {len(symbols)} symbols...")

        shortlist = []
        for i, symbol in enumerate(symbols, 1):
            if i % 50 == 0:
                print(f"🔄 Scanned {i}/{len(symbols)} symbols...")

            result = self.scan_symbol(symbol)
            if result:
                shortlist.append(result)

        # Sort by score (highest first)
        shortlist.sort(key=lambda x: x['score'], reverse=True)

        print("\n✅ SCAN COMPLETE")
        print(f"🎯 Found {len(shortlist)} high-probability candidates")

        # Display top candidates
        print("\n🏆 TOP CANDIDATES:")
        print("-" * 90)
        print(f"{'Rank':<8} {'Symbol':<12} {'Dir':<6} {'Score':<8} {'Close':<10} {'Volume':<12} {'Reasons'}")
        print("-" * 90)

        for i, candidate in enumerate(shortlist[:10], 1):
            direction = candidate.get('direction', 'LONG')
            reasons_str = ", ".join(candidate['reasons'][:3])  # Show first 3 reasons
            print(f"{i:<8} {candidate['symbol']:<12} {direction:<6} {candidate['score']:<8} ₹{candidate['close']:<10.2f} {candidate['volume']:<12,.0f} {reasons_str}")

        # Save shortlist to CSV
        if shortlist:
            shortlist_df = pd.DataFrame(shortlist)
            filename = f"scan_{self.today.strftime('%Y%m%d')}_0950.csv"
            shortlist_df.to_csv(filename, index=False)
            print(f"\n💾 Shortlist saved to: {filename}")

        return shortlist

    def calculate_position_size(self, entry_price: float, stop_loss: float) -> int:
        """Calculate position size based on risk management with leverage"""
        # Use 95% of capital
        effective_capital = self.capital * self.capital_utilization

        # Apply 5x leverage
        leveraged_capital = effective_capital * self.leverage

        # Calculate risk amount (2% of leveraged capital)
        risk_amount = leveraged_capital * self.risk_per_trade

        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share == 0:
            return 0

        # Calculate position size
        position_size = int(risk_amount / risk_per_share)

        # Cap at reasonable limits (considering leverage)
        max_shares = min(1000, int(leveraged_capital * 0.1 / entry_price))  # Max 10% of leveraged capital per position
        return min(position_size, max_shares)

    def phase2_trade_shortlist(self, shortlist: List[Dict]):
        """Phase 2: Trade the shortlisted symbols from 09:50 to 15:15"""
        print("\n🚀 PHASE 2: TRADING SHORTLIST (09:50 - 15:15)")
        print("="*60)

        if not shortlist:
            print("❌ No candidates to trade")
            return

        effective_capital = self.capital * self.capital_utilization
        leveraged_capital = effective_capital * self.leverage

        print(f"🎯 Trading {len(shortlist)} candidates")
        print(f"💰 Starting capital: ₹{self.capital:,.0f}")
        print(f"📊 Capital utilization: {self.capital_utilization*100:.0f}%")
        print(f"⚡ Leverage: {self.leverage}x")
        print(f"💪 Effective capital: ₹{leveraged_capital:,.0f}")
        print(f"📊 Max positions: {self.max_positions}")

        # Trading loop (simplified - in real implementation would be event-driven)
        active_positions = 0

        for candidate in shortlist:
            if active_positions >= self.max_positions:
                print(f"⚠️  Maximum positions ({self.max_positions}) reached")
                break

            symbol = candidate['symbol']
            direction = candidate.get('direction', 'LONG')
            entry_price = candidate['close']

            # Calculate stop loss based on direction
            if direction == 'LONG':
                stop_loss = candidate['orb_high'] * 0.98  # 2% below ORB high for longs
            else:  # SHORT
                stop_loss = candidate['orb_low'] * 1.02   # 2% above ORB low for shorts

            # Calculate position size
            quantity = self.calculate_position_size(entry_price, stop_loss)
            if quantity == 0:
                continue

            # Enter position
            position_value = entry_price * quantity
            if position_value > self.capital * 0.1:  # Max 10% of capital per position
                quantity = int((self.capital * 0.1) / entry_price)

            position = {
                'symbol': symbol,
                'direction': direction,
                'entry_price': entry_price,
                'quantity': quantity,
                'stop_loss': stop_loss,
                'entry_time': candidate['timestamp'],
                'status': 'active'
            }

            self.positions[symbol] = position
            active_positions += 1

            print(f"✅ ENTERED {direction}: {symbol} | Qty: {quantity} | Entry: ₹{entry_price:.2f} | SL: ₹{stop_loss:.2f}")

        print(f"\n📊 Active Positions: {active_positions}")

        # Simulate position management (in real implementation, this would be continuous)
        self._simulate_position_management()

    def _simulate_position_management(self):
        """Simulate position management until 15:15"""
        print("\n🔄 POSITION MANAGEMENT SIMULATION")
        print("-" * 60)

        # In a real implementation, this would:
        # 1. Monitor live prices
        # 2. Update stop losses
        # 3. Exit positions based on targets/stops
        # 4. Handle new entries if conditions improve

        for symbol, position in self.positions.items():
            direction = position.get('direction', 'LONG')

            # Simulate exit based on direction
            if direction == 'LONG':
                exit_price = position['entry_price'] * 1.02  # Assume 2% profit for longs
                pnl = (exit_price - position['entry_price']) * position['quantity']
            else:  # SHORT
                exit_price = position['entry_price'] * 0.98  # Assume 2% profit for shorts (price goes down)
                pnl = (position['entry_price'] - exit_price) * position['quantity']  # Profit when price decreases

            trade = {
                'symbol': symbol,
                'direction': direction,
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'quantity': position['quantity'],
                'pnl': pnl,
                'entry_time': position['entry_time'],
                'exit_time': datetime.combine(self.today, self.end_time)
            }

            self.trades.append(trade)

            pnl_pct = pnl / (position['entry_price'] * position['quantity']) * 100
            print(f"📈 CLOSED {direction}: {symbol} | P&L: ₹{pnl:,.0f} ({pnl_pct:.1f}%)")

    def generate_report(self):
        """Generate end-of-day report"""
        print("\n📊 END OF DAY REPORT")
        print("="*60)

        if not self.trades:
            print("❌ No trades executed today")
            return

        # Calculate summary statistics
        total_pnl = sum(trade['pnl'] for trade in self.trades)
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] < 0]

        print(f"💰 Total P&L: ₹{total_pnl:,.0f}")
        print(f"📈 Win Rate: {len(winning_trades)}/{len(self.trades)} ({len(winning_trades)/len(self.trades)*100:.1f}%)")
        print(f"🎯 Total Trades: {len(self.trades)}")
        print(f"📊 Average P&L per Trade: ₹{total_pnl/len(self.trades):,.0f}")

        # Save trades to CSV
        trades_df = pd.DataFrame(self.trades)
        filename = f"trades_{self.today.strftime('%Y%m%d')}.csv"
        trades_df.to_csv(filename, index=False)
        print(f"\n💾 Trades saved to: {filename}")

    def run_daily_flow(self):
        """Execute the complete daily flow"""
        print("🚀 STARTING DAILY TRADING FLOW")
        print("="*80)

        try:
            # Initialize
            self.initialize_database()

            # Phase 1: Scan at 09:50
            shortlist = self.phase1_scan_at_0950()

            # Phase 2: Trade shortlist
            if shortlist:
                self.phase2_trade_shortlist(shortlist)

            # Generate report
            self.generate_report()

            print("\n🎉 DAILY FLOW COMPLETED SUCCESSFULLY!")

        except Exception as e:
            print(f"❌ Error in daily flow: {e}")
            import traceback
            traceback.print_exc()

        finally:
            if self.db_manager:
                self.db_manager.close()


def main():
    """Main function to run the two-phase trading system"""
    import argparse

    parser = argparse.ArgumentParser(description='Two-Phase Intraday Trading Runner')
    parser.add_argument('--db-path', default='data/financial_data.duckdb',
                       help='Path to DuckDB database')
    parser.add_argument('--capital', type=float, default=100000,
                       help='Starting capital')
    parser.add_argument('--max-positions', type=int, default=5,
                       help='Maximum concurrent positions')

    args = parser.parse_args()

    # Initialize and run
    runner = TwoPhaseIntradayRunner(db_path=args.db_path)
    runner.capital = args.capital
    runner.max_positions = args.max_positions

    runner.run_daily_flow()


if __name__ == "__main__":
    main()
