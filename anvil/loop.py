"""The flywheel — where the six planes close into a self-improving loop.

One iteration:

1. **run + serve** — ``gauntlet`` drives the real agent loop over the task suite,
   using a :class:`~anvil.provider.ReflectiveProvider` that injects everything
   learned so far. (In production the inner provider is a real model served by
   ``ember`` and hardened by ``bulkhead``; here it is the offline stub.)
2. **observe** — the run is ingested into ``sonar`` for token/cost/latency.
3. **score** — ``gauntlet``'s graders decide, per task, pass or fail.
4. **reflect + store** — for a bounded number of still-failing tasks, distill a
   lesson from the failure evidence and write it to ``loom``-backed memory.

Next iteration those lessons are recalled and the score climbs. The bound in
step 4 (``lessons_per_iteration``) models limited digestion throughput per cycle
and is what turns a single 0%→100% jump into a readable rising curve.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass, field

from gauntlet import run_suite
from sonar import aggregate, from_gauntlet_result

from anvil.memory import LessonStore
from anvil.provider import LearningStubProvider, ReflectiveProvider
from anvil.reflect import Reflector
from anvil.scenarios import Scenario
from anvil.types import IterationReport, LoopResult


@dataclass
class ImprovementLoop:
    """Runs the reflect → remember → improve cycle over a scenario suite."""

    scenarios: list[Scenario]
    memory: LessonStore = field(default_factory=LessonStore)
    reflector: Reflector = field(default_factory=Reflector)
    model: str = "learning-stub"
    k: int = 1
    lessons_per_iteration: int = 2
    recall_k: int = 8
    memory_budget: int = 2000
    max_iterations: int = 6

    def run(
        self,
        iterations: int = 4,
        on_iteration: Callable[[IterationReport], None] | None = None,
    ) -> LoopResult:
        """Run ``iterations`` cycles and return the per-iteration report.

        ``on_iteration`` is invoked with each :class:`IterationReport` as soon as
        that cycle completes — a progress hook the CLI uses to animate the curve.
        """
        tasks = [sc.task for sc in self.scenarios]
        by_id = {sc.task.id: sc for sc in self.scenarios}
        inner = LearningStubProvider(self.scenarios)
        learned: set[str] = set()
        reports: list[IterationReport] = []

        for i in range(iterations):
            provider = ReflectiveProvider(
                inner,
                self.memory,
                recall_k=self.recall_k,
                memory_budget=self.memory_budget,
            )
            suite = run_suite(
                tasks,
                model=self.model,
                k=self.k,
                live_provider=provider,
                max_iterations=self.max_iterations,
            )
            summary = self._observe(suite)
            passed = sum(1 for tr in suite.task_results if tr.num_passed == tr.k)
            added = self._reflect(suite, by_id, learned)
            report = IterationReport(
                iteration=i,
                passed=passed,
                total=len(tasks),
                tokens=summary.usage.total_tokens,
                cost_usd=summary.cost_usd,
                lessons_in_memory=len(self.memory),
                lessons_added=added,
            )
            reports.append(report)
            if on_iteration is not None:
                on_iteration(report)

        return LoopResult(reports=reports, final_memory_size=len(self.memory))

    def _observe(self, suite: object) -> object:
        """Ingest the suite result into ``sonar`` and meter it."""
        data = dataclasses.asdict(suite)
        traces = from_gauntlet_result(data)
        return aggregate(traces)

    def _reflect(
        self,
        suite: object,
        by_id: dict[str, Scenario],
        learned: set[str],
    ) -> int:
        """Reflect on up to ``lessons_per_iteration`` still-failing tasks."""
        budget = self.lessons_per_iteration
        added = 0
        for tr in suite.task_results:  # gauntlet returns these sorted by task id
            if budget <= 0:
                break
            if tr.task_id in learned or tr.num_passed == tr.k:
                continue
            fail_index = next((j for j, g in enumerate(tr.grades) if not g.passed), 0)
            lesson = self.reflector.reflect(
                by_id[tr.task_id].task,
                tr.trajectories[fail_index],
                tr.grades[fail_index],
            )
            self.memory.add(lesson)
            learned.add(tr.task_id)
            budget -= 1
            added += 1
        return added
