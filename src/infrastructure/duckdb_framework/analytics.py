"""
Financial Analytics Framework
============================

Provides advanced analytical capabilities:
- Time series analysis
- Technical indicators
- Statistical functions
- Risk metrics
- Performance analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum


class TechnicalIndicator(Enum):
    """Technical indicators supported."""
    SMA = "SMA"
    EMA = "EMA"
    WMA = "WMA"
    RSI = "RSI"
    MACD = "MACD"
    BOLLINGER_BANDS = "BOLLINGER_BANDS"
    STOCHASTIC = "STOCHASTIC"
    WILLIAMS_R = "WILLIAMS_R"
    CCI = "CCI"
    ATR = "ATR"
    ADX = "ADX"


@dataclass
class IndicatorResult:
    """Result of technical indicator calculation."""
    name: str
    data: pd.DataFrame
    metadata: Dict[str, Any]


@dataclass
class TimeSeriesAnalysis:
    """Time series analysis results."""
    returns: pd.Series
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    cumulative_returns: pd.Series
    rolling_volatility: pd.Series


class TechnicalIndicators:
    """
    Technical indicator calculations using DuckDB.
    """

    def __init__(self, connection):
        self.connection = connection

    def calculate_sma(self, symbol: str, period: int = 20,
                     column: str = "close") -> IndicatorResult:
        """Calculate Simple Moving Average."""
        query = """
        SELECT
            timestamp,
            symbol,
            ?
            AVG(?) OVER (
                PARTITION BY symbol
                ORDER BY timestamp
                ROWS ? PRECEDING
            ) as sma_?
        FROM market_data_unified
        WHERE symbol = ?
        ORDER BY timestamp
        """

        df = self.connection.execute(query, [column, column, period-1, period, symbol]).fetchdf()

        return IndicatorResult(
            name=f"SMA_{period}",
            data=df,
            metadata={"period": period, "type": "trend"}
        )

    def calculate_rsi(self, symbol: str, period: int = 14) -> IndicatorResult:
        """Calculate Relative Strength Index."""
        query = """
        WITH price_changes AS (
            SELECT
                timestamp,
                symbol,
                close,
                close - LAG(close) OVER (PARTITION BY symbol ORDER BY timestamp) as price_change
            FROM market_data_unified
            WHERE symbol = ?
        ),
        gains_losses AS (
            SELECT
                timestamp,
                symbol,
                CASE WHEN price_change > 0 THEN price_change ELSE 0 END as gain,
                CASE WHEN price_change < 0 THEN ABS(price_change) ELSE 0 END as loss
            FROM price_changes
        ),
        avg_gains_losses AS (
            SELECT
                timestamp,
                symbol,
                AVG(gain) OVER (PARTITION BY symbol ORDER BY timestamp ROWS ? PRECEDING) as avg_gain,
                AVG(loss) OVER (PARTITION BY symbol ORDER BY timestamp ROWS ? PRECEDING) as avg_loss
            FROM gains_losses
        )
        SELECT
            timestamp,
            symbol,
            100 - (100 / (1 + (avg_gain / NULLIF(avg_loss, 0)))) as rsi_?
        FROM avg_gains_losses
        ORDER BY timestamp
        """

        df = self.connection.execute(query, [symbol, period-1, period-1, period]).fetchdf()

        return IndicatorResult(
            name=f"RSI_{period}",
            data=df,
            metadata={"period": period, "type": "momentum", "overbought": 70, "oversold": 30}
        )

    def calculate_bollinger_bands(self, symbol: str, period: int = 20,
                                 std_dev: float = 2.0) -> IndicatorResult:
        """Calculate Bollinger Bands."""
        query = """
        WITH sma_calc AS (
            SELECT
                timestamp,
                symbol,
                close,
                AVG(close) OVER (
                    PARTITION BY symbol
                    ORDER BY timestamp
                    ROWS ? PRECEDING
                ) as sma,
                STDDEV(close) OVER (
                    PARTITION BY symbol
                    ORDER BY timestamp
                    ROWS ? PRECEDING
                ) as stddev
            FROM market_data_unified
            WHERE symbol = ?
        )
        SELECT
            timestamp,
            symbol,
            close,
            sma as middle_band,
            sma + (? * stddev) as upper_band,
            sma - (? * stddev) as lower_band,
            (close - (sma - (? * stddev))) / NULLIF((sma + (? * stddev)) - (sma - (? * stddev)), 0) as bb_position
        FROM sma_calc
        ORDER BY timestamp
        """

        df = self.connection.execute(query, [period-1, period-1, symbol, std_dev, std_dev, std_dev, std_dev, std_dev]).fetchdf()

        return IndicatorResult(
            name=f"BB_{period}_{std_dev}",
            data=df,
            metadata={"period": period, "std_dev": std_dev, "type": "volatility"}
        )

    def calculate_macd(self, symbol: str, fast_period: int = 12,
                      slow_period: int = 26, signal_period: int = 9) -> IndicatorResult:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        query = """
        WITH ema_fast AS (
            SELECT
                timestamp,
                symbol,
                close,
                close * (2.0 / (? + 1)) +
                LAG(close * (2.0 / (? + 1)), 1) OVER (
                    PARTITION BY symbol ORDER BY timestamp
                ) as ema_fast
            FROM market_data
            WHERE symbol = ?
        ),
        ema_slow AS (
            SELECT
                timestamp,
                symbol,
                close,
                close * (2.0 / (? + 1)) +
                LAG(close * (2.0 / (? + 1)), 1) OVER (
                    PARTITION BY symbol ORDER BY timestamp
                ) as ema_slow
            FROM market_data
            WHERE symbol = ?
        ),
        macd_calc AS (
            SELECT
                f.timestamp,
                f.symbol,
                f.ema_fast - s.ema_slow as macd_line,
                f.ema_fast,
                s.ema_slow
            FROM ema_fast f
            JOIN ema_slow s ON f.timestamp = s.timestamp AND f.symbol = s.symbol
        ),
        signal_calc AS (
            SELECT
                timestamp,
                symbol,
                macd_line,
                AVG(macd_line) OVER (
                    PARTITION BY symbol
                    ORDER BY timestamp
                    ROWS ? PRECEDING
                ) as signal_line,
                macd_line - AVG(macd_line) OVER (
                    PARTITION BY symbol
                    ORDER BY timestamp
                    ROWS ? PRECEDING
                ) as histogram
            FROM macd_calc
        )
        SELECT * FROM signal_calc
        ORDER BY timestamp
        """

        df = self.connection.execute(query, [fast_period, fast_period, symbol, slow_period, slow_period, symbol, signal_period-1, signal_period-1]).fetchdf()

        return IndicatorResult(
            name=f"MACD_{fast_period}_{slow_period}_{signal_period}",
            data=df,
            metadata={
                "fast_period": fast_period,
                "slow_period": slow_period,
                "signal_period": signal_period,
                "type": "momentum"
            }
        )

    def calculate_volatility(self, symbol: str, window: int = 30) -> IndicatorResult:
        """Calculate rolling volatility."""
        query = """
        WITH returns AS (
            SELECT
                timestamp,
                symbol,
                close,
                (close - LAG(close) OVER (PARTITION BY symbol ORDER BY timestamp)) /
                NULLIF(LAG(close) OVER (PARTITION BY symbol ORDER BY timestamp), 0) as daily_return
            FROM market_data
            WHERE symbol = ?
        )
        SELECT
            timestamp,
            symbol,
            daily_return,
            STDDEV(daily_return) OVER (
                PARTITION BY symbol
                ORDER BY timestamp
                ROWS ? PRECEDING
            ) * SQRT(252) as annualized_volatility,
            STDDEV(daily_return) OVER (
                PARTITION BY symbol
                ORDER BY timestamp
                ROWS ? PRECEDING
            ) as rolling_volatility
        FROM returns
        ORDER BY timestamp
        """

        df = self.connection.execute(query, [symbol, window-1, window-1]).fetchdf()

        return IndicatorResult(
            name=f"VOLATILITY_{window}",
            data=df,
            metadata={"window": window, "type": "volatility"}
        )


class FinancialAnalytics:
    """
    Advanced financial analytics using DuckDB.
    """

    def __init__(self, connection):
        self.connection = connection
        self.indicators = TechnicalIndicators(connection)

    def analyze_portfolio_returns(self, symbols: List[str],
                                start_date: str, end_date: str) -> Dict[str, TimeSeriesAnalysis]:
        """Analyze portfolio returns for multiple symbols."""
        results = {}

        for symbol in symbols:
            analysis = self._analyze_symbol_returns(symbol, start_date, end_date)
            results[symbol] = analysis

        return results

    def _analyze_symbol_returns(self, symbol: str, start_date: str, end_date: str) -> TimeSeriesAnalysis:
        """Analyze returns for a single symbol."""
        query = """
        WITH daily_prices AS (
            SELECT
                date_trunc('day', timestamp) as date,
                FIRST(close) as close_price
            FROM market_data
            WHERE symbol = ?
              AND timestamp BETWEEN ? AND ?
            GROUP BY date_trunc('day', timestamp)
            ORDER BY date
        ),
        returns_calc AS (
            SELECT
                date,
                close_price,
                (close_price - LAG(close_price) OVER (ORDER BY date)) /
                NULLIF(LAG(close_price) OVER (ORDER BY date), 0) as daily_return
            FROM daily_prices
        )
        SELECT
            date,
            close_price,
            daily_return,
            STDDEV(daily_return) OVER (ORDER BY date ROWS 29 PRECEDING) as rolling_volatility
        FROM returns_calc
        ORDER BY date
        """

        df = self.connection.execute(query, [symbol, start_date, end_date]).fetchdf()

        # Calculate metrics
        returns = df['daily_return'].dropna()
        cumulative_returns = (1 + returns).cumprod() - 1
        rolling_volatility = df['rolling_volatility'].dropna()

        # Risk metrics
        volatility = returns.std() * np.sqrt(252)  # Annualized
        sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0

        # Maximum drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()

        return TimeSeriesAnalysis(
            returns=returns,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            cumulative_returns=cumulative_returns,
            rolling_volatility=rolling_volatility
        )

    def correlation_matrix(self, symbols: List[str],
                          start_date: str, end_date: str) -> pd.DataFrame:
        """Calculate correlation matrix for symbols."""
        returns_data = []

        for symbol in symbols:
            query = """
            SELECT
                date_trunc('day', timestamp) as date,
                (close - LAG(close) OVER (ORDER BY timestamp)) /
                NULLIF(LAG(close) OVER (ORDER BY timestamp), 0) as daily_return
            FROM market_data
            WHERE symbol = ?
              AND timestamp BETWEEN ? AND ?
            ORDER BY date
            """

            df = self.connection.execute(query, [symbol, start_date, end_date]).fetchdf()
            df = df.set_index('date')
            returns_data.append(df['daily_return'].rename(symbol))

        # Combine all returns into a single DataFrame
        combined_df = pd.concat(returns_data, axis=1)
        correlation_matrix = combined_df.corr()

        return correlation_matrix

    def sector_analysis(self, sector_symbols: Dict[str, List[str]],
                       start_date: str, end_date: str) -> Dict[str, Dict]:
        """Analyze performance by sector."""
        sector_results = {}

        for sector, symbols in sector_symbols.items():
            sector_returns = []

            for symbol in symbols:
                analysis = self._analyze_symbol_returns(symbol, start_date, end_date)
                sector_returns.append(analysis.cumulative_returns.iloc[-1] if not analysis.cumulative_returns.empty else 0)

            sector_results[sector] = {
                'avg_return': np.mean(sector_returns),
                'volatility': np.std(sector_returns),
                'best_performer': symbols[np.argmax(sector_returns)],
                'worst_performer': symbols[np.argmin(sector_returns)],
                'num_stocks': len(symbols)
            }

        return sector_results

    def risk_metrics(self, symbol: str, confidence_level: float = 0.95) -> Dict[str, float]:
        """Calculate comprehensive risk metrics."""
        query = """
        WITH returns AS (
            SELECT
                (close - LAG(close) OVER (ORDER BY timestamp)) /
                NULLIF(LAG(close) OVER (ORDER BY timestamp), 0) as daily_return
            FROM market_data
            WHERE symbol = ?
            ORDER BY timestamp
        )
        SELECT
            daily_return,
            PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY daily_return) as var_95,
            PERCENTILE_CONT(0.01) WITHIN GROUP (ORDER BY daily_return) as var_99,
            AVG(daily_return) as mean_return,
            STDDEV(daily_return) as volatility,
            MIN(daily_return) as max_loss,
            MAX(daily_return) as max_gain
        FROM returns
        WHERE daily_return IS NOT NULL
        """

        df = self.connection.execute(query, [symbol]).fetchdf()

        if df.empty:
            return {}

        row = df.iloc[0]

        return {
            'mean_return': row['mean_return'],
            'volatility': row['volatility'],
            'var_95': row['var_95'],
            'var_99': row['var_99'],
            'max_loss': row['max_loss'],
            'max_gain': row['max_gain'],
            'sharpe_ratio': row['mean_return'] / row['volatility'] if row['volatility'] > 0 else 0,
            'sortino_ratio': self._calculate_sortino_ratio(symbol)
        }

    def _calculate_sortino_ratio(self, symbol: str) -> float:
        """Calculate Sortino ratio (downside deviation only)."""
        query = """
        WITH returns AS (
            SELECT
                (close - LAG(close) OVER (ORDER BY timestamp)) /
                NULLIF(LAG(close) OVER (ORDER BY timestamp), 0) as daily_return
            FROM market_data
            WHERE symbol = ?
        ),
        downside AS (
            SELECT
                CASE WHEN daily_return < 0 THEN daily_return * daily_return ELSE 0 END as downside_return
            FROM returns
            WHERE daily_return IS NOT NULL
        )
        SELECT
            AVG(CASE WHEN daily_return > 0 THEN daily_return ELSE 0 END) as upside_return,
            SQRT(AVG(downside_return)) as downside_deviation
        FROM returns r
        CROSS JOIN downside d
        WHERE r.daily_return IS NOT NULL
        """

        df = self.connection.execute(query, [symbol]).fetchdf()

        if df.empty or df.iloc[0]['downside_deviation'] == 0:
            return 0

        row = df.iloc[0]
        return row['upside_return'] / row['downside_deviation']
