# Crypto Volatility Detection — Real-Time AI Service

## Setup (one command)
```bash
docker compose -f docker/compose.yaml up -d
mlflow server --backend-store-uri sqlite:///mlruns/mlflow.db --default-artifact-root ./mlruns/artifacts --host 0.0.0.0 --port 5001
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## Sample Predictions
```bash
# Health check
curl http://localhost:8000/health

# Predict volatility spike
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features": {"product_id": "BTC-USD", "ret_mean_10s": 0.000001, "ret_std_10s": 0.000012, "ret_abs_10s": 0.000008, "tick_count_10s": 25, "spread_mean_10s": 0.000002, "trade_intensity_10s": 2.5, "ret_mean_30s": 0.000001, "ret_std_30s": 0.000015, "ret_abs_30s": 0.000010, "tick_count_30s": 35, "spread_mean_30s": 0.000002, "trade_intensity_30s": 3.0, "ret_mean_60s": 0.000001, "ret_std_60s": 0.000020, "ret_abs_60s": 0.000012, "tick_count_60s": 45, "spread_mean_60s": 0.000002, "trade_intensity_60s": 3.5, "spread_bps": 0.05, "mid_price": 66900.0}}'

# Version info
curl http://localhost:8000/version

# Prometheus metrics
curl http://localhost:8000/metrics
```

## Replay Test
```bash
PYTHONPATH=. python scripts/replay.py --raw "data/raw/*.ndjson" --out data/processed/features.parquet --threshold 0.000054
```

## Results
- XGBoost test PR-AUC: 0.5598 | Baseline: 0.1103
- Spike threshold τ = 0.000054 | Spike rate: 14.8%
- Inference: 0.0000× real-time
