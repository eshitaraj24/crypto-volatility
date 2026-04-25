from fastapi import FastAPI
from pydantic import BaseModel
import json
import numpy as np
import xgboost as xgb
from pathlib import Path
from datetime import datetime, timezone
import time

app = FastAPI(title="Crypto Volatility API", version="1.0.0")

# Load model on startup
MODEL_PATH = Path("models/artifacts/xgboost_model.json")
META_PATH = Path("models/artifacts/model_meta.json")

model = xgb.XGBClassifier()
model.load_model(str(MODEL_PATH))

with open(META_PATH) as f:
    meta = json.load(f)

FEATURE_COLS = meta["feature_cols"]
BEST_THRESHOLD = meta["best_threshold"]
START_TIME = time.time()
predict_count = 0
spike_count = 0


class PredictRequest(BaseModel):
    features: dict


class PredictResponse(BaseModel):
    product_id: str
    spike_probability: float
    spike_predicted: bool
    threshold_used: float
    model_version: str


@app.get("/health")
def health():
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "model_loaded": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/version")
def version():
    return {
        "model": "XGBoost Volatility Classifier",
        "version": "1.0.0",
        "features": FEATURE_COLS,
        "threshold": BEST_THRESHOLD,
        "trained_on": "2026-04-05",
        "pairs": ["BTC-USD", "ETH-USD"],
    }


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    global predict_count, spike_count

    row = [request.features.get(f, 0.0) for f in FEATURE_COLS]
    X = np.array(row).reshape(1, -1)

    prob = float(model.predict_proba(X)[0][1])
    spike = prob >= BEST_THRESHOLD

    predict_count += 1
    if spike:
        spike_count += 1

    return PredictResponse(
        product_id=request.features.get("product_id", "UNKNOWN"),
        spike_probability=round(prob, 6),
        spike_predicted=spike,
        threshold_used=BEST_THRESHOLD,
        model_version="1.0.0",
    )


@app.get("/metrics")
def metrics():
    uptime = time.time() - START_TIME
    return {
        "total_predictions": predict_count,
        "total_spikes_predicted": spike_count,
        "spike_rate": round(spike_count / max(predict_count, 1), 4),
        "uptime_seconds": round(uptime, 1),
        "predictions_per_minute": round(predict_count / max(uptime / 60, 1), 2),
        "model_threshold": BEST_THRESHOLD,
        "status": "healthy",
    }
