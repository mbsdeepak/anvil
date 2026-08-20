"""Level 2 — a skill library: distill successes into reusable procedures.

Where reflection (L1) learns from failures, skill distillation learns from
*successes*: when the agent solves a task, the winning tool sequence is worth
keeping as a named, reusable procedure it can consult on similar tasks later
(the Voyager idea — grow a library of skills rather than re-deriving them).

This is the same loop shape as L1 with a different write-back artifact, so it
lives behind the same "recall → inject as a prompt block" seam a
:class:`~anvil.provider.ReflectiveProvider` already understands.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gauntlet.types import Task, Trajectory


@dataclass(frozen=True)
class Skill:
    """A reusable procedure distilled from a successful attempt."""

    name: str
    when: str
    tool_sequence: tuple[str, ...]
    source_task: str

    def as_text(self) -> str:
        seq = " → ".join(self.tool_sequence) if self.tool_sequence else "(no tools)"
        return f"{self.name}: when the task is {self.when!r}, use: {seq}."


@dataclass
class SkillLibrary:
    """A growing, recallable collection of :class:`Skill`\\ s."""

    skills: dict[str, Skill] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.skills)

    def distill(self, task: Task, trajectory: Trajectory) -> Skill:
        """Extract the winning tool sequence from a successful trajectory."""
        skill = Skill(
            name=f"{task.id}_skill",
            when=task.capability,
            tool_sequence=tuple(trajectory.tool_names),
            source_task=task.id,
        )
        self.skills[skill.name] = skill
        return skill

    def recall(self, capability: str | None = None) -> list[Skill]:
        """All skills, or only those learned for ``capability``."""
        if capability is None:
            return list(self.skills.values())
        return [s for s in self.skills.values() if s.when == capability]

    def as_prompt_block(self, capability: str | None = None) -> str:
        """Format recalled skills as a system-prompt section (``""`` if none)."""
        skills = self.recall(capability)
        if not skills:
            return ""
        return "Reusable skills from past successes:\n" + "\n".join(
            f"- {s.as_text()}" for s in skills
        )
