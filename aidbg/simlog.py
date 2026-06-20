"""Xcelium simulation-log parser: pull out errors/warnings and the nets they mention."""
from __future__ import annotations

import re
from dataclasses import dataclass

# xmsim: *W,CODE (file,line): message   |   *E,...   |   plain "Assertion ... at time N NS"
_MSG = re.compile(r"\*([WEF]),(\w+)(?:\s*\(([^,]+),(\d+)\))?:?\s*(.*)")
_NET = re.compile(r"'([\w.\[\]]+)'")
_TIME = re.compile(r"\bat time (\d+)\s*NS\b", re.IGNORECASE)


@dataclass
class LogMsg:
    severity: str       # W | E | F
    code: str
    file: str | None
    line: int | None
    time: int | None
    nets: list[str]
    text: str


def parse_log(text: str) -> list[LogMsg]:
    out: list[LogMsg] = []
    for line in text.splitlines():
        m = _MSG.search(line)
        if m:
            sev, code, f, ln, msg = m.groups()
            t = _TIME.search(line)
            out.append(LogMsg(
                severity=sev, code=code,
                file=f, line=int(ln) if ln else None,
                time=int(t.group(1)) if t else None,
                nets=_NET.findall(line), text=msg.strip() or line.strip(),
            ))
        elif "FAILED" in line or "Assertion" in line:
            t = _TIME.search(line)
            out.append(LogMsg(
                severity="E", code="ASSERT", file=None, line=None,
                time=int(t.group(1)) if t else None,
                nets=_NET.findall(line), text=line.strip(),
            ))
    return out
