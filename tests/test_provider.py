"""The stub model is deterministic, stateless, and cue-driven."""

from __future__ import annotations

from anvil.memory import LessonStore
from anvil.provider import LearningStubProvider, ReflectiveProvider
from anvil.scenarios import build_scenarios
from anvil.types import Lesson


def _scenario(scenario_id):
    return next(s for s in build_scenarios() if s.task.id == scenario_id)


def test_naive_path_without_cue():
    sc = _scenario("delete_confirm")
    stub = LearningStubProvider([sc])
    messages = [{"role": "user", "content": sc.task.prompt}]
    turn = stub.complete(system="", messages=messages, tools=[])
    # First naive step deletes without confirm.
    assert turn.tool_calls[0].name == "delete_file"
    assert "confirm" not in turn.tool_calls[0].arguments


def test_improved_path_with_cue_in_system():
    sc = _scenario("delete_confirm")
    stub = LearningStubProvider([sc])
    messages = [{"role": "user", "content": sc.task.prompt}]
    turn = stub.complete(system="remember: confirm=true", messages=messages, tools=[])
    assert turn.tool_calls[0].arguments.get("confirm") is True


def test_turn_index_derived_from_messages_not_cursor():
    sc = _scenario("discover_read")
    stub = LearningStubProvider([sc])
    sys = "hint: list_files"
    # Simulate being on the second turn: one assistant message already present.
    messages = [
        {"role": "user", "content": sc.task.prompt},
        {"role": "assistant", "content": [{"type": "text", "text": "listing"}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "l1"}]},
    ]
    turn = stub.complete(system=sys, messages=messages, tools=[])
    # Second improved step reads the discovered path.
    assert turn.tool_calls[0].name == "read_file"


def test_reflective_provider_injects_memory():
    sc = _scenario("delete_confirm")
    memory = LessonStore()
    memory.add(Lesson(task_id="delete_confirm", text="delete_file requires confirm=true."))
    provider = ReflectiveProvider(LearningStubProvider([sc]), memory)
    messages = [{"role": "user", "content": sc.task.prompt}]
    turn = provider.complete(system="", messages=messages, tools=[])
    # The injected lesson carries the cue, so the stub takes the improved path.
    assert turn.tool_calls[0].arguments.get("confirm") is True
