from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal

from openai.types.chat import ChatCompletionMessage

from app.assistant.prompts import build_system_prompt
from app.core.config import Settings
from app.llm.client import ChatMessageParam, LLMClient, LLMError, TokenUsage
from app.schemas.chat import (
    AssistantMetadata,
    AssistantOutput,
    ChatMessage,
    ToolExecution,
)
from app.tools.registry import ToolRegistry


@dataclass(frozen=True, slots=True)
class AgentStep:
    iteration: int
    action: Literal["tool", "answer"]
    tool_name: str | None = None
    success: bool | None = None


@dataclass(frozen=True, slots=True)
class AgentResult:
    output: AssistantOutput
    tools_used: list[ToolExecution]
    model: str
    used_fallback: bool
    iterations: int
    trajectory: list[AgentStep]
    token_usage: TokenUsage


@dataclass(frozen=True, slots=True)
class AgentToolEvent:
    execution: ToolExecution


@dataclass(frozen=True, slots=True)
class AgentDeltaEvent:
    content: str


@dataclass(frozen=True, slots=True)
class AgentCompleteEvent:
    answer: str
    metadata: AssistantMetadata
    tools_used: list[ToolExecution]
    model: str
    used_fallback: bool
    iterations: int
    trajectory: list[AgentStep]
    token_usage: TokenUsage


AgentStreamEvent = AgentToolEvent | AgentDeltaEvent | AgentCompleteEvent


class AssistantAgent:
    """Run the model/tool loop until the model returns a structured answer."""

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        settings: Settings,
    ) -> None:
        self._llm = llm_client
        self._tools = tool_registry
        self._max_iterations = settings.llm_max_tool_iterations
        self._tool_result_max_characters = settings.llm_tool_result_max_characters

    async def run(
        self,
        question: str,
        *,
        history: list[ChatMessage] | None = None,
        context: str | None = None,
    ) -> AgentResult:
        # Step 1: Build one conversation from the prompt, history, and question.
        messages = self._build_messages(question, history, context)

        executions: list[ToolExecution] = []
        active_model: str | None = None
        used_fallback = False
        trajectory: list[AgentStep] = []
        token_usage = TokenUsage()

        for iteration in range(1, self._max_iterations + 1):
            # Step 2: Let the model select any tools it needs.
            completion = await self._llm.complete(
                messages,
                response_model=AssistantOutput,
                tools=self._tools.schemas(),
                model=active_model,
            )
            token_usage += completion.usage
            used_fallback = used_fallback or completion.used_fallback
            if completion.used_fallback:
                # Once fallback starts, keep later tool-loop turns on that model.
                active_model = completion.model

            # Step 3: Execute requested tools and return their results to the model.
            if completion.message.tool_calls:
                iteration_executions = await self._execute_tools(
                    completion.message,
                    messages,
                    executions,
                )
                trajectory.extend(
                    AgentStep(
                        iteration=iteration,
                        action="tool",
                        tool_name=execution.name,
                        success=execution.success,
                    )
                    for execution in iteration_executions
                )
                continue

            # Step 4: Request JSON separately because some providers cannot
            # combine structured output with tool calling in one request.
            final_completion = await self._llm.complete(
                messages,
                response_model=AssistantOutput,
                model=active_model,
            )
            token_usage += final_completion.usage
            used_fallback = used_fallback or final_completion.used_fallback

            if final_completion.parsed is None:
                raise LLMError("Model did not return a structured final answer")

            # Step 5: Return the validated answer and execution metadata.
            trajectory.append(AgentStep(iteration=iteration, action="answer"))
            return AgentResult(
                output=final_completion.parsed,
                tools_used=executions,
                model=final_completion.model,
                used_fallback=used_fallback,
                iterations=iteration,
                trajectory=trajectory,
                token_usage=token_usage,
            )

        raise LLMError("Maximum tool-call iterations reached")

    async def stream(
        self,
        question: str,
        *,
        history: list[ChatMessage] | None = None,
        context: str | None = None,
    ) -> AsyncIterator[AgentStreamEvent]:
        """Run tools first, then stream the final text answer as it is generated."""

        messages = self._build_messages(question, history, context)
        executions: list[ToolExecution] = []
        active_model: str | None = None
        used_fallback = False
        trajectory: list[AgentStep] = []
        token_usage = TokenUsage()

        for iteration in range(1, self._max_iterations + 1):
            # Step 1: Ask the model whether it needs a tool.
            completion = await self._llm.complete(
                messages,
                response_model=AssistantOutput,
                tools=self._tools.schemas(),
                model=active_model,
            )
            token_usage += completion.usage
            used_fallback = used_fallback or completion.used_fallback
            if completion.used_fallback:
                active_model = completion.model

            # Step 2: Execute and emit each requested tool immediately.
            if completion.message.tool_calls:
                messages.append(completion.message.model_dump(exclude_none=True))

                for tool_call in completion.message.tool_calls:
                    if tool_call.type != "function":
                        continue

                    execution = await self._tools.execute(
                        tool_call.function.name,
                        tool_call.function.arguments,
                    )
                    executions.append(execution)
                    trajectory.append(
                        AgentStep(
                            iteration=iteration,
                            action="tool",
                            tool_name=execution.name,
                            success=execution.success,
                        )
                    )
                    messages.append(self._build_tool_message(tool_call.id, execution))
                    yield AgentToolEvent(execution=execution)
                continue

            # Step 3: Stream the final natural-language answer from the provider.
            answer_parts: list[str] = []
            final_model = completion.model
            final_messages = self._build_stream_final_messages(messages)

            async for chunk in self._llm.stream_text(
                final_messages,
                model=active_model,
            ):
                final_model = chunk.model
                used_fallback = used_fallback or chunk.used_fallback
                token_usage += chunk.usage
                if chunk.content:
                    answer_parts.append(chunk.content)
                    yield AgentDeltaEvent(content=chunk.content)

            answer = "".join(answer_parts).strip()
            if not answer:
                raise LLMError("Model returned an empty streamed answer")

            # Step 4: Validate metadata after the visible answer has finished.
            metadata_messages = [
                *messages,
                {"role": "assistant", "content": answer},
                {
                    "role": "user",
                    "content": (
                        "Return only structured metadata for the answer above: "
                        "cited chunk IDs, up to three ready-to-send next messages "
                        "written in the user's voice, and confidence. Do not "
                        "rewrite the answer or phrase suggestions as offers from "
                        "the assistant."
                    ),
                },
            ]
            metadata_completion = await self._llm.complete(
                metadata_messages,
                response_model=AssistantMetadata,
                model=final_model,
            )
            token_usage += metadata_completion.usage
            used_fallback = used_fallback or metadata_completion.used_fallback
            if metadata_completion.parsed is None:
                raise LLMError("Model did not return structured stream metadata")

            trajectory.append(AgentStep(iteration=iteration, action="answer"))
            yield AgentCompleteEvent(
                answer=answer,
                metadata=metadata_completion.parsed,
                tools_used=executions,
                model=metadata_completion.model,
                used_fallback=used_fallback,
                iterations=iteration,
                trajectory=trajectory,
                token_usage=token_usage,
            )
            return

        raise LLMError("Maximum tool-call iterations reached")

    @staticmethod
    def _build_stream_final_messages(
        messages: list[ChatMessageParam],
    ) -> list[ChatMessageParam]:
        """Convert tool protocol messages into context for the prose pass."""

        final_messages: list[ChatMessageParam] = []
        tool_results: list[str] = []

        # Step 1: Separate tool observations from normal conversation messages.
        for message in messages:
            if message.get("role") == "tool":
                content = message.get("content")
                if content:
                    tool_results.append(str(content))
                continue

            if message.get("role") == "assistant" and message.get("tool_calls"):
                continue

            final_messages.append(message)

        # Step 2: Add the observations as read-only context for the prose response.
        final_messages.append(
            {
                "role": "user",
                "content": (
                    "Answer the original question now using the available context "
                    "and tool results below. Do not call any tools.\n\n"
                    f"Tool results:\n{json.dumps(tool_results)}"
                ),
            }
        )
        return final_messages

    @staticmethod
    def _build_messages(
        question: str,
        history: list[ChatMessage] | None,
        context: str | None,
    ) -> list[ChatMessageParam]:
        messages: list[ChatMessageParam] = [
            {"role": "system", "content": build_system_prompt(context)}
        ]
        messages.extend(message.model_dump() for message in history or [])
        messages.append({"role": "user", "content": question})
        return messages

    async def _execute_tools(
        self,
        assistant_message: ChatCompletionMessage,
        messages: list[ChatMessageParam],
        executions: list[ToolExecution],
    ) -> list[ToolExecution]:
        # Step 1: Preserve the assistant's tool request in conversation history.
        messages.append(assistant_message.model_dump(exclude_none=True))
        iteration_executions: list[ToolExecution] = []

        # Step 2: Execute each valid function call and record its full result.
        for tool_call in assistant_message.tool_calls or []:
            if tool_call.type != "function":
                continue

            execution = await self._tools.execute(
                tool_call.function.name,
                tool_call.function.arguments,
            )
            executions.append(execution)
            iteration_executions.append(execution)
            messages.append(self._build_tool_message(tool_call.id, execution))

        # Step 3: Return this iteration's executions for trajectory tracking.
        return iteration_executions

    def _build_tool_message(
        self,
        tool_call_id: str,
        execution: ToolExecution,
    ) -> ChatMessageParam:
        """Keep a bounded structured observation in the model context."""

        # Step 1: Cap verbose output before returning it to the model context.
        output = execution.output
        truncated = len(output) > self._tool_result_max_characters
        if truncated:
            output = output[: self._tool_result_max_characters] + "... [truncated]"

        # Step 2: Preserve the information needed to judge the observation.
        note = {
            "tool": execution.name,
            "success": execution.success,
            "arguments": execution.arguments,
            "evidence": output,
            "truncated": truncated,
        }

        # Step 3: Attach the observation to the matching tool-call ID.
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": json.dumps(note),
        }
