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
    # Scan the whole text so instantiations split across lines are still caught
    # (\s in the pattern already spans newlines).
    gates: list[Tranif] = []
    for m in _TRANIF.finditer(text):
        lineno = text.count("\n", 0, m.start()) + 1
        gates.append(Tranif(kind=m.group(1), term0=m.group(2), term1=m.group(3),
                            ctrl=m.group(4), file=filename, line=lineno))
    return gates


def gates_touching(gates: list[Tranif], net: str) -> list[Tranif]:
    # Case-insensitive to match the rest of the name-resolution seam (SEL0/sel0).
    base = net.rsplit(".", 1)[-1].lower()
    return [g for g in gates if g.term0.lower() == base or g.term1.lower() == base]


def shared_nodes(gates: list[Tranif]) -> list[str]:
    """Nets that appear on terminals of two or more gates (contention candidates)."""
    counts: dict[str, int] = {}
    disp: dict[str, str] = {}
    for g in gates:
        for t in (g.term0, g.term1):
            k = t.lower()
            counts[k] = counts.get(k, 0) + 1
            disp.setdefault(k, t)   # preserve original casing for display
    return [disp[k] for k, c in counts.items() if c >= 2]
