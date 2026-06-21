"""Skill: when a glitch-checker SVA fires, decide real-glitch (design) vs
sim-artifact (verification-env), by correlating with physical evidence.
"""
from __future__ import annotations

from aidbg.core.context import Context
from aidbg.core.i18n import add_messages, t
from aidbg.core.models import Evidence, Finding, FixProposal
from aidbg.core.netlist import shared_nodes
from aidbg.core.registry import register

add_messages({
    "glitch.title_real": {"en": "glitch '{name}' is REAL (design)",
                          "ja": "グリッチ '{name}' は実グリッチ（設計）"},
    "glitch.title_artifact": {"en": "glitch '{name}' likely SIM-ARTIFACT (verification-env)",
                              "ja": "グリッチ '{name}' は見かけ上（検証環境）の可能性"},
    "glitch.error": {"en": "Glitch checker '{name}' fired at t={t}ns.",
                     "ja": "グリッチチェッカ '{name}' が t={t}ns で発火。"},
    "glitch.rc_real": {
        "en": "Corroborated by a physical contention/X event on '{node}' at t={t}ns → this is a real "
              "glitch from the design (see tranif-contention finding for the driving logic).",
        "ja": "t={t}ns に '{node}' で物理的な競合/X が併発 → 設計起因の実グリッチ（駆動ロジックは "
              "tranif-contention の指摘を参照）。"},
    "glitch.rc_artifact": {
        "en": "No physical contention/X found on a shared node near the firing time. Suspect a 0-delay "
              "race / delta-cycle ordering or model granularity in the TB/analog model rather than a real "
              "design glitch.",
        "ja": "発火時刻の近傍に共有ノードの物理的な競合/X が見当たらない。実設計のグリッチではなく、"
              "0遅延レース/デルタサイクル順序、またはTB/アナログモデルの粒度を疑う。"},
    "glitch.ev_fired": {"en": "glitch checker fired", "ja": "グリッチチェッカ発火"},
    "glitch.ev_phys": {"en": "contention/X on shared node", "ja": "共有ノードの競合/X"},
    "glitch.fix_real": {
        "en": "Fix the contention root cause in the control logic; the glitch checker is correctly "
              "reporting a real design defect.",
        "ja": "制御ロジックの競合の真因を修正する。グリッチチェッカは実設計欠陥を正しく報告している。"},
    "glitch.fix_artifact": {
        "en": "Check TB driving/sampling for 0-delay races; add NBA/#0 separation or refine the analog "
              "model's event granularity. Confirm before treating as a design bug.",
        "ja": "TB の駆動/サンプリングの0遅延レースを確認。NBA/#0 で分離、またはアナログモデルのイベント"
              "粒度を見直す。設計バグと断定する前に確認すること。"},
})


@register
class GlitchTriage:
    name = "glitch-triage"
    description = "classify a fired glitch checker as real (design) or sim-artifact (TB)"
    consumes = {"log", "wave", "netlist"}

    def match(self, ctx: Context) -> bool:
        return any(e.source == "sva" and e.name and ctx.assertion_type(e.name) == "glitch"
                   for e in ctx.log)

    def analyze(self, ctx: Context) -> list[Finding]:
        lang = ctx.lang
        findings: list[Finding] = []
        shared = {n for n in shared_nodes(ctx.netlist)} if ctx.netlist else set()

        for e in ctx.log:
            if not (e.source == "sva" and e.name and ctx.assertion_type(e.name) == "glitch"):
                continue
            tm = e.time
            net = e.nets[0] if e.nets else None

            physical = None
            if ctx.wave and tm is not None:
                for node in shared:
                    full = ctx.wave.resolve(node)
                    for ed in ctx.wave.edges_of(full):
                        if "x" in ed.value and abs(ed.time - tm) <= 1:
                            physical = (node, ed)
                            break
                    if physical:
                        break

            if physical:
                node, ed = physical
                findings.append(Finding(
                    skill=self.name,
                    title=t(lang, "glitch.title_real", name=e.name),
                    layer="design",
                    confidence=0.8,
                    error=t(lang, "glitch.error", name=e.name, t=tm),
                    root_cause=t(lang, "glitch.rc_real", node=node, t=ed.time),
                    evidence=[
                        Evidence(detail=t(lang, "glitch.ev_fired"), time=tm, net=net),
                        Evidence(detail=t(lang, "glitch.ev_phys"), time=ed.time, net=node),
                    ],
                    fix=FixProposal(description=t(lang, "glitch.fix_real")),
                ))
            else:
                findings.append(Finding(
                    skill=self.name,
                    title=t(lang, "glitch.title_artifact", name=e.name),
                    layer="verification-env",
                    confidence=0.5,
                    error=t(lang, "glitch.error", name=e.name, t=tm),
                    root_cause=t(lang, "glitch.rc_artifact"),
                    evidence=[Evidence(detail=t(lang, "glitch.ev_fired"), time=tm, net=net)],
                    fix=FixProposal(description=t(lang, "glitch.fix_artifact")),
                ))
        return findings
