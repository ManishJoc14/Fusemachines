from pathlib import Path

import pandas as pd

from telco_churn.dataset import load_dataset, split_dataset


def test_load_dataset_converts_total_charges_and_target(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.csv"
    pd.DataFrame(
        [
            {"customerID": "a", "TotalCharges": " ", "Churn": "No"},
            {"customerID": "b", "TotalCharges": "42.5", "Churn": "Yes"},
        ]
    ).to_csv(dataset_path, index=False)

    dataset = load_dataset(dataset_path)

    assert pd.isna(dataset.loc[0, "TotalCharges"])
    assert dataset.loc[1, "TotalCharges"] == 42.5
    assert dataset["Churn"].tolist() == [0, 1]


def test_split_dataset_is_stratified() -> None:
    rows = []
    for index in range(100):
        rows.append(
            {
                "customerID": str(index),
                "feature": index,
                "Churn": 1 if index < 20 else 0,
            }
        )
    split = split_dataset(pd.DataFrame(rows), test_size=0.2, random_state=42)

    assert len(split.X_train) == 80
    assert len(split.X_test) == 20
    assert split.y_train.mean() == split.y_test.mean() == 0.2
