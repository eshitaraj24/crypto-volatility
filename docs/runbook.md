# Runbook — Crypto Volatility AI Service

## Startup
```bash
# 1. Start infrastructure
docker compose -f docker/compose.yaml up -d

# 2. Start MLflow
mlflow server --backend-store-uri sqlite:///mlruns/mlflow.db \
  --default-artifact-root ./mlruns/artifacts --host 0.0.0.0 --port 5001

# 3. Start API
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000

# 4. Verify
curl http://localhost:8000/health
```

## Rollback to Baseline
```bash
# Stop API, restart with baseline variant
MODEL_VARIANT=baseline uvicorn api.main:app --host 0.0.0.0 --port 8000

# Verify
curl http://localhost:8000/version  # should show "variant": "baseline"
```

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| API won't start | Missing venv packages | source venv/bin/activate && pip install -r requirements.txt |
| Kafka not connecting | Container stopped | docker compose -f docker/compose.yaml up -d kafka |
| MLflow not accessible | Server not running | Run mlflow server command above |
| Prometheus target DOWN | API not running | Start uvicorn |
| Grafana no data | Prometheus not scraping | Check http://localhost:9090/targets |
| High latency | Too many workers busy | Restart uvicorn with --workers 4 |

## Recovery Steps
1. Check all services: `docker compose -f docker/compose.yaml ps`
2. Check API health: `curl http://localhost:8000/health`
3. Check Prometheus: `http://localhost:9090/targets`
4. Check Grafana: `http://localhost:3000`
5. If model degraded: switch to baseline with MODEL_VARIANT=baseline
