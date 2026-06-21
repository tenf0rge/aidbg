"""Waveform loader (FSDB text export, event-list form). Infrastructure layer.

Format is isolated here so it can be swapped for the real exporter output
without touching skills.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import Edge

_SLICE = re.compile(r"\[\d+(:\d+)?\]\s*$")   # paddr[31:0] -> paddr

_STRENGTH = {"St": "strong", "Pu": "pull", "Hi": "hiz", "We": "weak",
             "La": "large", "Me": "medium", "Sm": "small"}


@dataclass
class Waveform:
    edges: list[Edge] = field(default_factory=list)

    def signals(self) -> set[str]:
        return {e.signal for e in self.edges}

    def edges_of(self, signal: str) -> list[Edge]:
        return [e for e in self.edges if e.signal == signal]

    def resolve(self, basename: str) -> str:
        """Map a netlist/source basename (SEL0) to a full hierarchical signal."""
        b = basename.rsplit(".", 1)[-1].lower()
        for s in self.signals():
            if s.rsplit(".", 1)[-1].lower() == b:
                return s
        return basename

    def value_at(self, signal: str, time: int) -> Edge | None:
        last = None
        for e in self.edges:
            if e.signal == signal and e.time <= time:
                last = e
        return last


def _split_value(token: str) -> tuple[str, str]:
    """Strip a strength prefix only if the remainder is a legal logic value."""
    if len(token) >= 3 and token[:2] in _STRENGTH:
        rest = token[2:].lower()
        if rest and set(rest) <= {"0", "1", "x", "z"}:
            return rest, _STRENGTH[token[:2]]
    return token.lower(), ""


def _literal_body(tok: str) -> str:
    """'2'b01' -> '01', '8'hxx' -> 'xx'. Drops size and base."""
    body = tok.split("'", 1)[1]
    return body[1:] if body[:1].lower() in "bodh" else body


def parse_wave(text: str) -> Waveform:
    """Dispatch on format: CSV table (header starts with 'Time') vs event list."""
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if "," in s and s.lower().startswith("time"):
            return parse_wave_csv(text)
        break
    return _parse_wave_events(text)


def parse_wave_csv(text: str) -> Waveform:
    """CSV table export: header `Time(ns),sigA,sigB[31:0],...` then one row per
    timestep with all signal values. Bus values are hex (no base prefix), scalars
    0/1/x/z. Only change points are recorded (edges), matching the event model.
    """
    wf = Waveform()
    rows = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if not rows:
        return wf
    header = [h.strip() for h in rows[0].split(",")]
    names = [_SLICE.sub("", h) for h in header[1:]]   # strip [31:0] width
    prev: dict[str, str] = {}
    for row in rows[1:]:
        cells = [c.strip() for c in row.split(",")]
        if not cells or not cells[0]:
            continue
        try:
            time = int(cells[0])
        except ValueError:
            continue
        for name, raw in zip(names, cells[1:]):
            val = raw.lower()
            if prev.get(name) != val:                 # emit only on change
                wf.edges.append(Edge(time=time, signal=name, value=val, strength="", raw=raw))
                prev[name] = val
    wf.edges.sort(key=lambda e: e.time)
    return wf


def _parse_wave_events(text: str) -> Waveform:
    wf = Waveform()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            time = int(parts[0])
        except ValueError:
            continue
        # A sized literal in any value column (e.g. "2'b00") is the bus value
        # and takes precedence over a placeholder scalar/strength token.
        lit = next((t for t in parts[2:] if "'" in t), None)
        if lit is not None:
            raw, strength = lit, ""
            val = _literal_body(lit).lower()
        else:
            raw = parts[2]
            val, strength = _split_value(raw)
        wf.edges.append(Edge(time=time, signal=parts[1], value=val, strength=strength, raw=raw))
    wf.edges.sort(key=lambda e: e.time)
    return wf
