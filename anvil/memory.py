"""The lesson store — anvil's memory, built entirely on ``loom``.

Self-improvement needs somewhere to put what it learned and a way to pull the
relevant bits back on the next attempt. That is exactly the job ``loom`` already
does for documents, so anvil does not reinvent it: a :class:`Lesson` is embedded
with ``loom``'s pure-stdlib :class:`~loom.HashingEmbedder`, indexed in a
:class:`~loom.InMemoryVectorStore`, retrieved by cosine similarity via
:class:`~loom.Retriever`, and packed under a token budget with ``loom``'s budget
helpers. Zero credentials, zero network, fully deterministic.

The store is deliberately thin: it maps :class:`Lesson` objects onto ``loom``
chunks and back, and formats recalled lessons into a system-prompt block. All
the retrieval machinery is ``loom``'s.
"""

from __future__ import annotations

from loom import (
    Chunk,
    HashingEmbedder,
    InMemoryVectorStore,
    Retriever,
    estimate_tokens,
    trim_to_tokens,
)

from anvil.types import Lesson

_MEMORY_HEADER = "Lessons learned from past attempts at similar tasks:"


class LessonStore:
    """An embedded, retrievable store of :class:`Lesson`\\ s over ``loom``.

    Lessons are append-only (like a real experience log). Each is embedded once
    on ``add`` and recalled by semantic similarity to a query — normally the
    task prompt the agent is about to attempt.
    """

    def __init__(
        self,
        embedder: HashingEmbedder | None = None,
        store: InMemoryVectorStore | None = None,
        dim: int = 256,
    ) -> None:
        self.embedder = embedder or HashingEmbedder(dim=dim)
        self.store = store or InMemoryVectorStore()
        self.retriever = Retriever(self.embedder, self.store)
        # chunk id -> Lesson, so recall can return rich objects, not raw text.
        self._lessons: dict[str, Lesson] = {}

    def __len__(self) -> int:
        return len(self.store)

    def add(self, lesson: Lesson) -> None:
        """Embed and index one lesson."""
        chunk_id = f"lesson-{len(self.store)}-{lesson.task_id}"
        chunk = Chunk(
            id=chunk_id,
            doc_id=lesson.task_id,
            text=lesson.text,
            metadata={"task_id": lesson.task_id, "kind": lesson.kind},
        )
        vector = self.embedder.embed([lesson.text])[0]
        self.store.add([chunk.with_embedding(vector)])
        self._lessons[chunk_id] = lesson

    def recall(self, query: str, k: int = 8) -> list[Lesson]:
        """Return the ``k`` lessons most relevant to ``query``, best first."""
        scored = self.retriever.retrieve(query, k=k)
        return [self._lessons[sc.chunk.id] for sc in scored if sc.chunk.id in self._lessons]

    def as_prompt_block(self, query: str, k: int = 8, budget: int = 2000) -> str:
        """Format the recalled lessons as a system-prompt section under ``budget``.

        Returns ``""`` when memory is empty so the caller can cleanly omit the
        section. The token budget is enforced with ``loom``'s estimator/trimmer:
        with a large corpus this is where selection actually bites; for anvil's
        small demo suite everything fits.
        """
        lessons = self.recall(query, k=k)
        if not lessons:
            return ""
        lines = [_MEMORY_HEADER]
        used = estimate_tokens(_MEMORY_HEADER)
        for lesson in lessons:
            piece = f"- {lesson.text}"
            cost = estimate_tokens(piece)
            if used + cost > budget:
                trimmed = trim_to_tokens(piece, max(0, budget - used))
                if trimmed:
                    lines.append(trimmed)
                break
            lines.append(piece)
            used += cost
        return "\n".join(lines)
