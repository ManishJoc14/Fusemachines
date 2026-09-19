from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Confidence = Literal["low", "medium", "high"]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8_000)


class ChatRequest(BaseModel):
    session_id: uuid.UUID
    message: str = Field(min_length=1, max_length=8_000)
    document_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10)


class AssistantOutput(BaseModel):
    """JSON structure that the LLM must return for its final answer."""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1)
    cited_chunk_ids: list[str]
    follow_up_questions: list[str] = Field(
        max_length=3,
        description=(
            "Ready-to-send next messages written from the user's point of view."
        ),
    )
    confidence: Confidence


class AssistantMetadata(BaseModel):
    """Structured metadata generated after a streamed text answer."""

    model_config = ConfigDict(extra="forbid")

    cited_chunk_ids: list[str]
    follow_up_questions: list[str] = Field(
        max_length=3,
        description=(
            "Ready-to-send next messages written from the user's point of view."
        ),
    )
    confidence: Confidence


class SourceReference(BaseModel):
    citation_number: int
    chunk_id: str
    document_name: str
    chunk_index: int
    score: float
    text: str


class ToolExecution(BaseModel):
    name: str
    arguments: dict[str, object]
    output: str
    success: bool


class AgentStepStats(BaseModel):
    iteration: int
    action: Literal["tool", "answer"]
    tool_name: str | None = None
    success: bool | None = None


class TokenUsageStats(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class AgentStats(BaseModel):
    iterations: int
    trajectory: list[AgentStepStats]
    token_usage: TokenUsageStats


class PipelineStats(BaseModel):
    retrieval_strategy: Literal["hybrid_rerank", "dense_cosine", "disabled"]
    retrieved_chunks: int
    cited_chunks: int
    tool_executions: int


class ChatResponse(BaseModel):
    answer: str
    confidence: Confidence
    follow_up_questions: list[str]
    sources: list[SourceReference]
    tools_used: list[ToolExecution]
    model: str
    used_fallback: bool
    agent: AgentStats
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
