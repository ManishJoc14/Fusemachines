from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

from app.rag.chunker import TextChunker
from app.rag.embeddings import EmbeddingService
from app.rag.loader import DocumentLoader
from app.rag.vector_store import VectorStore
from app.schemas.document import IngestionResult


class IngestionService:
    def __init__(
        self,
        loader: DocumentLoader,
        chunker: TextChunker,
        embeddings: EmbeddingService,
        vector_store: VectorStore,
        *,
        max_upload_size_mb: int,
    ) -> None:
        self._loader = loader
        self._chunker = chunker
        self._embeddings = embeddings
        self._vector_store = vector_store
        self._max_upload_bytes = max_upload_size_mb * 1024 * 1024

    async def ingest(self, path: Path) -> IngestionResult:
        file_metadata = await asyncio.to_thread(path.stat)
        if file_metadata.st_size > self._max_upload_bytes:
            raise ValueError("Document exceeds the configured upload size limit")

        document = await self._loader.load(path)
        document_id = hashlib.sha256(document.text.encode("utf-8")).hexdigest()
        chunks = self._chunker.split(
            document.text,
            document_id=document_id,
            document_name=document.name,
        )
        vectors = await self._embeddings.embed_documents(
            [chunk.text for chunk in chunks]
        )
        await self._vector_store.replace_document(document_id, chunks, vectors)

        return IngestionResult(
            document_id=document_id,
            document_name=document.name,
            character_count=len(document.text),
            chunk_count=len(chunks),
        )
