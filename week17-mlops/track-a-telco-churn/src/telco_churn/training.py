from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
import pandas as pd
import seaborn as sns
from mlflow import MlflowClient
from mlflow.models import infer_signature
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from telco_churn.config import (
    FIGURES_DIR,
    MLFLOW_EXPERIMENT_NAME,
    MLFLOW_TRACKING_URI,
    REGISTERED_MODEL_NAME,
    REPORTS_DIR,
)
from telco_churn.dataset import DatasetSplit, load_dataset, split_dataset
from telco_churn.modeling import (
    ModelConfiguration,
    build_pipeline,
    model_configurations,
)


@dataclass(frozen=True)
class RunResult:
    run_id: str
    model_name: str
    metrics: dict[str, float]
    parameters: dict[str, str | int | float]


def calculate_metrics(y_true: pd.Series, probabilities: Any) -> dict[str, float]:
    """Calculate all classification metrics required by the assignment."""

    predictions = (probabilities >= 0.5).astype(int)
    return {
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
    }


def save_evaluation_figures(
    model_name: str,
    y_true: pd.Series,
    probabilities: Any,
) -> tuple[Path, Path]:
    """Save a confusion matrix and ROC curve for one experiment run."""

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    predictions = (probabilities >= 0.5).astype(int)

    confusion_path = FIGURES_DIR / f"{model_name}_confusion_matrix.png"
    figure, axis = plt.subplots(figsize=(5, 4))
    sns.heatmap(
        confusion_matrix(y_true, predictions),
        annot=True,
        fmt="d",
        cmap="Blues",
        cbar=False,
        ax=axis,
    )
    axis.set(title="Confusion Matrix", xlabel="Predicted", ylabel="Actual")
    figure.tight_layout()
    figure.savefig(confusion_path, dpi=160)
    plt.close(figure)

    roc_path = FIGURES_DIR / f"{model_name}_roc_curve.png"
    false_positive_rate, true_positive_rate, _ = roc_curve(y_true, probabilities)
    roc_auc = roc_auc_score(y_true, probabilities)
    figure, axis = plt.subplots(figsize=(5, 4))
    axis.plot(false_positive_rate, true_positive_rate, label=f"AUC = {roc_auc:.3f}")
    axis.plot([0, 1], [0, 1], linestyle="--", color="gray")
    axis.set(
        title="Receiver Operating Characteristic",
        xlabel="False Positive Rate",
        ylabel="True Positive Rate",
    )
    axis.legend(loc="lower right")
    figure.tight_layout()
    figure.savefig(roc_path, dpi=160)
    plt.close(figure)

    return confusion_path, roc_path


def run_experiment(
    configuration: ModelConfiguration,
    split: DatasetSplit,
) -> RunResult:
    """Train, evaluate, and log one model configuration to MLflow."""

    with mlflow.start_run(run_name=configuration.name) as run:
        # Step 1: Train preprocessing and the estimator as one pipeline.
        pipeline = build_pipeline(split.X_train, configuration.estimator)
        pipeline.fit(split.X_train, split.y_train)

        # Step 2: Evaluate against the untouched test split.
        probabilities = pipeline.predict_proba(split.X_test)[:, 1]
        metrics = calculate_metrics(split.y_test, probabilities)
        confusion_path, roc_path = save_evaluation_figures(
            configuration.name,
            split.y_test,
            probabilities,
        )

        # Step 3: Store comparable parameters, metrics, and artifacts.
        mlflow.log_params(configuration.parameters)
        mlflow.log_params(
            {
                "test_size": 0.2,
                "random_state": 42,
                "training_rows": len(split.X_train),
                "test_rows": len(split.X_test),
            }
        )
        mlflow.log_metrics(metrics)
        mlflow.log_artifact(str(confusion_path), artifact_path="evaluation")
        mlflow.log_artifact(str(roc_path), artifact_path="evaluation")

        signature = infer_signature(
            split.X_train,
            pipeline.predict(split.X_train.head(5)),
        )
        mlflow.sklearn.log_model(
            pipeline,
            name="model",
            serialization_format="cloudpickle",
            signature=signature,
            input_example=split.X_train.head(5),
        )

        return RunResult(
            run_id=run.info.run_id,
            model_name=configuration.name,
            metrics=metrics,
            parameters=configuration.parameters,
        )


def select_best_run(results: list[RunResult]) -> RunResult:
    """Select the model with the best F1 score, then ROC-AUC as a tie-breaker."""

    if not results:
        raise ValueError("At least one completed run is required")
    return max(
        results, key=lambda result: (result.metrics["f1"], result.metrics["roc_auc"])
    )


def export_comparison(results: list[RunResult], best_run: RunResult) -> Path:
    """Export a readable side-by-side comparison for the submission report."""

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "selected": result.run_id == best_run.run_id,
            "model": result.model_name,
            "run_id": result.run_id,
            **result.parameters,
            **result.metrics,
        }
        for result in results
    ]
    comparison = pd.DataFrame(rows).sort_values(by=["f1", "roc_auc"], ascending=False)
    comparison_path = REPORTS_DIR / "model_comparison.csv"
    comparison.to_csv(comparison_path, index=False)

    summary_path = REPORTS_DIR / "best_model.json"
    summary_path.write_text(
        json.dumps(
            {
                "selection_metric": "f1",
                "tie_breaker": "roc_auc",
                "best_run": rows[
                    [item["run_id"] for item in rows].index(best_run.run_id)
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return comparison_path


def register_best_model(best_run: RunResult) -> str:
    """Register and promote the winning pipeline for serving."""

    model_uri = f"runs:/{best_run.run_id}/model"
    registered = mlflow.register_model(model_uri, REGISTERED_MODEL_NAME)
    client = MlflowClient()

    # The assignment requires both lifecycle stages. MLflow now recommends
    # aliases, so we record the stages and also assign a production alias.
    client.transition_model_version_stage(
        name=REGISTERED_MODEL_NAME,
        version=registered.version,
        stage="Staging",
    )
    client.transition_model_version_stage(
        name=REGISTERED_MODEL_NAME,
        version=registered.version,
        stage="Production",
        archive_existing_versions=True,
    )
    client.set_registered_model_alias(
        REGISTERED_MODEL_NAME,
        "champion",
        registered.version,
    )
    client.set_model_version_tag(
        REGISTERED_MODEL_NAME,
        registered.version,
        "selection_metric",
        "f1",
    )
    registry_path = REPORTS_DIR / "registered_model.json"
    registry_path.write_text(
        json.dumps(
            {
                "name": REGISTERED_MODEL_NAME,
                "version": str(registered.version),
                "source_run_id": best_run.run_id,
                "model": best_run.model_name,
                "promotion_history": ["Staging", "Production"],
                "current_stage": "Production",
                "alias": "champion",
                "selection_metric": "f1",
                "selection_metric_value": best_run.metrics["f1"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return str(registered.version)


def train_all_models() -> tuple[list[RunResult], RunResult, str]:
    """Run the complete training, comparison, and registration workflow."""

    # Step 1: Configure local MLflow tracking and load one fixed data split.
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
    split = split_dataset(load_dataset(), test_size=0.2, random_state=42)

    # Step 2: Run every declared model configuration against the same test data.
    results = [
        run_experiment(configuration, split) for configuration in model_configurations()
    ]

    # Step 3: Select, export, register, and promote the strongest model.
    best_run = select_best_run(results)
    comparison_path = export_comparison(results, best_run)
    version = register_best_model(best_run)

    print(f"Compared {len(results)} runs: {comparison_path}")
    print(f"Registered {REGISTERED_MODEL_NAME} version {version} as champion")
    return results, best_run, version


def main() -> None:
    train_all_models()


if __name__ == "__main__":
    main()
