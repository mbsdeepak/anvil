"""anvil — a self-improving-agent flywheel, in ~2k readable lines of Python.

anvil is the seventh plane of a from-scratch agent platform. The other six run
an agent (``loom`` context, ``bulkhead`` gateway, ``cogs`` runtime, ``ember``
serving) and judge it (``sonar`` observability, ``gauntlet`` evaluation). anvil
closes the loop: it reflects on the eval outcomes, remembers the lessons, and
feeds them back so the agent gets measurably better each iteration.

Public API::

    from anvil import (
        ImprovementLoop, LoopResult, IterationReport,   # the flywheel
        LessonStore, Lesson, Reflector,                 # L1: reflection + memory
        SkillLibrary, Skill,                            # L2: skill library
        PromptOptimizer, PromptCandidate,               # L3: prompt self-editing
        ReflectiveProvider, LearningStubProvider,       # the provider seam
        Scenario, build_scenarios,                      # the demo suite
        render_curve, render_html,                      # the money shot
    )
"""

from __future__ import annotations

from anvil.loop import ImprovementLoop
from anvil.memory import LessonStore
from anvil.prompt import PromptCandidate, PromptOptimizer
from anvil.provider import LearningStubProvider, ReflectiveProvider
from anvil.reflect import Reflector
from anvil.report import render_curve, render_html
from anvil.scenarios import Scenario, build_scenarios
from anvil.skills import Skill, SkillLibrary
from anvil.types import IterationReport, Lesson, LoopResult

__version__ = "0.1.0"

__all__ = [
    "ImprovementLoop",
    "IterationReport",
    "LearningStubProvider",
    "Lesson",
    "LessonStore",
    "LoopResult",
    "PromptCandidate",
    "PromptOptimizer",
    "ReflectiveProvider",
    "Reflector",
    "Scenario",
    "Skill",
    "SkillLibrary",
    "__version__",
    "build_scenarios",
    "render_curve",
    "render_html",
]
