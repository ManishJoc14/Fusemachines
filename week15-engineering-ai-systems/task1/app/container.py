from __future__ import annotations

import asyncio

from app.assistant.agent import AssistantAgent
from app.core.config import Settings
from app.llm.client import LLMClient
from app.rag.chunker import TextChunker
from app.rag.embeddings import EmbeddingService
from app.rag.loader import DocumentLoader
from app.rag.retriever import Retriever
from app.rag.vector_store import VectorStore
from app.services.chat import ChatService
from app.services.ingestion import IngestionService
from app.tools.builtin import create_default_tool_registry


class ApplicationContainer:
    """Construct and own the shared services used by API requests."""

    def __init__(self, settings: Settings) -> None:
        # Step 1: Create clients shared for the application's lifetime.
        self.llm_client = LLMClient(settings)
        self.vector_store = VectorStore(settings)

        # Step 2: Assemble the retrieval pipeline.
        embeddings = EmbeddingService(
            settings.embedding_model,
            device=settings.embedding_device,
            batch_size=settings.embedding_batch_size,
            expected_dimension=settings.embedding_dimension,
        )
        retriever = Retriever(
            embeddings,
            self.vector_store,
            top_k=settings.rag_retrieval_top_k,
            score_threshold=settings.rag_score_threshold,
        )

        # Step 3: Assemble the model and tool-calling pipeline.
        agent = AssistantAgent(
            self.llm_client,
            create_default_tool_registry(),
            settings,
        )

        # Step 4: Expose use-case services consumed by API endpoints.
        self.chat_service = ChatService(retriever, agent)
        self.ingestion_service = IngestionService(
            DocumentLoader(),
            TextChunker(settings.rag_chunk_size, settings.rag_chunk_overlap),
            embeddings,
            self.vector_store,
            max_upload_size_mb=settings.max_upload_size_mb,
        )

    async def close(self) -> None:
        await asyncio.gather(
            self.llm_client.close(),
            self.vector_store.close(),
        )
