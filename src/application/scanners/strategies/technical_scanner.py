"""
Technical Scanner for intraday stock selection.
Identifies stocks based on technical indicators and patterns.
"""

from typing import Dict, Any, List
from datetime import datetime, date, time, timedelta
import pandas as pd
import numpy as np

from ..base_scanner import BaseScanner


class TechnicalScanner(BaseScanner):
    """Scanner that identifies stocks based on technical analysis."""

    @property
    def scanner_name(self) -> str:
        return "technical"

    def _get_default_config(self) -> Dict[str, Any]:
        return {
            'required_indicators': ['rsi', 'macd', 'bollinger_bands'],
            'rsi_overbought': 70,         # RSI overbought level
            'rsi_oversold': 30,           # RSI oversold level
            'macd_threshold': 0.1,        # MACD signal strength
            'bb_deviation': 1.5,          # Bollinger Band deviation
            'min_price': 50,              # Minimum stock price
            'max_price': 2000,            # Maximum stock price
            'max_results': 50
        }

    def scan(self, scan_date: date, cutoff_time: time = time(9, 50)) -> pd.DataFrame:
        """
        Scan for stocks with favorable technical patterns.
        
        Args:
            scan_date: Date to scan
            cutoff_time: Time cutoff for scanning
        
        Returns:
            DataFrame with technical scan results
        """
        print(f"📊 Scanning for favorable technical patterns by {cutoff_time}")

        # Get available symbols for technical analysis
        all_symbols = self.get_available_symbols()
        print(f"📈 Analyzing {len(all_symbols)} symbols for technical indicators...")

        # Get pattern scores for all symbols (optional analytics integration)
        pattern_scores = pd.DataFrame()
        if hasattr(self, 'pattern_analyzer') and self.pattern_analyzer:
            print("🔍 Integrating pattern analysis for enhanced technical scoring...")
            try:
                pattern_scores = self.get_pattern_scores(all_symbols)
                print(f"📈 Found pattern scores for {len(pattern_scores)} symbols")
            except Exception as e:
                print(f"⚠️  Pattern analysis failed, proceeding with basic scoring: {e}")

        # Simplified technical analysis query
        technical_query = """
        WITH symbol_stats AS (
            -- Get basic statistics for each symbol
            SELECT
                symbol,
                COUNT(*) as total_records,
                AVG(close) as avg_price,
                STDDEV(close) as price_volatility,
                MIN(close) as min_price,
                MAX(close) as max_price
            FROM market_data
            WHERE date_partition = ?
                AND strftime('%H:%M', timestamp) <= ?
                AND strftime('%H:%M', timestamp) >= '09:15'
            GROUP BY symbol
            HAVING COUNT(*) >= 10  -- At least 10 data points
        ),

        latest_data AS (
            -- Get latest price data
            SELECT
                m.symbol,
                LAST(m.close ORDER BY m.timestamp) as current_price,
                FIRST(m.close ORDER BY m.timestamp) as open_price,
                MAX(m.high) as day_high,
                MIN(m.low) as day_low,
                SUM(m.volume) as total_volume,
                AVG(m.close) as avg_close,
                STDDEV(m.close) as std_close
            FROM market_data m
            JOIN symbol_stats s ON m.symbol = s.symbol
            WHERE m.date_partition = ?
                AND strftime('%H:%M', m.timestamp) <= ?
                AND strftime('%H:%M', m.timestamp) >= '09:15'
            GROUP BY m.symbol
        )

        SELECT
            symbol,
            current_price,
            open_price,
            day_high,
            day_low,
            total_volume,
            ROUND(((current_price - open_price) / open_price) * 100, 2) as price_change_pct,

            -- Simple technical indicators
            ROUND(50 + 50 * ((current_price - avg_close) / NULLIF(std_close, 0)), 2) as rsi_approx,
            avg_close as sma20,
            avg_close * 0.98 as support_level,
            avg_close * 1.02 as resistance_level,

            -- Bollinger Band approximation
            avg_close + 2 * std_close as bb_upper,
            avg_close as bb_middle,
            avg_close - 2 * std_close as bb_lower,

            -- Position calculations
            ROUND(((current_price - (avg_close - 2 * std_close)) /
                   NULLIF((avg_close + 2 * std_close) - (avg_close - 2 * std_close), 0)) * 100, 2) as bb_position_pct,

            CASE
                WHEN current_price < avg_close - 2 * std_close THEN 'BELOW_LOWER'
                WHEN current_price > avg_close + 2 * std_close THEN 'ABOVE_UPPER'
                ELSE 'MIDDLE'
            END as bb_position,

            -- Trend approximation
            CASE
                WHEN current_price > avg_close THEN 'BULLISH_TREND'
                WHEN current_price < avg_close THEN 'BEARISH_TREND'
                ELSE 'SIDEWAYS'
            END as trend_signal,

            -- Momentum approximation
            CASE
                WHEN (current_price - avg_close) / NULLIF(avg_close, 0) > 0.01 THEN 'BULLISH_MOMENTUM'
                WHEN (current_price - avg_close) / NULLIF(avg_close, 0) < -0.01 THEN 'BEARISH_MOMENTUM'
                ELSE 'NEUTRAL'
            END as momentum_signal,

            -- Simple technical score (basic - will be enhanced with patterns)
            CASE
                WHEN current_price > avg_close AND ABS(price_change_pct) < 2 THEN 7  -- Moderate bullish
                WHEN current_price > avg_close THEN 5  -- Bullish
                WHEN current_price < avg_close THEN -3  -- Bearish
                ELSE 1  -- Neutral
            END as basic_technical_score

        FROM latest_data
        WHERE current_price > ?
            AND current_price < ?
        ORDER BY basic_technical_score DESC, ABS(price_change_pct) ASC
        LIMIT ?
        """

        params = [
            scan_date, cutoff_time.strftime('%H:%M'),  # symbol_stats
            scan_date, cutoff_time.strftime('%H:%M'),  # latest_data
            self.config['min_price'], self.config['max_price'],  # price filters
            self.config['max_results'] * 2  # Get more candidates to filter after pattern scoring
        ]

        try:
            result = self._execute_query(technical_query, params)

            if result.empty:
                print("⚠️  No stocks found with favorable technical patterns")
                return pd.DataFrame()

            # Merge with pattern scores if available
            if not pattern_scores.empty and not result.empty:
                # Merge pattern scores by symbol
                result = result.merge(
                    pattern_scores,
                    on='symbol',
                    how='left'
                ).fillna({
                    'confidence_score': 0.0,
                    'volume_multiplier': 1.0
                })

                # Enhanced technical score incorporating pattern analysis
                def calculate_enhanced_technical_score(row):
                    basic_score = row.get('basic_technical_score', 0)
                    confidence = row.get('confidence_score', 0.0)
                    pattern_volume = row.get('volume_multiplier', 1.0)
                    
                    print(f"DEBUG TECHNICAL: symbol={row.get('symbol')}, basic={basic_score}, conf={confidence}, vol_mult={pattern_volume}")
                    
                    # Weight factors: 70% technicals, 20% pattern confidence, 10% pattern volume
                    enhanced_score = (
                        basic_score * 0.7 +
                        confidence * 10 * 0.20 +  # Scale confidence (0-1) to 0-10
                        (pattern_volume - 1.0) * 0.10  # Volume multiplier contribution
                    )
                    
                    print(f"DEBUG TECHNICAL: enhanced_score={enhanced_score}")
                    return round(enhanced_score, 2)
                
                result['technical_score'] = result.apply(calculate_enhanced_technical_score, axis=1)
                
                # Filter and sort by enhanced score (only positive setups)
                print(f"DEBUG TECHNICAL FILTER: before filter len={len(result)}, scores={result['technical_score'].tolist()}")
                result = result[result['technical_score'] > 3].sort_values('technical_score', ascending=False).head(self.config['max_results'])
                print(f"DEBUG TECHNICAL FILTER: after filter len={len(result)}, symbols={result['symbol'].tolist()}")
                
                print(f"🎯 Enhanced technical scoring applied - top {len(result)} candidates after pattern analysis")
            else:
                # Fallback to basic score
                result['technical_score'] = result['basic_technical_score']
                result['confidence_score'] = 0.0
                result['volume_multiplier'] = 1.0

            # Add additional analysis
            result['setup_type'] = result.apply(
                lambda row: self._classify_technical_setup(row), axis=1
            )

            result['risk_level'] = result.apply(
                lambda row: self._assess_risk(row), axis=1
            )

            print(f"✅ Found {len(result)} stocks with favorable technical setups")
            return result

        except Exception as e:
            print(f"❌ Error in technical scanning: {e}")
            return pd.DataFrame()

    def _classify_technical_setup(self, row) -> str:
        """Classify the type of technical setup."""
        if pd.isna(row.get('rsi')) or pd.isna(row.get('macd_histogram')) or pd.isna(row.get('ema20')) or pd.isna(row.get('ema50')):
            return "UNKNOWN"

        setup = []

        if row['rsi'] <= self.config['rsi_oversold']:
            setup.append("OVERSOLD")
        elif row['rsi'] > self.config['rsi_overbought']:
            setup.append("OVERBOUGHT")

        if row['macd_histogram'] > self.config['macd_threshold']:
            setup.append("MACD_BULLISH")
        elif row['macd_histogram'] < -self.config['macd_threshold']:
            setup.append("MACD_BEARISH")

        if row['ema20'] > row['ema50']:
            setup.append("TREND_UP")
        elif row['ema20'] < row['ema50']:
            setup.append("TREND_DOWN")

        if not setup:
            return "NEUTRAL"

        return " + ".join(sorted(set(setup)))

    def _assess_risk(self, row) -> str:
        """Assess technical risk level."""
        if pd.isna(row.get('rsi')) or pd.isna(row.get('bb_position_pct')):
            return "UNKNOWN"

        risk_factors = 0

        # RSI near extremes
        if row['rsi'] >= 75 or row['rsi'] <= 25:
            risk_factors += 2

        # Price at Bollinger Band extremes
        bb_pos = row['bb_position_pct']
        if bb_pos <= 10 or bb_pos >= 90:
            risk_factors += 1

        # Volatility warning
        if abs(row.get('price_change_pct', 0)) > 3:
            risk_factors += 1

        # Trend confirmation
        if row.get('trend_signal') == 'SIDEWAYS':
            risk_factors += 1

        if risk_factors >= 3:
            return "HIGH_RISK"
        elif risk_factors >= 2:
            return "MEDIUM_RISK"
        elif risk_factors >= 1:
            return "LOW_RISK"
        else:
            return "VERY_LOW_RISK"
