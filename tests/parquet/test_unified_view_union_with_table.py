from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def _write_minute_parquet(path: Path, day: str, rows: int = 3):
    ts_base = datetime.fromisoformat(f"{day}T09:15:00")
    df = pd.DataFrame({
        "timestamp": [ts_base + pd.Timedelta(minutes=i) for i in range(rows)],
        "open": [10 + i for i in range(rows)],
        "high": [11 + i for i in range(rows)],
        "low": [9 + i for i in range(rows)],
        "close": [10.5 + i for i in range(rows)],
        "volume": [100 + i for i in range(rows)],
    })
    pq.write_table(pa.Table.from_pandas(df), path)


def test_unified_view_unions_table_and_parquet(tmp_path: Path):
    # Arrange: create small duckdb table with one row
    db_path = str(tmp_path / "test.duckdb")
    con = duckdb.connect(db_path)
    con.execute("CREATE TABLE market_data (symbol VARCHAR, timestamp TIMESTAMP, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT)")
    con.execute("INSERT INTO market_data VALUES ('DBSYM', TIMESTAMP '2025-09-04 09:15:00', 100,101,99,100.5,1000)")

    # Create parquet for another symbol/date
    root = tmp_path / "data"
    day = "2025-09-05"
    y,m,d = day.split('-')
    day_dir = root / y / m / d
    day_dir.mkdir(parents=True, exist_ok=True)
    f = day_dir / f"PQSYN_minute_{day}.parquet"
    _write_minute_parquet(f, day, rows=2)

    glob = str(root / "*" / "*" / "*" / "*.parquet")

    # Act: create unified view similar to adapter (with defaults for missing cols)
    con.execute(f"""
    CREATE OR REPLACE VIEW market_data_unified AS
    SELECT
      symbol,
      timestamp,
      open,
      high,
      low,
      close,
      volume,
      '1m' AS timeframe,
      CAST(timestamp AS DATE) AS date_partition
    FROM market_data
    UNION ALL
    SELECT
      regexp_extract(filename, '.*/([A-Za-z0-9._-]+)_minute_.*', 1) AS symbol,
      CAST(timestamp AS TIMESTAMP) AS timestamp,
      CAST(open AS DOUBLE) AS open,
      CAST(high AS DOUBLE) AS high,
      CAST(low AS DOUBLE) AS low,
      CAST(close AS DOUBLE) AS close,
      CAST(COALESCE(volume, 0) AS BIGINT) AS volume,
      '1m' AS timeframe,
      CAST(timestamp AS DATE) AS date_partition
    FROM read_parquet('{glob}', filename=true)
    """)

    # Assert: contains both sources
    syms = {r[0] for r in con.execute("SELECT DISTINCT symbol FROM market_data_unified").fetchall()}
    assert "DBSYM" in syms
    assert "PQSYN" in syms

    # Date filtering works
    latest = con.execute("SELECT MAX(date_partition) FROM market_data_unified").fetchone()[0]
    assert str(latest) == day
