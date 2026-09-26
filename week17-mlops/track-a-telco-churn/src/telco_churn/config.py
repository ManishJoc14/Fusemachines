from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = PROJECT_ROOT.parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_ROOT / "artifacts" / "reports"
FIGURES_DIR = PROJECT_ROOT / "artifacts" / "figures"

SHARED_DATASET_PATH = (
    REPOSITORY_ROOT / "week4-linear-models" / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
)
RAW_DATASET_PATH = RAW_DATA_DIR / "telco_customer_churn.csv"

MLFLOW_DATABASE_PATH = PROJECT_ROOT / "mlflow.db"
MLFLOW_TRACKING_URI = f"sqlite:///{MLFLOW_DATABASE_PATH.as_posix()}"
MLFLOW_EXPERIMENT_NAME = "telco-churn-model-comparison"
MLFLOW_MONITORING_EXPERIMENT_NAME = "telco-churn-drift-monitoring"
REGISTERED_MODEL_NAME = "telco-churn-classifier"
