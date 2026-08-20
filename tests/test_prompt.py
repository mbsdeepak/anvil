"""L3 prompt optimizer: adopt a candidate only if the eval score rises."""

from __future__ import annotations

from anvil.prompt import PromptOptimizer


def test_keeps_base_when_no_candidate_is_better():
    scores = {"base": 0.8, "worse": 0.5, "same": 0.8}
    best = PromptOptimizer().optimize("base", ["worse", "same"], lambda p: scores[p])
    assert best.text == "base"
    assert best.score == 0.8


def test_adopts_strictly_better_candidate():
    scores = {"base": 0.4, "better": 0.9}
    best = PromptOptimizer().optimize("base", ["better"], lambda p: scores[p])
    assert best.text == "better"
    assert best.score == 0.9


def test_min_gain_prevents_churn_on_noise():
    scores = {"base": 0.80, "marginal": 0.82}
    best = PromptOptimizer(min_gain=0.05).optimize("base", ["marginal"], lambda p: scores[p])
    assert best.text == "base"  # 0.02 gain does not clear the 0.05 margin
