import datetime
from typing import Dict, Any, List
import pandas as pd

from ..base_scanner import BaseScanner


class Nifty500FilterScanner(BaseScanner):
    """
    Scanner that implements the NIFTY-500 filter logic.
    Identifies stocks based on specific price and volume conditions.
    """

    @property
    def scanner_name(self) -> str:
        return "nifty500_filter"

    def _get_default_config(self) -> Dict[str, Any]:
        return {
            "high_period": 120,  # Days for previous high calculation
            "high_multiplier": 1.05,  # Close > X% of previous high
            "volume_avg_period": 5,  # Days for simple moving average of volume
            "min_price": 10,  # Minimum stock price (example)
            "max_price": 10000,  # Maximum stock price (example)
            "max_results": 50  # Maximum results to return
        }

    def scan(self, scan_date: datetime.date, cutoff_time: datetime.time = datetime.time(9, 50)) -> pd.DataFrame:
        """
        Scan for stocks matching the NIFTY-500 filter criteria.

        Args:
            scan_date: The date for which to run the scan.
            cutoff_time: The time cutoff for the scan (not directly used in SQL but part of signature).

        Returns:
            A Pandas DataFrame with the scan results.
        """
        print(f"📊 Running NIFTY-500 Filter Scanner for {scan_date}...")

        # Calculate the start date for the 120-day high and 5-day volume average
        # We need data going back at least high_period + 1 day for prev_high_period_high
        # and volume_avg_period days for sma_volume
        data_start_date = scan_date - datetime.timedelta(days=self.config["high_period"] + self.config["volume_avg_period"] + 5) # Add buffer

        # SQL query incorporating the filter logic
        query = f"""
        WITH base AS (
          SELECT
            symbol,
            date_partition AS date,
            close,
            high,
            volume,
            LAG(close) OVER (PARTITION BY symbol ORDER BY date_partition) AS prev_close,
            MAX(high) OVER (PARTITION BY symbol ORDER BY date_partition
                              ROWS BETWEEN {self.config["high_period"]} PRECEDING AND 1 PRECEDING) AS prev_high_period_high,
            AVG(volume) OVER (PARTITION BY symbol ORDER BY date_partition
                              ROWS BETWEEN {self.config["volume_avg_period"] - 1} PRECEDING AND CURRENT ROW) AS sma_volume
          FROM market_data_unified
          WHERE date_partition >= ? AND date_partition <= ?
        )
        SELECT
            symbol,
            date,
            close,
            high,
            volume,
            prev_close,
            prev_high_period_high,
            sma_volume
        FROM base
        WHERE date = ?
          AND close > {self.config["high_multiplier"]} * prev_high_period_high
          AND volume > sma_volume
          AND close > prev_close
          AND close BETWEEN {self.config["min_price"]} AND {self.config["max_price"]}
        ORDER BY symbol
        LIMIT {self.config["max_results"]}
        """

        params = [
            data_start_date,
            scan_date,
            scan_date
        ]

        try:
            results_df = self._execute_query(query, params)

            if results_df.empty:
                print(f"⚠️  No stocks found matching NIFTY-500 filter for {scan_date}.")
                return pd.DataFrame()

            print(f"✅ Found {len(results_df)} stocks matching NIFTY-500 filter for {scan_date}.")
            return results_df

        except Exception as e:
            print(f"❌ Error running NIFTY-500 Filter Scanner: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
