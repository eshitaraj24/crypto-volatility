cat > docs/feature_spec.md << 'EOF'
# Feature Specification — Crypto Volatility Detection

## Overview
This document defines the complete feature engineering pipeline for the crypto volatility
spike detector. All features are computed from raw WebSocket ticker data and are strictly
backward-looking to prevent lookahead bias.

## Target Definition

| Parameter | Value |
|---|---|
| **Target horizon** | 60 seconds |
| **Volatility proxy** | Rolling standard deviation of log mid-price returns over the next 60s |
| **Label definition** | `1` if `σ_future ≥ τ`, else `0` |
| **Chosen threshold τ** | `0.000054` |
| **Justification** | 85th percentile of the `future_vol` distribution across all sessions. Targets ~15% spike rate for workable class balance. Verified via percentile plot in `notebooks/eda.ipynb`. |
| **Spike rate** | 14.8% (3,170 spikes / 18,246 non-spikes out of 21,416 total rows) |

## No-Lookahead Guarantee
All features at time `t` are computed using only ticks with timestamp `< t`.
The label horizon is strictly forward-looking: `(t, t + 60s]`.
Replay and live featurizer produce identical features for the same input sequence.

## Mid-Price Definition
mid_price = (best_bid + best_ask) / 2

## Feature Dictionary

### Return Features (3 windows × 3 stats = 9 features)

| Feature | Formula | Windows |
|---|---|---|
| `ret_mean_Ws` | Mean of log returns: `mean(Δlog(mid))` | 10s, 30s, 60s |
| `ret_std_Ws` | Std dev of log returns: `std(Δlog(mid))` | 10s, 30s, 60s |
| `ret_abs_Ws` | Mean absolute log return: `mean(|Δlog(mid)|)` | 10s, 30s, 60s |

### Liquidity Features (3 windows × 2 stats = 6 features)

| Feature | Formula | Windows |
|---|---|---|
| `spread_mean_Ws` | Mean relative spread: `mean((ask-bid)/mid)` | 10s, 30s, 60s |
| `trade_intensity_Ws` | Ticks per second: `count / duration` | 10s, 30s, 60s |

### Activity Features (3 windows × 1 stat = 3 features)

| Feature | Formula | Windows |
|---|---|---|
| `tick_count_Ws` | Number of ticks in window | 10s, 30s, 60s |

### Instantaneous Features (2 features)

| Feature | Formula |
|---|---|
| `spread_bps` | Current spread in basis points: `(ask-bid)/mid × 10,000` |
| `mid_price` | Current mid price |

**Total: 20 features**

## Top Features by XGBoost Importance

| Rank | Feature | Importance |
|---|---|---|
| 1 | `ret_abs_60s` | 0.412 |
| 2 | `trade_intensity_30s` | 0.203 |
| 3 | `ret_std_30s` | 0.086 |
| 4 | `trade_intensity_60s` | 0.062 |
| 5 | `ret_mean_60s` | 0.045 |

## Replay Consistency
The `scripts/replay.py` script processes raw NDJSON files through the identical
`featurize_records()` function used by the live Kafka consumer. Both paths produce
byte-identical Parquet output for the same input sequence, verified by running both
on the same raw file and comparing outputs.

## Data Quality
- Missing values: None in feature columns (filled with 0 for insufficient window data)
- Minimum window requirement: 5 ticks before any features are computed
- Label coverage: 99.9% of rows have valid labels (18 rows dropped due to insufficient forward data)
EOF