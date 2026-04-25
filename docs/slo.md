# Service Level Objectives (SLOs)

## API SLOs

| SLO | Target | Current | Status |
|-----|--------|---------|--------|
| p95 latency /predict | ≤ 800ms | ~12ms | ✅ Met |
| p50 latency /predict | ≤ 200ms | ~7ms | ✅ Met |
| Error rate | < 1% | 0% | ✅ Met |
| Availability | ≥ 99% | 100% | ✅ Met |
| Throughput | ≥ 10 req/s | 782 req/s | ✅ Met |

## Model SLOs

| SLO | Target | Current | Status |
|-----|--------|---------|--------|
| Test PR-AUC | ≥ 0.55 | 0.5598 | ✅ Met |
| Inference latency | < 2× real-time | 0.0000× | ✅ Met |

## Monitoring
- Prometheus scrapes metrics every 15 seconds
- Grafana dashboard auto-refreshes every 10 seconds
- Evidently drift reports generated on demand

## SLO Breach Response
If p95 > 800ms: scale uvicorn workers
If error rate > 1%: check logs, switch to baseline variant
If PR-AUC drops: trigger retraining pipeline
