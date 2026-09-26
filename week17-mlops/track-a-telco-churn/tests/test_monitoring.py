import pandas as pd
import pytest

from telco_churn.monitoring import create_monitoring_sets, inject_synthetic_drift


def make_dataset(rows: int = 100) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "customerID": [str(index) for index in range(rows)],
            "MonthlyCharges": [50.0] * rows,
            "Contract": ["One year"] * rows,
            "Churn": [0, 1] * (rows // 2),
        }
    )


def test_monitoring_split_uses_seventy_thirty_ratio() -> None:
    reference, current = create_monitoring_sets(make_dataset())

    assert len(reference) == 70
    assert len(current) == 30
    assert reference["Churn"].mean() == current["Churn"].mean() == 0.5


def test_synthetic_drift_changes_expected_distributions() -> None:
    _, current = create_monitoring_sets(make_dataset())

    drifted = inject_synthetic_drift(current)

    assert drifted["MonthlyCharges"].mean() == 70.0
    assert drifted["Contract"].eq("Month-to-month").mean() == 0.9
    assert drifted["Churn"].mean() == pytest.approx(0.55, abs=0.02)
