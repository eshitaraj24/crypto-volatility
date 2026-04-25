#!/usr/bin/env python3
"""
Replay raw NDJSON files through the feature pipeline.
Output must be identical to live featurizer for the same inputs.
"""

import argparse
import glob
import json
import logging
from pathlib import Path

import pandas as pd

from features.featurizer import featurize_records, add_labels

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw",   nargs="+", required=True, help="Glob pattern or list of NDJSON files")
    parser.add_argument("--out",   default="data/processed/features.parquet")
    parser.add_argument("--threshold", type=float, default=None)
    args = parser.parse_args()

    # Expand globs
    files = []
    for pattern in args.raw:
        files.extend(glob.glob(pattern))
    files = sorted(set(files))

    if not files:
        log.error("No files matched: %s", args.raw)
        return

    # Load all records
    records = []
    for fpath in files:
        log.info("Loading %s", fpath)
        with open(fpath) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    log.info("Loaded %d raw records from %d files", len(records), len(files))

    # Sort by timestamp before processing (same as live)
    records.sort(key=lambda r: r.get("ts", ""))

    df = featurize_records(records)

    if df.empty:
        log.error("No features computed — check raw data format")
        return

    if args.threshold:
        df = add_labels(df, threshold=args.threshold)
        log.info("Labels added with threshold=%.6f", args.threshold)
    else:
        df = add_labels(df, threshold=None)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    log.info("Saved %d rows to %s", len(df), out)
    print(df.describe())


if __name__ == "__main__":
    main()