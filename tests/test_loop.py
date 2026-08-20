"""The flagship test: the agent's score climbs, iteration over iteration.

This exercises the whole flywheel end to end over ``gauntlet``'s real world,
tools, and graders — the only stand-in is the offline model. If this passes, the
loop genuinely self-improves.
"""

from __future__ import annotations

from anvil.loop import ImprovementLoop
from anvil.scenarios import build_scenarios


def test_score_climbs_monotonically_to_full():
    loop = ImprovementLoop(build_scenarios(), lessons_per_iteration=2)
    result = loop.run(iterations=4)

    rates = result.pass_rates
    # Starts from zero (no memory), ends fully solved.
    assert rates[0] == 0.0
    assert rates[-1] == 1.0
    # Never regresses.
    assert all(b >= a for a, b in zip(rates, rates[1:], strict=False))
    # And actually moves.
    assert result.improved


def test_curve_is_gradual_with_bounded_reflection():
    # 6 tasks, 2 lessons digested per cycle -> 0, 2, 4, 6 solved.
    loop = ImprovementLoop(build_scenarios(), lessons_per_iteration=2)
    result = loop.run(iterations=4)
    solved = [r.passed for r in result.reports]
    assert solved == [0, 2, 4, 6]


def test_memory_grows_each_cycle_until_all_learned():
    loop = ImprovementLoop(build_scenarios(), lessons_per_iteration=2)
    result = loop.run(iterations=4)
    mem = [r.lessons_in_memory for r in result.reports]
    assert mem == [2, 4, 6, 6]  # capped once every task has a lesson


def test_determinism():
    a = ImprovementLoop(build_scenarios(), lessons_per_iteration=2).run(iterations=4)
    b = ImprovementLoop(build_scenarios(), lessons_per_iteration=2).run(iterations=4)
    assert a.pass_rates == b.pass_rates


def test_sonar_meters_real_tokens():
    loop = ImprovementLoop(build_scenarios(), lessons_per_iteration=2)
    result = loop.run(iterations=1)
    # sonar ingested the run and counted the stub's synthetic-but-real usage.
    assert result.reports[0].tokens > 0
