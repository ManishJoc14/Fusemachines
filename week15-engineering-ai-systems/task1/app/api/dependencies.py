from __future__ import annotations

from typing import cast

from fastapi import Request

from app.container import ApplicationContainer
from app.services.chat import ChatService
from app.services.ingestion import IngestionService


def get_container(request: Request) -> ApplicationContainer:
    return cast(ApplicationContainer, request.app.state.container)


def get_chat_service(request: Request) -> ChatService:
    return get_container(request).chat_service


def get_ingestion_service(request: Request) -> IngestionService:
    return get_container(request).ingestion_service
