from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_chat_service
from app.llm.client import LLMError
from app.schemas.chat import ChatRequest, ChatResponse, ChatStreamError, ChatStreamEvent
from app.services.chat import ChatService

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    try:
        return await service.chat(request)
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post("/chat/stream", response_class=StreamingResponse)
async def stream_chat(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    """Stream assistant progress and results as Server-Sent Events."""

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for event in service.stream(request):
                yield _format_sse(event)
        except LLMError as exc:
            yield _format_sse(ChatStreamError(message=str(exc)))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _format_sse(event: ChatStreamEvent) -> str:
    """Serialize one typed event using the SSE wire format."""

    return f"event: {event.type}\ndata: {event.model_dump_json()}\n\n"
