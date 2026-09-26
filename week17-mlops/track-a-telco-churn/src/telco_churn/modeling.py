from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from telco_churn.dataset import NUMERIC_COLUMNS, categorical_columns


@dataclass(frozen=True)
class ModelConfiguration:
    name: str
    estimator: Any
    parameters: dict[str, str | int | float]


def model_configurations() -> list[ModelConfiguration]:
    """Define the genuinely different configurations compared by MLflow."""

    return [
        ModelConfiguration(
            name="logistic_regression_c_0_5",
            estimator=LogisticRegression(
                C=0.5,
                class_weight="balanced",
                max_iter=1_000,
                random_state=42,
            ),
            parameters={
                "model_family": "logistic_regression",
                "C": 0.5,
                "class_weight": "balanced",
            },
        ),
        ModelConfiguration(
            name="logistic_regression_c_1_5",
            estimator=LogisticRegression(
                C=1.5,
                class_weight="balanced",
                max_iter=1_000,
                random_state=42,
            ),
            parameters={
                "model_family": "logistic_regression",
                "C": 1.5,
                "class_weight": "balanced",
            },
        ),
        ModelConfiguration(
            name="random_forest_depth_10",
            estimator=RandomForestClassifier(
                n_estimators=250,
                max_depth=10,
                min_samples_leaf=2,
                class_weight="balanced",
                n_jobs=-1,
                random_state=42,
            ),
            parameters={
                "model_family": "random_forest",
                "n_estimators": 250,
                "max_depth": 10,
                "min_samples_leaf": 2,
                "class_weight": "balanced",
            },
        ),
    ]


def build_pipeline(features: pd.DataFrame, estimator: Any) -> Pipeline:
    """Build preprocessing and classification as one leakage-safe pipeline."""

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_COLUMNS),
            ("categorical", categorical_pipeline, categorical_columns(features)),
        ]
    )
    return Pipeline(steps=[("preprocessor", preprocessor), ("model", estimator)])
