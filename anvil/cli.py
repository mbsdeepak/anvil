"""``anvil`` command line: run the self-improvement loop and print the curve."""

from __future__ import annotations

import argparse
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="anvil",
        description="A self-improving-agent flywheel over loom + gauntlet + sonar.",
    )
    sub = parser.add_subparsers(dest="command")

    demo = sub.add_parser("demo", help="Run the loop on the built-in scenario suite.")
    demo.add_argument("--iterations", type=int, default=4, help="Number of cycles to run.")
    demo.add_argument(
        "--lessons-per-iteration",
        type=int,
        default=2,
        help="How many failing tasks to reflect on each cycle.",
    )
    demo.add_argument(
        "--html",
        type=Path,
        default=None,
        help="Also write the curve to this HTML file.",
    )

    args = parser.parse_args(argv)

    # Default to the demo when no subcommand is given.
    if args.command in (None, "demo"):
        iterations = getattr(args, "iterations", 4)
        lessons = getattr(args, "lessons_per_iteration", 2)
        html_path = getattr(args, "html", None)
        return _run_demo(iterations, lessons, html_path)

    parser.print_help()
    return 1


def _run_demo(iterations: int, lessons_per_iteration: int, html_path: Path | None) -> int:
    from anvil.loop import ImprovementLoop
    from anvil.report import render_curve, render_html
    from anvil.scenarios import build_scenarios

    loop = ImprovementLoop(build_scenarios(), lessons_per_iteration=lessons_per_iteration)
    result = loop.run(iterations=iterations)
    print(render_curve(result.reports))
    if html_path is not None:
        html_path.write_text(render_html(result.reports), encoding="utf-8")
        print(f"\nWrote {html_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
