"""Reflection distills lessons from real failure evidence (not an answer key)."""

from __future__ import annotations

from gauntlet.types import Grade, ToolCall, ToolResult, Trajectory, Turn

from anvil.reflect import Reflector
from anvil.scenarios import build_scenarios


def _scenario(scenario_id):
    return next(s for s in build_scenarios() if s.task.id == scenario_id)


def test_lesson_captures_tool_error():
    task = _scenario("delete_confirm").task
    trajectory = Trajectory(
        turns=[
            Turn(
                text="deleting",
                tool_calls=(ToolCall("d1", "delete_file", {"path": "logs/old.log"}),),
                tool_results=(
                    ToolResult(
                        "d1",
                        "error: refusing to delete logs/old.log: destructive action requires confirm=true",
                        is_error=True,
                    ),
                ),
            )
        ]
    )
    grade = Grade(passed=False, score=0.0, reasons=("[trajectory] args for 'delete_file': no call matched",))
    lesson = Reflector().reflect(task, trajectory, grade)
    assert "confirm=true" in lesson.text
    assert lesson.task_id == "delete_confirm"


def test_lesson_captures_failing_grader_reason():
    task = _scenario("config_deploy").task
    trajectory = Trajectory(turns=[Turn(text="done")])
    grade = Grade(
        passed=False,
        score=0.0,
        reasons=("[state] config.deploy_enabled: got False, expected True",),
    )
    lesson = Reflector().reflect(task, trajectory, grade)
    assert "deploy_enabled" in lesson.text


def test_satisfied_reasons_are_dropped():
    task = _scenario("ticket_search").task
    trajectory = Trajectory(turns=[Turn(text="done")])
    grade = Grade(
        passed=False,
        score=0.0,
        reasons=(
            "[trajectory] required tool 'search_tickets': NOT called",
            "[trajectory] required tool 'update_ticket': called",
        ),
    )
    lesson = Reflector().reflect(task, trajectory, grade)
    assert "search_tickets" in lesson.text
    assert "update_ticket': called" not in lesson.text  # satisfied check filtered out
