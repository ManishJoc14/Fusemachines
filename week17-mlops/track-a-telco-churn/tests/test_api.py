from typing import Any

import numpy as np
from fastapi.testclient import TestClient

from telco_churn.api import ModelService, create_app

VALID_CUSTOMER = {
    "gender": "Female",
    "SeniorCitizen": 0,
    "Partner": "Yes",
    "Dependents": "No",
    "tenure": 1,
    "PhoneService": "No",
    "MultipleLines": "No phone service",
    "InternetService": "DSL",
    "OnlineSecurity": "No",
    "OnlineBackup": "Yes",
    "DeviceProtection": "No",
    "TechSupport": "No",
    "StreamingTV": "No",
    "StreamingMovies": "No",
    "Contract": "Month-to-month",
    "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check",
    "MonthlyCharges": 29.85,
    "TotalCharges": 29.85,
}


class FakeModel:
    def predict_proba(self, _: Any) -> np.ndarray:
        return np.array([[0.2, 0.8]])


def test_health_endpoint() -> None:
    client = TestClient(create_app(lambda: ModelService(FakeModel())))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_prediction_endpoint_returns_probability() -> None:
    client = TestClient(create_app(lambda: ModelService(FakeModel())))

    response = client.post("/predict", json=VALID_CUSTOMER)

    assert response.status_code == 200
    assert response.json() == {
        "churn": True,
        "churn_label": "Yes",
        "churn_probability": 0.8,
        "model": "telco-churn-classifier@champion",
    }


def test_prediction_endpoint_rejects_invalid_categories() -> None:
    client = TestClient(create_app(lambda: ModelService(FakeModel())))
    invalid_customer = {**VALID_CUSTOMER, "Contract": "Five years"}

    response = client.post("/predict", json=invalid_customer)

    assert response.status_code == 422
