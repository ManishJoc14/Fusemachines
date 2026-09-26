from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from app.assistant.agent import AssistantAgent
from app.assistant.prompts import load_system_prompt
from app.core.config import PROJECT_ROOT, Settings, get_settings
from app.llm.client import LLMClient
from scripts.evaluate_agent import (
    CASES_PATH,
    EvaluationResult,
    build_registry,
    evaluate_case,
    load_cases,
)

TRACKING_URI = f"sqlite:///{(PROJECT_ROOT / 'mlflow.db').as_posix()}"
EXPERIMENT_NAME = "agent-prompt-comparison"
OUTPUT_DIRECTORY = PROJECT_ROOT / "evals" / "mlops"


@dataclass(frozen=True, slots=True)
class ExperimentConfiguration:
    prompt_version: str
    temperature: float
    max_iterations: int
    diagnosis_from_previous_version: str


CONFIGURATIONS = [
    ExperimentConfiguration(
        prompt_version="prompt_v1",
        temperature=0.2,
        max_iterations=3,
        diagnosis_from_previous_version="Baseline configuration.",
    ),
    ExperimentConfiguration(
        prompt_version="prompt_v2",
        temperature=0.2,
        max_iterations=4,
        diagnosis_from_previous_version=(
            "Adds independent-source verification, conflict handling, and failed-tool "
            "rules because the baseline can stop after one observation."
        ),
    ),
    ExperimentConfiguration(
        prompt_version="prompt_v3",
        temperature=0.1,
        max_iterations=5,
        diagnosis_from_previous_version=(
            "Adds adaptive stopping, focused clarification, sequential evidence calls, "
            "and recovery because fixed two-source rules can over-search or mishandle "
            "ambiguous and unavailable evidence."
        ),
    ),
]


def aggregate_metrics(results: list[EvaluationResult]) -> dict[str, float]:
    count = len(results)
    if count == 0:
        raise ValueError("At least one evaluation result is required")

    return {
        "task_completion_rate": sum(item.completed for item in results) / count,
        "tool_correctness_rate": (
            sum(item.tool_calls_correct for item in results) / count
        ),
        "average_iterations": sum(item.iterations for item in results) / count,
        "average_tool_calls": sum(item.tool_calls for item in results) / count,
        "average_tokens": sum(item.total_tokens for item in results) / count,
        "total_tokens": float(sum(item.total_tokens for item in results)),
        "hard_failures": float(
            sum(item.failure_class == "hard failure" for item in results)
        ),
        "soft_failures": float(
            sum("soft failure" in item.failure_class for item in results)
        ),
    }


def write_run_artifacts(
    configuration: ExperimentConfiguration,
    results: list[EvaluationResult],
    metrics: dict[str, float],
) -> Path:
    run_directory = OUTPUT_DIRECTORY / "runs" / configuration.prompt_version
    traces_directory = run_directory / "traces"
    traces_directory.mkdir(parents=True, exist_ok=True)

    for result in results:
        trace_path = traces_directory / f"{result.case_id}.json"
        trace_path.write_text(
            json.dumps(asdict(result), indent=2),
            encoding="utf-8",
        )

    failed = [result for result in results if not result.completed]
    diagnosis_lines = [
        f"# {configuration.prompt_version} diagnosis",
        "",
        configuration.diagnosis_from_previous_version,
        "",
    ]
    if failed:
        diagnosis_lines.extend(
            f"- **{result.case_id}:** {result.notes}" for result in failed
        )
    else:
        diagnosis_lines.append("- All controlled evaluation cases completed.")

    (run_directory / "diagnosis.md").write_text(
        "\n".join(diagnosis_lines) + "\n",
        encoding="utf-8",
    )
    (run_directory / "metrics.json").write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )
    return run_directory


async def run_configuration(
    base_settings: Settings,
    configuration: ExperimentConfiguration,
) -> tuple[dict[str, float], str]:
    import mlflow

    settings = base_settings.model_copy(
        update={
            "agent_prompt_version": configuration.prompt_version,
            "llm_temperature": configuration.temperature,
            "llm_max_tool_iterations": configuration.max_iterations,
        }
    )
    client = LLMClient(settings)
    agent = AssistantAgent(client, build_registry(), settings)
    try:
        results = [await evaluate_case(agent, case) for case in load_cases(CASES_PATH)]
    finally:
        await client.close()

    metrics = aggregate_metrics(results)
    run_directory = write_run_artifacts(configuration, results, metrics)
    prompt_path = (
        PROJECT_ROOT
        / "app"
        / "assistant"
        / "prompt_versions"
        / f"{configuration.prompt_version}.txt"
    )
    prompt_text = load_system_prompt(configuration.prompt_version)

    with mlflow.start_run(run_name=configuration.prompt_version) as active_run:
        mlflow.log_params(
            {
                "prompt_version": configuration.prompt_version,
                "prompt_sha256": hashlib.sha256(prompt_text.encode()).hexdigest(),
                "model": settings.hf_model,
                "fallback_model": settings.hf_fallback_model,
                "temperature": configuration.temperature,
                "top_p": settings.llm_top_p,
                "max_iterations": configuration.max_iterations,
                "retrieval_top_k": settings.rag_retrieval_top_k,
                "candidate_top_k": settings.rag_candidate_top_k,
                "chunk_size": settings.rag_chunk_size,
            }
        )
        mlflow.log_metrics(metrics)
        mlflow.log_artifact(str(prompt_path), artifact_path="prompt")
        mlflow.log_artifact(str(CASES_PATH), artifact_path="evaluation")
        mlflow.log_artifacts(str(run_directory), artifact_path="evaluation")
        return metrics, active_run.info.run_id


def export_comparison(rows: list[dict[str, str | float]]) -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    comparison_path = OUTPUT_DIRECTORY / "prompt_comparison.csv"
    with comparison_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Prompt Experiment Comparison",
        "",
        "| Version | Completion | Tool correctness | Avg iterations | Avg tokens |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['prompt_version']} | "
            f"{float(row['task_completion_rate']):.0%} | "
            f"{float(row['tool_correctness_rate']):.0%} | "
            f"{float(row['average_iterations']):.2f} | "
            f"{float(row['average_tokens']):.0f} |"
        )
    (OUTPUT_DIRECTORY / "prompt_comparison.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


async def run_experiments() -> None:
    import mlflow

    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
    base_settings = get_settings()
    comparison_rows: list[dict[str, str | float]] = []

    for configuration in CONFIGURATIONS:
        metrics, run_id = await run_configuration(base_settings, configuration)
        comparison_rows.append(
            {
                "prompt_version": configuration.prompt_version,
                "run_id": run_id,
                **metrics,
            }
        )

    export_comparison(comparison_rows)
    print((OUTPUT_DIRECTORY / "prompt_comparison.md").read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(
        description="Compare all versioned agent prompts in MLflow"
    ).parse_args()


def main() -> None:
    parse_args()
    asyncio.run(run_experiments())


if __name__ == "__main__":
    main()
