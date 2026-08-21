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
        default=None,
        help="Cap how many failing tasks to reflect on each cycle (default: all of them).",
    )
    demo.add_argument(
        "--html",
        type=Path,
        default=None,
        help="Also write the curve to this HTML file.",
    )
    demo.add_argument(
        "--no-animate",
        action="store_true",
        help="Print the whole curve at once instead of revealing it per iteration.",
    )

    args = parser.parse_args(argv)

    # Default to the demo when no subcommand is given.
    if args.command in (None, "demo"):
        iterations = getattr(args, "iterations", 4)
        lessons = getattr(args, "lessons_per_iteration", 2)
        html_path = getattr(args, "html", None)
        animate = not getattr(args, "no_animate", False)
        return _run_demo(iterations, lessons, html_path, animate)

    parser.print_help()
    return 1


def _run_demo(
    iterations: int,
    lessons_per_iteration: int,
    html_path: Path | None,
    animate: bool,
) -> int:
    import time

    from anvil.loop import ImprovementLoop
    from anvil.report import render_header, render_html, render_row
    from anvil.scenarios import build_scenarios

    loop = ImprovementLoop(build_scenarios(), lessons_per_iteration=lessons_per_iteration)

    if animate:
        # Reveal the curve one iteration at a time so you can watch it climb.
        print(render_header())
        print()

        def show(report):
            print(render_row(report))
            time.sleep(0.7)

        result = loop.run(iterations=iterations, on_iteration=show)
        first, last = result.reports[0], result.reports[-1]
        print()
        print(
            f"Δ pass rate: {first.pass_rate * 100:.0f}% → {last.pass_rate * 100:.0f}% "
            f"over {len(result.reports)} iterations, "
            f"driven by {last.lessons_in_memory} learned lessons."
        )
    else:
        from anvil.report import render_curve

        result = loop.run(iterations=iterations)
        print(render_curve(result.reports))

    if html_path is not None:
        html_path.write_text(render_html(result.reports), encoding="utf-8")
        print(f"\nWrote {html_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
