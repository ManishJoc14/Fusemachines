# Track A: Telco Churn MLOps

This project applies a reproducible MLOps workflow to the IBM Telco Customer
Churn dataset. It will cover data preparation, experiment tracking, model
registration, serving, and drift monitoring.

## Setup

```bash
uv sync
uv run prepare-data
```

The preparation command copies and validates the dataset already stored in this
repository at `week4-linear-models/WA_Fn-UseC_-Telco-Customer-Churn.csv`.

The remaining commands and experiment results will be documented as each
workflow stage is implemented and verified.

