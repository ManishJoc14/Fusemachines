from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DocumentChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    document_id: str
    document_name: str
    chunk_index: int = Field(ge=0)
    text: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(gt=0)


class RetrievedChunk(DocumentChunk):
    score: float


class IngestionResult(BaseModel):
    document_id: str
    document_name: str
    character_count: int
    chunk_count: int
