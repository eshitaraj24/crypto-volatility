#!/usr/bin/env python3
"""
Score a feature Parquet file using the trained XGBoost model.
Checks that inference runs in < 2x real-time.
"""

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

ARTIFACTS_DIR = Path("models/artifacts")


def load_model():
    model = xgb.XGBClassifier()
    model.load_model(str(ARTIFACTS_DIR / "xgboost_model.json"))
    with open(ARTIFACTS_DIR / "model_meta.json") as f:
        meta = json.load(f)
    return model, meta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", required=True)
    parser.add_argument("--out",      default="data/processed/predictions.csv")
    args = parser.parse_args()

    df = pd.read_parquet(args.features)
    df = df.sort_values("ts").reset_index(drop=True)

    model, meta = load_model()
    feat_cols     = meta["feature_cols"]
    best_threshold = meta["best_threshold"]

    # Estimate covered real-time span
    if "ts" in df.columns and len(df) > 1:
        real_time_span = df["ts"].iloc[-1] - df["ts"].iloc[0]
    else:
        real_time_span = len(df) * 1.0

    X = df[feat_cols].fillna(0).values

    t0 = time.time()
    scores = model.predict_proba(X)[:, 1]
    t1 = time.time()

    inference_time = t1 - t0
    rtf = inference_time / real_time_span if real_time_span > 0 else 0

    df["spike_prob"]  = scores
    df["spike_pred"]  = (scores >= best_threshold).astype(int)

    log.info("Scored %d rows in %.3fs (%.4fx real-time)", len(df), inference_time, rtf)

    if rtf > 2.0:
        log.warning("⚠️  Inference is %.2fx real-time (> 2x limit)", rtf)
    else:
        log.info("✅ Inference speed OK: %.4fx real-time", rtf)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df[["ts", "product_id", "spike_prob", "spike_pred"]].to_csv(out, index=False)
    log.info("Predictions saved → %s", out)

    print("\n--- Sample predictions ---")
    print(df[["ts", "product_id", "spike_prob", "spike_pred"]].tail(10).to_string(index=False))


if __name__ == "__main__":
    main()