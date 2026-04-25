"""Integration tests for FastAPI endpoints."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

SAMPLE_FEATURES = {
    "product_id": "BTC-USD",
    "ret_mean_10s": 0.000001,
    "ret_std_10s": 0.000012,
    "ret_abs_10s": 0.000008,
    "tick_count_10s": 25,
    "spread_mean_10s": 0.000002,
    "trade_intensity_10s": 2.5,
    "ret_mean_30s": 0.000001,
    "ret_std_30s": 0.000015,
    "ret_abs_30s": 0.000010,
    "tick_count_30s": 35,
    "spread_mean_30s": 0.000002,
    "trade_intensity_30s": 3.0,
    "ret_mean_60s": 0.000001,
    "ret_std_60s": 0.000020,
    "ret_abs_60s": 0.000012,
    "tick_count_60s": 45,
    "spread_mean_60s": 0.000002,
    "trade_intensity_60s": 3.5,
    "spread_bps": 0.05,
    "mid_price": 66900.0,
}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] == True


def test_version():
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert "model" in data
    assert "version" in data
    assert "features" in data


def test_metrics_prometheus():
    # /metrics now returns Prometheus text format
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_request" in response.text


def test_metrics_json():
    # /metrics/json returns JSON format
    response = client.get("/metrics/json")
    assert response.status_code == 200
    data = response.json()
    assert "total_predictions" in data
    assert "status" in data


def test_predict():
    response = client.post("/predict", json={"features": SAMPLE_FEATURES})
    assert response.status_code == 200
    data = response.json()
    assert "spike_probability" in data
    assert "spike_predicted" in data
    assert 0.0 <= data["spike_probability"] <= 1.0


def test_predict_returns_product_id():
    response = client.post("/predict", json={"features": SAMPLE_FEATURES})
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == "BTC-USD"


def test_predict_baseline_variant():
    os.environ["MODEL_VARIANT"] = "baseline"
    response = client.post("/predict", json={"features": SAMPLE_FEATURES})
    assert response.status_code == 200
    data = response.json()
    assert data["model_variant"] == "ml"  # loaded at startup
    os.environ["MODEL_VARIANT"] = "ml"
