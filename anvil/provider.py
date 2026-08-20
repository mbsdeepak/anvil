"""The two providers that make the loop run — and the seam that improves it.

Both ``gauntlet`` and ``cogs`` drive their agent loop through the same narrow
contract: ``complete(system, messages, tools) -> AssistantTurn``. anvil hangs
its whole improvement mechanism on that seam:

* :class:`ReflectiveProvider` is a **decorator**. It wraps any inner provider,
  and on every turn it recalls the relevant lessons from memory and injects them
  into the system prompt before delegating. This is the one place learning
  becomes behavior — and because it only touches the system prompt, the exact
  same wrapper works in ``gauntlet`` (to score) and in ``cogs`` (to run for
  real). Swapping the inner provider for ``cogs.AnthropicProvider`` is the only
  change needed to drive a real model.

* :class:`LearningStubProvider` is a **deterministic, offline stand-in for a
  real model**. A real model reads the lessons in its context and does better;
  this stub simulates exactly that, reproducibly: it follows a scenario's
  ``improved`` playbook when that scenario's cue is present in the system prompt,
  and its ``naive`` one otherwise. It is the only "fake" in the pipeline — the
  world, the tools, and the grading are all ``gauntlet``'s real machinery.

Critically, the stub is **stateless**: ``gauntlet``'s runner reuses one provider
instance across every attempt and task, so the stub derives everything it needs
from the ``messages`` argument (the task from ``messages[0]``, the turn index
from the count of assistant messages so far) and never from internal cursors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gauntlet.providers import AssistantTurn
from gauntlet.types import ToolCall, Usage

from anvil.memory import LessonStore
from anvil.scenarios import Scenario


def _turn_from_step(step: dict[str, Any], in_tokens: int, out_tokens: int) -> AssistantTurn:
    """Build a normalized :class:`AssistantTurn` from a scenario step dict."""
    calls = tuple(
        ToolCall(id=c["id"], name=c["name"], arguments=dict(c.get("arguments", {})))
        for c in step.get("tool_calls", [])
    )
    stop = step.get("stop_reason", "tool_use" if calls else "end_turn")
    return AssistantTurn(
        text=step.get("text", ""),
        tool_calls=calls,
        stop_reason=stop,
        usage=Usage(input_tokens=in_tokens, output_tokens=out_tokens),
        content_blocks=None,
    )


@dataclass
class LearningStubProvider:
    """A deterministic offline model whose behavior improves with its context.

    Given the scenario suite, it looks up the scenario by the task prompt
    (``messages[0]``), decides whether that scenario's ``cue`` is present in the
    system prompt, and replays the matching (naive vs improved) trajectory step
    for the current turn. No randomness, no network, no state between calls.
    """

    scenarios: list[Scenario]
    name: str = "learning-stub"
    per_step_input_tokens: int = 120
    per_step_output_tokens: int = 30
    _by_prompt: dict[str, Scenario] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self._by_prompt = {sc.task.prompt.strip(): sc for sc in self.scenarios}

    def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AssistantTurn:
        prompt = (messages[0]["content"] if messages else "").strip()
        scenario = self._by_prompt.get(prompt)
        if scenario is None:
            return AssistantTurn(
                text="I don't recognize this task.",
                tool_calls=(),
                stop_reason="end_turn",
                usage=Usage(),
            )
        improved = scenario.cue in (system or "")
        steps = scenario.improved_steps if improved else scenario.naive_steps
        turn_index = sum(1 for m in messages if m.get("role") == "assistant")
        if turn_index >= len(steps):
            # Playbook exhausted — end cleanly rather than loop.
            return AssistantTurn(text="", tool_calls=(), stop_reason="end_turn", usage=Usage())
        return _turn_from_step(
            steps[turn_index], self.per_step_input_tokens, self.per_step_output_tokens
        )


@dataclass
class ReflectiveProvider:
    """Wraps a provider so past lessons are injected into every system prompt.

    On each turn it recalls the lessons most relevant to the current task and
    prepends them to the system prompt, then delegates to ``inner``. ``inner``
    can be the offline :class:`LearningStubProvider` (for scoring) or a real
    model provider (``cogs.AnthropicProvider``) — the wrapper is identical.

    ``base_system`` overrides the caller-supplied system prompt when set; this is
    the hook the L3 prompt-optimizer uses to try an evolved base prompt while
    keeping the lesson-injection behavior.
    """

    inner: Any
    memory: LessonStore
    base_system: str = ""
    recall_k: int = 8
    memory_budget: int = 2000
    name: str = "reflective"

    def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AssistantTurn:
        base = self.base_system or system or ""
        query = messages[0]["content"] if messages else ""
        block = self.memory.as_prompt_block(query, k=self.recall_k, budget=self.memory_budget)
        merged = self._merge(base, block)
        return self.inner.complete(merged, messages, tools)

    @staticmethod
    def _merge(base: str, block: str) -> str:
        if not block:
            return base
        if base:
            return f"{base}\n\n{block}"
        return block
