from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from telco_churn.config import RAW_DATASET_PATH

TARGET_COLUMN = "Churn"
IDENTIFIER_COLUMN = "customerID"
NUMERIC_COLUMNS = ["SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"]


@dataclass(frozen=True)
class DatasetSplit:
    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series


def load_dataset(path: Path = RAW_DATASET_PATH) -> pd.DataFrame:
    """Load the churn data and normalize columns with known data-quality issues."""

    if not path.is_file():
        raise FileNotFoundError(
            f"Prepared dataset not found at {path}. Run `uv run prepare-data` first."
        )

    dataset = pd.read_csv(path)
    dataset["TotalCharges"] = pd.to_numeric(
        dataset["TotalCharges"].astype(str).str.strip(), errors="coerce"
    )
    dataset[TARGET_COLUMN] = dataset[TARGET_COLUMN].map({"No": 0, "Yes": 1})

    if dataset[TARGET_COLUMN].isna().any():
        raise ValueError("Churn must contain only 'Yes' or 'No' values")

    return dataset


def split_dataset(
    dataset: pd.DataFrame,
    *,
    test_size: float = 0.2,
    random_state: int = 42,
) -> DatasetSplit:
    """Create a reproducible, stratified train/test split."""

    features = dataset.drop(columns=[IDENTIFIER_COLUMN, TARGET_COLUMN])
    target = dataset[TARGET_COLUMN].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=test_size,
        random_state=random_state,
        stratify=target,
    )
    return DatasetSplit(X_train, X_test, y_train, y_test)


def categorical_columns(features: pd.DataFrame) -> list[str]:
    """Return every model feature that is not part of the numeric schema."""

    return [column for column in features.columns if column not in NUMERIC_COLUMNS]
