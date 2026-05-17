#!/usr/bin/env python3
"""Run benchmark against local Text-to-SQL agent HTTP API.

Usage:
  python -m scripts.run_benchmark --dataset benchmark/benchmark_dataset.json --out reports/benchmark_results.csv

The script posts each question to POST /agent/sql on the provided base URL and records the response.
It computes simple metrics (SQL exact-match rate, execution success rate, retry stats) and writes CSV + summary JSON.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import httpx


def normalize_sql(s: str) -> str:
    if s is None:
        return ""
    return " ".join(s.strip().lower().replace('\n', ' ').split())


def run(dataset_path: Path, out_path: Path, base_url: str, timeout: float = 30.0) -> int:
    with dataset_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    csv_file = out_path

    rows: list[dict[str, Any]] = []

    client = httpx.Client(base_url=base_url, timeout=timeout)

    for idx, entry in enumerate(data, start=1):
        question = entry.get("question")
        gold_sql = entry.get("sql") or ""

        print(f"[{idx}/{len(data)}] Query: {question}")
        try:
            resp = client.post("/agent/sql", json={"question": question})
            resp.raise_for_status()
            jr = resp.json()
        except Exception as exc:
            print(f"  Request failed: {exc}")
            rows.append(
                {
                    "qid": idx,
                    "question": question,
                    "gold_sql": gold_sql,
                    "gen_sql": "",
                    "sql_match": 0,
                    "status": "request_failed",
                    "error": str(exc),
                }
            )
            continue

        gen_sql = jr.get("sql") or ""
        status = jr.get("status")
        attempts = jr.get("attempts") or 0
        result = jr.get("result")
        result_count = None
        if isinstance(result, list):
            result_count = len(result)
        elif result is None:
            result_count = 0
        else:
            result_count = 1

        sql_match = 1 if normalize_sql(gen_sql) == normalize_sql(gold_sql) else 0

        rows.append(
            {
                "qid": idx,
                "question": question,
                "gold_sql": gold_sql,
                "gen_sql": gen_sql,
                "sql_match": sql_match,
                "status": status,
                "attempts": attempts,
                "result_count": result_count,
                "error": jr.get("error"),
            }
        )

    # write CSV
    keys = [
        "qid",
        "question",
        "gold_sql",
        "gen_sql",
        "sql_match",
        "status",
        "attempts",
        "result_count",
        "error",
    ]
    with csv_file.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # summary metrics
    total = len(rows)
    sql_matches = sum(r.get("sql_match", 0) for r in rows)
    exec_success = sum(1 for r in rows if r.get("status") == "success")
    avg_attempts = sum(r.get("attempts", 0) for r in rows) / total if total else 0

    summary = {
        "total_queries": total,
        "sql_exact_match_rate": sql_matches / total if total else 0,
        "execution_success_rate": exec_success / total if total else 0,
        "average_attempts": avg_attempts,
    }

    summary_path = out_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\nBenchmark complete")
    print(json.dumps(summary, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", required=True, help="Path to benchmark dataset JSON file")
    p.add_argument("--out", required=True, help="CSV output path for results")
    p.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL of FastAPI service")
    p.add_argument("--timeout", type=float, default=100.0, help="HTTP timeout seconds")
    args = p.parse_args(argv)

    dataset_path = Path(args.dataset)
    out_path = Path(args.out)

    if not dataset_path.exists():
        print(f"Dataset not found: {dataset_path}")
        return 2

    return run(dataset_path, out_path, args.base_url, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
