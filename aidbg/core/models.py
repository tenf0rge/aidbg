"""Core data models. Infrastructure layer — no debug-specific knowledge here.

These types are the contract between skills and the report engine. A skill
produces `Finding`s; the agent collects them into a `Report`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ----- waveform -----------------------------------------------------------

@dataclass(frozen=True)
class Edge:
    time: int          # ns
    signal: str        # full hierarchical name, e.g. tb.dut.u_mux.AOUT
    value: str         # logic value: 0 1 x z
    strength: str      # strong | pull | hiz | weak | ... | "" if none
    raw: str           # original token, e.g. "Stx", "HiZ"


# ----- netlist ------------------------------------------------------------

@dataclass(frozen=True)
class Tranif:
    kind: str          # tranif0 | tranif1 | rtranif0 | rtranif1
    term0: str
    term1: str
    ctrl: str
    file: str
    line: int

    @property
    def active_high(self) -> bool:
        return self.kind.endswith("1")


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


# ----- findings / report --------------------------------------------------

@dataclass
class Evidence:
    detail: str
    time: int | None = None
    net: str | None = None
    source: str | None = None      # "file:line"


@dataclass
class Attribution:
    """Who/which commit introduced the offending source line (from git blame)."""
    commit: str | None = None
    author: str | None = None
    date: str | None = None
    summary: str | None = None
    source: str | None = None      # "file:line" the blame refers to


@dataclass
class FixProposal:
    """A suggestion only. aidbg never edits source — this is text for a human."""
    description: str
    location: str | None = None    # "file:line"
    snippet: str | None = None     # illustrative, not applied


@dataclass
class Finding:
    skill: str
    title: str
    layer: str                     # "design" | "verification-env" | "unknown"
    confidence: float              # 0..1
    error: str                     # what error was observed
    root_cause: str                # MOST IMPORTANT
    evidence: list[Evidence] = field(default_factory=list)
    attribution: Attribution | None = None
    fix: FixProposal | None = None


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    inputs: dict[str, str] = field(default_factory=dict)

    def ranked(self) -> list[Finding]:
        return sorted(self.findings, key=lambda f: f.confidence, reverse=True)
