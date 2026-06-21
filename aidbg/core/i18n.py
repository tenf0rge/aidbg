"""Localization. Infrastructure layer.

The core catalog holds only the *report chrome* (section labels, layer names).
Each skill owns its own prose and registers it with `add_messages(...)` at import
time — so a skill is self-contained and adding one never edits this file.

Skills carry logic, not literal text: they reference message *keys* via
`t(lang, key, **kw)`. Missing keys fall back to English, then to the raw key, so
a partial translation never crashes a run.
"""
from __future__ import annotations

SUPPORTED = ("en", "ja")

CATALOG: dict[str, dict[str, str]] = {
    # ---- report chrome (core-owned) ----
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
    # ---- layer labels (core-owned) ----
    "layer.design": {"en": "DESIGN", "ja": "設計（DESIGN）"},
    "layer.verification-env": {"en": "VERIFICATION-ENV", "ja": "検証環境（VERIFICATION-ENV）"},
    "layer.unknown": {"en": "UNKNOWN", "ja": "不明（UNKNOWN）"},
}


def add_messages(catalog: dict[str, dict[str, str]]) -> None:
    """Merge a skill's own message catalog into the global catalog."""
    for key, langs in catalog.items():
        CATALOG.setdefault(key, {}).update(langs)


def t(lang: str, key: str, **kw) -> str:
    entry = CATALOG.get(key)
    if entry is None:
        return key.format(**kw) if kw else key
    template = entry.get(lang) or entry.get("en") or key
    try:
        return template.format(**kw)
    except (KeyError, IndexError):
        return template
