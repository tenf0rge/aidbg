"""Skill-level tests against the in-repo (non-git) sample scenario."""
from pathlib import Path

from aidbg.core import agent
from aidbg.core.context import Context
from aidbg.core.logs import parse_log
from aidbg.core.netlist import parse_netlist
from aidbg.core.wave import parse_wave

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def _ctx() -> Context:
    ctx = Context()
    ctx.wave = parse_wave((SAMPLES / "wave.txt").read_text())
    ctx.netlist = parse_netlist((SAMPLES / "analog_mux.v").read_text(),
                                filename=str(SAMPLES / "analog_mux.v"))
    ctx.log = parse_log((SAMPLES / "uvm.log").read_text())
    import json
    ctx.assertions = json.loads((SAMPLES / "assertions.json").read_text())["assertions"]
    return ctx


def test_tranif_contention_detected():
    rep = agent.run(_ctx())
    f = next(f for f in rep.findings if f.skill == "tranif-contention")
    assert f.layer == "design"
    assert "AOUT" in f.title
    assert "SEL0" in f.root_cause and "SEL1" in f.root_cause


def test_glitch_classified_real():
    rep = agent.run(_ctx())
    g = next(f for f in rep.findings if f.skill == "glitch-triage")
    assert g.layer == "design"          # corroborated by physical contention
    assert "REAL" in g.title


def test_uvm_env_seqr_is_verification_env():
    rep = agent.run(_ctx())
    seqr = next(f for f in rep.findings
                if f.skill == "uvm-env" and "seqr" in f.title)
    assert seqr.layer == "verification-env"
