from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import pandas as pd

from telco_churn.config import RAW_DATASET_PATH, SHARED_DATASET_PATH

EXPECTED_COLUMNS = {
    "customerID",
    "gender",
    "SeniorCitizen",
    "Partner",
    "Dependents",
    "tenure",
    "PhoneService",
    "MultipleLines",
    "InternetService",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
    "Contract",
    "PaperlessBilling",
    "PaymentMethod",
    "MonthlyCharges",
    "TotalCharges",
    "Churn",
}


def prepare_dataset(source: Path, destination: Path = RAW_DATASET_PATH) -> Path:
    """Copy the shared churn dataset into this project after validation."""

    # Step 1: Fail clearly if the source file is unavailable.
    if not source.is_file():
        raise FileNotFoundError(f"Dataset not found: {source}")

    # Step 2: Validate the schema before accepting the file.
    dataset = pd.read_csv(source)
    missing_columns = EXPECTED_COLUMNS.difference(dataset.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Dataset is missing required columns: {missing}")
    if dataset.empty:
        raise ValueError("Dataset must contain at least one row")

    # Step 3: Create the local data directory and copy the validated source.
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)

    print(f"Prepared {len(dataset):,} rows at {destination}")
    return destination


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare the Telco churn dataset")
    parser.add_argument(
        "--source",
        type=Path,
        default=SHARED_DATASET_PATH,
        help="Path to the source Telco Customer Churn CSV",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prepare_dataset(args.source.resolve())


if __name__ == "__main__":
    main()
