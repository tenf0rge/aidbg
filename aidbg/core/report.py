"""Report renderers: Markdown (human) and JSON (machine). Infrastructure layer."""
from __future__ import annotations

import json
from dataclasses import asdict

from .models import Report

_LAYER = {"design": "DESIGN", "verification-env": "VERIFICATION-ENV", "unknown": "UNKNOWN"}


def render_markdown(report: Report) -> str:
    out: list[str] = ["# aidbg debug report", ""]
    if report.inputs:
        out.append("**Inputs**")
        for k, v in report.inputs.items():
            out.append(f"- {k}: `{v}`")
        out.append("")

    findings = report.ranked()
    if not findings:
        out.append("_No findings — no skill matched the provided evidence._")
        return "\n".join(out)

    out.append(f"**{len(findings)} finding(s)**, ranked by confidence.\n")
    for i, f in enumerate(findings, 1):
        out.append(f"## {i}. {f.title}")
        out.append(f"- **Layer**: {_LAYER.get(f.layer, f.layer)}  ·  "
                   f"**Confidence**: {f.confidence:.0%}  ·  **Skill**: `{f.skill}`")
        out.append("")
        out.append(f"**Error observed**\n\n{f.error}\n")
        out.append(f"**Root cause (most important)**\n\n{f.root_cause}\n")

        if f.attribution and f.attribution.commit:
            a = f.attribution
            out.append("**Attribution (git blame)**\n")
            out.append(f"- Commit `{a.commit}` by {a.author or '?'} ({a.date or '?'})")
            if a.summary:
                out.append(f"  - {a.summary}")
            if a.source:
                out.append(f"  - introduced at `{a.source}`")
            out.append("")

        if f.evidence:
            out.append("**Evidence**\n")
            for ev in f.evidence:
                loc = []
                if ev.time is not None:
                    loc.append(f"t={ev.time}ns")
                if ev.net:
                    loc.append(f"net={ev.net}")
                if ev.source:
                    loc.append(f"`{ev.source}`")
                prefix = f"[{', '.join(loc)}] " if loc else ""
                out.append(f"- {prefix}{ev.detail}")
            out.append("")

        if f.fix:
            out.append("**Suggested fix (proposal — not applied)**\n")
            if f.fix.location:
                out.append(f"- at `{f.fix.location}`")
            out.append(f"- {f.fix.description}")
            if f.fix.snippet:
                out.append("\n```systemverilog")
                out.append(f.fix.snippet)
                out.append("```")
            out.append("")
        out.append("")
    return "\n".join(out)


def render_json(report: Report) -> str:
    return json.dumps(asdict(report), indent=2, ensure_ascii=False)
