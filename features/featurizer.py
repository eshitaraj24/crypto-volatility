#!/usr/bin/env python3
"""
Kafka consumer that reads ticks.raw, computes windowed features,
publishes to ticks.features, and saves to Parquet.
"""

import argparse
import json
import logging
import os
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from kafka import KafkaConsumer, KafkaProducer

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC_IN = "ticks.raw"
TOPIC_OUT = "ticks.features"
WINDOW_SIZES = [10, 30, 60]  # seconds
SPIKE_HORIZON = 60  # seconds
PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


class WindowBuffer:
    """Maintains a time-based sliding window of ticks per product."""

    def __init__(self, max_seconds: int = 120):
        self.max_seconds = max_seconds
        self.ticks: deque = deque()  # list of dicts with 'ts', 'mid', 'bid', 'ask'

    def add(self, ts: float, mid: float, bid: float, ask: float):
        self.ticks.append({"ts": ts, "mid": mid, "bid": bid, "ask": ask})
        self._evict(ts)

    def _evict(self, now: float):
        while self.ticks and (now - self.ticks[0]["ts"]) > self.max_seconds:
            self.ticks.popleft()

    def window(self, seconds: int, now: float) -> list:
        cutoff = now - seconds
        return [t for t in self.ticks if t["ts"] >= cutoff]


def compute_features(buf: WindowBuffer, now: float, product_id: str) -> dict | None:
    """Compute all windowed features for a single tick."""
    w60 = buf.window(60, now)
    if len(w60) < 5:
        return None  # not enough data yet

    feat = {
        "ts": now,
        "product_id": product_id,
    }

    for w in WINDOW_SIZES:
        ticks = buf.window(w, now)
        if len(ticks) < 2:
            mids = [t["mid"] for t in w60[-2:]]
        else:
            mids = [t["mid"] for t in ticks]

        rets = np.diff(np.log(mids)) if len(mids) >= 2 else np.array([0.0])

        feat[f"ret_mean_{w}s"] = float(np.mean(rets))
        feat[f"ret_std_{w}s"] = float(np.std(rets)) if len(rets) > 1 else 0.0
        feat[f"ret_abs_{w}s"] = float(np.mean(np.abs(rets)))
        feat[f"tick_count_{w}s"] = len(ticks)

        spreads = [(t["ask"] - t["bid"]) / t["mid"] for t in ticks if t["mid"] > 0]
        feat[f"spread_mean_{w}s"] = float(np.mean(spreads)) if spreads else 0.0

        if len(ticks) >= 2:
            duration = ticks[-1]["ts"] - ticks[0]["ts"]
            feat[f"trade_intensity_{w}s"] = len(ticks) / max(duration, 1.0)
        else:
            feat[f"trade_intensity_{w}s"] = 0.0

    # Bid-ask imbalance using latest tick
    latest = buf.ticks[-1]
    mid = latest["mid"]
    bid = latest["bid"]
    ask = latest["ask"]
    feat["spread_bps"] = (ask - bid) / mid * 10_000 if mid > 0 else 0.0
    feat["mid_price"] = mid

    return feat


def featurize_records(records: list[dict]) -> pd.DataFrame:
    """
    Pure function: take a list of raw tick dicts, return feature DataFrame.
    Used by both live consumer and replay script.
    """
    buffers: dict[str, WindowBuffer] = defaultdict(
        lambda: WindowBuffer(max_seconds=130)
    )
    rows = []

    for rec in records:
        try:
            ts = pd.Timestamp(rec["ts"]).timestamp()
            mid = (float(rec["best_bid"]) + float(rec["best_ask"])) / 2
            bid = float(rec["best_bid"])
            ask = float(rec["best_ask"])
            pid = rec["product_id"]
        except (KeyError, ValueError, TypeError):
            continue

        buffers[pid].add(ts, mid, bid, ask)
        feat = compute_features(buffers[pid], ts, pid)
        if feat:
            rows.append(feat)

    return pd.DataFrame(rows)


def add_labels(df: pd.DataFrame, threshold: float | None = None) -> pd.DataFrame:
    """
    For each row, compute forward 60s rolling std of midprice returns.
    Label = 1 if sigma_future >= threshold, else 0.
    threshold=None means compute but don't assign labels yet.
    """
    df = df.sort_values("ts").copy()
    results = []

    for pid, grp in df.groupby("product_id"):
        grp = grp.sort_values("ts").copy()
        grp["future_vol"] = np.nan

        for i in range(len(grp)):
            t0 = grp.iloc[i]["ts"]
            horizon = grp[(grp["ts"] > t0) & (grp["ts"] <= t0 + SPIKE_HORIZON)]
            if len(horizon) >= 3:
                mids = horizon["mid_price"].values
                rets = np.diff(np.log(mids + 1e-12))
                grp.at[grp.index[i], "future_vol"] = float(np.std(rets))

        results.append(grp)

    df = pd.concat(results).sort_values("ts")

    if threshold is not None:
        df["label"] = (df["future_vol"] >= threshold).astype(int)

    return df


def run_live(topic_in: str, topic_out: str, output_path: str, max_msgs: int | None):
    consumer = KafkaConsumer(
        topic_in,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        auto_offset_reset="earliest",
        value_deserializer=lambda b: json.loads(b.decode()),
        consumer_timeout_ms=30_000,
        group_id="featurizer-v1",
    )
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode(),
    )

    buffers: dict[str, WindowBuffer] = defaultdict(
        lambda: WindowBuffer(max_seconds=130)
    )
    rows = []
    count = 0

    log.info("Featurizer listening on '%s' …", topic_in)

    for msg in consumer:
        rec = msg.value
        try:
            ts = pd.Timestamp(rec["ts"]).timestamp()
            mid = (float(rec["best_bid"]) + float(rec["best_ask"])) / 2
            bid = float(rec["best_bid"])
            ask = float(rec["best_ask"])
            pid = rec["product_id"]
        except (KeyError, ValueError):
            continue

        buffers[pid].add(ts, mid, bid, ask)
        feat = compute_features(buffers[pid], ts, pid)

        if feat:
            producer.send(topic_out, feat)
            rows.append(feat)
            count += 1
            if count % 100 == 0:
                log.info("Computed %d feature rows", count)

        if max_msgs and count >= max_msgs:
            break

    consumer.close()
    producer.flush()

    if rows:
        df = pd.DataFrame(rows)
        df.to_parquet(output_path, index=False)
        log.info("Saved %d rows to %s", len(df), output_path)
    else:
        log.warning("No feature rows computed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic_in", default=TOPIC_IN)
    parser.add_argument("--topic_out", default=TOPIC_OUT)
    parser.add_argument("--output", default=str(PROCESSED_DIR / "features.parquet"))
    parser.add_argument("--max_msgs", type=int, default=None)
    args = parser.parse_args()

    run_live(args.topic_in, args.topic_out, args.output, args.max_msgs)


if __name__ == "__main__":
    main()
