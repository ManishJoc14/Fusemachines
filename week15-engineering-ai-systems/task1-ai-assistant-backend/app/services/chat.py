from __future__ import annotations

import re
from collections.abc import AsyncIterator

from app.assistant.agent import (
    AgentCompleteEvent,
    AgentDeltaEvent,
    AgentToolEvent,
    AssistantAgent,
)
from app.rag.retriever import Retriever
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatStreamComplete,
    ChatStreamDelta,
    ChatStreamEvent,
    ChatStreamStatus,
    ChatStreamTool,
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

        retrieved_chunks = await self._retrieve(request)
        return await self._generate_response(request, retrieved_chunks)

    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatStreamEvent]:
        """Stream pipeline progress followed by a validated assistant response."""

        # Step 1: Tell the client when document retrieval begins.
        if request.use_rag:
            yield ChatStreamStatus(
                stage="retrieving",
                message="Searching relevant documents",
            )
        retrieved_chunks = await self._retrieve(request)

        # Step 2: Stream tool activity and answer text from the agent.
        yield ChatStreamStatus(
            stage="generating",
            message="Generating an answer",
        )
        context = self._retriever.format_context(retrieved_chunks)

        async for agent_event in self._agent.stream(
            request.message,
            history=request.history,
            context=context,
        ):
            if isinstance(agent_event, AgentToolEvent):
                yield ChatStreamTool(tool=agent_event.execution)
                continue

            if isinstance(agent_event, AgentDeltaEvent):
                yield ChatStreamDelta(content=agent_event.content)
                continue

            if isinstance(agent_event, AgentCompleteEvent):
                sources = self._build_sources(
                    agent_event.metadata.cited_chunk_ids,
                    retrieved_chunks,
                )
                response = ChatResponse(
                    answer=self._format_citations(agent_event.answer, sources),
                    confidence=agent_event.metadata.confidence,
                    follow_up_questions=agent_event.metadata.follow_up_questions,
                    sources=sources,
                    tools_used=agent_event.tools_used,
                    model=agent_event.model,
                    used_fallback=agent_event.used_fallback,
                    pipeline_stats=PipelineStats(
                        retrieval_strategy=(
                            "dense_cosine" if request.use_rag else "disabled"
                        ),
                        retrieved_chunks=len(retrieved_chunks),
                        cited_chunks=len(sources),
                        tool_executions=len(agent_event.tools_used),
                    ),
                )
                yield ChatStreamComplete(response=response)

    async def _retrieve(self, request: ChatRequest) -> list[RetrievedChunk]:
        if not request.use_rag:
            return []
        return await self._retriever.retrieve(request.message)

    async def _generate_response(
        self,
        request: ChatRequest,
        retrieved_chunks: list[RetrievedChunk],
    ) -> ChatResponse:
        """Generate the final response from already retrieved document chunks."""

        # Step 1: Convert retrieved chunks into bounded prompt context.
        context = self._retriever.format_context(retrieved_chunks)

        # Step 2: Generate a validated answer, executing tools when requested.
        agent_result = await self._agent.run(
            request.message,
            history=request.history,
            context=context,
        )

        # Step 3: Keep only citations that came from our retrieval result.
        sources = self._build_sources(
            agent_result.output.cited_chunk_ids,
            retrieved_chunks,
        )

        return ChatResponse(
            answer=self._format_citations(agent_result.output.answer, sources),
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

        chunks_by_id = {
            chunk.chunk_id: (source_number, chunk)
            for source_number, chunk in enumerate(retrieved_chunks, start=1)
        }
        sources: list[SourceReference] = []
        seen_ids: set[str] = set()

        for chunk_id in cited_chunk_ids:
            source = chunks_by_id.get(chunk_id)
            if source is None or chunk_id in seen_ids:
                continue

            citation_number, chunk = source
            seen_ids.add(chunk_id)
            sources.append(
                SourceReference(
                    citation_number=citation_number,
                    chunk_id=chunk.chunk_id,
                    document_name=chunk.document_name,
                    chunk_index=chunk.chunk_index,
                    score=chunk.score,
                    text=chunk.text,
                )
            )

        return sources

    @staticmethod
    def _format_citations(answer: str, sources: list[SourceReference]) -> str:
        """Convert provider citation variations into compact inline numbers."""

        # Step 1: Replace internal IDs if the model exposes them.
        for source in sources:
            citation = f"[{source.citation_number}]"
            answer = answer.replace(f"【{source.chunk_id}】", citation)
            answer = answer.replace(f"[{source.chunk_id}]", citation)

        # Step 2: Convert verbose source lines such as
        # "Source: document chunks 2 and 4." into "[2][4]".
        available_numbers = {source.citation_number for source in sources}

        def replace_source_line(match: re.Match[str]) -> str:
            mentioned_numbers = [
                int(number) for number in re.findall(r"\d+", match.group(1))
            ]
            citations = [
                f"[{number}]"
                for number in mentioned_numbers
                if number in available_numbers
            ]
            return " " + "".join(citations) if citations else ""

        answer = re.sub(
            r"\\?\s*\n?\s*\*{0,2}Source:\s*document\s+chunks?\s+"
            r"([\d,\sand]+)\.?\*{0,2}",
            replace_source_line,
            answer,
            flags=re.IGNORECASE,
        )

        # Step 3: Remove model-generated Markdown hard-break escapes.
        answer = answer.replace("\\\n", "\n")
        return answer
