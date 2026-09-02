from __future__ import annotations

import json
from dataclasses import dataclass

from openai.types.chat import ChatCompletionMessage

from app.assistant.prompts import build_system_prompt
from app.core.config import Settings
from app.llm.client import ChatMessageParam, LLMClient, LLMError
from app.schemas.chat import AssistantOutput, ChatMessage, ToolExecution
from app.tools.registry import ToolRegistry


@dataclass(frozen=True, slots=True)
class AgentResult:
    output: AssistantOutput
    tools_used: list[ToolExecution]
    model: str
    used_fallback: bool


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

        for _ in range(self._max_iterations):
            # Step 2: Let the model select any tools it needs.
            completion = await self._llm.complete(
                messages,
                response_model=AssistantOutput,
                tools=self._tools.schemas(),
                model=active_model,
            )
            used_fallback = used_fallback or completion.used_fallback
            if completion.used_fallback:
                # Once fallback starts, keep later tool-loop turns on that model.
                active_model = completion.model

            # Step 3: Execute requested tools and return their results to the model.
            if completion.message.tool_calls:
                await self._execute_tools(
                    completion.message,
                    messages,
                    executions,
                )
                continue

            # Step 4: Request JSON separately because some providers cannot
            # combine structured output with tool calling in one request.
            final_completion = await self._llm.complete(
                messages,
                response_model=AssistantOutput,
                model=active_model,
            )
            used_fallback = used_fallback or final_completion.used_fallback

            if final_completion.parsed is None:
                raise LLMError("Model did not return a structured final answer")

            # Step 5: Return the validated answer and execution metadata.
            return AgentResult(
                output=final_completion.parsed,
                tools_used=executions,
                model=final_completion.model,
                used_fallback=used_fallback,
            )

        raise LLMError("Maximum tool-call iterations reached")

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
    ) -> None:
        messages.append(assistant_message.model_dump(exclude_none=True))

        for tool_call in assistant_message.tool_calls or []:
            execution = await self._tools.execute(
                tool_call.function.name,
                tool_call.function.arguments,
            )
            executions.append(execution)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(execution.model_dump()),
                }
            )
