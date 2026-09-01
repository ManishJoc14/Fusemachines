from __future__ import annotations

from qdrant_client import AsyncQdrantClient, models

from app.core.config import Settings
from app.schemas.document import DocumentChunk, RetrievedChunk


class VectorStore:
    UPSERT_BATCH_SIZE = 100

    def __init__(self, settings: Settings) -> None:
        api_key = (
            settings.qdrant_api_key.get_secret_value()
            if settings.qdrant_api_key
            else None
        )
        self._client = AsyncQdrantClient(
            url=str(settings.qdrant_url),
            api_key=api_key or None,
        )
        self._collection = settings.qdrant_collection
        self._dimension = settings.embedding_dimension

    async def close(self) -> None:
        await self._client.close()

    async def ensure_collection(self) -> None:
        if await self._client.collection_exists(self._collection):
            return

        await self._client.create_collection(
            collection_name=self._collection,
            vectors_config=models.VectorParams(
                size=self._dimension,
                distance=models.Distance.COSINE,
            ),
        )

    async def replace_document(
        self,
        document_id: str,
        chunks: list[DocumentChunk],
        vectors: list[list[float]],
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("Every chunk must have exactly one embedding")

        await self.ensure_collection()
        await self._client.delete(
            collection_name=self._collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
            wait=True,
        )

        points = [
            models.PointStruct(
                id=chunk.chunk_id,
                vector=vector,
                payload=chunk.model_dump(),
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        for start in range(0, len(points), self.UPSERT_BATCH_SIZE):
            await self._client.upsert(
                collection_name=self._collection,
                points=points[start : start + self.UPSERT_BATCH_SIZE],
                wait=True,
            )

    async def search(
        self,
        query_vector: list[float],
        *,
        limit: int,
        score_threshold: float,
    ) -> list[RetrievedChunk]:
        await self.ensure_collection()
        response = await self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=False,
        )

        results: list[RetrievedChunk] = []
        for point in response.points:
            payload = dict(point.payload or {})
            payload["score"] = point.score
            results.append(RetrievedChunk.model_validate(payload))
        return results
