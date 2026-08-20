"""L2 skill library: distill a winning tool sequence, recall it."""

from __future__ import annotations

from gauntlet.types import ToolCall, Trajectory, Turn

from anvil.scenarios import build_scenarios
from anvil.skills import SkillLibrary


def _scenario(scenario_id):
    return next(s for s in build_scenarios() if s.task.id == scenario_id)


def test_distill_captures_tool_sequence():
    task = _scenario("discover_read").task
    trajectory = Trajectory(
        turns=[
            Turn(text="", tool_calls=(ToolCall("l1", "list_files", {}),)),
            Turn(text="", tool_calls=(ToolCall("r1", "read_file", {"path": "secrets/db.env"}),)),
        ]
    )
    lib = SkillLibrary()
    skill = lib.distill(task, trajectory)
    assert skill.tool_sequence == ("list_files", "read_file")
    assert skill.source_task == "discover_read"
    assert len(lib) == 1


def test_recall_by_capability():
    task = _scenario("discover_read").task
    trajectory = Trajectory(turns=[Turn(text="", tool_calls=(ToolCall("l1", "list_files", {}),))])
    lib = SkillLibrary()
    lib.distill(task, trajectory)
    assert lib.recall("discover-before-act")
    assert not lib.recall("nonexistent-capability")


def test_prompt_block_formats_skills():
    task = _scenario("discover_read").task
    trajectory = Trajectory(
        turns=[
            Turn(text="", tool_calls=(ToolCall("l1", "list_files", {}),)),
            Turn(text="", tool_calls=(ToolCall("r1", "read_file", {"path": "x"}),)),
        ]
    )
    lib = SkillLibrary()
    lib.distill(task, trajectory)
    block = lib.as_prompt_block()
    assert "list_files" in block and "read_file" in block


def test_empty_library_has_empty_block():
    assert SkillLibrary().as_prompt_block() == ""
