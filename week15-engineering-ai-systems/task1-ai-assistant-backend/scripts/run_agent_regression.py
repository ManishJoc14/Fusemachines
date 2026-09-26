from __future__ import annotations

import json
from pathlib import Path

import mlflow
import pandas as pd
from evidently import Dataset, Report
from evidently.descriptors import LLMJudge
from evidently.llm.options import OpenAIOptions
from evidently.llm.templates import BinaryClassificationPromptTemplate
from evidently.metrics import InListValueCount
from evidently.tests import gte, is_in

from app.core.config import PROJECT_ROOT, get_settings

MLOPS_DIRECTORY = PROJECT_ROOT / "evals" / "mlops"
GOLDEN_PATH = MLOPS_DIRECTORY / "golden_responses.json"
COMPARISON_PATH = MLOPS_DIRECTORY / "prompt_comparison.csv"
REPORT_DIRECTORY = MLOPS_DIRECTORY / "regression"
TRACKING_URI = f"sqlite:///{(PROJECT_ROOT / 'mlflow.db').as_posix()}"
PROMOTION_THRESHOLD = 0.75


def load_regression_rows() -> pd.DataFrame:
    golden = {
        item["case_id"]: item["reference_answer"]
        for item in json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    }
    rows: list[dict[str, str]] = []
    for trace_path in sorted((MLOPS_DIRECTORY / "runs").glob("*/traces/*.json")):
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        case_id = str(trace["case_id"])
        question = str(trace["question"])
        response = str(trace["answer"])
        reference = golden[case_id]
        rows.append(
            {
                "prompt_version": trace_path.parents[1].name,
                "case_id": case_id,
                "question": question,
                "reference": reference,
                "response": response,
                "correctness_input": (
                    f"QUESTION:\n{question}\n\nREFERENCE:\n{reference}\n\n"
                    f"RESPONSE:\n{response}"
                ),
                "relevance_input": f"QUESTION:\n{question}\n\nRESPONSE:\n{response}",
            }
        )
    if not rows:
        raise FileNotFoundError(
            "No prompt traces found. Run "
            "`python -m scripts.run_prompt_experiments` first."
        )
    return pd.DataFrame(rows)


def build_judges(model: str) -> list[LLMJudge]:
    correctness_template = BinaryClassificationPromptTemplate(
        criteria=(
            "The text contains a QUESTION, approved REFERENCE, and candidate "
            "RESPONSE. Classify correct only when the response preserves the key "
            "reference information and does not contradict it."
        ),
        target_category="correct",
        non_target_category="incorrect",
        include_reasoning=True,
    )
    relevance_template = BinaryClassificationPromptTemplate(
        criteria=(
            "The text contains a QUESTION and RESPONSE. Classify relevant only "
            "when the response directly addresses the question or asks a necessary "
            "focused clarification. Empty or off-topic responses are irrelevant."
        ),
        target_category="relevant",
        non_target_category="irrelevant",
        include_reasoning=True,
    )
    return [
        LLMJudge(
            provider="openai",
            model=model,
            template=correctness_template,
            input_column="correctness_input",
            alias="correctness",
            tests=[is_in(["correct"])],
        ),
        LLMJudge(
            provider="openai",
            model=model,
            template=relevance_template,
            input_column="relevance_input",
            alias="relevance",
            tests=[is_in(["relevant"])],
        ),
    ]


def version_pass_rates(evaluated: pd.DataFrame) -> dict[str, float]:
    rates: dict[str, float] = {}
    for version, rows in evaluated.groupby("prompt_version"):
        checks = pd.concat(
            [rows["correctness"].eq("correct"), rows["relevance"].eq("relevant")]
        )
        rates[str(version)] = float(checks.mean())
    return rates


def write_summary(evaluated: pd.DataFrame, rates: dict[str, float]) -> Path:
    lines = [
        "# Agent Regression Results",
        "",
        "The Evidently LLM judge checks reference-based correctness and answer "
        "relevance.",
        "",
        "| Prompt version | Checks passed | Promotion decision |",
        "| --- | ---: | --- |",
    ]
    for version, rate in rates.items():
        decision = "pass" if rate >= PROMOTION_THRESHOLD else "block"
        lines.append(f"| {version} | {rate:.0%} | {decision} |")

    lines.extend(["", "## Failed cases", ""])
    failed = evaluated[
        (evaluated["correctness"] != "correct") | (evaluated["relevance"] != "relevant")
    ]
    if failed.empty:
        lines.append("- None.")
    else:
        for row in failed.to_dict(orient="records"):
            lines.append(
                f"- **{row['prompt_version']} / {row['case_id']}**: "
                f"correctness={row['correctness']}, relevance={row['relevance']}. "
                f"Judge notes: {row['correctness reasoning']}"
            )

    lines.extend(
        [
            "",
            "## Judge sanity check",
            "",
            "The verdicts must still be reviewed with the saved candidate, reference, "
            "and reasoning columns. The judge is a model and can be wrong; its result "
            "is a regression signal, not an unquestionable ground truth.",
        ]
    )
    summary_path = REPORT_DIRECTORY / "summary.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_path


def log_results_to_existing_runs(rates: dict[str, float]) -> None:
    comparison = pd.read_csv(COMPARISON_PATH)
    mlflow.set_tracking_uri(TRACKING_URI)
    for row in comparison.to_dict(orient="records"):
        version = str(row["prompt_version"])
        run_id = str(row["run_id"])
        with mlflow.start_run(run_id=run_id):
            mlflow.log_metric("pct_tests_passed", rates[version])
            mlflow.log_artifacts(str(REPORT_DIRECTORY), artifact_path="regression")


def run_regression() -> dict[str, float]:
    settings = get_settings()
    if settings.hf_token is None:
        raise ValueError("HF_TOKEN is required for the Evidently LLM judge")

    # Step 1: Evaluate the same fixed cases and references for every prompt version.
    source_rows = load_regression_rows()
    options = OpenAIOptions(
        api_key=settings.hf_token.get_secret_value(),
        api_url=str(settings.hf_base_url),
    )
    evaluated_dataset = Dataset.from_pandas(
        source_rows,
        descriptors=build_judges(settings.hf_fallback_model),
        options=options,
    )
    evaluated = evaluated_dataset.as_dataframe()

    # Step 2: Run two explicit suite-level checks and save the Evidently report.
    report = Report(
        [
            InListValueCount(
                column="correctness",
                values=["correct"],
                share_tests=[gte(PROMOTION_THRESHOLD)],
            ),
            InListValueCount(
                column="relevance",
                values=["relevant"],
                share_tests=[gte(PROMOTION_THRESHOLD)],
            ),
        ],
        include_tests=True,
    )
    snapshot = report.run(current_data=evaluated_dataset)

    # Step 3: Export verdicts, reasoning, HTML, JSON, and a human review summary.
    REPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    evaluated.to_csv(REPORT_DIRECTORY / "verdicts.csv", index=False)
    snapshot.save_html(str(REPORT_DIRECTORY / "regression_report.html"))
    snapshot.save_json(str(REPORT_DIRECTORY / "regression_report.json"))
    rates = version_pass_rates(evaluated)
    summary_path = write_summary(evaluated, rates)

    # Step 4: Add the regression signal and evidence to each MLflow comparison run.
    log_results_to_existing_runs(rates)
    print(summary_path.read_text(encoding="utf-8"))
    return rates


def main() -> None:
    run_regression()


if __name__ == "__main__":
    main()
