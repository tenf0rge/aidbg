"""Localization tests."""
import json
from pathlib import Path

from aidbg.core import agent, report as report_mod
from aidbg.core.context import Context
from aidbg.core.i18n import t
from aidbg.core.logs import parse_log
from aidbg.core.netlist import parse_netlist
from aidbg.core.wave import parse_wave

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def _ctx(lang: str) -> Context:
    ctx = Context(lang=lang)
    ctx.wave = parse_wave((SAMPLES / "wave.txt").read_text())
    ctx.netlist = parse_netlist((SAMPLES / "analog_mux.v").read_text(), filename="n.v")
    ctx.log = parse_log((SAMPLES / "uvm.log").read_text())
    ctx.assertions = json.loads((SAMPLES / "assertions.json").read_text())["assertions"]
    return ctx


def test_t_fallback_to_en_then_key():
    assert t("ja", "report.root_cause") == "真因（最重要）"
    assert t("xx", "report.root_cause") == "Root cause (most important)"  # unknown lang -> en
    assert t("ja", "no.such.key") == "no.such.key"                        # unknown key -> key


def test_japanese_report_renders():
    rep = agent.run(_ctx("ja"))
    md = report_mod.render_markdown(rep, lang="ja")
    assert "真因（最重要）" in md
    assert "設計（DESIGN）" in md
    # skill-produced prose is localized too
    f = next(f for f in rep.findings if f.skill == "tranif-contention")
    assert "競合" in f.root_cause


def test_english_default_unchanged():
    rep = agent.run(_ctx("en"))
    f = next(f for f in rep.findings if f.skill == "tranif-contention")
    assert "strength conflict" in f.root_cause
