"""Agent orchestration: run matching skills, collect findings into a Report.

This is the autonomous loop. It owns no debug knowledge — it only decides
which skills apply and aggregates what they return.
"""
from __future__ import annotations

from .context import Context
from .models import Report
from .registry import SKILLS


def run(ctx: Context, inputs: dict[str, str] | None = None) -> Report:
    import aidbg.skills  # noqa: F401  (import side effect: populates SKILLS)

    report = Report(inputs=inputs or {})
    for skill in SKILLS:
        try:
            if skill.match(ctx):
                report.findings.extend(skill.analyze(ctx))
        except Exception as e:  # a misbehaving skill must not crash the run
            from .models import Finding
            report.findings.append(Finding(
                skill=skill.name, title=f"skill error: {skill.name}",
                layer="unknown", confidence=0.0,
                error=f"{type(e).__name__}: {e}",
                root_cause="(skill raised an exception; see error)",
            ))
    return report
