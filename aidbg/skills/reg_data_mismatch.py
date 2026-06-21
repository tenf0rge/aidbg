"""Skill: correlate a scoreboard read-data miscompare with the actual bus.

For a register read mismatch, look at what the DUT actually drove on `prdata`
at that read (matched by address on the waveform):

  bus == observed (≠ expected)  -> DUT returned wrong data        -> DESIGN
  bus == expected               -> bus was right, TB mis-captured -> VERIFICATION-ENV
  otherwise                     -> timing/decode unclear          -> UNKNOWN

This is the design-vs-verification-env discriminator for register interfaces:
it trusts the silicon-level waveform over the testbench's claim.
"""
from __future__ import annotations

import re

from aidbg.core.context import Context
from aidbg.core.i18n import t
from aidbg.core.models import Evidence, Finding, FixProposal
from aidbg.core.registry import register

_ADDR = re.compile(r"Addr\s*=\s*([0-9A-Fa-fxz_'h]+)")
_EXP = re.compile(r"(?:Expected|Exp)\s*=\s*([0-9A-Fa-fxz_'h]+)")
_GOT = re.compile(r"(?:Got|Actual|Observed)\s*=\s*([0-9A-Fa-fxz_'h]+)")
_SCB_ROLES = ("sb", "scb", "scoreboard", "predict", "model")


def _num(s: str | None):
    """Hex token (32'hAB_CD / 0xabcd / abcd) -> int, or None if it has x/z."""
    if not s:
        return None
    s = re.sub(r"^\d*'h", "", s.strip().lower()).replace("0x", "").replace("_", "")
    return int(s, 16) if s and all(c in "0123456789abcdef" for c in s) else None


def _basename(sig: str) -> str:
    return sig.rsplit(".", 1)[-1].lower()


def _has(wf, base: str) -> bool:
    return any(_basename(s) == base for s in wf.signals())


@register
class RegDataMismatch:
    name = "reg-data-mismatch"
    description = "correlate a scoreboard read miscompare with the actual bus prdata"
    consumes = {"log", "wave"}

    def match(self, ctx: Context) -> bool:
        if ctx.wave is None or not (_has(ctx.wave, "prdata") and _has(ctx.wave, "pready")):
            return False
        return any(self._is_scb_mismatch(e) for e in ctx.log)

    @staticmethod
    def _is_scb_mismatch(e) -> bool:
        if e.source != "uvm" or e.severity not in ("ERROR", "FATAL"):
            return False
        comp = (e.component or "").lower()
        if not any(r in comp for r in _SCB_ROLES):
            return False
        return bool(_EXP.search(e.text) and _GOT.search(e.text))

    def _reads(self, wf):
        """List of (time, addr_num, prdata_str) for completed APB reads."""
        pready, pwrite = wf.resolve("pready"), wf.resolve("pwrite")
        paddr, prdata = wf.resolve("paddr"), wf.resolve("prdata")
        out = []
        for e in wf.edges_of(pready):
            if e.value not in ("1", "St1"):
                continue
            pw = wf.value_at(pwrite, e.time)
            if pw is not None and pw.value not in ("0", "St0"):
                continue   # a write, not a read
            a = wf.value_at(paddr, e.time)
            pr = wf.value_at(prdata, e.time)
            if a is not None and pr is not None:
                out.append((e.time, _num(a.value), pr))
        return out

    def analyze(self, ctx: Context) -> list[Finding]:
        lang = ctx.lang
        wf = ctx.wave
        reads = self._reads(wf)
        findings: list[Finding] = []

        for e in ctx.log:
            if not self._is_scb_mismatch(e):
                continue
            addr_tok = (_ADDR.search(e.text) or [None, None])[1] if _ADDR.search(e.text) else None
            exp_tok = _EXP.search(e.text).group(1)
            got_tok = _GOT.search(e.text).group(1)
            addr_n, exp_n, got_n = _num(addr_tok), _num(exp_tok), _num(got_tok)

            # find the read on the bus for this address, nearest at/before the report
            cands = [r for r in reads if addr_n is not None and r[1] == addr_n]
            cands = cands or reads
            before = [r for r in cands if e.time is None or r[0] <= e.time]
            rd = (max(before, key=lambda r: r[0]) if before
                  else (min(cands, key=lambda r: r[0]) if cands else None))

            addr_s = addr_tok or "?"
            wave_v = rd[2].value if rd else "?"
            wave_n = _num(wave_v) if rd else None

            if rd and wave_n is not None and got_n is not None and wave_n == got_n and wave_n != exp_n:
                layer, conf, rc, fix = "design", 0.85, "reg.rc_design", "reg.fix_design"
            elif rd and wave_n is not None and exp_n is not None and wave_n == exp_n:
                layer, conf, rc, fix = "verification-env", 0.8, "reg.rc_tb", "reg.fix_tb"
            else:
                layer, conf, rc, fix = "unknown", 0.4, "reg.rc_unknown", "reg.fix_unknown"

            ev = [Evidence(detail=t(lang, "reg.ev_scb", exp=exp_tok, got=got_tok),
                           time=e.time, net=wf.resolve("prdata"))]
            if rd:
                ev.append(Evidence(detail=t(lang, "reg.ev_bus", wave=wave_v, addr=addr_s, t=rd[0]),
                                   time=rd[0], net=wf.resolve("prdata")))

            findings.append(Finding(
                skill=self.name,
                title=t(lang, "reg.title", addr=addr_s),
                layer=layer, confidence=conf,
                error=t(lang, "reg.error", addr=addr_s, exp=exp_tok, got=got_tok),
                root_cause=t(lang, rc, wave=wave_v, addr=addr_s, exp=exp_tok, got=got_tok),
                evidence=ev,
                fix=FixProposal(description=t(lang, fix, addr=addr_s)),
            ))
        return findings
