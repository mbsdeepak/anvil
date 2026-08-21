"""The flagship test: the agent's score climbs, iteration over iteration.

This exercises the whole flywheel end to end over ``gauntlet``'s real world,
tools, and graders — the only stand-in is the offline model. If this passes, the
loop genuinely self-improves.
"""

from __future__ import annotations

from anvil.loop import ImprovementLoop
from anvil.scenarios import build_scenarios


def test_score_climbs_monotonically_to_full():
    result = ImprovementLoop(build_scenarios()).run(iterations=4)

    rates = result.pass_rates
    # Starts from zero (no memory), ends fully solved.
    assert rates[0] == 0.0
    assert rates[-1] == 1.0
    # Never regresses.
    assert all(b >= a for a, b in zip(rates, rates[1:], strict=False))
    # And actually moves.
    assert result.improved


def test_curve_is_uneven_because_tasks_differ_in_difficulty():
    # Difficulties are 1,1,1,2,2,3 -> tasks solved when they have enough lessons:
    #   after iter0 each failing task has 1 lesson -> the three 1-pitfall tasks pass,
    #   then the two 2-pitfall, then the single 3-pitfall. Uneven steps, not +2,+2,+2.
    result = ImprovementLoop(build_scenarios()).run(iterations=4)
    solved = [r.passed for r in result.reports]
    assert solved == [0, 3, 5, 6]


def test_memory_growth_tapers_as_tasks_get_solved():
    result = ImprovementLoop(build_scenarios()).run(iterations=4)
    added = [r.lessons_added for r in result.reports]
    mem = [r.lessons_in_memory for r in result.reports]
    assert added == [6, 3, 1, 0]  # fewer failures left to learn from each cycle
    assert mem == [6, 9, 10, 10]


def test_tokens_rise_as_memory_fills_the_context():
    result = ImprovementLoop(build_scenarios()).run(iterations=4)
    tokens = [r.tokens for r in result.reports]
    assert tokens[0] > 0
    # Input grows as recalled lessons enlarge the system prompt.
    assert tokens[1] > tokens[0]


def test_bounded_reflection_slows_the_curve():
    # Cap digestion to 2 lessons/cycle: strictly no faster than unbounded.
    capped = ImprovementLoop(build_scenarios(), lessons_per_iteration=2).run(iterations=4)
    full = ImprovementLoop(build_scenarios()).run(iterations=4)
    assert capped.reports[-1].passed <= full.reports[-1].passed


def test_determinism():
    a = ImprovementLoop(build_scenarios()).run(iterations=4)
    b = ImprovementLoop(build_scenarios()).run(iterations=4)
    assert a.pass_rates == b.pass_rates
    assert [r.tokens for r in a.reports] == [r.tokens for r in b.reports]
