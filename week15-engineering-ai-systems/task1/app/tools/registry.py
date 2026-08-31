from __future__ import annotations

import inspect
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from openai.types.chat import ChatCompletionToolParam
from pydantic import BaseModel, ValidationError

from app.schemas.chat import ToolExecution

ToolHandler = Callable[[BaseModel], str | Awaitable[str]]


@dataclass(frozen=True, slots=True)
class RegisteredTool:
    name: str
    description: str
    input_model: type[BaseModel]
    handler: ToolHandler

    def as_chat_tool(self) -> ChatCompletionToolParam:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_model.model_json_schema(),
                "strict": True,
            },
        }


class ToolRegistry:
    def __init__(self, tools: list[RegisteredTool] | None = None) -> None:
        self._tools = {tool.name: tool for tool in tools or []}

    def schemas(self) -> list[ChatCompletionToolParam]:
        return [tool.as_chat_tool() for tool in self._tools.values()]

    async def execute(self, name: str, raw_arguments: str) -> ToolExecution:
        tool = self._tools.get(name)
        if tool is None:
            return ToolExecution(
                name=name,
                arguments={},
                output=f"Unknown tool: {name}",
                success=False,
            )

        arguments: object = {}
        try:
            arguments = json.loads(raw_arguments)
            validated = tool.input_model.model_validate(arguments)
            result = tool.handler(validated)
            output = await result if inspect.isawaitable(result) else result
            return ToolExecution(
                name=name,
                arguments=validated.model_dump(),
                output=output,
                success=True,
            )
        except (
            json.JSONDecodeError,
            ValidationError,
            ValueError,
            ArithmeticError,
        ) as exc:
            arguments = arguments if isinstance(arguments, dict) else {}
            return ToolExecution(
                name=name,
                arguments=arguments,
                output=f"Tool error: {exc}",
                success=False,
            )
