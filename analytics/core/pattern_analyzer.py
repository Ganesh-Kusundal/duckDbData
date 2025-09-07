"""
Pattern Analyzer for Breakout Discovery
======================================

Analyzes stock data to discover high-probability breakout patterns.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, time
import logging
from dataclasses import dataclass

from .duckdb_connector import DuckDBAnalytics

logger = logging.getLogger(__name__)


@dataclass
class BreakoutPattern:
    """Represents a discovered breakout pattern."""
    pattern_type: str
    symbol: str
    trigger_time: datetime
    volume_multiplier: float
    price_move_pct: float
    confidence_score: float
    technical_indicators: Dict[str, Any]
    success_rate: float = 0.0


@dataclass
class PatternStatistics:
    """Statistics for pattern analysis."""
    total_occurrences: int
    successful_breakouts: int
    average_win_rate: float
    average_price_move: float
    best_time_window: str
    volume_threshold: float


class PatternAnalyzer:
    """Analyzes stock data for breakout patterns."""
    
    def __init__(self, db_connector: DuckDBAnalytics, scanner_mode: Optional[str] = None):
        """
        Initialize pattern analyzer.
        
        Args:
            db_connector: DuckDB analytics connector
            scanner_mode: Optional scanner mode ('breakout', 'technical', etc.) for specialized analysis
        """
        self.db = db_connector
        self.scanner_mode = scanner_mode or 'general'
        self.discovered_patterns: List[BreakoutPattern] = []
        
        logger.info(f"PatternAnalyzer initialized in {self.scanner_mode} mode")

    def discover_volume_spike_patterns(self,
                                     min_volume_multiplier: float = 1.5,
                                     min_price_move: float = 0.03,
                                     time_window_minutes: int = 10,
                                     scanner_mode: Optional[str] = None) -> List[BreakoutPattern]:
        """
        Discover volume spike patterns that lead to breakouts.
        
        Args:
            min_volume_multiplier: Minimum volume increase required
            min_price_move: Minimum price move percentage
            time_window_minutes: Analysis window in minutes
            scanner_mode: Scanner mode to adjust analysis parameters
        
        Returns:
            List of discovered breakout patterns
        """
        effective_mode = scanner_mode or self.scanner_mode
        
        # Adjust parameters based on scanner mode
        if effective_mode == 'breakout':
            min_volume_multiplier = max(min_volume_multiplier, 2.0)  # Stricter for breakouts
            min_price_move = max(min_price_move, 0.05)
            time_window_minutes = min(time_window_minutes, 5)  # Shorter window for breakouts
        elif effective_mode == 'technical':
            min_volume_multiplier = max(min_volume_multiplier, 1.8)
            min_price_move = max(min_price_move, 0.04)
        # 'general' mode uses default parameters
        
        logger.info(f"Discovering volume spike patterns in {effective_mode} mode (vol_mult={min_volume_multiplier}, price_move={min_price_move})")
        
        try:
            df = self.db.get_volume_spike_patterns(
                min_volume_multiplier=min_volume_multiplier,
                time_window_minutes=time_window_minutes,
                min_price_move=min_price_move
            )

            patterns = []
            for _, row in df.iterrows():
                pattern = BreakoutPattern(
                    pattern_type="volume_spike",
                    symbol=row['symbol'],
                    trigger_time=row['spike_time'],
                    volume_multiplier=row['volume_multiplier'],
                    price_move_pct=row['price_move_pct'],
                    confidence_score=self._calculate_confidence_score(row),
                    technical_indicators=self._extract_technical_indicators(row)
                )
                patterns.append(pattern)

            self.discovered_patterns.extend(patterns)
            logger.info(f"Discovered {len(patterns)} volume spike patterns")

            return patterns

        except Exception as e:
            logger.error(f"Failed to discover volume spike patterns: {e}")
            return []

    def discover_time_window_patterns(self,
                                    start_time: str = "09:35",
                                    end_time: str = "09:50",
                                    scanner_mode: Optional[str] = None) -> List[BreakoutPattern]:
        """
        Discover patterns within specific time windows.
        
        Args:
            start_time: Start of analysis window (HH:MM)
            end_time: End of analysis window (HH:MM)
            scanner_mode: Scanner mode to adjust time windows
        
        Returns:
            List of discovered time-window patterns
        """
        effective_mode = scanner_mode or self.scanner_mode
        
        # Adjust time windows based on scanner mode
        if effective_mode == 'breakout':
            start_time = "09:30"  # Earlier for breakout detection
            end_time = "09:45"
        elif effective_mode == 'technical':
            start_time = "09:40"
            end_time = "10:00"  # Later window for technical confirmation
        
        logger.info(f"Discovering time window patterns in {effective_mode} mode: {start_time}-{end_time}")
        
        try:
            df = self.db.get_time_window_analysis(start_time, end_time)

            patterns = []
            for _, row in df.iterrows():
                pattern = BreakoutPattern(
                    pattern_type="time_window",
                    symbol=row['symbol'],
                    trigger_time=row['trade_time'],
                    volume_multiplier=row['volume_ratio'],
                    price_move_pct=row['breakout_move_pct'],
                    confidence_score=self._calculate_confidence_score(row),
                    technical_indicators=self._extract_technical_indicators(row)
                )
                patterns.append(pattern)

            self.discovered_patterns.extend(patterns)
            logger.info(f"Discovered {len(patterns)} time window patterns")

            return patterns

        except Exception as e:
            logger.error(f"Failed to discover time window patterns: {e}")
            return []

    def analyze_pattern_success_rates(self,
                                    patterns: List[BreakoutPattern]) -> PatternStatistics:
        """
        Analyze success rates and statistics for discovered patterns.

        Args:
            patterns: List of patterns to analyze

        Returns:
            Pattern statistics
        """
        if not patterns:
            return PatternStatistics(0, 0, 0.0, 0.0, "", 0.0)

        # Convert to DataFrame for analysis
        df = pd.DataFrame([{
            'symbol': p.symbol,
            'trigger_time': p.trigger_time,
            'volume_multiplier': p.volume_multiplier,
            'price_move_pct': p.price_move_pct,
            'confidence_score': p.confidence_score
        } for p in patterns])

        # Calculate statistics
        total_occurrences = len(df)
        successful_breakouts = len(df[df['price_move_pct'] > 0.02])  # 2% move considered success
        average_win_rate = successful_breakouts / total_occurrences if total_occurrences > 0 else 0
        average_price_move = df['price_move_pct'].mean()

        # Find best time window
        df['hour'] = df['trigger_time'].dt.hour
        df['minute'] = df['trigger_time'].dt.minute
        df['time_window'] = df.apply(lambda row: f"{row['hour']:02d}:{row['minute']//15*15:02d}", axis=1)

        best_window = df.groupby('time_window')['price_move_pct'].mean().idxmax()
        volume_threshold = df['volume_multiplier'].quantile(0.75)  # 75th percentile

        return PatternStatistics(
            total_occurrences=total_occurrences,
            successful_breakouts=successful_breakouts,
            average_win_rate=average_win_rate,
            average_price_move=average_price_move,
            best_time_window=best_window,
            volume_threshold=volume_threshold
        )

    def get_pattern_summary_table(self,
                                patterns: List[BreakoutPattern]) -> pd.DataFrame:
        """
        Create summary table of pattern performance.

        Args:
            patterns: List of patterns to summarize

        Returns:
            Summary DataFrame
        """
        if not patterns:
            return pd.DataFrame()

        df = pd.DataFrame([{
            'Pattern_Type': p.pattern_type,
            'Symbol': p.symbol,
            'Trigger_Time': p.trigger_time,
            'Volume_Multiplier': p.volume_multiplier,
            'Price_Move_Pct': p.price_move_pct,
            'Confidence_Score': p.confidence_score
        } for p in patterns])

        # Add time window grouping
        df['Hour'] = df['Trigger_Time'].dt.hour
        df['Time_Window'] = df.apply(
            lambda row: f"{row['Hour']:02d}:{(row['Trigger_Time'].minute // 15) * 15:02d}",
            axis=1
        )

        return df

    def _calculate_confidence_score(self, row: pd.Series) -> float:
        """
        Calculate confidence score for a pattern.
        
        Args:
            row: DataFrame row with pattern data
        
        Returns:
            Confidence score (0-1)
        """
        volume_score = min(row.get('volume_multiplier', 1.0) / 3.0, 1.0)  # Max at 3x volume
        price_score = min(row.get('price_move_pct', 0.0) / 0.10, 1.0)    # Max at 10% move

        # Combine scores with weights
        confidence = (volume_score * 0.6) + (price_score * 0.4)
        
        # Adjust confidence based on scanner mode (stored in pattern)
        if hasattr(self, 'scanner_mode') and self.scanner_mode == 'breakout':
            confidence = min(confidence * 1.1, 1.0)  # Slight boost for breakout mode
        elif self.scanner_mode == 'technical':
            confidence = min(confidence * 0.95, 1.0)  # Slightly more conservative
        
        return round(confidence, 3)

    def _extract_technical_indicators(self, row: pd.Series) -> Dict[str, Any]:
        """
        Extract technical indicators from pattern data.

        Args:
            row: DataFrame row with pattern data

        Returns:
            Dictionary of technical indicators
        """
        return {
            'volume_multiplier': row.get('volume_multiplier', 1.0),
            'price_move_pct': row.get('price_move_pct', 0.0),
            'entry_price': row.get('close', row.get('entry_price', 0.0)),
            'volume': row.get('volume', 0),
            'time_of_day': row.get('trade_time', row.get('spike_time', datetime.now())).strftime('%H:%M')
        }

    def export_patterns_to_csv(self,
                              patterns: List[BreakoutPattern],
                              filename: str = "discovered_patterns.csv"):
        """
        Export discovered patterns to CSV file.

        Args:
            patterns: List of patterns to export
            filename: Output filename
        """
        if not patterns:
            logger.warning("No patterns to export")
            return

        df = self.get_pattern_summary_table(patterns)
        df.to_csv(filename, index=False)
        logger.info(f"Exported {len(patterns)} patterns to {filename}")

    def save_patterns_to_json(self,
                             patterns: List[BreakoutPattern],
                             filename: str = "patterns_backup.json"):
        """
        Save patterns to JSON for backup/loading.

        Args:
            patterns: List of patterns to save
            filename: Output filename
        """
        import json

        pattern_data = []
        for pattern in patterns:
            pattern_dict = {
                'pattern_type': pattern.pattern_type,
                'symbol': pattern.symbol,
                'trigger_time': pattern.trigger_time.isoformat(),
                'volume_multiplier': pattern.volume_multiplier,
                'price_move_pct': pattern.price_move_pct,
                'confidence_score': pattern.confidence_score,
                'technical_indicators': pattern.technical_indicators,
                'success_rate': pattern.success_rate
            }
            pattern_data.append(pattern_dict)

        with open(filename, 'w') as f:
            json.dump(pattern_data, f, indent=2, default=str)

        logger.info(f"Saved {len(patterns)} patterns to {filename}")
