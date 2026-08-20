"""Render the money shot: the score-over-iterations curve.

A self-improving agent's whole claim is a number that goes up. These renderers
turn a list of :class:`~anvil.types.IterationReport`\\ s into something you can
read in a terminal (:func:`render_curve`) or drop in a README
(:func:`render_html`).
"""

from __future__ import annotations

from anvil.types import IterationReport

_BAR_WIDTH = 24


def render_curve(reports: list[IterationReport]) -> str:
    """A compact ASCII bar chart of tasks-solved per iteration."""
    if not reports:
        return "(no iterations)"
    lines = ["Self-improvement curve — tasks solved per iteration:", ""]
    for r in reports:
        filled = round(r.pass_rate * _BAR_WIDTH)
        bar = "█" * filled + "·" * (_BAR_WIDTH - filled)
        lines.append(
            f"  iter {r.iteration}  [{bar}] {r.passed}/{r.total}  "
            f"({r.pass_rate * 100:3.0f}%)   memory={r.lessons_in_memory} "
            f"(+{r.lessons_added})   tokens={r.tokens}"
        )
    first, last = reports[0], reports[-1]
    lines.append("")
    lines.append(
        f"Δ pass rate: {first.pass_rate * 100:.0f}% → {last.pass_rate * 100:.0f}% "
        f"over {len(reports)} iterations, driven by {last.lessons_in_memory} learned lessons."
    )
    return "\n".join(lines)


def render_html(reports: list[IterationReport], title: str = "anvil — self-improvement curve") -> str:
    """A self-contained HTML bar chart (no external assets)."""
    rows = []
    for r in reports:
        pct = round(r.pass_rate * 100)
        rows.append(
            f'<div class="row"><span class="lbl">iter {r.iteration}</span>'
            f'<span class="track"><span class="fill" style="width:{pct}%"></span></span>'
            f'<span class="val">{r.passed}/{r.total} · {pct}%</span></div>'
        )
    bars = "\n".join(rows)
    return (
        f"<!doctype html><meta charset=utf-8><title>{title}</title>"
        "<style>body{font:14px/1.5 system-ui,sans-serif;max-width:640px;margin:2rem auto;padding:0 1rem}"
        ".row{display:flex;align-items:center;gap:.6rem;margin:.35rem 0}"
        ".lbl{width:3.5rem;color:#555}.val{width:6rem;color:#333}"
        ".track{flex:1;background:#eee;border-radius:4px;height:1.1rem;overflow:hidden}"
        ".fill{display:block;height:100%;background:#2b8a3e;transition:width .3s}</style>"
        f"<h2>{title}</h2>{bars}"
    )
