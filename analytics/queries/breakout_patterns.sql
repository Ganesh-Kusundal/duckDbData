-- Breakout Pattern Discovery Queries
-- ===================================

-- 1. Volume Spike Breakout Analysis
-- Finds cases where volume spikes lead to significant price moves
SELECT
  symbol,
  date,
  ts as spike_time,
  volume,
  close as entry_price,
  -- Rolling volume calculation (10-minute window)
  AVG(volume) OVER (
    PARTITION BY symbol, date
    ORDER BY ts
    ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
  ) as avg_volume_10min,
  -- Price movement after spike (next 60 minutes)
  MAX(high) OVER (
    PARTITION BY symbol, date
    ORDER BY ts
    ROWS BETWEEN CURRENT ROW AND 59 FOLLOWING
  ) as max_high_next_60min,
  -- Calculations
  volume / AVG(volume) OVER (
    PARTITION BY symbol, date
    ORDER BY ts
    ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
  ) as volume_multiplier,
  (MAX(high) OVER (
    PARTITION BY symbol, date
    ORDER BY ts
    ROWS BETWEEN CURRENT ROW AND 59 FOLLOWING
  ) - close) / close as price_move_pct
FROM parquet_scan('data/**/*.parquet')
WHERE volume > 0 AND close > 0
  AND volume / AVG(volume) OVER (
    PARTITION BY symbol, date
    ORDER BY ts
    ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
  ) >= 1.5  -- 50% volume increase
  AND (MAX(high) OVER (
    PARTITION BY symbol, date
    ORDER BY ts
    ROWS BETWEEN CURRENT ROW AND 59 FOLLOWING
  ) - close) / close >= 0.03  -- 3% price move
ORDER BY volume_multiplier DESC, price_move_pct DESC
LIMIT 1000;

-- 2. Time Window Breakout Analysis
-- Analyzes breakouts within specific time windows (e.g., opening range)
WITH time_window_data AS (
  SELECT
    symbol,
    date,
    ts,
    time(ts) as trade_time,
    open,
    high,
    low,
    close,
    volume,
    -- Pre-window volume baseline (first 30 minutes)
    AVG(volume) OVER (
      PARTITION BY symbol, date
      ORDER BY ts
      ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
    ) as pre_window_avg_volume,
    -- Post-window price movement (next 60 minutes)
    MAX(high) OVER (
      PARTITION BY symbol, date
      ORDER BY ts
      ROWS BETWEEN CURRENT ROW AND 59 FOLLOWING
    ) as post_window_max_high
  FROM parquet_scan('data/**/*.parquet')
  WHERE time(ts) BETWEEN '09:35' AND '09:50'  -- Opening range
)
SELECT
  symbol,
  date,
  trade_time,
  volume,
  close as entry_price,
  post_window_max_high,
  (post_window_max_high - close) / close as breakout_move_pct,
  volume / pre_window_avg_volume as volume_ratio
FROM time_window_data
WHERE volume / pre_window_avg_volume >= 1.2  -- 20% volume increase
  AND (post_window_max_high - close) / close >= 0.02  -- 2% breakout
ORDER BY breakout_move_pct DESC, volume_ratio DESC
LIMIT 1000;

-- 3. Multi-Factor Breakout Pattern
-- Combines volume, time, and technical indicators
WITH technical_indicators AS (
  SELECT
    symbol,
    date,
    ts,
    close,
    volume,
    -- Simple moving averages
    AVG(close) OVER (
      PARTITION BY symbol, date
      ORDER BY ts
      ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
    ) as sma_20,
    AVG(close) OVER (
      PARTITION BY symbol, date
      ORDER BY ts
      ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
    ) as sma_50,
    -- RSI calculation (simplified)
    CASE
      WHEN sma_20 > sma_50 THEN 'BULLISH'
      WHEN sma_20 < sma_50 THEN 'BEARISH'
      ELSE 'NEUTRAL'
    END as trend_direction,
    -- Volume analysis
    AVG(volume) OVER (
      PARTITION BY symbol, date
      ORDER BY ts
      ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
    ) as avg_volume_10min
  FROM parquet_scan('data/**/*.parquet')
)
SELECT
  symbol,
  date,
  ts as signal_time,
  close as entry_price,
  volume / avg_volume_10min as volume_multiplier,
  trend_direction,
  -- Post-signal performance (next 30 minutes)
  MAX(high) OVER (
    PARTITION BY symbol, date
    ORDER BY ts
    ROWS BETWEEN CURRENT ROW AND 29 FOLLOWING
  ) as max_high_next_30min,
  (MAX(high) OVER (
    PARTITION BY symbol, date
    ORDER BY ts
    ROWS BETWEEN CURRENT ROW AND 29 FOLLOWING
  ) - close) / close as breakout_move_pct
FROM technical_indicators
WHERE volume / avg_volume_10min >= 1.5  -- Volume spike
  AND trend_direction = 'BULLISH'       -- Bullish trend
  AND time(ts) BETWEEN '09:30' AND '10:30'  -- Morning session
  AND (MAX(high) OVER (
    PARTITION BY symbol, date
    ORDER BY ts
    ROWS BETWEEN CURRENT ROW AND 29 FOLLOWING
  ) - close) / close >= 0.025  -- 2.5% breakout
ORDER BY breakout_move_pct DESC, volume_multiplier DESC
LIMIT 1000;

-- 4. Pattern Success Rate Analysis
-- Analyzes historical success rates of different pattern types
WITH pattern_occurrences AS (
  SELECT
    symbol,
    date,
    ts,
    'volume_spike' as pattern_type,
    volume / AVG(volume) OVER (
      PARTITION BY symbol, date
      ORDER BY ts
      ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
    ) as volume_multiplier,
    (MAX(high) OVER (
      PARTITION BY symbol, date
      ORDER BY ts
      ROWS BETWEEN CURRENT ROW AND 59 FOLLOWING
    ) - close) / close as price_move_pct,
    time(ts) as trigger_time
  FROM parquet_scan('data/**/*.parquet')
  WHERE volume / AVG(volume) OVER (
    PARTITION BY symbol, date
    ORDER BY ts
    ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
  ) >= 1.5
),
success_analysis AS (
  SELECT
    pattern_type,
    COUNT(*) as total_occurrences,
    COUNT(CASE WHEN price_move_pct >= 0.02 THEN 1 END) as successful_breakouts,
    AVG(price_move_pct) as avg_price_move,
    AVG(volume_multiplier) as avg_volume_multiplier,
    -- Time window grouping
    CASE
      WHEN EXTRACT(hour FROM trigger_time) = 9 AND EXTRACT(minute FROM trigger_time) BETWEEN 35 AND 50 THEN '09:35-09:50'
      WHEN EXTRACT(hour FROM trigger_time) = 10 THEN '10:00-10:59'
      WHEN EXTRACT(hour FROM trigger_time) = 11 THEN '11:00-11:59'
      ELSE 'Other'
    END as time_window
  FROM pattern_occurrences
  GROUP BY pattern_type, CASE
    WHEN EXTRACT(hour FROM trigger_time) = 9 AND EXTRACT(minute FROM trigger_time) BETWEEN 35 AND 50 THEN '09:35-09:50'
    WHEN EXTRACT(hour FROM trigger_time) = 10 THEN '10:00-10:59'
    WHEN EXTRACT(hour FROM trigger_time) = 11 THEN '11:00-11:59'
    ELSE 'Other'
  END
)
SELECT
  pattern_type,
  time_window,
  total_occurrences,
  successful_breakouts,
  ROUND(successful_breakouts * 100.0 / total_occurrences, 2) as success_rate_pct,
  ROUND(avg_price_move * 100, 2) as avg_price_move_pct,
  ROUND(avg_volume_multiplier, 2) as avg_volume_multiplier
FROM success_analysis
WHERE total_occurrences >= 10  -- Minimum sample size
ORDER BY success_rate_pct DESC, total_occurrences DESC;

-- 5. Sector Performance Analysis
-- Analyzes breakout patterns by sector/industry
WITH sector_data AS (
  SELECT
    symbol,
    date,
    ts,
    close,
    volume,
    -- Extract sector from symbol (simplified - would need actual sector mapping)
    CASE
      WHEN symbol LIKE 'RELIANCE%' THEN 'Energy'
      WHEN symbol LIKE 'TCS%' OR symbol LIKE 'INFY%' THEN 'Technology'
      WHEN symbol LIKE 'HDFC%' OR symbol LIKE 'ICICI%' THEN 'Financial'
      WHEN symbol LIKE 'BAJAJ%' THEN 'Auto'
      ELSE 'Other'
    END as sector,
    -- Pattern detection
    volume / AVG(volume) OVER (
      PARTITION BY symbol, date
      ORDER BY ts
      ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
    ) as volume_multiplier,
    (MAX(high) OVER (
      PARTITION BY symbol, date
      ORDER BY ts
      ROWS BETWEEN CURRENT ROW AND 59 FOLLOWING
    ) - close) / close as price_move_pct
  FROM parquet_scan('data/**/*.parquet')
  WHERE volume > 0
)
SELECT
  sector,
  COUNT(*) as pattern_occurrences,
  COUNT(CASE WHEN volume_multiplier >= 1.5 THEN 1 END) as volume_spikes,
  COUNT(CASE WHEN price_move_pct >= 0.03 THEN 1 END) as successful_breakouts,
  ROUND(
    COUNT(CASE WHEN price_move_pct >= 0.03 THEN 1 END) * 100.0 /
    COUNT(CASE WHEN volume_multiplier >= 1.5 THEN 1 END),
    2
  ) as success_rate_pct,
  ROUND(AVG(CASE WHEN volume_multiplier >= 1.5 THEN price_move_pct END) * 100, 2) as avg_breakout_move_pct
FROM sector_data
GROUP BY sector
HAVING COUNT(CASE WHEN volume_multiplier >= 1.5 THEN 1 END) >= 5
ORDER BY success_rate_pct DESC;
