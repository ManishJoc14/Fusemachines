from __future__ import annotations

from app.rag.embeddings import EmbeddingService
from app.rag.vector_store import VectorStore
from app.schemas.document import RetrievedChunk


class Retriever:
    def __init__(
        self,
        embeddings: EmbeddingService,
        vector_store: VectorStore,
        *,
        top_k: int,
        score_threshold: float,
    ) -> None:
        self._embeddings = embeddings
        self._vector_store = vector_store
        self._top_k = top_k
        self._score_threshold = score_threshold

    async def retrieve(self, query: str) -> list[RetrievedChunk]:
        """Embed a question and retrieve its nearest document chunks."""

        # Step 1: Represent the question in the same vector space as documents.
        query_vector = await self._embeddings.embed_query(query)

        # Step 2: Apply the configured result limit and relevance threshold.
        return await self._vector_store.search(
            query_vector,
            limit=self._top_k,
            score_threshold=self._score_threshold,
        )

    @staticmethod
    def format_context(chunks: list[RetrievedChunk]) -> str | None:
        """Format evidence with chunk IDs that the model can cite."""

        if not chunks:
            return None

        sections = [
            (
                f"[chunk_id={chunk.chunk_id} document={chunk.document_name}]\n"
                f"{chunk.text}"
            )
            for chunk in chunks
        ]
        return "\n\n".join(sections)
