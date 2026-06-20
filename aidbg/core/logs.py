"""Log loaders: Xcelium simulator log + UVM report log + SVA failures.

Infrastructure layer: turns text into `LogEvent`s. No classification policy
lives here — that is a skill's job.
"""
from __future__ import annotations

import re

from .models import LogEvent

# xmsim: *W,CODE (file,line): message
_XM = re.compile(r"\*([WEF]),(\w+)(?:\s*\(([^,]+),(\d+)\))?:?\s*(.*)")
# UVM_ERROR ./tb/env/sb.sv(142) @ 40 ns: uvm_test_top.env.sb [MISCMP] msg
_UVM = re.compile(
    r"UVM_(INFO|WARNING|ERROR|FATAL)\s+(?:([\w./]+)\((\d+)\)\s+)?@\s*(\d+)\s*(?:ns)?:\s*"
    r"(\S+)?\s*(?:\[(\w+)\])?\s*(.*)"
)
# Assertion <name> FAILED at time <N> NS[: msg]
_ASRT = re.compile(r"[Aa]ssertion\s+([\w.\[\]]+)\s+FAILED(?:\s+at time\s+(\d+)\s*NS)?:?\s*(.*)")
_NET = re.compile(r"'([\w.\[\]]+)'")
_TIME = re.compile(r"\bat time (\d+)\s*NS\b", re.IGNORECASE)

_SEV = {"W": "WARNING", "E": "ERROR", "F": "FATAL"}


def parse_log(text: str) -> list[LogEvent]:
    """Parse a mixed Xcelium/UVM/SVA log into a flat list of events."""
    out: list[LogEvent] = []
    for line in text.splitlines():
        a = _ASRT.search(line)
        if a:
            name, t, msg = a.groups()
            out.append(LogEvent(
                source="sva", severity="ERROR", code="ASSERT",
                time=int(t) if t else None, file=None, line=None,
                nets=_NET.findall(line), name=name.rsplit(".", 1)[-1],
                text=msg.strip() or line.strip(),
            ))
            continue
        u = _UVM.search(line)
        if u:
            sev, f, ln, t, comp, uid, msg = u.groups()
            out.append(LogEvent(
                source="uvm", severity=sev, code=uid or "-",
                time=int(t) if t else None, file=f, line=int(ln) if ln else None,
                nets=_NET.findall(line), component=comp, text=msg.strip(),
            ))
            continue
        x = _XM.search(line)
        if x:
            sev, code, f, ln, msg = x.groups()
            tm = _TIME.search(line)
            out.append(LogEvent(
                source="xcelium", severity=_SEV.get(sev, sev), code=code,
                time=int(tm.group(1)) if tm else None,
                file=f, line=int(ln) if ln else None,
                nets=_NET.findall(line), text=msg.strip() or line.strip(),
            ))
    return out
