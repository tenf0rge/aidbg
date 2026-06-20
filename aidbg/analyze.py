"""Contention / X-origin analyzer.

The core skill: find where a net first goes X, and back-trace through the
tranif pass gates to explain *why* — typically two enabled gates driving
conflicting values onto a shared analog node.
"""
from __future__ import annotations

from dataclasses import dataclass

from .netlist import Tranif, gates_touching
from .wave import Edge, Waveform


@dataclass
class Finding:
    net: str
    time: int                 # ns where net first became X
    drivers: list[tuple[Tranif, Edge]]   # (gate, driven-terminal value) that were conducting
    summary: str

    def render(self) -> str:
        lines = [
            f"X-contention on '{self.net}' at t={self.time} ns",
            "",
            "Conducting pass gates at that time:",
        ]
        for g, drv in self.drivers:
            other = g.term1 if g.term0.endswith(self.net.rsplit('.', 1)[-1]) else g.term0
            lines.append(
                f"  - {g.kind} ({g.term0}, {g.term1}, ctrl={g.ctrl})  "
                f"[{g.file}:{g.line}]  drives {other}={drv.raw}"
            )
        lines += ["", self.summary]
        return "\n".join(lines)


def _is_conducting(gate: Tranif, wf: Waveform, time: int) -> bool:
    ctrl_edge = wf.value_at(_resolve(gate.ctrl, wf), time)
    if ctrl_edge is None:
        return False
    on_val = "1" if gate.active_high else "0"
    return ctrl_edge.value == on_val


def _resolve(basename: str, wf: Waveform) -> str:
    """Map a netlist basename (SEL0) to a full hierarchical signal in the wave."""
    for s in wf.signals():
        if s.rsplit(".", 1)[-1].lower() == basename.lower():
            return s
    return basename


def find_x_contention(wf: Waveform, gates: list[Tranif], net: str) -> Finding | None:
    full = _resolve(net, wf)
    x_edge = next((e for e in wf.edges_of(full) if e.value == "x"), None)
    if x_edge is None:
        return None

    touching = gates_touching(gates, full)
    drivers: list[tuple[Tranif, Edge]] = []
    for g in touching:
        if not _is_conducting(g, wf, x_edge.time):
            continue
        other_base = g.term1 if g.term0 == full.rsplit(".", 1)[-1] else g.term0
        drv = wf.value_at(_resolve(other_base, wf), x_edge.time)
        if drv is not None:
            drivers.append((g, drv))

    if len(drivers) >= 2:
        vals = {d.value for _, d in drivers}
        if len(vals) > 1:
            ctrls = ", ".join(sorted({g.ctrl for g, _ in drivers}))
            summary = (
                f"Root cause: {len(drivers)} pass gates conduct simultaneously, "
                f"driving conflicting values {sorted(vals)} onto '{net}' -> strength conflict -> X.\n"
                f"Next: check why controls ({ctrls}) are asserted together."
            )
            return Finding(net=full, time=x_edge.time, drivers=drivers, summary=summary)

    summary = (
        f"'{net}' is X at t={x_edge.time} ns but a clear multi-driver contention "
        f"was not confirmed from the netlist; inspect drivers manually."
    )
    return Finding(net=full, time=x_edge.time, drivers=drivers, summary=summary)
