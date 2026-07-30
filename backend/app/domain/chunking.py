import re
from dataclasses import dataclass

_CONTEXT_TAIL_CHARS = 200


@dataclass(frozen=True)
class ChunkData:
    order_index: int
    raw_text: str
    context_tail: str | None


def chunk_document(text: str) -> list[ChunkData]:
    """Splits on blank lines (paragraph/section boundaries), never mid-sentence.

    Each chunk carries the tail of the previous paragraph as context so a later
    per-chunk LLM call doesn't lose the local thread between paragraphs.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]

    chunks: list[ChunkData] = []
    previous_tail: str | None = None
    for index, paragraph in enumerate(paragraphs):
        chunks.append(ChunkData(order_index=index, raw_text=paragraph, context_tail=previous_tail))
        previous_tail = paragraph[-_CONTEXT_TAIL_CHARS:]
    return chunks
