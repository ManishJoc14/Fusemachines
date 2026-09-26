from pathlib import Path

import pandas as pd
import pytest

from telco_churn.data import EXPECTED_COLUMNS, prepare_dataset


def test_prepare_dataset_copies_a_valid_file(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    destination = tmp_path / "raw" / "dataset.csv"
    row = {column: "value" for column in EXPECTED_COLUMNS}
    pd.DataFrame([row]).to_csv(source, index=False)

    prepared_path = prepare_dataset(source, destination)

    assert prepared_path == destination
    assert destination.is_file()
    assert len(pd.read_csv(destination)) == 1


def test_prepare_dataset_rejects_an_invalid_schema(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    pd.DataFrame([{"Churn": "No"}]).to_csv(source, index=False)

    with pytest.raises(ValueError, match="missing required columns"):
        prepare_dataset(source, tmp_path / "dataset.csv")
