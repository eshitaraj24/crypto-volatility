"""Load test — 100 burst requests to /predict endpoint."""
import time
import statistics
import httpx

URL = "http://localhost:8000/predict"
SAMPLE_FEATURES = {
    "product_id": "BTC-USD",
    "ret_mean_10s": 0.000001,
    "ret_std_10s": 0.000012,
    "ret_abs_10s": 0.000008,
    "tick_count_10s": 25,
    "spread_mean_10s": 0.000002,
    "trade_intensity_10s": 2.5,
    "ret_mean_30s": 0.000001,
    "ret_std_30s": 0.000015,
    "ret_abs_30s": 0.000010,
    "tick_count_30s": 35,
    "spread_mean_30s": 0.000002,
    "trade_intensity_30s": 3.0,
    "ret_mean_60s": 0.000001,
    "ret_std_60s": 0.000020,
    "ret_abs_60s": 0.000012,
    "tick_count_60s": 45,
    "spread_mean_60s": 0.000002,
    "trade_intensity_60s": 3.5,
    "spread_bps": 0.05,
    "mid_price": 66900.0,
}

def run_load_test(n=100):
    latencies = []
    errors = 0

    print(f"Running {n} burst requests to {URL}...")
    start_total = time.time()

    with httpx.Client() as client:
        for i in range(n):
            t0 = time.time()
            try:
                r = client.post(URL, json={"features": SAMPLE_FEATURES}, timeout=5.0)
                if r.status_code != 200:
                    errors += 1
            except Exception as e:
                errors += 1
                print(f"Request {i} failed: {e}")
                continue
            latencies.append((time.time() - t0) * 1000)

    total_time = time.time() - start_total

    print(f"\n=== Load Test Results ({n} requests) ===")
    print(f"Total time:      {total_time:.2f}s")
    print(f"Successful:      {n - errors}/{n}")
    print(f"Errors:          {errors}")
    print(f"Avg latency:     {statistics.mean(latencies):.1f}ms")
    print(f"p50 latency:     {statistics.median(latencies):.1f}ms")
    print(f"p95 latency:     {sorted(latencies)[int(len(latencies)*0.95)]:.1f}ms")
    print(f"p99 latency:     {sorted(latencies)[int(len(latencies)*0.99)]:.1f}ms")
    print(f"Max latency:     {max(latencies):.1f}ms")
    print(f"Req/sec:         {(n-errors)/total_time:.1f}")

if __name__ == "__main__":
    run_load_test(100)
