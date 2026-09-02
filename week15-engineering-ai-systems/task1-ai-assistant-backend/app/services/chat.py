from __future__ import annotations

from app.assistant.agent import AssistantAgent
from app.rag.retriever import Retriever
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    PipelineStats,
    SourceReference,
)
from app.schemas.document import RetrievedChunk


class ChatService:
    def __init__(self, retriever: Retriever, agent: AssistantAgent) -> None:
        self._retriever = retriever
        self._agent = agent

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Answer a message using retrieval, tools, and structured generation.

        Pipeline:
        1. Retrieve relevant document chunks when RAG is enabled.
        2. Build a clearly delimited context for the model.
        3. Run the model and tool-calling loop.
        4. Verify citations and build the API response.
        """

        # Step 1: Retrieve evidence for the user's question.
        retrieved_chunks = (
            await self._retriever.retrieve(request.message) if request.use_rag else []
        )

        # Step 2: Convert retrieved chunks into bounded prompt context.
        context = self._retriever.format_context(retrieved_chunks)

        # Step 3: Generate a validated answer, executing tools when requested.
        agent_result = await self._agent.run(
            request.message,
            history=request.history,
            context=context,
        )

        # Step 4: Keep only citations that came from our retrieval result.
        sources = self._build_sources(
            agent_result.output.cited_chunk_ids,
            retrieved_chunks,
        )

        return ChatResponse(
            answer=agent_result.output.answer,
            confidence=agent_result.output.confidence,
            follow_up_questions=agent_result.output.follow_up_questions,
            sources=sources,
            tools_used=agent_result.tools_used,
            model=agent_result.model,
            used_fallback=agent_result.used_fallback,
            pipeline_stats=PipelineStats(
                retrieval_strategy="dense_cosine" if request.use_rag else "disabled",
                retrieved_chunks=len(retrieved_chunks),
                cited_chunks=len(sources),
                tool_executions=len(agent_result.tools_used),
            ),
        )

    @staticmethod
    def _build_sources(
        cited_chunk_ids: list[str],
        retrieved_chunks: list[RetrievedChunk],
    ) -> list[SourceReference]:
        """Discard invented and duplicate chunk IDs before returning citations."""

        chunks_by_id = {chunk.chunk_id: chunk for chunk in retrieved_chunks}
        sources: list[SourceReference] = []
        seen_ids: set[str] = set()

        for chunk_id in cited_chunk_ids:
            chunk = chunks_by_id.get(chunk_id)
            if chunk is None or chunk_id in seen_ids:
                continue

            seen_ids.add(chunk_id)
            sources.append(
                SourceReference(
                    chunk_id=chunk.chunk_id,
                    document_name=chunk.document_name,
                    chunk_index=chunk.chunk_index,
                    score=chunk.score,
                    text_preview=ChatService._preview(chunk.text),
                )
            )

        return sources

    @staticmethod
    def _preview(text: str, max_characters: int = 200) -> str:
        if len(text) <= max_characters:
            return text
        return text[:max_characters].rstrip() + "..."
