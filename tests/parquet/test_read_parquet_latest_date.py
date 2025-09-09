import os
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def _write_minute_parquet(path: Path, symbol: str, day: str, rows: int = 5):
    ts_base = datetime.fromisoformat(f"{day}T09:15:00")
    data = {
        "timestamp": [ts_base + pd.Timedelta(minutes=i) for i in range(rows)],
        "open": [100.0 + i for i in range(rows)],
        "high": [101.0 + i for i in range(rows)],
        "low": [99.0 + i for i in range(rows)],
        "close": [100.5 + i for i in range(rows)],
        "volume": [1000 + i * 10 for i in range(rows)],
    }
    table = pa.Table.from_pandas(pd.DataFrame(data))
    pq.write_table(table, path)


def test_parquet_scan_and_latest_date(tmp_path: Path):
    # Arrange: create YYYY/MM/DD directory with two symbols
    root = tmp_path / "data"
    day = "2025-09-05"
    y, m, d = day.split("-")
    day_dir = root / y / m / d
    day_dir.mkdir(parents=True, exist_ok=True)

    f1 = day_dir / f"TCS_minute_{day}.parquet"
    f2 = day_dir / f"RELIANCE_minute_{day}.parquet"
    _write_minute_parquet(f1, "TCS", day, rows=7)
    _write_minute_parquet(f2, "RELIANCE", day, rows=9)

    # Act: read via DuckDB read_parquet with filename=true and create unified view
    db_path = str(tmp_path / "test.duckdb")
    con = duckdb.connect(db_path)
    con.execute("SET enable_object_cache=true")
    glob = str(root / "*" / "*" / "*" / "*.parquet")

    con.execute(f"""
    CREATE OR REPLACE VIEW market_data_unified AS
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

    # Assert: latest date_partition and symbol aggregation
    latest = con.execute("SELECT MAX(date_partition) FROM market_data_unified").fetchone()[0]
    assert str(latest) == day

    counts = con.execute(
        """
        SELECT symbol, COUNT(*) as rows
        FROM market_data_unified
        WHERE date_partition = ?
        GROUP BY 1
        ORDER BY rows DESC
        """,
        [day],
    ).fetchall()
    assert dict(counts)["RELIANCE"] == 9
    assert dict(counts)["TCS"] == 7
