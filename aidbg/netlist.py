"""Minimal netlist parser: extract tranif switches and their connectivity.

Only what the contention analyzer needs: for each pass gate we record the
two terminals (bidirectional) and the control (enable) net, plus the source
location so findings can point back at the schematic-extracted file.

This is a regex-level extraction, not a full Verilog parser. tranif/tranif0/
tranif1/rtran* primitives are recognized.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# tranif1 (AOUT, IN0, SEL0);   ->  (kind, t0, t1, ctrl)
_TRANIF = re.compile(
    r"\b(tranif[01]|rtranif[01])\b\s*"
    r"(?:\w+\s*)?"                       # optional instance name
    r"\(\s*([\w.\[\]]+)\s*,\s*([\w.\[\]]+)\s*,\s*([\w.\[\]]+)\s*\)\s*;"
)


@dataclass(frozen=True)
class Tranif:
    kind: str          # tranif0 | tranif1 | rtranif0 | rtranif1
    term0: str         # bidirectional terminal
    term1: str         # bidirectional terminal
    ctrl: str          # enable net
    file: str
    line: int

    @property
    def active_high(self) -> bool:
        return self.kind.endswith("1")


def parse_netlist(text: str, filename: str = "<netlist>") -> list[Tranif]:
    gates: list[Tranif] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for m in _TRANIF.finditer(line):
            kind, t0, t1, ctrl = m.group(1), m.group(2), m.group(3), m.group(4)
            gates.append(Tranif(kind=kind, term0=t0, term1=t1, ctrl=ctrl, file=filename, line=lineno))
    return gates


def gates_touching(gates: list[Tranif], net: str) -> list[Tranif]:
    """Gates with `net` (basename match) on either terminal."""
    base = net.rsplit(".", 1)[-1]
    return [g for g in gates if g.term0 == base or g.term1 == base]
