import numpy as np
import pandas as pd

from telco_churn.training import RunResult, calculate_metrics, select_best_run


def test_calculate_metrics_returns_required_values() -> None:
    target = pd.Series([0, 0, 1, 1])
    probabilities = np.array([0.1, 0.4, 0.7, 0.9])

    metrics = calculate_metrics(target, probabilities)

    assert set(metrics) == {"accuracy", "precision", "recall", "f1", "roc_auc"}
    assert all(value == 1.0 for value in metrics.values())


def test_select_best_run_prioritizes_f1_then_roc_auc() -> None:
    lower_f1 = RunResult("1", "first", {"f1": 0.7, "roc_auc": 0.9}, {})
    higher_f1 = RunResult("2", "second", {"f1": 0.8, "roc_auc": 0.8}, {})

    selected = select_best_run([lower_f1, higher_f1])

    assert selected == higher_f1
