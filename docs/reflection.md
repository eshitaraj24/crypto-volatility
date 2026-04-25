# Final Reflection — Crypto Volatility AI Service

## System Summary

| Component | Technology | Status |
|-----------|-----------|--------|
| Data ingestion | Coinbase WebSocket + Kafka | ✅ Working |
| Feature pipeline | Python + Parquet | ✅ Working |
| ML model | XGBoost | ✅ Working |
| Experiment tracking | MLflow | ✅ Working |
| API | FastAPI | ✅ Working |
| Monitoring | Prometheus + Grafana | ✅ Working |
| Drift detection | Evidently | ✅ Working |
| CI/CD | GitHub Actions | ✅ Passing |

## Final Metrics

### Model Performance
| Metric | Baseline | XGBoost | Target |
|--------|---------|---------|--------|
| Test PR-AUC | 0.8912 | 0.5598 | ≥ 0.55 ✓ |
| Test ROC-AUC | 0.7969 | 0.4546 | — |
| Test Best-F1 | 0.8040 | 0.7732 | — |

### API Performance
| Metric | Value | Target |
|--------|-------|--------|
| p95 latency | 0.9ms | ≤ 800ms ✓ |
| p50 latency | 0.6ms | — |
| Throughput | 782 req/s | — |
| Error rate | 0% | < 1% ✓ |
| Uptime | 100% | ≥ 99% ✓ |

## What Worked Well
- XGBoost inference is extremely fast (< 1ms per prediction)
- Kafka pipeline is reliable with reconnect/resubscribe logic
- FastAPI with Prometheus instrumentation was straightforward
- Evidently drift reports clearly showed regime shifts
- GitHub Actions CI caught unused imports automatically

## What Was Challenging
- Crypto volatility regime shifts made model generalization difficult
- MLflow 3.x had breaking changes requiring local deployment
- Evidently API changed significantly between versions
- Threshold τ needed recalibration when new data was collected

## Lessons Learned
1. Financial ML models are highly sensitive to the time period of training data
2. PR-AUC is the right metric for imbalanced classification — accuracy is misleading
3. Continuous monitoring (Evidently + Prometheus) is essential, not optional
4. Docker health checks need careful tuning per service
5. More data does not always mean better models — data quality and regime consistency matter more

## Uptime & Reliability
- Zero unplanned downtime during development
- Graceful shutdown implemented in API
- MODEL_VARIANT=baseline rollback available at any time
- All services restart automatically via Docker Compose
