from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import chat, documents, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, tags=["assistant"])
api_router.include_router(documents.router, tags=["documents"])
