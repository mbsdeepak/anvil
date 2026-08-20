"""anvil demo — watch an agent teach itself, fully offline.

Runs the built-in scenario suite through the improvement loop and prints the
score-over-iterations curve. Every plane is exercised with its own offline seam:

  * gauntlet  -> real world + tools + graders, driven by anvil's LearningStub
  * loom      -> HashingEmbedder + InMemoryVectorStore hold the lessons
  * sonar     -> ingests each run for token/cost/latency
  * anvil     -> reflects on failures, remembers, and improves

No credentials, no network. Run:  python examples/improve_demo.py
"""

from __future__ import annotations

from anvil.loop import ImprovementLoop
from anvil.report import render_curve
from anvil.scenarios import build_scenarios


def main() -> None:
    scenarios = build_scenarios()
    print(f"Suite: {len(scenarios)} tasks, each with a classic agent pitfall.\n")

    loop = ImprovementLoop(scenarios, lessons_per_iteration=2)
    result = loop.run(iterations=4)

    print(render_curve(result.reports))
    print("\nWhat happened: with empty memory the agent trips every pitfall (0%).")
    print("Each cycle it reflects on the failures it can digest, writes the lesson")
    print("to loom-backed memory, and recalls it next time — until every task passes.")


if __name__ == "__main__":
    main()
