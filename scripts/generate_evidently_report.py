#!/usr/bin/env python3
"""Generate Evidently data quality + drift report - compatible with Evidently 0.7.x"""

import argparse
import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", default="data/processed/features.parquet")
    parser.add_argument("--out_dir", default="reports/evidently")
    parser.add_argument("--report_name", default="drift_report")
    parser.add_argument("--split_pct", type=float, default=0.5)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(args.features)
    df = df.sort_values("ts").reset_index(drop=True)

    drop_cols = ["ts", "product_id", "label", "future_vol"]
    num_cols = [
        c
        for c in df.columns
        if c not in drop_cols and df[c].dtype in ["float64", "float32", "int64"]
    ]

    split = int(len(df) * args.split_pct)
    reference = df[num_cols].iloc[:split].copy()
    current = df[num_cols].iloc[split:].copy()

    log.info("Reference: %d rows | Current: %d rows", len(reference), len(current))

    try:
        # Try Evidently 0.7.x API
        from evidently.report import Report
        from evidently.metric_preset import DataDriftPreset, DataQualityPreset

        report = Report(
            metrics=[
                DataQualityPreset(),
                DataDriftPreset(),
            ]
        )
        report.run(reference_data=reference, current_data=current)

        html_path = out_dir / f"{args.report_name}.html"
        json_path = out_dir / f"{args.report_name}.json"
        report.save_html(str(html_path))
        report.save_json(str(json_path))
        log.info("Report saved → %s", html_path)

    except Exception as e:
        log.warning("Standard API failed (%s), trying legacy API...", e)
        try:
            from evidently.test_suite import TestSuite
            from evidently.tests import (
                TestNumberOfMissingValues,
                TestNumberOfDriftedColumns,
            )

            suite = TestSuite(
                tests=[
                    TestNumberOfMissingValues(),
                    TestNumberOfDriftedColumns(),
                ]
            )
            suite.run(reference_data=reference, current_data=current)
            html_path = out_dir / f"{args.report_name}.html"
            suite.save_html(str(html_path))
            log.info("Report saved → %s", html_path)

        except Exception as e2:
            log.warning("Legacy API also failed (%s), generating manual report...", e2)

            # Manual fallback - generate a simple HTML report
            from scipy import stats

            rows = []
            for col in num_cols:
                ref_vals = reference[col].dropna()
                cur_vals = current[col].dropna()
                if len(ref_vals) > 10 and len(cur_vals) > 10:
                    stat, pval = stats.ks_2samp(ref_vals, cur_vals)
                    drifted = pval < 0.05
                    rows.append(
                        {
                            "feature": col,
                            "ref_mean": ref_vals.mean(),
                            "cur_mean": cur_vals.mean(),
                            "ks_stat": stat,
                            "p_value": pval,
                            "drifted": drifted,
                        }
                    )

            drift_df = pd.DataFrame(rows)
            n_drifted = drift_df["drifted"].sum()

            html = f"""<!DOCTYPE html>
<html>
<head><title>Drift Report</title>
<style>
body {{ font-family: Arial; margin: 40px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background-color: #4CAF50; color: white; }}
.drifted {{ background-color: #ffcccc; }}
.ok {{ background-color: #ccffcc; }}
</style>
</head>
<body>
<h1>Data Drift Report — Milestone 2</h1>
<p>Reference: first {split} rows | Current: last {len(df)-split} rows</p>
<p>Features drifted: <b>{n_drifted}/{len(drift_df)}</b> (KS test, p &lt; 0.05)</p>
<table>
<tr><th>Feature</th><th>Ref Mean</th><th>Cur Mean</th><th>KS Stat</th><th>P-Value</th><th>Drifted</th></tr>
"""
            for _, row in drift_df.iterrows():
                css = "drifted" if row["drifted"] else "ok"
                html += f"""<tr class="{css}">
<td>{row['feature']}</td>
<td>{row['ref_mean']:.6f}</td>
<td>{row['cur_mean']:.6f}</td>
<td>{row['ks_stat']:.4f}</td>
<td>{row['p_value']:.4f}</td>
<td>{'YES' if row['drifted'] else 'NO'}</td>
</tr>"""

            html += "</table></body></html>"

            html_path = out_dir / f"{args.report_name}.html"
            with open(html_path, "w") as f:
                f.write(html)

            json_path = out_dir / f"{args.report_name}.json"
            drift_df.to_json(json_path, orient="records", indent=2)

            log.info("Manual drift report saved → %s", html_path)
            log.info("Drifted features: %d/%d", n_drifted, len(drift_df))


if __name__ == "__main__":
    main()
