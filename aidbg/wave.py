"""Waveform parser for FSDB text export (event-list form).

Format (one change point per line)::

    <time_ns>  <scope.signal>  <value>[ <extra...>]

value carries an optional strength prefix, e.g. ``St0``, ``HiZ``, ``Pu1``,
``Stx``. Plain ``0/1/x/z`` (no strength) is also accepted. Lines starting
with ``#`` and blank lines are ignored.

The format is deliberately isolated here so it can be swapped for the real
exporter output (table form / VCD-style) without touching the analyzer.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# strength prefixes emitted by the FSDB text exporter
_STRENGTH = {"St": "strong", "Pu": "pull", "Hi": "hiz", "We": "weak", "La": "large", "Me": "medium", "Sm": "small"}


@dataclass(frozen=True)
class Edge:
    time: int          # ns
    signal: str        # full hierarchical name, e.g. tb.dut.u_mux.AOUT
    value: str         # logic value: 0 1 x z
    strength: str      # strong | pull | hiz | weak | ... | "" if none
    raw: str           # original value token, e.g. "Stx", "HiZ"


@dataclass
class Waveform:
    edges: list[Edge] = field(default_factory=list)

    def signals(self) -> set[str]:
        return {e.signal for e in self.edges}

    def edges_of(self, signal: str) -> list[Edge]:
        return [e for e in self.edges if e.signal == signal]

    def value_at(self, signal: str, time: int) -> Edge | None:
        """Last edge of `signal` at or before `time`."""
        last = None
        for e in self.edges:
            if e.signal == signal and e.time <= time:
                last = e
        return last


def _split_value(token: str) -> tuple[str, str]:
    """('Stx') -> ('x','strong'); ('HiZ') -> ('z','hiz'); ('1') -> ('1','')."""
    if len(token) >= 3 and token[:2] in _STRENGTH:
        return token[2:].lower(), _STRENGTH[token[:2]]
    return token.lower(), ""


def parse_wave(text: str) -> Waveform:
    wf = Waveform()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        time_s, signal, value_tok = parts[0], parts[1], parts[2]
        try:
            time = int(time_s)
        except ValueError:
            continue
        val, strength = _split_value(value_tok)
        wf.edges.append(Edge(time=time, signal=signal, value=val, strength=strength, raw=value_tok))
    wf.edges.sort(key=lambda e: e.time)
    return wf
