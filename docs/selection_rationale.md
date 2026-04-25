# Model Selection Rationale

## Decision
We selected **Eshita Rajvegesna's XGBoost model** as the team base model.

## Evaluation Criteria

| Criterion | Eshita's Model | Notes |
|-----------|---------------|-------|
| Test PR-AUC | 0.5598 | Meets 0.55 target ✓ |
| Inference speed | 0.0000× real-time | Well under 2× limit ✓ |
| Pipeline completeness | Full end-to-end | Kafka → Features → MLflow → API ✓ |
| Documentation | Complete | Model card, feature spec, scoping brief ✓ |
| Drift monitoring | Evidently reports | HTML + JSON reports ✓ |
| Docker | Kafka + MLflow | compose.yaml + Dockerfile ✓ |
| FastAPI | 4 endpoints | /health /predict /version /metrics ✓ |

## Why XGBoost
- Handles class imbalance via scale_pos_weight
- Interpretable feature importances
- Fast inference (< 1ms per window)
- Well-suited for tabular financial data
- Outperforms z-score baseline by 3.5× on test PR-AUC (0.56 vs 0.11)

## Key Features
The dominant predictive signal is ret_abs_60s (41% importance),
confirming that recent absolute price movement is the strongest
predictor of near-term volatility spikes.

## Limitations Acknowledged
- Test PR-AUC of 0.5598 meets but does not greatly exceed the 0.55 target
- Validation PR-AUC is low due to volatility regime shifts across sessions
- Performance expected to improve with continuous data collection

## Next Steps for Team
1. Collect longer continuous data sessions to reduce regime shift impact
2. Add more features: order book imbalance, volume-weighted prices
3. Experiment with LSTM or ensemble models
4. Set up automated retraining pipeline
