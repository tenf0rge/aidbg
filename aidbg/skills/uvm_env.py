"""Skill: triage UVM component errors toward design vs verification-env."""
from __future__ import annotations

from aidbg.core.context import Context
from aidbg.core.models import Evidence, Finding, FixProposal
from aidbg.core.registry import register

_ROLES = [
    ("scoreboard", "scoreboard"), ("sb", "scoreboard"),
    ("predict", "ref-model"), ("model", "ref-model"),
    ("monitor", "monitor"), ("mon", "monitor"),
    ("driver", "driver"), ("drv", "driver"),
    ("sequenc", "sequencer"), ("seqr", "sequencer"), ("seq", "sequence"),
    ("agent", "agent"),
]


def _role(comp: str | None) -> str | None:
    c = (comp or "").lower()
    for key, role in _ROLES:
        if key in c:
            return role
    return None


@register
class UvmEnv:
    name = "uvm-env"
    description = "triage UVM ERROR/FATAL events toward design or verification-env"
    consumes = {"log"}

    def match(self, ctx: Context) -> bool:
        return any(e.source == "uvm" and e.severity in ("ERROR", "FATAL") for e in ctx.log)

    def analyze(self, ctx: Context) -> list[Finding]:
        findings: list[Finding] = []
        for e in ctx.log:
            if not (e.source == "uvm" and e.severity in ("ERROR", "FATAL")):
                continue
            role = _role(e.component)
            if role in ("scoreboard", "ref-model"):
                layer, conf = "unknown", 0.45
                rc = ("Mismatch reported by a checker — a symptom, not a root cause. "
                      "Trace expected vs actual back to the DESIGN output; separately "
                      "confirm the reference/expected value is itself correct (TB).")
                fix = "Compare DUT output against the reference model at the mismatch time; verify the predictor."
            elif role in ("driver", "sequencer", "sequence", "agent"):
                layer, conf = "verification-env", 0.65
                rc = ("Error originates in the stimulus/transport path → most likely a "
                      "VERIFICATION-ENV defect (sequence/driver/TLM wiring).")
                fix = "Inspect the sequence/driver: item generation, response handling, TLM port connections."
            elif role == "monitor":
                layer, conf = "verification-env", 0.55
                rc = ("Monitor-side error → check sampling alignment to clock/reset before "
                      "attributing to the design.")
                fix = "Align monitor sampling (clocking block / @posedge) with the protocol."
            else:
                layer, conf = "unknown", 0.4
                rc = "UVM component error; localize the reporting component to weigh design vs TB."
                fix = "Identify the reporting component and its data source."

            loc = f"{e.file}:{e.line}" if e.file else None
            attribution = ctx.blame(e.file, e.line) if e.file and e.line else None
            findings.append(Finding(
                skill=self.name,
                title=f"UVM {e.severity} [{e.code}] @ {e.component or '?'}",
                layer=layer, confidence=conf,
                error=f"{e.text} (t={e.time}ns)" if e.time is not None else e.text,
                root_cause=rc,
                evidence=[Evidence(detail=e.text, time=e.time,
                                   net=e.nets[0] if e.nets else None, source=loc)],
                attribution=attribution,
                fix=FixProposal(location=loc, description=fix),
            ))
        return findings
