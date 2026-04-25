#!/usr/bin/env python3
"""
Train baseline (z-score rule) and ML model (XGBoost).
Log everything to MLflow. Use time-based splits.
"""

import argparse
import json
import logging
import os
import time
from pathlib import Path

import mlflow
import mlflow.sklearn
import mlflow.xgboost
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, f1_score,
                             precision_recall_curve, roc_auc_score)
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

MLFLOW_URI      = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001")
EXPERIMENT_NAME = "crypto-volatility"
ARTIFACTS_DIR   = Path("models/artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def load_and_split(parquet_path: str):
    """Time-based split: 60% train, 20% val, 20% test."""
    df = pd.read_parquet(parquet_path)
    df = df.sort_values("ts").reset_index(drop=True)

    # Drop rows without labels
    df = df.dropna(subset=["label", "future_vol"])
    log.info("Dataset: %d rows, spike rate: %.1f%%", len(df), df["label"].mean() * 100)

    n = len(df)
    i_val  = int(n * 0.60)
    i_test = int(n * 0.80)

    train = df.iloc[:i_val]
    val   = df.iloc[i_val:i_test]
    test  = df.iloc[i_test:]

    feat_cols = [c for c in df.columns
                 if c not in ["ts", "product_id", "label", "future_vol"]
                 and df[c].dtype in ["float64", "float32", "int64", "int32"]]

    log.info("Train: %d | Val: %d | Test: %d", len(train), len(val), len(test))
    log.info("Features: %s", feat_cols)

    return train, val, test, feat_cols


def evaluate(y_true, y_pred, y_score, split_name: str) -> dict:
    pr_auc = average_precision_score(y_true, y_score)
    roc    = roc_auc_score(y_true, y_score)

    # F1 at 0.5 threshold
    f1     = f1_score(y_true, y_pred, zero_division=0)

    # F1 at best threshold
    prec, rec, thresholds = precision_recall_curve(y_true, y_score)
    f1_scores = 2 * prec * rec / (prec + rec + 1e-12)
    best_f1   = float(np.max(f1_scores))
    best_thr  = float(thresholds[np.argmax(f1_scores)]) if len(thresholds) > 0 else 0.5

    metrics = {
        f"{split_name}_pr_auc":  pr_auc,
        f"{split_name}_roc_auc": roc,
        f"{split_name}_f1":      f1,
        f"{split_name}_best_f1": best_f1,
        f"{split_name}_best_threshold": best_thr,
        f"{split_name}_spike_rate": float(y_true.mean()),
    }
    log.info("%s — PR-AUC=%.4f | ROC-AUC=%.4f | F1=%.4f | Best-F1=%.4f@%.3f",
             split_name, pr_auc, roc, f1, best_f1, best_thr)
    return metrics


def train_baseline(train, val, test, feat_cols):
    """Z-score rule: predict spike if ret_std_60s > mean + 1.5*std."""
    log.info("=== Baseline: Z-Score Rule ===")

    with mlflow.start_run(run_name="baseline_zscore"):
        params = {"z_multiplier": 1.5, "feature": "ret_std_60s"}
        mlflow.log_params(params)

        col   = "ret_std_60s"
        mu    = train[col].mean()
        sigma = train[col].std()
        threshold = mu + params["z_multiplier"] * sigma
        mlflow.log_param("zscore_threshold", threshold)

        all_metrics = {}
        for split_name, split_df in [("val", val), ("test", test)]:
            y_true  = split_df["label"].values
            y_score = split_df[col].values   # higher = more volatile
            y_pred  = (y_score >= threshold).astype(int)
            m = evaluate(y_true, y_pred, y_score, split_name)
            all_metrics.update(m)

        mlflow.log_metrics(all_metrics)

        # Save threshold artifact
        artifact = {"type": "zscore", "feature": col, "mu": mu, "sigma": sigma,
                    "z_multiplier": params["z_multiplier"], "threshold": threshold}
        artifact_path = ARTIFACTS_DIR / "baseline_zscore.json"
        with open(artifact_path, "w") as f:
            json.dump(artifact, f, indent=2)
        mlflow.log_artifact(str(artifact_path))

        run_id = mlflow.active_run().info.run_id
        log.info("Baseline run_id: %s", run_id)

    return all_metrics


def train_xgboost(train, val, test, feat_cols):
    """XGBoost classifier with time-based validation."""
    log.info("=== ML Model: XGBoost ===")

    X_train = train[feat_cols].fillna(0).values
    y_train = train["label"].values
    X_val   = val[feat_cols].fillna(0).values
    y_val   = val["label"].values
    X_test  = test[feat_cols].fillna(0).values
    y_test  = test["label"].values

    # Class weight
    pos_rate = y_train.mean()
    scale_pw  = (1 - pos_rate) / (pos_rate + 1e-12)

    params = {
        "n_estimators":     300,
        "max_depth":        4,
        "learning_rate":    0.05,
        "subsample":        0.8,
        "colsample_bytree": 0.8,
        "scale_pos_weight": scale_pw,
        "eval_metric":      "aucpr",
        "use_label_encoder": False,
        "random_state":     42,
    }

    with mlflow.start_run(run_name="xgboost_v1"):
        mlflow.log_params({k: v for k, v in params.items() if k != "eval_metric"})
        mlflow.log_param("features", feat_cols)
        mlflow.log_param("train_size", len(X_train))
        mlflow.log_param("val_size",   len(X_val))
        mlflow.log_param("test_size",  len(X_test))

        model = xgb.XGBClassifier(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=50,
        )

        all_metrics = {}
        for split_name, X, y in [("val", X_val, y_val), ("test", X_test, y_test)]:
            y_score = model.predict_proba(X)[:, 1]
            y_pred  = model.predict(X)
            m = evaluate(y, y_pred, y_score, split_name)
            all_metrics.update(m)

        mlflow.log_metrics(all_metrics)

        # Feature importance
        imp = dict(zip(feat_cols, model.feature_importances_))
        imp_sorted = sorted(imp.items(), key=lambda x: x[1], reverse=True)
        log.info("Top features: %s", imp_sorted[:5])

        # Log model
        mlflow.xgboost.log_model(model, "xgboost_model")

        # Save artifact
        model.save_model(str(ARTIFACTS_DIR / "xgboost_model.json"))

        # Save feature list
        feat_path = ARTIFACTS_DIR / "feature_cols.json"
        with open(feat_path, "w") as f:
            json.dump(feat_cols, f)
        mlflow.log_artifact(str(feat_path))

        # Save best threshold from val
        val_score = model.predict_proba(X_val)[:, 1]
        prec, rec, thresholds = precision_recall_curve(y_val, val_score)
        f1s = 2 * prec * rec / (prec + rec + 1e-12)
        best_thr = float(thresholds[np.argmax(f1s)]) if len(thresholds) > 0 else 0.5
        mlflow.log_param("best_threshold_from_val", best_thr)

        meta = {"type": "xgboost", "best_threshold": best_thr, "feature_cols": feat_cols}
        meta_path = ARTIFACTS_DIR / "model_meta.json"
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)
        mlflow.log_artifact(str(meta_path))

        run_id = mlflow.active_run().info.run_id
        log.info("XGBoost run_id: %s", run_id)

    return model, all_metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", default="data/processed/features.parquet")
    args = parser.parse_args()

    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    train, val, test, feat_cols = load_and_split(args.features)

    # Run baseline
    baseline_metrics = train_baseline(train, val, test, feat_cols)

    # Run XGBoost
    model, xgb_metrics = train_xgboost(train, val, test, feat_cols)

    log.info("\n=== COMPARISON ===")
    log.info("Baseline  test PR-AUC: %.4f", baseline_metrics.get("test_pr_auc", 0))
    log.info("XGBoost   test PR-AUC: %.4f", xgb_metrics.get("test_pr_auc", 0))


if __name__ == "__main__":
    main()