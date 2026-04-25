#!/usr/bin/env python3
"""Generate Evidently report comparing train vs test distributions (Milestone 3)."""

import logging
from pathlib import Path
import pandas as pd
from evidently import ColumnMapping
from evidently.metric_preset import DataDriftPreset, DataQualityPreset, ClassificationPreset
from evidently.report import Report

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

df = pd.read_parquet("data/processed/features.parquet")
df = df.sort_values("ts").dropna(subset=["label"]).reset_index(drop=True)

n = len(df)
train = df.iloc[:int(n * 0.60)]
test  = df.iloc[int(n * 0.80):]

num_cols = [c for c in df.columns
            if c not in ["ts", "product_id", "label", "future_vol"]
            and df[c].dtype in ["float64", "float32", "int64"]]

column_mapping = ColumnMapping(
    target="label",
    numerical_features=num_cols,
)

report = Report(metrics=[DataQualityPreset(), DataDriftPreset()])
report.run(reference_data=train, current_data=test, column_mapping=column_mapping)

out = Path("reports/evidently")
out.mkdir(parents=True, exist_ok=True)
report.save_html(str(out / "train_vs_test_drift.html"))
log.info("Saved → reports/evidently/train_vs_test_drift.html")