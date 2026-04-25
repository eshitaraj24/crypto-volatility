#!/usr/bin/env python3
"""
Validates that messages are flowing in a Kafka topic.
Exits 0 if --min messages seen within --timeout seconds, else exits 1.
"""

import argparse
import json
import logging
import sys
import time

from kafka import KafkaConsumer

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Kafka Consumer Sanity Check")
    parser.add_argument("--topic", default="ticks.raw")
    parser.add_argument("--min", type=int, default=100, dest="min_msgs")
    parser.add_argument("--timeout", type=int, default=60, help="Max seconds to wait")
    parser.add_argument("--bootstrap", default="localhost:9092")
    args = parser.parse_args()

    consumer = KafkaConsumer(
        args.topic,
        bootstrap_servers=args.bootstrap,
        auto_offset_reset="earliest",
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        consumer_timeout_ms=args.timeout * 1000,
        group_id=f"check-{int(time.time())}",
    )

    count = 0
    start = time.time()
    log.info("Listening on topic '%s' for up to %ds …", args.topic, args.timeout)

    for msg in consumer:
        count += 1
        record = msg.value
        if count <= 3 or count % 100 == 0:
            log.info("[%d] offset=%d  %s", count, msg.offset, record)
        if count >= args.min_msgs:
            break

    elapsed = time.time() - start
    consumer.close()

    if count >= args.min_msgs:
        log.info("✅ SUCCESS: %d messages received in %.1fs", count, elapsed)
        sys.exit(0)
    else:
        log.error(
            "❌ FAIL: only %d/%d messages in %.1fs", count, args.min_msgs, elapsed
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
