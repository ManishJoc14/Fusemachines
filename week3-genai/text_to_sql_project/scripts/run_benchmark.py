from __future__ import annotations

import asyncio
import csv
import json
import sys
import os
from pathlib import Path
from typing import Any

# Add project root to sys.path to allow imports when running from project root or scripts directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agent.engine import TextToSQLAgent
from app.core.logging import logger
from app.core.config import settings
from app.db.executor import SQLExecutor


ROOT = Path(__file__).resolve().parents[1]
print(f"Using DATABASE_URL: {settings.DATABASE_URL}")
DATASET_PATH = ROOT / "benchmark" / "benchmark_dataset.json"
OUTPUT_DIR = ROOT / "evaluation"
JSON_OUTPUT_PATH = OUTPUT_DIR / "benchmark_results.json"
CSV_OUTPUT_PATH = OUTPUT_DIR / "benchmark_results.csv"


class BenchmarkRunner:
    def __init__(
        self, agent: TextToSQLAgent | None = None, executor: SQLExecutor | None = None
    ) -> None:
        self.agent = agent or TextToSQLAgent()
        self.executor = executor or SQLExecutor()

    async def _execute_expected_sql(self, sql: str) -> Any:
        rows = await self.executor.run_sql(sql)
        if len(rows) == 1 and len(rows[0]) == 1:
            return next(iter(rows[0].values()))
        return rows

    async def evaluate(self) -> dict[str, Any]:
        if not DATASET_PATH.exists():
            logger.error("Dataset not found at %s", DATASET_PATH)
            return {"error": "Dataset not found"}

        dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        records: list[dict[str, Any]] = []

        for item in dataset:
            question = item["question"]
            logger.info("Benchmark question: %s", question)

            agent_response = await self.agent.run(question)

            expected_result: Any = None
            expected_error: str | None = None
            try:
                expected_result = await self._execute_expected_sql(item["sql"])
            except Exception as exc:
                expected_error = str(exc)

            generated_result = _canonicalize(agent_response.result)
            expected_result = _canonicalize(expected_result)

            result_match = (
                expected_error is None
                and agent_response.status == "success"
                and generated_result == expected_result
            )

            records.append(
                {
                    "question": question,
                    "expected_sql": item["sql"],
                    "generated_sql": agent_response.sql,
                    "status": agent_response.status,
                    "attempts": agent_response.attempts,
                    "execution_ms": agent_response.execution_ms,
                    "result_match": result_match,
                    "error": agent_response.error,
                    "expected_error": expected_error,
                    "summary": agent_response.summary,
                }
            )

        total = len(records)
        success_count = sum(1 for record in records if record["status"] == "success")
        result_match_count = sum(1 for record in records if record["result_match"])
        retry_count = sum(
            1 for record in records if record["attempts"] and record["attempts"] > 1
        )
        latencies = [
            record["execution_ms"]
            for record in records
            if record["execution_ms"] is not None
        ]

        report = {
            "metrics": {
                "total_questions": total,
                "success_rate": success_count / total if total else 0,
                "result_match_rate": result_match_count / total if total else 0,
                "retry_rate": retry_count / total if total else 0,
                "average_latency_ms": sum(latencies) / len(latencies)
                if latencies
                else 0,
            },
            "results": records,
        }

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        JSON_OUTPUT_PATH.write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        with CSV_OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
            fieldnames = [
                "question",
                "expected_sql",
                "generated_sql",
                "status",
                "attempts",
                "execution_ms",
                "result_match",
                "error",
                "expected_error",
                "summary",
            ]
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

        return report


def _canonicalize(value: Any) -> Any:
    if isinstance(value, list):
        if value and all(isinstance(item, dict) for item in value):
            return sorted(
                json.dumps(item, sort_keys=True, ensure_ascii=False) for item in value
            )
        return value

    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)

    return value


if __name__ == "__main__":
    result = asyncio.run(BenchmarkRunner().evaluate())
    if "metrics" in result:
        print(json.dumps(result["metrics"], indent=2))
    else:
        print(result)
