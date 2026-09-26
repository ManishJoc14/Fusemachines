from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import mlflow
import pandas as pd
from evidently import Report
from evidently.metrics import MeanValue, ValueDrift
from evidently.presets import DataDriftPreset
from evidently.tests import gte, lte
from sklearn.model_selection import train_test_split

from telco_churn.config import (
    MLFLOW_MONITORING_EXPERIMENT_NAME,
    MLFLOW_TRACKING_URI,
    PROCESSED_DATA_DIR,
    REPORTS_DIR,
)
from telco_churn.dataset import IDENTIFIER_COLUMN, TARGET_COLUMN, load_dataset

DRIFT_REPORT_DIR = REPORTS_DIR / "drift"
DRIFT_THRESHOLD = 0.1


@dataclass(frozen=True)
class DriftSummary:
    reference_rows: int
    current_rows: int
    drifted_columns: int
    monthly_charges_reference_mean: float
    monthly_charges_current_mean: float
    monthly_charges_mean_shift: float
    monthly_charges_drift_score: float
    contract_month_to_month_reference_share: float
    contract_month_to_month_current_share: float
    contract_drift_score: float
    churn_reference_rate: float
    churn_current_rate: float
    churn_rate_shift: float
    churn_drift_score: float


def create_monitoring_sets(
    dataset: pd.DataFrame,
    *,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create the assignment's 70/30 reference and synthetic-current datasets."""

    reference, current = train_test_split(
        dataset.drop(columns=[IDENTIFIER_COLUMN]),
        test_size=0.3,
        random_state=random_state,
        stratify=dataset[TARGET_COLUMN],
    )
    return reference.reset_index(drop=True), current.reset_index(drop=True)


def inject_synthetic_drift(
    current: pd.DataFrame,
    *,
    random_state: int = 42,
) -> pd.DataFrame:
    """Inject deterministic numeric, categorical, and target drift."""

    drifted = current.copy()

    # Step 1: Shift a production billing feature by a visible amount.
    drifted["MonthlyCharges"] = (drifted["MonthlyCharges"] + 20).clip(upper=150)

    # Step 2: Make month-to-month contracts much more common.
    contract_indexes = drifted.sample(frac=0.9, random_state=random_state).index
    drifted.loc[contract_indexes, "Contract"] = "Month-to-month"

    # Step 3: Simulate target drift by increasing churn prevalence to 55%.
    churn_indexes = drifted.sample(frac=0.55, random_state=random_state + 1).index
    drifted[TARGET_COLUMN] = 0
    drifted.loc[churn_indexes, TARGET_COLUMN] = 1
    return drifted


def metric_value(snapshot_data: dict[str, Any], metric_prefix: str) -> Any:
    """Read a named value from Evidently's serializable snapshot."""

    for metric in snapshot_data["metrics"]:
        if str(metric["metric_name"]).startswith(metric_prefix):
            return metric["value"]
    raise KeyError(f"Metric not found in Evidently report: {metric_prefix}")


def build_summary(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    snapshot_data: dict[str, Any],
) -> DriftSummary:
    """Combine Evidently scores with business-readable custom metrics."""

    reference_mean = float(reference["MonthlyCharges"].mean())
    current_mean = float(current["MonthlyCharges"].mean())
    reference_contract_share = float(reference["Contract"].eq("Month-to-month").mean())
    current_contract_share = float(current["Contract"].eq("Month-to-month").mean())
    reference_churn_rate = float(reference[TARGET_COLUMN].mean())
    current_churn_rate = float(current[TARGET_COLUMN].mean())
    drift_count = metric_value(snapshot_data, "DriftedColumnsCount")

    return DriftSummary(
        reference_rows=len(reference),
        current_rows=len(current),
        drifted_columns=int(drift_count["count"]),
        monthly_charges_reference_mean=reference_mean,
        monthly_charges_current_mean=current_mean,
        monthly_charges_mean_shift=current_mean - reference_mean,
        monthly_charges_drift_score=float(
            metric_value(snapshot_data, "ValueDrift(column=MonthlyCharges")
        ),
        contract_month_to_month_reference_share=reference_contract_share,
        contract_month_to_month_current_share=current_contract_share,
        contract_drift_score=float(
            metric_value(snapshot_data, "ValueDrift(column=Contract")
        ),
        churn_reference_rate=reference_churn_rate,
        churn_current_rate=current_churn_rate,
        churn_rate_shift=current_churn_rate - reference_churn_rate,
        churn_drift_score=float(metric_value(snapshot_data, "ValueDrift(column=Churn")),
    )


def validate_detected_drift(summary: DriftSummary) -> None:
    """Fail the monitoring job if engineered drift was not detected."""

    expected_scores = {
        "MonthlyCharges": summary.monthly_charges_drift_score,
        "Contract": summary.contract_drift_score,
        "Churn": summary.churn_drift_score,
    }
    missed = [
        name for name, score in expected_scores.items() if score <= DRIFT_THRESHOLD
    ]
    if missed:
        raise RuntimeError(f"Evidently did not detect engineered drift in: {missed}")


def save_summary(summary: DriftSummary, path: Path) -> None:
    """Save the important monitoring results as readable Markdown."""

    path.write_text(
        "\n".join(
            [
                "# Synthetic Drift Summary",
                "",
                f"- Drifted columns: **{summary.drifted_columns}**",
                "- MonthlyCharges mean: "
                f"{summary.monthly_charges_reference_mean:.2f} -> "
                f"{summary.monthly_charges_current_mean:.2f} "
                f"(shift {summary.monthly_charges_mean_shift:+.2f})",
                "- Month-to-month contract share: "
                f"{summary.contract_month_to_month_reference_share:.1%} -> "
                f"{summary.contract_month_to_month_current_share:.1%}",
                "- Churn rate: "
                f"{summary.churn_reference_rate:.1%} -> "
                f"{summary.churn_current_rate:.1%}",
                "",
                "The injected drift was detected in MonthlyCharges, Contract, "
                "and Churn. "
                "In production, this result should block silent promotion and trigger "
                "investigation followed by retraining if the change is genuine.",
            ]
        ),
        encoding="utf-8",
    )


def run_monitoring() -> DriftSummary:
    """Generate, validate, save, and track the complete Evidently report."""

    # Step 1: Build stable reference data and drifted incoming data.
    reference, current = create_monitoring_sets(load_dataset())
    current_with_drift = inject_synthetic_drift(current)
    reference_mean = float(reference["MonthlyCharges"].mean())

    # Step 2: Run dataset drift, explicit target drift, and custom mean tests.
    report = Report(
        [
            DataDriftPreset(drift_share=0.5, include_tests=True),
            ValueDrift(column=TARGET_COLUMN, threshold=DRIFT_THRESHOLD),
            MeanValue(
                column="MonthlyCharges",
                tests=[
                    lte(reference_mean * 1.15),
                    gte(reference_mean * 0.85),
                ],
            ),
        ],
        include_tests=True,
    )
    snapshot = report.run(current_data=current_with_drift, reference_data=reference)
    summary = build_summary(reference, current_with_drift, snapshot.dict())
    validate_detected_drift(summary)

    # Step 3: Persist the report and the exact datasets used to produce it.
    DRIFT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    html_path = DRIFT_REPORT_DIR / "data_and_target_drift.html"
    json_path = DRIFT_REPORT_DIR / "data_and_target_drift.json"
    summary_path = DRIFT_REPORT_DIR / "summary.md"
    snapshot.save_html(str(html_path))
    snapshot.save_json(str(json_path))
    save_summary(summary, summary_path)
    reference.to_csv(PROCESSED_DATA_DIR / "reference.csv", index=False)
    current_with_drift.to_csv(
        PROCESSED_DATA_DIR / "current_with_synthetic_drift.csv", index=False
    )

    # Step 4: Log monitoring parameters, metrics, and reports to MLflow.
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_MONITORING_EXPERIMENT_NAME)
    with mlflow.start_run(run_name="synthetic_production_drift"):
        mlflow.log_params(
            {
                "reference_share": 0.7,
                "current_share": 0.3,
                "monthly_charges_offset": 20,
                "month_to_month_target_share": 0.9,
                "synthetic_churn_rate": 0.55,
                "drift_threshold": DRIFT_THRESHOLD,
            }
        )
        mlflow.log_metrics(
            {
                key: float(value)
                for key, value in asdict(summary).items()
                if isinstance(value, int | float)
            }
        )
        mlflow.log_artifacts(str(DRIFT_REPORT_DIR), artifact_path="evidently")

    print(f"Evidently report: {html_path}")
    print(json.dumps(asdict(summary), indent=2))
    return summary


def main() -> None:
    run_monitoring()


if __name__ == "__main__":
    main()
