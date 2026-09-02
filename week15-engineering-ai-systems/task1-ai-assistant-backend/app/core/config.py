from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import AnyHttpUrl, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class LLMBackend(StrEnum):
    HUGGINGFACE = "huggingface"
    VLLM = "vllm"


class Settings(BaseSettings):
    """Typed application configuration loaded from environment variables."""

    app_name: str = "Engineering AI Assistant"
    app_version: str = "0.1.0"
    app_environment: Environment = Environment.DEVELOPMENT
    app_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    app_api_v1_prefix: str = Field(default="/api/v1", pattern=r"^/")
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    llm_backend: LLMBackend = LLMBackend.HUGGINGFACE
    hf_token: SecretStr | None = None
    hf_base_url: AnyHttpUrl = AnyHttpUrl("https://router.huggingface.co/v1")
    hf_model: str = "openai/gpt-oss-20b:groq"
    hf_fallback_model: str = "deepseek-ai/DeepSeek-V4-Flash-0731:deepinfra"

    vllm_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8001/v1")
    vllm_api_key: SecretStr = SecretStr("local-only")
    vllm_model: str = "Qwen/Qwen2.5-1.5B-Instruct"

    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    llm_top_p: float = Field(default=1.0, gt=0.0, le=1.0)
    llm_max_output_tokens: int = Field(default=1200, gt=0)
    llm_timeout_seconds: float = Field(default=60.0, gt=0.0)
    llm_max_tool_iterations: int = Field(default=5, ge=1, le=10)

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_device: Literal["cpu", "cuda", "mps"] = "cpu"
    embedding_batch_size: int = Field(default=32, gt=0)
    embedding_dimension: int = Field(default=384, gt=0)

    qdrant_url: AnyHttpUrl = AnyHttpUrl("http://localhost:6333")
    qdrant_api_key: SecretStr | None = None
    qdrant_collection: str = "assistant_documents"

    rag_chunk_size: int = Field(default=800, gt=0)
    rag_chunk_overlap: int = Field(default=120, ge=0)
    rag_retrieval_top_k: int = Field(default=5, gt=0, le=50)
    rag_score_threshold: float = Field(default=0.25, ge=0.0, le=1.0)

    documents_directory: Path = Path("data/documents")
    max_upload_size_mb: int = Field(default=10, gt=0)
    max_batch_upload_files: int = Field(default=10, gt=0, le=50)

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_related_settings(self) -> Self:
        """Validate rules involving more than one environment variable."""

        if self.rag_chunk_overlap >= self.rag_chunk_size:
            raise ValueError("RAG_CHUNK_OVERLAP must be smaller than RAG_CHUNK_SIZE")

        return self


@lru_cache
def get_settings() -> Settings:
    """Build settings once per process and reuse the validated instance."""

    return Settings()  # type: ignore[call-arg]
