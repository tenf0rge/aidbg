"""Skill: when a glitch-checker SVA fires, decide real-glitch (design) vs
sim-artifact (verification-env), by correlating with physical evidence.
"""
from __future__ import annotations

from aidbg.core.context import Context
from aidbg.core.i18n import t
from aidbg.core.models import Evidence, Finding, FixProposal
from aidbg.core.netlist import shared_nodes
from aidbg.core.registry import register


@register
class GlitchTriage:
    name = "glitch-triage"
    description = "classify a fired glitch checker as real (design) or sim-artifact (TB)"
    consumes = {"log", "wave", "netlist"}

    def match(self, ctx: Context) -> bool:
        return any(e.source == "sva" and e.name and ctx.assertion_type(e.name) == "glitch"
                   for e in ctx.log)

    def analyze(self, ctx: Context) -> list[Finding]:
        lang = ctx.lang
        findings: list[Finding] = []
        shared = {n for n in shared_nodes(ctx.netlist)} if ctx.netlist else set()

        for e in ctx.log:
            if not (e.source == "sva" and e.name and ctx.assertion_type(e.name) == "glitch"):
                continue
            tm = e.time
            net = e.nets[0] if e.nets else None

            physical = None
            if ctx.wave and tm is not None:
                for node in shared:
                    full = ctx.wave.resolve(node)
                    for ed in ctx.wave.edges_of(full):
                        if "x" in ed.value and abs(ed.time - tm) <= 1:
                            physical = (node, ed)
                            break
                    if physical:
                        break

            if physical:
                node, ed = physical
                findings.append(Finding(
                    skill=self.name,
                    title=t(lang, "glitch.title_real", name=e.name),
                    layer="design",
                    confidence=0.8,
                    error=t(lang, "glitch.error", name=e.name, t=tm),
                    root_cause=t(lang, "glitch.rc_real", node=node, t=ed.time),
                    evidence=[
                        Evidence(detail=t(lang, "glitch.ev_fired"), time=tm, net=net),
                        Evidence(detail=t(lang, "glitch.ev_phys"), time=ed.time, net=node),
                    ],
                    fix=FixProposal(description=t(lang, "glitch.fix_real")),
                ))
            else:
                findings.append(Finding(
                    skill=self.name,
                    title=t(lang, "glitch.title_artifact", name=e.name),
                    layer="verification-env",
                    confidence=0.5,
                    error=t(lang, "glitch.error", name=e.name, t=tm),
                    root_cause=t(lang, "glitch.rc_artifact"),
                    evidence=[Evidence(detail=t(lang, "glitch.ev_fired"), time=tm, net=net)],
                    fix=FixProposal(description=t(lang, "glitch.fix_artifact")),
                ))
        return findings
