"""Unit tests for FastAPI REST endpoints."""

import pytest
from fastapi.testclient import TestClient
from sovereign_embi.api.server import app

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_fit_curve_endpoint():
    payload = {
        "maturities": [0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
        "yields": [12.245, 12.939, 13.494, 12.556, 12.286, 12.207],
        "target_maturities": [1.0, 5.0, 10.0]
    }
    res = client.post("/fit-curve", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "beta0" in data
    assert "tau" in data
    assert len(data["zero_rates"]) == 3
    assert len(data["forward_rates"]) == 3
    assert len(data["discount_factors"]) == 3


def test_analyze_spread_endpoint():
    payload = {
        "maturities": [1.0, 2.0, 10.0],
        "br_yields": [13.0, 12.5, 12.0],
        "us_yields": [1.5, 2.0, 2.5],
        "embi_bps": 334.0
    }
    res = client.post("/analyze-spread", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["nominal_spreads_bps"]) == 3
    assert data["policy_spread_bps"] == (10.75 - 0.25) * 100.0


def test_macro_summary_endpoint():
    res = client.get("/macro-summary")
    assert res.status_code == 200
    data = res.json()
    assert "br_curve" in data
    assert "us_curve" in data
    assert data["embi_bps"] == 334.0
