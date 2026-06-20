"""error-classify skill: classify UVM + SVA log events and give a Design/TB hint.

Categories
----------
GLITCH_SVA   : a glitch-checker assertion fired => a glitch was detected.
               Open question is real-glitch (design) vs sim-artifact (TB/model).
CIRCUIT_SVA  : a circuit-spec assertion fired => design behavior violated spec.
UVM_ENV      : an error reported by a UVM component (scoreboard/driver/monitor/
               sequencer/...). Often a symptom; may be design OR TB root cause.

Which SVA is a glitch checker is *not* guessed from naming. It comes from a
user-maintained registry (see samples/assertions.json). Unknown assertions
default to CIRCUIT_SVA.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# UVM_ERROR ./tb/env/scoreboard.sv(142) @ 40 ns: uvm_test_top.env.sb [MISCMP] msg
_UVM = re.compile(
    r"UVM_(INFO|WARNING|ERROR|FATAL)\s+(?:([\w./]+)\((\d+)\)\s+)?@\s*(\d+)\s*(?:ns)?:\s*"
    r"(\S+)?\s*(?:\[(\w+)\])?\s*(.*)"
)
# Assertion <name> FAILED at time <N> NS[: msg]
_ASRT = re.compile(r"[Aa]ssertion\s+([\w.\[\]]+)\s+FAILED(?:\s+at time\s+(\d+)\s*NS)?:?\s*(.*)")
_NET = re.compile(r"'([\w.\[\]]+)'")

# UVM component path -> role (used for the Design/TB hint)
_ROLE = [
    ("scoreboard", "scoreboard"), ("sb", "scoreboard"),
    ("monitor", "monitor"), ("mon", "monitor"),
    ("driver", "driver"), ("drv", "driver"),
    ("sequenc", "sequencer"), ("seqr", "sequencer"), ("seq", "sequence"),
    ("agent", "agent"), ("model", "ref-model"), ("predict", "ref-model"),
]


@dataclass
class Event:
    kind: str                 # GLITCH_SVA | CIRCUIT_SVA | UVM_ENV
    severity: str             # INFO | WARNING | ERROR | FATAL
    time: int | None
    name: str                 # assertion name or UVM id/component
    file: str | None
    line: int | None
    nets: list[str] = field(default_factory=list)
    text: str = ""
    hint: str = ""            # Design / TB triage hint


def load_registry(path: str | None) -> dict[str, dict]:
    if not path:
        return {}
    data = json.loads(Path(path).read_text())
    return data.get("assertions", {})


def _role_of(component: str) -> str | None:
    c = (component or "").lower()
    for key, role in _ROLE:
        if key in c:
            return role
    return None


def classify(text: str, registry: dict[str, dict] | None = None) -> list[Event]:
    registry = registry or {}
    events: list[Event] = []

    for line in text.splitlines():
        a = _ASRT.search(line)
        if a:
            name, t, msg = a.group(1), a.group(2), a.group(3)
            base = name.rsplit(".", 1)[-1]
            reg = registry.get(base, {})
            is_glitch = reg.get("type") == "glitch"
            kind = "GLITCH_SVA" if is_glitch else "CIRCUIT_SVA"
            if is_glitch:
                hint = ("Glitch detected on this net. Decide real vs sim-artifact: "
                        "real (design) = contention / delay-mismatch path in RTL/netlist; "
                        "artifact (TB/model) = 0-delay race / delta-cycle / model granularity.")
            else:
                hint = "Spec violated. Most likely DESIGN unless the checker's sampling/clock is TB-misconfigured."
            events.append(Event(
                kind=kind, severity="ERROR", time=int(t) if t else None,
                name=base, file=None, line=None, nets=_NET.findall(line),
                text=msg.strip() or line.strip(), hint=hint,
            ))
            continue

        u = _UVM.search(line)
        if u:
            sev, f, ln, t, comp, uid, msg = u.groups()
            if sev in ("INFO", "WARNING"):
                continue
            role = _role_of(comp or "")
            if role in ("scoreboard", "ref-model"):
                hint = "Mismatch reported by checker — symptom, not root cause. Trace expected vs actual back to DESIGN output; confirm ref-model/expected is correct (TB)."
            elif role in ("driver", "sequencer", "sequence", "agent"):
                hint = "Originates in the stimulus/transport path — likely VERIFICATION-ENV root cause (sequence/driver/TLM)."
            elif role == "monitor":
                hint = "Monitor-side error — check sampling alignment (TB) before blaming design."
            else:
                hint = "UVM component error — localize the reporting component to weigh Design vs TB."
            events.append(Event(
                kind="UVM_ENV", severity=sev, time=int(t) if t else None,
                name=f"{comp or '?'} [{uid or '-'}]", file=f, line=int(ln) if ln else None,
                nets=_NET.findall(line), text=msg.strip(), hint=hint,
            ))

    return events


def summarize(events: list[Event]) -> str:
    counts: dict[str, int] = {}
    for e in events:
        counts[e.kind] = counts.get(e.kind, 0) + 1
    parts = [f"{k}={v}" for k, v in sorted(counts.items())]
    return "  ".join(parts) if parts else "no error events"
