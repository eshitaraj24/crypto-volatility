# Scoping Brief: Real-Time Crypto Volatility Detection

## Use Case
Detect short-term volatility spikes in BTC-USD and ETH-USD using live Coinbase WebSocket data.
A volatility spike is defined as the rolling standard deviation of mid-price returns over the
next 60 seconds exceeding a threshold τ (determined by EDA in Milestone 2).

## Prediction Goal (60-second horizon)
Given the last N ticks of market data, predict whether the next 60 seconds will exhibit
abnormally high price volatility. This is a binary classification task (spike / no-spike).

## Success Metric
- **Primary**: PR-AUC ≥ 0.55 on a held-out time-based test set
  (class-imbalance aware; spikes are rare ~10–20% of windows).
- **Secondary**: Inference latency < 2× real-time (i.e., one 60s window scored in < 120s).

## Risk Assumptions
1. **Data latency**: WebSocket feed may lag during extreme market events; reconnect logic mitigates.
2. **Class imbalance**: Spikes are rare; we will use PR-AUC not accuracy.
3. **Concept drift**: Crypto volatility regimes shift; Evidently drift reports will flag this.
4. **No lookahead bias**: Feature windows use only data strictly before the label horizon.
5. **Public data only**: We use market data; no private keys or trading.