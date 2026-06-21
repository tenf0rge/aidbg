"""Skill: triage UVM component errors toward design vs verification-env."""
from __future__ import annotations

from aidbg.core.context import Context
from aidbg.core.i18n import t
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

# role -> (layer, confidence, root_cause key, fix key)
_PLAN = {
    "scoreboard": ("unknown", 0.45, "uvm.rc_checker", "uvm.fix_checker"),
    "ref-model":  ("unknown", 0.45, "uvm.rc_checker", "uvm.fix_checker"),
    "driver":     ("verification-env", 0.65, "uvm.rc_stimulus", "uvm.fix_stimulus"),
    "sequencer":  ("verification-env", 0.65, "uvm.rc_stimulus", "uvm.fix_stimulus"),
    "sequence":   ("verification-env", 0.65, "uvm.rc_stimulus", "uvm.fix_stimulus"),
    "agent":      ("verification-env", 0.65, "uvm.rc_stimulus", "uvm.fix_stimulus"),
    "monitor":    ("verification-env", 0.55, "uvm.rc_monitor", "uvm.fix_monitor"),
}
_DEFAULT = ("unknown", 0.4, "uvm.rc_unknown", "uvm.fix_unknown")


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
        lang = ctx.lang
        findings: list[Finding] = []
        for e in ctx.log:
            if not (e.source == "uvm" and e.severity in ("ERROR", "FATAL")):
                continue
            layer, conf, rc_key, fix_key = _PLAN.get(_role(e.component), _DEFAULT)

            # The reported file is often the UVM macro location (uvm_pkg.sv),
            # not the user's source — don't attribute the bug to the library.
            is_lib = bool(e.file) and ("uvm_pkg" in e.file or "/uvm/" in e.file
                                       or e.file.rsplit("/", 1)[-1].startswith("uvm_"))
            loc = f"{e.file}:{e.line}" if e.file and not is_lib else None
            attribution = ctx.blame(e.file, e.line) if loc and e.line else None
            err = t(lang, "uvm.error_t", text=e.text, t=e.time) if e.time is not None else e.text
            findings.append(Finding(
                skill=self.name,
                title=t(lang, "uvm.title", sev=e.severity, code=e.code, comp=e.component or "?"),
                layer=layer, confidence=conf,
                error=err,
                root_cause=t(lang, rc_key),
                evidence=[Evidence(detail=e.text, time=e.time,
                                   net=e.nets[0] if e.nets else None, source=loc)],
                attribution=attribution,
                fix=FixProposal(location=loc, description=t(lang, fix_key)),
            ))
        return findings
