"""Level 1 — reflection: turn a failed attempt into a reusable lesson.

Reflection is the cheapest form of real self-improvement: no training, just a
short verbal note the agent writes to itself after a failure and reads back next
time. The honest question is *where the note comes from*. Here it is distilled
from the **concrete failure evidence** the run already produced — the tool-error
strings the world returned and the reasons ``gauntlet``'s graders gave for
failing — never from a hidden answer key. That is what makes the loop legitimate:
the agent improves because it read *why* it failed.

In production the composition step is itself a model call ("here is the task,
your trajectory, and why it failed — write one lesson"). :class:`Reflector`
factors that behind a template so the whole loop stays deterministic and
offline-testable; the evidence-gathering is identical either way.
"""

from __future__ import annotations

from dataclasses import dataclass

from gauntlet.types import Grade, Task, Trajectory

from anvil.types import Lesson

# Substrings that mark a grader reason as describing a *failure* (as opposed to a
# satisfied check). Reasons matching none of these are dropped so a lesson keeps
# only the signal that mattered.
_FAILURE_MARKERS = (
    "NOT called",
    "no call matched",
    "got ",
    "missing",
    "violation",
    "never called",
)


@dataclass
class Reflector:
    """Distills a :class:`Lesson` from a failed attempt's observable evidence."""

    max_evidence: int = 6

    def reflect(self, task: Task, trajectory: Trajectory, grade: Grade) -> Lesson:
        """Produce one lesson from a failed ``(task, trajectory, grade)``."""
        evidence = self._gather(trajectory, grade)
        text = self._compose(task, evidence)
        return Lesson(task_id=task.id, text=text, evidence=tuple(evidence))

    def _gather(self, trajectory: Trajectory, grade: Grade) -> list[str]:
        """Collect tool errors and failing grader reasons, de-duplicated."""
        raw: list[str] = []
        for turn in trajectory.turns:
            for result in turn.tool_results:
                if result.is_error:
                    raw.append(f"a tool call failed: {result.content}")
        for reason in grade.reasons:
            if any(marker in reason for marker in _FAILURE_MARKERS):
                raw.append(f"grader feedback: {reason}")

        seen: set[str] = set()
        unique: list[str] = []
        for item in raw:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        return unique[: self.max_evidence]

    @staticmethod
    def _compose(task: Task, evidence: list[str]) -> str:
        body = "\n".join(f"  - {e}" for e in evidence) or "  - (no specific signal captured)"
        return (
            f'When the goal is: "{task.prompt.strip()}"\n'
            f"a past attempt failed for these reasons:\n{body}\n"
            f"Adjust the approach so these checks pass next time."
        )
