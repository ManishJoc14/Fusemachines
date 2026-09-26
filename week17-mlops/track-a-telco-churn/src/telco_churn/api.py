from __future__ import annotations

import os
from collections.abc import Callable
from functools import lru_cache
from typing import Annotated, Any, Literal

import mlflow
import mlflow.sklearn
import pandas as pd
import uvicorn
from fastapi import Depends, FastAPI
from pydantic import BaseModel, ConfigDict, Field

from telco_churn.config import (
    MLFLOW_TRACKING_URI,
    REGISTERED_MODEL_NAME,
)

YesNo = Literal["Yes", "No"]
InternetAddon = Literal["Yes", "No", "No internet service"]


class ChurnFeatures(BaseModel):
    """Validated customer attributes expected by the registered pipeline."""

    model_config = ConfigDict(populate_by_name=True)

    gender: Literal["Female", "Male"]
    senior_citizen: Literal[0, 1] = Field(alias="SeniorCitizen")
    partner: YesNo = Field(alias="Partner")
    dependents: YesNo = Field(alias="Dependents")
    tenure: Annotated[int, Field(ge=0, le=100)]
    phone_service: YesNo = Field(alias="PhoneService")
    multiple_lines: Literal["Yes", "No", "No phone service"] = Field(
        alias="MultipleLines"
    )
    internet_service: Literal["DSL", "Fiber optic", "No"] = Field(
        alias="InternetService"
    )
    online_security: InternetAddon = Field(alias="OnlineSecurity")
    online_backup: InternetAddon = Field(alias="OnlineBackup")
    device_protection: InternetAddon = Field(alias="DeviceProtection")
    tech_support: InternetAddon = Field(alias="TechSupport")
    streaming_tv: InternetAddon = Field(alias="StreamingTV")
    streaming_movies: InternetAddon = Field(alias="StreamingMovies")
    contract: Literal["Month-to-month", "One year", "Two year"] = Field(
        alias="Contract"
    )
    paperless_billing: YesNo = Field(alias="PaperlessBilling")
    payment_method: Literal[
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    ] = Field(alias="PaymentMethod")
    monthly_charges: Annotated[float, Field(ge=0)] = Field(alias="MonthlyCharges")
    total_charges: Annotated[float, Field(ge=0)] = Field(alias="TotalCharges")

    def to_dataframe(self) -> pd.DataFrame:
        values = self.model_dump(by_alias=True)
        return pd.DataFrame([values])


class PredictionResponse(BaseModel):
    churn: bool
    churn_label: Literal["Yes", "No"]
    churn_probability: float
    model: str


class ModelService:
    """Load the promoted MLflow model and expose prediction behavior."""

    def __init__(self, model: Any) -> None:
        self._model = model

    def predict(self, features: ChurnFeatures) -> PredictionResponse:
        probability = float(self._model.predict_proba(features.to_dataframe())[0, 1])
        churn = probability >= 0.5
        return PredictionResponse(
            churn=churn,
            churn_label="Yes" if churn else "No",
            churn_probability=round(probability, 6),
            model=f"{REGISTERED_MODEL_NAME}@champion",
        )


@lru_cache
def load_model_service() -> ModelService:
    """Load the champion once and reuse it across API requests."""

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    model_uri = f"models:/{REGISTERED_MODEL_NAME}@champion"
    return ModelService(mlflow.sklearn.load_model(model_uri))


def create_app(
    model_loader: Callable[[], ModelService] = load_model_service,
) -> FastAPI:
    application = FastAPI(
        title="Telco Churn Prediction API",
        version="0.1.0",
        description="Serves the champion model registered in MLflow.",
    )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "healthy"}

    @application.post("/predict", response_model=PredictionResponse)
    def predict(
        features: ChurnFeatures,
        service: ModelService = Depends(model_loader),  # noqa: B008
    ) -> PredictionResponse:
        return service.predict(features)

    return application


app = create_app()


def run() -> None:
    """Start the prediction API using the platform-provided port when present."""

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("telco_churn.api:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    run()
