"""Localization catalog. Infrastructure layer.

Skills carry logic, not prose: they reference message *keys* + params via
`t(lang, key, **kw)`, and the human-readable text lives here. This keeps the
infra/skill separation intact while supporting multiple report languages.

Add a language by adding a column to CATALOG. Missing keys fall back to English,
then to the raw key, so a partial translation never crashes a run.
"""
from __future__ import annotations

SUPPORTED = ("en", "ja")

CATALOG: dict[str, dict[str, str]] = {
    # ---- report chrome ----
    "report.title": {"en": "aidbg debug report", "ja": "aidbg デバッグレポート"},
    "report.inputs": {"en": "Inputs", "ja": "入力"},
    "report.findings_count": {
        "en": "**{n} finding(s)**, ranked by confidence.",
        "ja": "**{n} 件の指摘**（確信度順）。"},
    "report.no_findings": {
        "en": "_No findings — no skill matched the provided evidence._",
        "ja": "_指摘なし — 与えられた証拠に該当するスキルがありませんでした。_"},
    "report.layer": {"en": "Layer", "ja": "レイヤ"},
    "report.confidence": {"en": "Confidence", "ja": "確信度"},
    "report.skill": {"en": "Skill", "ja": "スキル"},
    "report.error": {"en": "Error observed", "ja": "観測されたエラー"},
    "report.root_cause": {"en": "Root cause (most important)", "ja": "真因（最重要）"},
    "report.attribution": {"en": "Attribution (git blame)", "ja": "作り込み元（git blame）"},
    "report.commit_by": {
        "en": "Commit `{commit}` by {author} ({date})",
        "ja": "コミット `{commit}` — {author}（{date}）"},
    "report.introduced_at": {"en": "introduced at `{src}`", "ja": "作り込み箇所: `{src}`"},
    "report.evidence": {"en": "Evidence", "ja": "根拠"},
    "report.fix": {
        "en": "Suggested fix (proposal — not applied)",
        "ja": "修正提案（提案のみ・未適用）"},
    "report.fix_at": {"en": "at `{loc}`", "ja": "対象: `{loc}`"},
    # ---- layer labels ----
    "layer.design": {"en": "DESIGN", "ja": "設計（DESIGN）"},
    "layer.verification-env": {"en": "VERIFICATION-ENV", "ja": "検証環境（VERIFICATION-ENV）"},
    "layer.unknown": {"en": "UNKNOWN", "ja": "不明（UNKNOWN）"},

    # ---- tranif-contention skill ----
    "tranif.title": {"en": "tranif contention on {node} → X", "ja": "{node} で tranif 競合 → X"},
    "tranif.error": {
        "en": "Node '{node}' becomes X at t={t}ns; sim/assertion flags multi-driver strength conflict.",
        "ja": "ノード '{node}' が t={t}ns で X 化。シム/アサーションが多重ドライブの strength 競合を検出。"},
    "tranif.root_cause": {
        "en": "{n} pass gates conduct simultaneously because controls ({ctrls}) are asserted together, "
              "so conflicting analog inputs fight on '{node}' → strength conflict → X. The defect is in "
              "the control logic that allows the enables to overlap.",
        "ja": "制御 ({ctrls}) が同時にアサートされ、{n} 個のパスゲートが同時導通。競合するアナログ入力が "
              "'{node}' で衝突し strength 競合 → X。真因はイネーブルの重なりを許している制御ロジック。"},
    "tranif.fix": {
        "en": "Make {ctrls} mutually exclusive (one-hot). Ensure reset/default drives all enables inactive "
              "so the pass gates never overlap.",
        "ja": "{ctrls} を相互排他（one-hot）にする。リセット/デフォルトで全イネーブルを非活性にし、"
              "パスゲートが重ならないようにする。"},
    "tranif.ev_x": {"en": "{node} goes X", "ja": "{node} が X 化"},
    "tranif.ev_gate": {
        "en": "{kind} conducting (ctrl {ctrl}=on), drives {other}={raw}",
        "ja": "{kind} が導通（制御 {ctrl}=オン）、{other}={raw} を駆動"},
    "tranif.ev_driven": {"en": "{ctrl} driven: {txt}", "ja": "{ctrl} の駆動: {txt}"},

    # ---- glitch-triage skill ----
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

    # ---- uvm-env skill ----
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
}


def t(lang: str, key: str, **kw) -> str:
    entry = CATALOG.get(key)
    if entry is None:
        return key.format(**kw) if kw else key
    template = entry.get(lang) or entry.get("en") or key
    try:
        return template.format(**kw)
    except (KeyError, IndexError):
        return template
