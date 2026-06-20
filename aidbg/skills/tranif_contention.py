"""Skill: detect tranif pass-gate contention driving a shared node to X,
then bridge to the RTL control that enabled the gates and blame the commit.
"""
from __future__ import annotations

from aidbg.core.context import Context
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
        wf, gates = ctx.wave, ctx.netlist
        findings: list[Finding] = []

        for node in shared_nodes(gates):
            full = wf.resolve(node)
            x_edge = next((e for e in wf.edges_of(full) if e.value == "x"), None)
            if x_edge is None:
                continue

            drivers = []
            for g in gates_touching(gates, full):
                ctrl_full = wf.resolve(g.ctrl)
                ctrl_edge = wf.value_at(ctrl_full, x_edge.time)
                on = "1" if g.active_high else "0"
                if ctrl_edge is None or ctrl_edge.value != on:
                    continue
                other = g.term1 if g.term0 == node else g.term0
                drv = wf.value_at(wf.resolve(other), x_edge.time)
                if drv is not None:
                    drivers.append((g, other, drv))

            if len(drivers) < 2 or len({d.value for _, _, d in drivers}) < 2:
                continue

            evidence = [Evidence(detail=f"{node} goes X", time=x_edge.time, net=full)]
            for g, other, drv in drivers:
                evidence.append(Evidence(
                    detail=f"{g.kind} conducting (ctrl {g.ctrl}=on), drives {other}={drv.raw}",
                    time=x_edge.time, source=f"{g.file}:{g.line}"))

            # bridge to the RTL control: blame whoever drives the enables.
            ctrls = sorted({g.ctrl for g, _, _ in drivers})
            attribution = None
            fix_loc = None
            for c in ctrls:
                for f, ln, txt in ctx.find_assignments(c):
                    evidence.append(Evidence(detail=f"{c} driven: {txt}", source=f"{f}:{ln}"))
                    blame = ctx.blame(f, ln)
                    if blame and attribution is None:
                        attribution = blame
                        fix_loc = f"{f}:{ln}"

            findings.append(Finding(
                skill=self.name,
                title=f"tranif contention on {node} → X",
                layer="design",
                confidence=0.9,
                error=f"Node '{node}' becomes X at t={x_edge.time}ns; "
                      f"sim/assertion flags multi-driver strength conflict.",
                root_cause=(
                    f"{len(drivers)} pass gates conduct simultaneously because controls "
                    f"({', '.join(ctrls)}) are asserted together, so conflicting analog "
                    f"inputs fight on '{node}' → strength conflict → X. The defect is "
                    f"in the control logic that allows the enables to overlap."),
                evidence=evidence,
                attribution=attribution,
                fix=FixProposal(
                    location=fix_loc,
                    description=(f"Make {', '.join(ctrls)} mutually exclusive (one-hot). "
                                 f"Ensure reset/default drives all enables inactive so the "
                                 f"pass gates never overlap."),
                    snippet=None),
            ))
        return findings
