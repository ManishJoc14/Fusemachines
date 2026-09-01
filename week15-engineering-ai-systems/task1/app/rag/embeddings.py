from __future__ import annotations

import asyncio

from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Create normalized local embeddings without blocking the event loop."""

    def __init__(
        self,
        model_name: str,
        *,
        device: str,
        batch_size: int,
        expected_dimension: int,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._batch_size = batch_size
        self._expected_dimension = expected_dimension
        self._model: SentenceTransformer | None = None

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await asyncio.to_thread(self._encode, texts)

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self.embed_documents([text])
        return vectors[0]

    def _encode(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:
            self._model = SentenceTransformer(self._model_name, device=self._device)

        vectors = self._model.encode(
            texts,
            batch_size=self._batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        if vectors.shape[1] != self._expected_dimension:
            raise ValueError(
                "Embedding dimension mismatch: "
                f"expected {self._expected_dimension}, got {vectors.shape[1]}"
            )
        return vectors.tolist()
