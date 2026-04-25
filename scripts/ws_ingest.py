#!/usr/bin/env python3
"""
Coinbase Advanced Trade WebSocket ingestor.
Publishes ticks to Kafka topic ticks.raw and optionally mirrors to NDJSON files.
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import websockets
from dotenv import load_dotenv
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

COINBASE_WS_URL = os.getenv("COINBASE_WS_URL", "wss://advanced-trade-ws.coinbase.com")
KAFKA_BOOTSTRAP  = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC_RAW        = "ticks.raw"
RAW_DIR          = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Global stop flag
stop_event = asyncio.Event()


def get_producer(retries: int = 10, delay: float = 3.0) -> KafkaProducer:
    for attempt in range(retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
                retries=5,
            )
            log.info("Kafka producer connected to %s", KAFKA_BOOTSTRAP)
            return producer
        except NoBrokersAvailable:
            log.warning("Kafka not ready, retry %d/%d in %.0fs…", attempt + 1, retries, delay)
            time.sleep(delay)
    raise RuntimeError("Could not connect to Kafka after %d retries" % retries)


def build_subscribe_msg(pairs: list[str]) -> dict:
    return {
        "type": "subscribe",
        "product_ids": pairs,
        "channel": "ticker",
    }


def build_heartbeat_msg() -> dict:
    return {
        "type": "subscribe",
        "product_ids": [],
        "channel": "heartbeats",
    }


async def send_heartbeat(ws, interval: float = 10.0):
    """Send periodic heartbeat pings."""
    while not stop_event.is_set():
        try:
            await ws.ping()
            log.debug("Heartbeat ping sent")
        except Exception:
            break
        await asyncio.sleep(interval)


async def ingest(pairs: list[str], minutes: float, producer: KafkaProducer, mirror: bool):
    deadline = time.time() + minutes * 60
    raw_file = None

    if mirror:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        raw_path = RAW_DIR / f"ticks_{ts}.ndjson"
        raw_file = open(raw_path, "w")
        log.info("Mirroring to %s", raw_path)

    msg_count = 0
    subscribe_msg = build_subscribe_msg(pairs)

    while not stop_event.is_set() and time.time() < deadline:
        try:
            log.info("Connecting to %s …", COINBASE_WS_URL)
            async with websockets.connect(
                COINBASE_WS_URL,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
            ) as ws:
                await ws.send(json.dumps(subscribe_msg))
                await ws.send(json.dumps(build_heartbeat_msg()))
                log.info("Subscribed to %s", pairs)

                # Start heartbeat task
                hb_task = asyncio.create_task(send_heartbeat(ws))

                try:
                    while not stop_event.is_set() and time.time() < deadline:
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
                        except asyncio.TimeoutError:
                            log.warning("No message in 30s, reconnecting…")
                            break

                        msg = json.loads(raw)
                        msg_type = msg.get("channel", msg.get("type", ""))

                        if msg_type == "ticker":
                            for event in msg.get("events", []):
                                for tick in event.get("tickers", []):
                                    record = {
                                        "ts": datetime.now(timezone.utc).isoformat(),
                                        "product_id": tick.get("product_id"),
                                        "price": float(tick.get("price", 0)),
                                        "best_bid": float(tick.get("best_bid", 0)),
                                        "best_ask": float(tick.get("best_ask", 0)),
                                        "volume_24h": float(tick.get("volume_24h", 0)),
                                    }
                                    producer.send(TOPIC_RAW, record)
                                    if raw_file:
                                        raw_file.write(json.dumps(record) + "\n")
                                    msg_count += 1
                                    if msg_count % 50 == 0:
                                        log.info("Published %d ticks", msg_count)

                        elif msg_type == "heartbeats":
                            log.debug("Heartbeat received")

                finally:
                    hb_task.cancel()

        except (websockets.ConnectionClosed, ConnectionError, OSError) as e:
            log.warning("Connection lost: %s — reconnecting in 3s…", e)
            await asyncio.sleep(3)
        except Exception as e:
            log.error("Unexpected error: %s", e, exc_info=True)
            await asyncio.sleep(3)

    producer.flush()
    if raw_file:
        raw_file.close()
    log.info("Ingestion complete. Total ticks published: %d", msg_count)
    return msg_count


def main():
    parser = argparse.ArgumentParser(description="Coinbase WS Ingestor")
    parser.add_argument("--pair", nargs="+", default=["BTC-USD"], help="Trading pairs")
    parser.add_argument("--minutes", type=float, default=15.0, help="Run duration in minutes")
    parser.add_argument("--no-mirror", action="store_true", help="Don't write NDJSON files")
    args = parser.parse_args()

    def _shutdown(sig, frame):
        log.info("Caught signal %s, shutting down…", sig)
        stop_event.set()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    producer = get_producer()
    asyncio.run(ingest(args.pair, args.minutes, producer, mirror=not args.no_mirror))


if __name__ == "__main__":
    main()