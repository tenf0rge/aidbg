"""Netlist loader: extract tranif pass gates. Infrastructure layer."""
from __future__ import annotations

import re

from .models import Tranif

_TRANIF = re.compile(
    r"\b(tranif[01]|rtranif[01])\b\s*"
    r"(?:\w+\s*)?"
    r"\(\s*([\w.\[\]]+)\s*,\s*([\w.\[\]]+)\s*,\s*([\w.\[\]]+)\s*\)\s*;"
)


def parse_netlist(text: str, filename: str = "<netlist>") -> list[Tranif]:
    gates: list[Tranif] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for m in _TRANIF.finditer(line):
            gates.append(Tranif(kind=m.group(1), term0=m.group(2), term1=m.group(3),
                                ctrl=m.group(4), file=filename, line=lineno))
    return gates


def gates_touching(gates: list[Tranif], net: str) -> list[Tranif]:
    base = net.rsplit(".", 1)[-1]
    return [g for g in gates if g.term0 == base or g.term1 == base]


def shared_nodes(gates: list[Tranif]) -> list[str]:
    """Nets that appear on terminals of two or more gates (contention candidates)."""
    counts: dict[str, int] = {}
    for g in gates:
        for t in (g.term0, g.term1):
            counts[t] = counts.get(t, 0) + 1
    return [n for n, c in counts.items() if c >= 2]
