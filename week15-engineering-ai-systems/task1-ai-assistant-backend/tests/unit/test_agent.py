from __future__ import annotations

import copy
import json
from types import SimpleNamespace
from typing import Any, cast

import pytest
from openai.types.chat import ChatCompletionMessage
from pydantic import BaseModel, ConfigDict

from app.assistant.agent import AgentCompleteEvent, AssistantAgent
from app.llm.client import LLMCompletion, LLMError, LLMTextChunk, TokenUsage
from app.schemas.chat import AssistantMetadata, AssistantOutput
from app.tools.registry import RegisteredTool, ToolRegistry


class EvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str


def search_evidence(input_data: BaseModel) -> str:
    evidence = EvidenceInput.model_validate(input_data.model_dump())
    return f"{evidence.source}: " + "evidence " * 100


def tool_message(call_id: str, source: str) -> ChatCompletionMessage:
    return ChatCompletionMessage.model_validate(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": "search_evidence",
                        "arguments": json.dumps({"source": source}),
                    },
                }
            ],
        }
    )


def completion(
    message: ChatCompletionMessage,
    *,
    parsed: AssistantOutput | None = None,
) -> LLMCompletion[AssistantOutput]:
    return LLMCompletion(
        message=message,
        parsed=parsed,
        model="test-model",
        used_fallback=False,
        usage=TokenUsage(prompt_tokens=8, completion_tokens=2, total_tokens=10),
    )


class ScriptedLLM:
    def __init__(self, responses: list[LLMCompletion[AssistantOutput]]) -> None:
        self._responses = iter(responses)
        self.calls: list[list[dict[str, Any]]] = []

    async def complete(self, messages: list[dict[str, Any]], **_: Any):
        self.calls.append(copy.deepcopy(messages))
        return next(self._responses)

    async def stream_text(self, *_: Any, **__: Any):
        yield LLMTextChunk(
            content="Verified answer.",
            model="test-model",
            used_fallback=False,
        )
        yield LLMTextChunk(
            content="",
            model="test-model",
            used_fallback=False,
            is_complete=True,
            usage=TokenUsage(prompt_tokens=5, completion_tokens=3, total_tokens=8),
        )


class RepeatingToolLLM:
    async def complete(self, messages: list[dict[str, Any]], **_: Any):
        call_number = len(messages)
        return completion(tool_message(f"call-{call_number}", "source-a"))


def build_agent(llm: object, *, max_iterations: int = 4) -> AssistantAgent:
    registry = ToolRegistry(
        [
            RegisteredTool(
                name="search_evidence",
                description="Search one independent evidence source.",
                input_model=EvidenceInput,
                handler=search_evidence,
            )
        ]
    )
    settings = SimpleNamespace(
        llm_max_tool_iterations=max_iterations,
        llm_tool_result_max_characters=500,
    )
    return AssistantAgent(cast(Any, llm), registry, cast(Any, settings))


@pytest.mark.asyncio
async def test_agent_runs_multiple_tool_iterations_and_records_usage() -> None:
    # Step 1: Arrange two tool calls followed by a structured final answer.
    final_output = AssistantOutput(
        answer="Both independent sources support the claim.",
        cited_chunk_ids=[],
        follow_up_questions=[],
        confidence="high",
    )
    llm = ScriptedLLM(
        [
            completion(tool_message("call-1", "source-a")),
            completion(tool_message("call-2", "source-b")),
            completion(ChatCompletionMessage(role="assistant", content="Ready")),
            completion(
                ChatCompletionMessage(role="assistant", content="{}"),
                parsed=final_output,
            ),
        ]
    )

    # Step 2: Run the agent through the complete scripted trajectory.
    result = await build_agent(llm).run("Verify the claim using two sources.")

    # Step 3: Verify the trajectory, token total, and bounded tool context.
    assert result.iterations == 3
    assert [step.tool_name for step in result.trajectory[:-1]] == [
        "search_evidence",
        "search_evidence",
    ]
    assert result.trajectory[-1].action == "answer"
    assert result.token_usage.total_tokens == 40
    assert len(result.tools_used) == 2

    first_tool_note = json.loads(llm.calls[1][-1]["content"])
    assert first_tool_note["tool"] == "search_evidence"
    assert first_tool_note["success"] is True
    assert first_tool_note["truncated"] is True
    assert len(first_tool_note["evidence"]) < 530


@pytest.mark.asyncio
async def test_agent_stops_at_the_iteration_limit() -> None:
    # Step 1: Arrange a model that requests another tool on every turn.
    agent = build_agent(RepeatingToolLLM(), max_iterations=2)

    # Step 2: Verify the bounded loop stops instead of running forever.
    with pytest.raises(LLMError, match="Maximum tool-call iterations reached"):
        await agent.run("Keep searching forever.")


@pytest.mark.asyncio
async def test_stream_returns_trajectory_and_complete_token_usage() -> None:
    # Step 1: Arrange one tool turn, one answer turn, and final metadata.
    metadata = AssistantMetadata(
        cited_chunk_ids=[],
        follow_up_questions=[],
        confidence="high",
    )
    llm = ScriptedLLM(
        [
            completion(tool_message("call-1", "source-a")),
            completion(ChatCompletionMessage(role="assistant", content="Ready")),
            completion(
                ChatCompletionMessage(role="assistant", content="{}"),
                parsed=cast(Any, metadata),
            ),
        ]
    )

    # Step 2: Collect the streamed events exactly as the chat service does.
    events = [
        event
        async for event in build_agent(llm).stream(
            "Verify the claim using an independent source."
        )
    ]

    # Step 3: Verify the final event contains the complete public agent metrics.
    final_event = events[-1]
    assert isinstance(final_event, AgentCompleteEvent)
    assert final_event.iterations == 2
    assert [step.action for step in final_event.trajectory] == ["tool", "answer"]
    assert final_event.token_usage == TokenUsage(
        prompt_tokens=29,
        completion_tokens=9,
        total_tokens=38,
    )
