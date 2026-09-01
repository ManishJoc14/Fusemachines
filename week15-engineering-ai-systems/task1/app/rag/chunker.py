from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from app.schemas.document import DocumentChunk


class TextChunker:
    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")

        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be between 0 and chunk_size")

        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def split(
        self,
        text: str,
        *,
        document_id: str,
        document_name: str,
    ) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        start = 0

        while start < len(text):
            hard_end = min(start + self._chunk_size, len(text))
            end = self._find_natural_boundary(text, start, hard_end)
            raw_chunk = text[start:end]
            leading_whitespace = len(raw_chunk) - len(raw_chunk.lstrip())
            clean_text = raw_chunk.strip()

            if clean_text:
                char_start = start + leading_whitespace
                char_end = char_start + len(clean_text)
                chunk_index = len(chunks)
                chunk_id = str(uuid5(NAMESPACE_URL, f"{document_id}:{chunk_index}"))
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        document_name=document_name,
                        chunk_index=chunk_index,
                        text=clean_text,
                        char_start=char_start,
                        char_end=char_end,
                    )
                )

            if end >= len(text):
                break
            start = max(start + 1, end - self._chunk_overlap)

        return chunks

    def _find_natural_boundary(self, text: str, start: int, hard_end: int) -> int:
        if hard_end == len(text):
            return hard_end

        earliest_boundary = start + self._chunk_size // 2
        for separator in ("\n\n", ". ", " "):
            position = text.rfind(separator, earliest_boundary, hard_end)
            if position != -1:
                return position + len(separator)

        return hard_end
