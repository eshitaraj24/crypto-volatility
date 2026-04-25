import json
import os
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import xgboost as xgb
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

app = FastAPI(title="Crypto Volatility API", version="1.0.0")

# Prometheus instrumentation — exposes /metrics in Prometheus format
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Load model — support MODEL_VARIANT=ml|baseline
MODEL_VARIANT = os.getenv("MODEL_VARIANT", "ml")
MODEL_PATH = Path("models/artifacts/xgboost_model.json")
META_PATH = Path("models/artifacts/model_meta.json")
BASELINE_PATH = Path("models/artifacts/baseline_zscore.json")

model = xgb.XGBClassifier()
model.load_model(str(MODEL_PATH))

with open(META_PATH) as f:
    meta = json.load(f)

with open(BASELINE_PATH) as f:
    baseline = json.load(f)

FEATURE_COLS = meta["feature_cols"]
BEST_THRESHOLD = meta["best_threshold"]
START_TIME = time.time()
predict_count = 0
spike_count = 0
error_count = 0
is_shutting_down = False


def handle_shutdown(signum, frame):
    global is_shutting_down
    is_shutting_down = True


signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


class PredictRequest(BaseModel):
    features: dict


class PredictResponse(BaseModel):
    product_id: str
    spike_probability: float
    spike_predicted: bool
    threshold_used: float
    model_version: str
    model_variant: str


@app.get("/health")
def health():
    return {
        "status": "shutting_down" if is_shutting_down else "ok",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "model_loaded": True,
        "model_variant": MODEL_VARIANT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/version")
def version():
    return {
        "model": "XGBoost Volatility Classifier",
        "version": "1.0.0",
        "variant": MODEL_VARIANT,
        "features": FEATURE_COLS,
        "threshold": BEST_THRESHOLD,
        "trained_on": "2026-04-05",
        "pairs": ["BTC-USD", "ETH-USD"],
    }


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    global predict_count, spike_count, error_count

    try:
        if MODEL_VARIANT == "baseline":
            val = request.features.get("ret_std_60s", 0.0)
            prob = float(
                min(1.0, max(0.0, (val - baseline["mu"]) / (baseline["sigma"] + 1e-12)))
            )
            spike = val >= baseline["threshold"]
        else:
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
            model_variant=MODEL_VARIANT,
        )

    except Exception as e:
        error_count += 1
        raise e


@app.get("/metrics/json")
def metrics_json():
    uptime = time.time() - START_TIME
    return {
        "total_predictions": predict_count,
        "total_spikes_predicted": spike_count,
        "total_errors": error_count,
        "spike_rate": round(spike_count / max(predict_count, 1), 4),
        "error_rate": round(error_count / max(predict_count, 1), 4),
        "uptime_seconds": round(uptime, 1),
        "predictions_per_minute": round(predict_count / max(uptime / 60, 1), 2),
        "model_threshold": BEST_THRESHOLD,
        "model_variant": MODEL_VARIANT,
        "status": "shutting_down" if is_shutting_down else "healthy",
    }
