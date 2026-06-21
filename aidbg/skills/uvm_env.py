"""Skill: triage UVM component errors toward design vs verification-env."""
from __future__ import annotations

from aidbg.core.context import Context
from aidbg.core.i18n import add_messages, t
from aidbg.core.models import Evidence, Finding, FixProposal
from aidbg.core.registry import register

add_messages({
    "uvm.title": {"en": "UVM {sev} [{code}] @ {comp}", "ja": "UVM {sev} [{code}] @ {comp}"},
    "uvm.error_t": {"en": "{text} (t={t}ns)", "ja": "{text}（t={t}ns）"},
    "uvm.rc_checker": {
        "en": "Mismatch reported by a checker — a symptom, not a root cause. Trace expected vs actual back "
              "to the DESIGN output; separately confirm the reference/expected value is itself correct (TB).",
        "ja": "チェッカが報告した不一致 — 症状であり真因ではない。期待値と実値を DESIGN 出力まで辿り、"
              "別途、参照/期待値そのものの正しさ（TB）も確認する。"},
    "uvm.fix_checker": {
        "en": "Compare DUT output against the reference model at the mismatch time; verify the predictor.",
        "ja": "不一致時刻で DUT 出力と参照モデルを突き合わせ、予測器（predictor）を検証する。"},
    "uvm.rc_stimulus": {
        "en": "Error originates in the stimulus/transport path → most likely a VERIFICATION-ENV defect "
              "(sequence/driver/TLM wiring).",
        "ja": "エラーは stimulus/transport 経路に由来 → 検証環境側の欠陥の可能性が高い"
              "（sequence/driver/TLM 結線）。"},
    "uvm.fix_stimulus": {
        "en": "Inspect the sequence/driver: item generation, response handling, TLM port connections.",
        "ja": "sequence/driver を点検: アイテム生成、レスポンス処理、TLM ポート接続。"},
    "uvm.rc_monitor": {
        "en": "Monitor-side error → check sampling alignment to clock/reset before attributing to the design.",
        "ja": "モニタ側のエラー → 設計のせいにする前に、クロック/リセットへのサンプリング整合を確認する。"},
    "uvm.fix_monitor": {
        "en": "Align monitor sampling (clocking block / @posedge) with the protocol.",
        "ja": "モニタのサンプリング（clocking block / @posedge）をプロトコルに整合させる。"},
    "uvm.rc_unknown": {
        "en": "UVM component error; localize the reporting component to weigh design vs TB.",
        "ja": "UVM コンポーネントのエラー。報告元コンポーネントを特定し、設計か TB かを判断する。"},
    "uvm.fix_unknown": {
        "en": "Identify the reporting component and its data source.",
        "ja": "報告元コンポーネントとそのデータ源を特定する。"},
})

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
