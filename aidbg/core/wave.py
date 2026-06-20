"""Waveform loader (FSDB text export, event-list form). Infrastructure layer.

Format is isolated here so it can be swapped for the real exporter output
without touching skills.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .models import Edge

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
        try:
            time = int(parts[0])
        except ValueError:
            continue
        val, strength = _split_value(parts[2])
        wf.edges.append(Edge(time=time, signal=parts[1], value=val, strength=strength, raw=parts[2]))
    wf.edges.sort(key=lambda e: e.time)
    return wf
