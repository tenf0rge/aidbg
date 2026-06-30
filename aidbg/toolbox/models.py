"""Toolbox data types. Layer 1 only — these are what the parsers emit so the
primitives can return plain JSON-able facts. No debug-specific judgement here.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ----- waveform -----------------------------------------------------------

@dataclass(frozen=True)
class Edge:
    time: int          # ns
    signal: str        # full hierarchical name, e.g. tb.dut.u_mux.AOUT
    value: str         # logic value: 0 1 x z (or a sized literal body)
    strength: str      # strong | pull | hiz | weak | ... | "" if none
    raw: str           # original token, e.g. "Stx", "HiZ"


# ----- log events ---------------------------------------------------------

@dataclass
class LogEvent:
    source: str        # "xcelium" | "uvm" | "sva"
    severity: str      # INFO | WARNING | ERROR | FATAL
    code: str          # message id / code
    time: int | None
    file: str | None
    line: int | None
    nets: list[str] = field(default_factory=list)
    component: str | None = None   # UVM component path
    name: str | None = None        # assertion name
    text: str = ""


# ----- git attribution ----------------------------------------------------

@dataclass
class Attribution:
    """Who/which commit introduced the offending source line (from git blame)."""
    commit: str | None = None
    author: str | None = None
    date: str | None = None
    summary: str | None = None
    source: str | None = None      # "file:line" the blame refers to
