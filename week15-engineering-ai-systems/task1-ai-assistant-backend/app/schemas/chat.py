from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8_000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8_000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    use_rag: bool = True


class AssistantOutput(BaseModel):
    """JSON structure that the LLM must return for its final answer."""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1)
    cited_chunk_ids: list[str]
    follow_up_questions: list[str] = Field(max_length=3)
    confidence: Literal["low", "medium", "high"]


class AssistantMetadata(BaseModel):
    """Structured metadata generated after a streamed text answer."""

    model_config = ConfigDict(extra="forbid")

    cited_chunk_ids: list[str]
    follow_up_questions: list[str] = Field(max_length=3)
    confidence: Literal["low", "medium", "high"]


class SourceReference(BaseModel):
    chunk_id: str
    document_name: str
    chunk_index: int
    score: float
    text_preview: str


class ToolExecution(BaseModel):
    name: str
    arguments: dict[str, object]
    output: str
    success: bool


class PipelineStats(BaseModel):
    retrieval_strategy: Literal["dense_cosine", "disabled"]
    retrieved_chunks: int
    cited_chunks: int
    tool_executions: int


class ChatResponse(BaseModel):
    answer: str
    confidence: Literal["low", "medium", "high"]
    follow_up_questions: list[str]
    sources: list[SourceReference]
    tools_used: list[ToolExecution]
    model: str
    used_fallback: bool
    pipeline_stats: PipelineStats


class ChatStreamStatus(BaseModel):
    type: Literal["status"] = "status"
    stage: Literal["retrieving", "generating"]
    message: str


class ChatStreamTool(BaseModel):
    type: Literal["tool"] = "tool"
    tool: ToolExecution


class ChatStreamDelta(BaseModel):
    type: Literal["delta"] = "delta"
    content: str


class ChatStreamComplete(BaseModel):
    type: Literal["complete"] = "complete"
    response: ChatResponse


class ChatStreamError(BaseModel):
    type: Literal["error"] = "error"
    message: str


ChatStreamEvent = (
    ChatStreamStatus
    | ChatStreamTool
    | ChatStreamDelta
    | ChatStreamComplete
    | ChatStreamError
)
