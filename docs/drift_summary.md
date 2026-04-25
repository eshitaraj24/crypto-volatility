# Drift Summary — Crypto Volatility Detection

## Schedule
Evidently drift reports are generated after each new data collection session
and compared against the training distribution.

## Latest Report
- **Generated**: 2026-04-05
- **Reference**: Training set (first 60% of data, 12,849 rows)
- **Current**: Test set (last 20% of data, 4,284 rows)
- **Report**: reports/evidently/train_vs_test_drift.html

## Drift Results

| Feature | Drifted | KS Stat | P-Value |
|---------|---------|---------|---------|
| ret_abs_60s | YES | 0.41 | < 0.05 |
| trade_intensity_30s | YES | 0.38 | < 0.05 |
| ret_std_30s | YES | 0.35 | < 0.05 |
| spread_bps | YES | 0.29 | < 0.05 |
| mid_price | YES | 0.51 | < 0.05 |

All 20 features showed statistically significant drift (KS test, p < 0.05).

## Root Cause
Data was collected across 3 separate sessions spanning 2 days.
Crypto volatility regimes changed between sessions causing feature drift.

## Action Taken
- Documented in model card as known limitation
- MODEL_VARIANT=baseline rollback available if XGBoost degrades
- Recommend retraining weekly with fresh continuous data

## Next Scheduled Report
After next data collection session (weekly cadence recommended).
