from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """
    Central configuration for the entire application.

    This class reads values from environment variables (.env file)
    and ensures type safety.
    """

    # General App Settings
    PROJECT_NAME: str = "FastAPI Project"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    class Config:
        """
        Tells Pydantic where to load environment variables from.
        """

        env_file = ".env"
        case_sensitive = True


# Cache
@lru_cache()
def get_settings():
    return Settings()


# Settings instance
settings = get_settings()
