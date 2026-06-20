"""Context: the read-only view handed to every skill.

This is the seam between infrastructure and skills. Skills receive a Context
and may only *read* — there is no API here to modify source, waveforms, or the
repository. aidbg never edits the design/TB; its only output is the report.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .models import Attribution, LogEvent
from .netlist import Tranif
from .repo import Repo
from .wave import Waveform


@dataclass
class Context:
    wave: Waveform | None = None
    netlist: list[Tranif] = field(default_factory=list)
    log: list[LogEvent] = field(default_factory=list)
    assertions: dict[str, dict] = field(default_factory=dict)  # registry
    source_root: Path | None = None
    repo: Repo | None = None
    _src_cache: list[Path] = field(default_factory=list, repr=False)

    # ---- source (read-only) ----
    def _sources(self) -> list[Path]:
        if not self._src_cache and self.source_root:
            self._src_cache = [p for p in Path(self.source_root).rglob("*")
                               if p.suffix in (".sv", ".v", ".svh")]
        return self._src_cache

    def find_assignments(self, signal: str) -> list[tuple[str, int, str]]:
        """Locate where `signal` (basename) is driven in the SV source.

        Matches `sig <= ...`, `sig = ...`, `assign sig = ...`. Returns
        (file, line, text). Used to bridge a waveform net to its source driver.
        """
        base = re.escape(signal.rsplit(".", 1)[-1])
        # netlist (extracted) and RTL casing often differ (SEL0 vs sel0); match loosely.
        pat = re.compile(rf"\b(?:assign\s+)?{base}\s*(<=|=)", re.IGNORECASE)
        hits: list[tuple[str, int, str]] = []
        for f in self._sources():
            try:
                for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
                    if pat.search(line):
                        hits.append((str(f), i, line.strip()))
            except OSError:
                continue
        return hits

    def blame(self, file: str, line: int) -> Attribution | None:
        return self.repo.blame(file, line) if self.repo else None

    # ---- log helpers ----
    def assertion_type(self, name: str) -> str:
        """'glitch' | 'circuit_spec' from the registry; default circuit_spec."""
        return self.assertions.get(name.rsplit(".", 1)[-1], {}).get("type", "circuit_spec")
