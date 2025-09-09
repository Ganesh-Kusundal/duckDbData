import os
import pytest
from datetime import date, time

try:
    from fastapi.testclient import TestClient
    from src.interfaces.api.app import app
    HAS_FASTAPI = True
except Exception:
    HAS_FASTAPI = False


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI not available")
def test_scan_endpoint_smoke():
    from src.infrastructure.config.settings import get_settings

    db_path = get_settings().database.path
    if not os.path.exists(db_path):
        pytest.skip(f"DB not found at {db_path}")

    client = TestClient(app)
    payload = {
        "scanner_type": "enhanced_breakout",
        "scan_date": str(date.today()),
        "cutoff_time": "09:50:00",
        "end_of_day_time": "15:15:00",
        "config": {}
    }
    resp = client.post("/api/v1/scanner/scan", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
