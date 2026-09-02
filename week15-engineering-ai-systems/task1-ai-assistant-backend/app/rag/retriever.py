from __future__ import annotations

from app.rag.embeddings import EmbeddingService
from app.rag.vector_store import CloudInferenceUnavailable, VectorStore
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

        # Step 1: Prefer the managed model used during cloud ingestion.
        try:
            return await self._vector_store.search_text(
                query,
                limit=self._top_k,
                score_threshold=self._score_threshold,
            )
        except CloudInferenceUnavailable:
            # Step 2: Fall back to the equivalent local embedding model.
            query_vector = await self._embeddings.embed_query(query)
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
