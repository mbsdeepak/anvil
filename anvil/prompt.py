"""Level 3 — prompt self-editing, gated by the eval score.

The riskiest and most powerful lever: let the agent rewrite its own base system
prompt. The thing that makes it *improvement* rather than drift is the gate — a
proposed prompt is kept only if it scores strictly better on ``gauntlet`` than
the incumbent. The eval is the fitness function; nothing is adopted on faith.

:class:`PromptOptimizer` is deliberately mechanism-only: you hand it candidate
prompts and an ``evaluate`` callable (in practice, run the suite with that prompt
as ``base_system`` and return the pass rate). It returns the best-scoring prompt,
never regressing below the incumbent. Generating candidates and wiring the eval
are the caller's job, which keeps this component pure and trivially testable.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class PromptCandidate:
    """A system prompt paired with the score it achieved."""

    text: str
    score: float


@dataclass
class PromptOptimizer:
    """Selects the best system prompt, keeping the incumbent unless beaten.

    ``min_gain`` is the margin a candidate must clear to be adopted — set it
    above zero to avoid churning the prompt on noise.
    """

    min_gain: float = 0.0

    def optimize(
        self,
        base_prompt: str,
        candidates: list[str],
        evaluate: Callable[[str], float],
    ) -> PromptCandidate:
        """Return the best of ``base_prompt`` and ``candidates`` under ``evaluate``."""
        best = PromptCandidate(text=base_prompt, score=evaluate(base_prompt))
        for candidate in candidates:
            score = evaluate(candidate)
            if score > best.score + self.min_gain:
                best = PromptCandidate(text=candidate, score=score)
        return best
