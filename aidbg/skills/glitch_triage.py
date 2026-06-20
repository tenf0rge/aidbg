"""Skill: when a glitch-checker SVA fires, decide real-glitch (design) vs
sim-artifact (verification-env), by correlating with physical evidence.

Real glitch  -> a contention / multi-driver event exists on the same net at
                the same time (design root cause).
Artifact     -> no such physical cause found near the firing time (suspect
                0-delay race / delta cycle / model granularity in the TB/model).
"""
from __future__ import annotations

from aidbg.core.context import Context
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
        findings: list[Finding] = []
        shared = {n for n in shared_nodes(ctx.netlist)} if ctx.netlist else set()

        for e in ctx.log:
            if not (e.source == "sva" and e.name and ctx.assertion_type(e.name) == "glitch"):
                continue
            t = e.time
            net = e.nets[0] if e.nets else None

            # physical corroboration: a contention/X event on a shared node near t
            physical = None
            if ctx.wave and t is not None:
                for node in shared:
                    full = ctx.wave.resolve(node)
                    for ed in ctx.wave.edges_of(full):
                        if ed.value == "x" and abs(ed.time - t) <= 1:
                            physical = (node, ed)
                            break
                    if physical:
                        break

            if physical:
                node, ed = physical
                findings.append(Finding(
                    skill=self.name,
                    title=f"glitch '{e.name}' is REAL (design)",
                    layer="design",
                    confidence=0.8,
                    error=f"Glitch checker '{e.name}' fired at t={t}ns.",
                    root_cause=(f"Corroborated by a physical contention/X event on '{node}' "
                                f"at t={ed.time}ns → this is a real glitch from the design "
                                f"(see tranif-contention finding for the driving logic)."),
                    evidence=[
                        Evidence(detail=f"glitch checker fired", time=t, net=net),
                        Evidence(detail=f"contention/X on shared node", time=ed.time, net=node),
                    ],
                    fix=FixProposal(description=(
                        "Fix the contention root cause in the control logic; the glitch "
                        "checker is correctly reporting a real design defect.")),
                ))
            else:
                findings.append(Finding(
                    skill=self.name,
                    title=f"glitch '{e.name}' likely SIM-ARTIFACT (verification-env)",
                    layer="verification-env",
                    confidence=0.5,
                    error=f"Glitch checker '{e.name}' fired at t={t}ns.",
                    root_cause=("No physical contention/X found on a shared node near the "
                                "firing time. Suspect a 0-delay race / delta-cycle ordering "
                                "or model granularity in the TB/analog model rather than a "
                                "real design glitch."),
                    evidence=[Evidence(detail="glitch checker fired", time=t, net=net)],
                    fix=FixProposal(description=(
                        "Check TB driving/sampling for 0-delay races; add NBA/#0 separation "
                        "or refine the analog model's event granularity. Confirm before "
                        "treating as a design bug.")),
                ))
        return findings
