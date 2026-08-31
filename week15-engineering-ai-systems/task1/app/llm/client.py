from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, cast

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    InternalServerError,
    RateLimitError,
)
from openai.types.chat import ChatCompletionMessage, ChatCompletionToolParam
from pydantic import BaseModel, ValidationError

from app.core.config import LLMBackend, Settings

logger = logging.getLogger(__name__)

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)
ChatMessageParam = dict[str, Any]


class LLMError(RuntimeError):
    """Raised when neither the primary nor fallback model can respond."""


@dataclass(frozen=True, slots=True)
class LLMCompletion(Generic[ResponseModelT]):
    message: ChatCompletionMessage
    parsed: ResponseModelT | None
    model: str
    used_fallback: bool


class LLMClient:
    """OpenAI-compatible client for Hugging Face Router and local vLLM."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

        if settings.llm_backend is LLMBackend.HUGGINGFACE:
            if settings.hf_token is None:  # Guard for static type narrowing.
                raise ValueError("HF_TOKEN is required for the Hugging Face backend")
            api_key = settings.hf_token.get_secret_value()
            base_url = str(settings.hf_base_url).rstrip("/")
            self._models = [settings.hf_model, settings.hf_fallback_model]
        else:
            api_key = settings.vllm_api_key.get_secret_value()
            base_url = str(settings.vllm_base_url).rstrip("/")
            self._models = [settings.vllm_model]

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=1,
        )

    async def close(self) -> None:
        await self._client.close()

    async def complete(
        self,
        messages: list[ChatMessageParam],
        *,
        response_model: type[ResponseModelT],
        tools: list[ChatCompletionToolParam] | None = None,
        model: str | None = None,
    ) -> LLMCompletion[ResponseModelT]:
        """Call a model and validate final content against a Pydantic schema."""

        candidate_models = [model] if model else self._models
        errors: list[str] = []

        for candidate in candidate_models:
            try:
                completion = await self._client.chat.completions.create(
                    model=candidate,
                    messages=cast(Any, messages),
                    tools=tools,
                    tool_choice="auto" if tools else None,
                    response_format=self._response_format(response_model),
                    temperature=self._settings.llm_temperature,
                    top_p=self._settings.llm_top_p,
                    max_tokens=self._settings.llm_max_output_tokens,
                )
                message = completion.choices[0].message

                # A tool-call turn intentionally has no final structured answer yet.
                parsed = None
                if not message.tool_calls:
                    parsed = self._parse_response(message.content, response_model)

                return LLMCompletion(
                    message=message,
                    parsed=parsed,
                    model=candidate,
                    used_fallback=candidate != self._models[0],
                )
            except (
                APIConnectionError,
                APITimeoutError,
                InternalServerError,
                RateLimitError,
                json.JSONDecodeError,
                ValidationError,
                ValueError,
            ) as exc:
                errors.append(f"{candidate}: {exc}")
                logger.warning("LLM attempt failed for model %s: %s", candidate, exc)

        raise LLMError("All configured models failed: " + " | ".join(errors))

    @staticmethod
    def _response_format(response_model: type[BaseModel]) -> Any:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": response_model.__name__,
                "strict": True,
                "schema": response_model.model_json_schema(),
            },
        }

    @staticmethod
    def _parse_response(
        content: str | None,
        response_model: type[ResponseModelT],
    ) -> ResponseModelT:
        if not content:
            raise ValueError("Model returned an empty response")
        return response_model.model_validate_json(content)
