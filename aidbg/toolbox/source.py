"""Read-only source-tree helper: locate where a signal is driven in SV/Verilog.

Used by the `find-driver` primitive to bridge a waveform net back to the source
line that drives it (which git blame then attributes to a commit). Read-only —
it never writes to the tree.
"""
from __future__ import annotations

import re
from pathlib import Path

_SUFFIX = (".sv", ".v", ".svh")


def _sources(root: Path) -> list[Path]:
    return [p for p in Path(root).rglob("*") if p.suffix in _SUFFIX]


def find_assignments(root: Path | str, signal: str) -> list[tuple[str, int, str]]:
    """Locate where `signal` (basename) is driven in the SV/Verilog source.

    Matches `sig <= ...`, `sig = ...`, `assign sig = ...`. Returns
    (file, line, text). Netlist (extracted) and RTL casing often differ
    (SEL0 vs sel0), so the match is case-insensitive.
    """
    base = re.escape(signal.rsplit(".", 1)[-1])
    pat = re.compile(rf"\b(?:assign\s+)?{base}\s*(<=|=)", re.IGNORECASE)
    hits: list[tuple[str, int, str]] = []
    for f in _sources(Path(root)):
        try:
            for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
                if pat.search(line):
                    hits.append((str(f), i, line.strip()))
        except OSError:
            continue
    return hits
