"""Deterministic primitives — the tool box an LLM agent (opencode) calls.

These let an agent *query* facts precisely without ingesting a huge waveform or
log into its context. Each returns plain JSON-able data. No judgement here; the
agent (or a skill) does the reasoning.
"""
from __future__ import annotations

import re
from pathlib import Path

from .logs import parse_log
from .repo import Repo
from .wave import parse_wave


_RX_FLIST = re.compile(r"-f\s+(\S+)")
_RX_TIMESCALE = re.compile(r"-timescale\s+(\S+)")
_RX_COMPILE = re.compile(r"Compil\w+\s+.*?\(([^)]+)\)")
_RX_SNAP = re.compile(r"(?:Loading snapshot|snapshot)\s+(\S+)", re.IGNORECASE)
_RX_TEST = re.compile(r"Running test\s+(\w+)")
_RX_SEQ = re.compile(r"Starting sequence:?\s*(\S+)")
_RX_COMP = re.compile(r"\buvm_test_top(?:\.\w+)*")


def env(log_path: str) -> dict:
    """Understand the verification environment from the log: what was loaded
    (flist/compiled files/snapshot), the test and sequences, and the UVM
    component hierarchy. This is the 'read the log first' step a human does.
    """
    text = Path(log_path).read_text(errors="ignore")
    flists, compiled, seqs, paths = [], [], [], set()
    snapshot = test = timescale = None
    for line in text.splitlines():
        if (m := _RX_FLIST.search(line)):
            flists.append(m.group(1))
        if (m := _RX_TIMESCALE.search(line)):
            timescale = m.group(1)
        if (m := _RX_COMPILE.search(line)):
            compiled.append(m.group(1))
        if snapshot is None and (m := _RX_SNAP.search(line)):
            snapshot = m.group(1).rstrip(".")
        if test is None and (m := _RX_TEST.search(line)):
            test = m.group(1)
        if (m := _RX_SEQ.search(line)):
            seqs.append(m.group(1))
        for p in _RX_COMP.findall(line):
            paths.add(p)

    # build the component tree from all dotted paths (+ their prefixes)
    tree: dict = {}
    for path in paths:
        parts = path.split(".")
        node = tree
        for part in parts:
            node = node.setdefault(part, {})
    return {
        "tool_inputs": {"flists": sorted(set(flists)), "compiled": compiled,
                        "snapshot": snapshot, "timescale": timescale},
        "test": test,
        "sequences": seqs,
        "uvm_component_tree": tree,
    }


def signals(wave_path: str) -> list[str]:
    wf = parse_wave(Path(wave_path).read_text())
    return sorted(wf.signals())


def query(wave_path: str, signal: str, time: int | None = None) -> dict:
    """Value of `signal` at `time` (last edge ≤ time), or all change points."""
    wf = parse_wave(Path(wave_path).read_text())
    full = wf.resolve(signal)
    if time is not None:
        e = wf.value_at(full, time)
        return {"signal": full, "time": time,
                "value": e.value if e else None,
                "raw": e.raw if e else None,
                "strength": e.strength if e else None}
    return {"signal": full,
            "edges": [{"time": e.time, "value": e.value, "raw": e.raw,
                       "strength": e.strength} for e in wf.edges_of(full)]}


def grep_log(log_path: str, severity: str | None = None,
             pattern: str | None = None) -> list[dict]:
    """Filter log events by severity and/or a regex over the message text."""
    rx = re.compile(pattern) if pattern else None
    out = []
    for e in parse_log(Path(log_path).read_text()):
        if severity and e.severity != severity.upper():
            continue
        if rx and not rx.search(e.text):
            continue
        out.append({"source": e.source, "severity": e.severity, "code": e.code,
                    "time": e.time, "file": e.file, "line": e.line,
                    "component": e.component, "name": e.name,
                    "nets": e.nets, "text": e.text})
    return out


def grep_source(source: str, pattern: str) -> list[dict]:
    """Search SV/Verilog source under `source` for a regex. Lets an agent read an
    assertion (or any) definition by name to infer its intent — no config needed."""
    rx = re.compile(pattern)
    out = []
    for f in Path(source).rglob("*"):
        if f.suffix not in (".sv", ".v", ".svh"):
            continue
        try:
            lines = f.read_text(errors="ignore").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            if rx.search(line):
                out.append({"file": str(f), "line": i, "text": line.strip()})
    return out


def blame(source: str, file: str, line: int) -> dict | None:
    repo = Repo.discover(Path(source))
    if not repo:
        return None
    a = repo.blame(file, line)
    if not a:
        return None
    return {"commit": a.commit, "author": a.author, "date": a.date,
            "summary": a.summary, "source": a.source}


def find_driver(source: str, signal: str) -> list[dict]:
    """Where a signal is driven in the SV source (+ git blame per site)."""
    from .context import Context
    ctx = Context(source_root=Path(source), repo=Repo.discover(Path(source)))
    out = []
    for f, ln, txt in ctx.find_assignments(signal):
        b = ctx.blame(f, ln)
        out.append({"file": f, "line": ln, "text": txt,
                    "commit": b.commit if b else None,
                    "author": b.author if b else None})
    return out
