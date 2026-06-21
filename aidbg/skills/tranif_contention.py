"""Skill: detect tranif pass-gate contention driving a shared node to X,
then bridge to the RTL control that enabled the gates and blame the commit.
"""
from __future__ import annotations

from aidbg.core.context import Context
from aidbg.core.i18n import t
from aidbg.core.models import Evidence, Finding, FixProposal
from aidbg.core.netlist import gates_touching, shared_nodes
from aidbg.core.registry import register


@register
class TranifContention:
    name = "tranif-contention"
    description = "X on a shared analog node caused by simultaneously-conducting tranif gates"
    consumes = {"wave", "netlist"}

    def match(self, ctx: Context) -> bool:
        return ctx.wave is not None and bool(ctx.netlist)

    def analyze(self, ctx: Context) -> list[Finding]:
        wf, gates, lang = ctx.wave, ctx.netlist, ctx.lang
        findings: list[Finding] = []

        for node in shared_nodes(gates):
            full = wf.resolve(node)
            # any X bit (scalar "x" or a bus value like "xxxx")
            x_edge = next((e for e in wf.edges_of(full) if "x" in e.value), None)
            if x_edge is None:
                continue

            drivers = []
            for g in gates_touching(gates, full):
                ctrl_full = wf.resolve(g.ctrl)
                ctrl_edge = wf.value_at(ctrl_full, x_edge.time)
                on = "1" if g.active_high else "0"
                if ctrl_edge is None or ctrl_edge.value != on:
                    continue
                other = g.term1 if g.term0.lower() == node.lower() else g.term0
                drv = wf.value_at(wf.resolve(other), x_edge.time)
                if drv is not None:
                    drivers.append((g, other, drv))

            if len(drivers) < 2 or len({d.value for _, _, d in drivers}) < 2:
                continue

            evidence = [Evidence(detail=t(lang, "tranif.ev_x", node=node), time=x_edge.time, net=full)]
            for g, other, drv in drivers:
                evidence.append(Evidence(
                    detail=t(lang, "tranif.ev_gate", kind=g.kind, ctrl=g.ctrl, other=other, raw=drv.raw),
                    time=x_edge.time, source=f"{g.file}:{g.line}"))

            # bridge to the RTL control: blame whoever drives the enables.
            ctrls = sorted({g.ctrl for g, _, _ in drivers})
            attribution = None
            fix_loc = None
            for c in ctrls:
                for f, ln, txt in ctx.find_assignments(c):
                    evidence.append(Evidence(detail=t(lang, "tranif.ev_driven", ctrl=c, txt=txt),
                                             source=f"{f}:{ln}"))
                    blame = ctx.blame(f, ln)
                    if blame and attribution is None:
                        attribution = blame
                        fix_loc = f"{f}:{ln}"

            ctrls_s = ", ".join(ctrls)
            findings.append(Finding(
                skill=self.name,
                title=t(lang, "tranif.title", node=node),
                layer="design",
                confidence=0.9,
                error=t(lang, "tranif.error", node=node, t=x_edge.time),
                root_cause=t(lang, "tranif.root_cause", n=len(drivers), ctrls=ctrls_s, node=node),
                evidence=evidence,
                attribution=attribution,
                fix=FixProposal(location=fix_loc, description=t(lang, "tranif.fix", ctrls=ctrls_s)),
            ))
        return findings
