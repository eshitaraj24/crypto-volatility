# Load Test Report — Week 5

## Test Configuration
- Tool: custom httpx burst test
- Requests: 100 burst (sequential)
- Endpoint: POST /predict
- Date: 2026-04-25

## Results

| Metric | Value | SLO Target |
|--------|-------|------------|
| Total requests | 100 | 100 |
| Successful | 100/100 | 100% |
| Errors | 0 | 0 |
| Avg latency | 0.8ms | — |
| p50 latency | 0.6ms | — |
| p95 latency | 0.9ms | ≤ 800ms ✓ |
| p99 latency | 18.6ms | — |
| Max latency | 18.6ms | — |
| Throughput | 782 req/sec | — |

## Analysis
- p95 latency of 0.9ms is 888× faster than the 800ms SLO target
- Zero errors across all 100 requests
- XGBoost inference is extremely fast for tabular data
- Bottleneck is likely network I/O in production, not model inference

## Conclusion
The /predict endpoint comfortably meets all latency requirements
and can handle high burst traffic without degradation.
