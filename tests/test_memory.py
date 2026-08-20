"""LessonStore: add, recall by relevance, and budgeted prompt formatting."""

from __future__ import annotations

from anvil.memory import LessonStore
from anvil.types import Lesson


def test_recall_returns_stored_lessons():
    store = LessonStore()
    store.add(Lesson(task_id="a", text="Always pass confirm=true to delete_file."))
    store.add(Lesson(task_id="b", text="Search tickets before updating one."))
    assert len(store) == 2

    recalled = store.recall("how do I delete a file safely", k=5)
    texts = [r.text for r in recalled]
    assert any("confirm=true" in t for t in texts)


def test_relevant_lesson_ranks_first():
    store = LessonStore()
    store.add(Lesson(task_id="del", text="When deleting a file, delete_file needs confirm=true."))
    store.add(Lesson(task_id="tick", text="When resolving tickets, search_tickets first."))

    top = store.recall("delete the stale file with delete_file", k=1)
    assert len(top) == 1
    assert "confirm=true" in top[0].text


def test_prompt_block_empty_when_no_memory():
    store = LessonStore()
    assert store.as_prompt_block("anything") == ""


def test_prompt_block_contains_lessons_and_header():
    store = LessonStore()
    store.add(Lesson(task_id="a", text="Pass confirm=true to delete_file."))
    block = store.as_prompt_block("delete a file", k=5)
    assert "Lessons learned" in block
    assert "confirm=true" in block


def test_prompt_block_respects_budget():
    store = LessonStore()
    for i in range(20):
        store.add(Lesson(task_id=f"t{i}", text=f"Lesson number {i} " * 20))
    from loom import estimate_tokens

    block = store.as_prompt_block("lesson", k=20, budget=50)
    assert estimate_tokens(block) <= 60  # header + one trimmed item, never unbounded
