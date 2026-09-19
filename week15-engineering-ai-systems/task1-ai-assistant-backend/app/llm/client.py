from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar, cast

from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    InternalServerError,
    RateLimitError,
)
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessage,
    ChatCompletionToolParam,
)
from pydantic import BaseModel, ValidationError

from app.core.config import LLMBackend, Settings

logger = logging.getLogger(__name__)

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)
ChatMessageParam = dict[str, Any]


class LLMError(RuntimeError):
    """Raised when neither the primary nor fallback model can respond."""


@dataclass(frozen=True, slots=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


@dataclass(frozen=True, slots=True)
class LLMCompletion(Generic[ResponseModelT]):
    message: ChatCompletionMessage
    parsed: ResponseModelT | None
    model: str
    used_fallback: bool
    usage: TokenUsage


@dataclass(frozen=True, slots=True)
class LLMTextChunk:
    content: str
    model: str
    used_fallback: bool
    is_complete: bool = False
    usage: TokenUsage = field(default_factory=TokenUsage)


@dataclass(frozen=True, slots=True)
class _BackendConfig:
    api_key: str
    base_url: str
    models: list[str]


class LLMClient:
    """OpenAI-compatible client for Hugging Face Router and local vLLM."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        backend = self._backend_config(settings)
        self._models = backend.models
        self._client = AsyncOpenAI(
            api_key=backend.api_key,
            base_url=backend.base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=1,
        )

    async def close(self) -> None:
        await self._client.close()

    @staticmethod
    def _backend_config(settings: Settings) -> _BackendConfig:
        if settings.llm_backend is LLMBackend.HUGGINGFACE:
            if settings.hf_token is None:  # Guard for static type narrowing.
                raise ValueError("HF_TOKEN is required for the Hugging Face backend")
            return _BackendConfig(
                api_key=settings.hf_token.get_secret_value(),
                base_url=str(settings.hf_base_url).rstrip("/"),
                models=[settings.hf_model, settings.hf_fallback_model],
            )

        return _BackendConfig(
            api_key=settings.vllm_api_key.get_secret_value(),
            base_url=str(settings.vllm_base_url).rstrip("/"),
            models=[settings.vllm_model],
        )

    async def complete(
        self,
        messages: list[ChatMessageParam],
        *,
        response_model: type[ResponseModelT],
        tools: list[ChatCompletionToolParam] | None = None,
        model: str | None = None,
    ) -> LLMCompletion[ResponseModelT]:
        """Try configured models until one returns tools or valid structured output."""

        candidate_models = self._candidate_models(model)
        errors: list[str] = []

        for candidate in candidate_models:
            try:
                # Step 1: Send the conversation and schema to this model.
                response = await self._request(
                    candidate,
                    messages,
                    response_model,
                    tools,
                )
                message = response.choices[0].message

                # Step 2: Validate content when this is a final-answer turn.
                parsed = self._parse_final_answer(
                    message,
                    response_model,
                    tools_enabled=bool(tools),
                )

                # Step 3: Return the SDK message and validated model output.
                return LLMCompletion(
                    message=message,
                    parsed=parsed,
                    model=candidate,
                    used_fallback=candidate != self._models[0],
                    usage=self._read_usage(response),
                )
            except (
                APIError,
                APIConnectionError,
                APIStatusError,
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

    async def stream_text(
        self,
        messages: list[ChatMessageParam],
        *,
        model: str | None = None,
    ) -> AsyncIterator[LLMTextChunk]:
        """Stream plain text from the first available configured model."""

        errors: list[str] = []

        for candidate in self._candidate_models(model):
            received_content = False
            stream_usage = TokenUsage()

            try:
                # Step 1: Open a streaming request with the current model.
                stream = await self._client.chat.completions.create(
                    model=candidate,
                    messages=cast(Any, messages),
                    temperature=self._settings.llm_temperature,
                    top_p=self._settings.llm_top_p,
                    max_tokens=self._settings.llm_max_output_tokens,
                    stream=True,
                    stream_options={"include_usage": True},
                )

                # Step 2: Forward text chunks as soon as they arrive.
                async for chunk in stream:
                    stream_usage += self._read_usage(chunk)
                    if not chunk.choices:
                        continue

                    content = chunk.choices[0].delta.content
                    if not content:
                        continue

                    received_content = True
                    yield LLMTextChunk(
                        content=content,
                        model=candidate,
                        used_fallback=candidate != self._models[0],
                    )

                # Step 3: Emit a marker so callers know the stream completed.
                yield LLMTextChunk(
                    content="",
                    model=candidate,
                    used_fallback=candidate != self._models[0],
                    is_complete=True,
                    usage=stream_usage,
                )
                return
            except (
                APIError,
                APIConnectionError,
                APIStatusError,
                APITimeoutError,
                InternalServerError,
                RateLimitError,
            ) as exc:
                # Step 4: Fall back only if no partial answer was already emitted.
                if received_content:
                    raise LLMError(
                        f"Model stream interrupted after output began: {exc}"
                    ) from exc

                errors.append(f"{candidate}: {exc}")
                logger.warning("LLM stream failed for model %s: %s", candidate, exc)

        raise LLMError("All configured models failed: " + " | ".join(errors))

    def _candidate_models(self, requested_model: str | None) -> list[str]:
        return [requested_model] if requested_model else self._models

    async def _request(
        self,
        model: str,
        messages: list[ChatMessageParam],
        response_model: type[BaseModel],
        tools: list[ChatCompletionToolParam] | None,
    ) -> ChatCompletion:
        # Step 1: Use tool mode only while the agent is planning an action.
        if tools:
            completion = await self._request_with_tools(model, messages, tools)
        else:
            # Step 2: Use JSON Schema mode for the final validated response.
            completion = await self._request_structured_output(
                model,
                messages,
                response_model,
            )

        return completion

    @staticmethod
    def _read_usage(
        completion: ChatCompletion | ChatCompletionChunk,
    ) -> TokenUsage:
        # Some OpenAI-compatible providers omit usage from their responses.
        usage = completion.usage
        if usage is None:
            return TokenUsage()
        return TokenUsage(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
        )

    async def _request_with_tools(
        self,
        model: str,
        messages: list[ChatMessageParam],
        tools: list[ChatCompletionToolParam],
    ) -> ChatCompletion:
        """Ask the model to either call a tool or continue without one."""

        return await self._client.chat.completions.create(
            model=model,
            messages=cast(Any, messages),
            tools=tools,
            tool_choice="auto",
            temperature=self._settings.llm_temperature,
            top_p=self._settings.llm_top_p,
            max_tokens=self._settings.llm_max_output_tokens,
        )

    async def _request_structured_output(
        self,
        model: str,
        messages: list[ChatMessageParam],
        response_model: type[BaseModel],
    ) -> ChatCompletion:
        """Ask for JSON without sending tool fields to the provider."""

        return await self._client.chat.completions.create(
            model=model,
            messages=cast(Any, messages),
            response_format=self._response_format(response_model),
            temperature=self._settings.llm_temperature,
            top_p=self._settings.llm_top_p,
            max_tokens=self._settings.llm_max_output_tokens,
        )

    def _parse_final_answer(
        self,
        message: ChatCompletionMessage,
        response_model: type[ResponseModelT],
        *,
        tools_enabled: bool,
    ) -> ResponseModelT | None:
        # Tool-selection turns cannot also use JSON mode on some providers.
        if tools_enabled:
            return None
        return self._parse_response(message.content, response_model)

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
