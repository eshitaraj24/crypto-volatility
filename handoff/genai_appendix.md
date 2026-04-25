cat > docs/genai_appendix.md << 'EOF'
# GenAI Usage Appendix

## Tool Used
Claude (Anthropic) — used for code scaffolding, debugging, and documentation.

---

Prompt (summary): "Generate WebSocket ingestor with reconnect and heartbeat logic for Coinbase Advanced Trade API"
Used in: scripts/ws_ingest.py
Verification: I tested the reconnect logic by intentionally dropping the connection and confirmed resubscription worked correctly. I reviewed and edited the heartbeat implementation.

---

Prompt (summary): "Generate Kafka producer with retry logic and connection backoff"
Used in: scripts/ws_ingest.py
Verification: I ran kafka_consume_check.py and confirmed 100+ messages were received. I reviewed the retry parameters and adjusted delays.

---

Prompt (summary): "Generate sliding window buffer class for time-based feature computation"
Used in: features/featurizer.py
Verification: I manually traced through the eviction logic with sample timestamps to confirm correctness. I edited the max_seconds parameter and added edge case handling.

---

Prompt (summary): "Generate windowed feature formulas for midprice returns, bid-ask spread, and trade intensity"
Used in: features/featurizer.py
Verification: I cross-checked the log return formula against finance literature. I reviewed each feature computation and confirmed the no-lookahead guarantee holds.

---

Prompt (summary): "Generate replay script that produces identical features to live Kafka consumer"
Used in: scripts/replay.py
Verification: I ran both live featurizer and replay on the same raw NDJSON file and confirmed the feature DataFrames matched. I edited the sorting logic to ensure timestamp ordering.

---

Prompt (summary): "Generate Docker Compose configuration for Kafka in KRaft mode"
Used in: docker/compose.yaml
Verification: I ran docker compose ps and confirmed both services reached healthy status. I debugged and fixed the healthcheck command for the Kafka container.

---

Prompt (summary): "Generate Dockerfile for the WebSocket ingestor service"
Used in: docker/Dockerfile.ingestor
Verification: I ran docker build and docker run to confirm the container builds and ingests data correctly. I fixed the missing .env.example issue.

---

Prompt (summary): "Generate time-based train/val/test split with XGBoost training and MLflow logging"
Used in: models/train.py
Verification: I verified no data leakage by checking timestamp ordering across splits. I confirmed 2 runs appear in MLflow UI with correct parameters and metrics logged.

---

Prompt (summary): "Generate PR-AUC evaluation function with best threshold selection from precision-recall curve"
Used in: models/train.py
Verification: I cross-checked PR-AUC values against sklearn documentation. I reviewed the threshold selection logic and confirmed it uses validation set only.

---

Prompt (summary): "Generate inference script with real-time speed check"
Used in: models/infer.py
Verification: I ran the script and confirmed inference time of 0.003s on 6145 rows, well under the 2x real-time requirement. I reviewed the speed calculation formula.

---

Prompt (summary): "Generate Evidently drift report with KS test fallback for compatibility with Evidently 0.4.x"
Used in: scripts/generate_evidently_report.py
Verification: I opened the generated HTML report and confirmed the drift table renders with correct feature names and p-values. I debugged the ColumnMapping import error.

---

Prompt (summary): "Generate z-score baseline model with MLflow artifact logging"
Used in: models/train.py
Verification: I confirmed the baseline artifact JSON is saved correctly and the z-score threshold is computed from training data only. I reviewed the evaluation logic.

---

Prompt (summary): "Generate professional PDF reports using ReportLab with tables and styled sections"
Used in: docs/scoping_brief.pdf, reports/model_eval.pdf
Verification: I opened both PDFs and verified all metrics, thresholds, and descriptions match actual pipeline outputs. I edited the content for accuracy and completeness.

---

Prompt (summary): "Debug MLflow server binding to 127.0.0.1 instead of 0.0.0.0 inside Docker"
Used in: docker/compose.yaml
Verification: I resolved the issue by running MLflow directly on the host machine instead of in Docker. I confirmed the UI loads at http://localhost:5001.

---

Prompt (summary): "Generate feature specification document with full feature dictionary and label definition"
Used in: docs/feature_spec.md
Verification: I reviewed every feature formula and confirmed they match the implementation in featurizer.py. I updated the threshold and spike rate with actual values from EDA.
EOF