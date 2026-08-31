from __future__ import annotations

import json

from app.assistant.prompts import build_system_prompt
from app.core.config import Settings
from app.llm.client import ChatMessageParam, LLMClient, LLMError
from app.schemas.chat import AssistantOutput, ChatMessage, ToolExecution
from app.tools.registry import ToolRegistry


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
    ) -> tuple[AssistantOutput, list[ToolExecution], str, bool]:
        messages: list[ChatMessageParam] = [
            {"role": "system", "content": build_system_prompt(context)}
        ]
        messages.extend(message.model_dump() for message in history or [])
        messages.append({"role": "user", "content": question})

        executions: list[ToolExecution] = []
        active_model: str | None = None
        used_fallback = False

        for _ in range(self._max_iterations):
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

            if completion.message.tool_calls:
                messages.append(completion.message.model_dump(exclude_none=True))
                for tool_call in completion.message.tool_calls:
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
                continue

            if completion.parsed is None:
                raise LLMError("Model returned neither tool calls nor a final answer")

            return completion.parsed, executions, completion.model, used_fallback

        raise LLMError("Maximum tool-call iterations reached")
