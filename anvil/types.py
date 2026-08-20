"""Core value types for the self-improvement loop.

These are inert dataclasses — the *records* the loop passes around. A
:class:`Lesson` is what reflection produces and memory stores; an
:class:`IterationReport` is one row of the score-over-iterations curve; a
:class:`LoopResult` is the whole run. Keeping them behavior-free is what makes
the loop deterministic and easy to assert on in tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Lesson:
    """A single thing the agent learned from a failed attempt.

    ``text`` is the natural-language lesson that gets injected into a future
    system prompt. ``evidence`` is the concrete failure signal it was distilled
    from (tool-error strings and grader reasons) — kept so a lesson is auditable
    rather than a black box. ``task_id`` ties it back to the task that produced
    it (used for retrieval filtering and de-duplication).
    """

    task_id: str
    text: str
    evidence: tuple[str, ...] = ()
    kind: str = "reflection"


@dataclass(frozen=True)
class IterationReport:
    """One iteration of the flywheel: how well it scored and what it learned."""

    iteration: int
    passed: int
    total: int
    tokens: int
    cost_usd: float
    lessons_in_memory: int
    lessons_added: int

    @property
    def pass_rate(self) -> float:
        """Fraction of tasks fully solved this iteration, in ``[0, 1]``."""
        return self.passed / self.total if self.total else 0.0


@dataclass
class LoopResult:
    """The full record of an :class:`~anvil.loop.ImprovementLoop` run."""

    reports: list[IterationReport] = field(default_factory=list)
    final_memory_size: int = 0

    @property
    def pass_rates(self) -> list[float]:
        """The pass rate at each iteration, in order."""
        return [r.pass_rate for r in self.reports]

    @property
    def improved(self) -> bool:
        """True if the last iteration scored strictly better than the first."""
        if len(self.reports) < 2:
            return False
        return self.reports[-1].pass_rate > self.reports[0].pass_rate
