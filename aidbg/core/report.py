"""Report renderers: Markdown (human) and JSON (machine). Infrastructure layer."""
from __future__ import annotations

import json
from dataclasses import asdict

from .i18n import t
from .models import Report


def render_markdown(report: Report, lang: str = "en") -> str:
    out: list[str] = [f"# {t(lang, 'report.title')}", ""]
    if report.inputs:
        out.append(f"**{t(lang, 'report.inputs')}**")
        for k, v in report.inputs.items():
            out.append(f"- {k}: `{v}`")
        out.append("")

    findings = report.ranked()
    if not findings:
        out.append(t(lang, "report.no_findings"))
        return "\n".join(out)

    out.append(t(lang, "report.findings_count", n=len(findings)) + "\n")
    for i, f in enumerate(findings, 1):
        out.append(f"## {i}. {f.title}")
        out.append(f"- **{t(lang, 'report.layer')}**: {t(lang, 'layer.' + f.layer)}  ·  "
                   f"**{t(lang, 'report.confidence')}**: {f.confidence:.0%}  ·  "
                   f"**{t(lang, 'report.skill')}**: `{f.skill}`")
        out.append("")
        out.append(f"**{t(lang, 'report.error')}**\n\n{f.error}\n")
        out.append(f"**{t(lang, 'report.root_cause')}**\n\n{f.root_cause}\n")

        if f.attribution and f.attribution.commit:
            a = f.attribution
            out.append(f"**{t(lang, 'report.attribution')}**\n")
            out.append("- " + t(lang, "report.commit_by", commit=a.commit,
                                 author=a.author or "?", date=a.date or "?"))
            if a.summary:
                out.append(f"  - {a.summary}")
            if a.source:
                out.append("  - " + t(lang, "report.introduced_at", src=a.source))
            out.append("")

        if f.evidence:
            out.append(f"**{t(lang, 'report.evidence')}**\n")
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
            out.append(f"**{t(lang, 'report.fix')}**\n")
            if f.fix.location:
                out.append("- " + t(lang, "report.fix_at", loc=f.fix.location))
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
