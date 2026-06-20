"""Scenario test: clean design, verification-env root cause (sim-artifact glitch)."""
import json
from pathlib import Path

from aidbg.core import agent
from aidbg.core.context import Context
from aidbg.core.logs import parse_log
from aidbg.core.netlist import parse_netlist
from aidbg.core.wave import parse_wave

SC = Path(__file__).resolve().parents[1] / "samples" / "scenario_tb"


def _ctx() -> Context:
    ctx = Context()
    ctx.wave = parse_wave((SC / "wave.txt").read_text())
    ctx.netlist = parse_netlist((SC / "analog_mux.v").read_text(),
                                filename=str(SC / "analog_mux.v"))
    ctx.log = parse_log((SC / "uvm.log").read_text())
    ctx.assertions = json.loads((SC / "assertions.json").read_text())["assertions"]
    return ctx


def test_no_contention_finding():
    rep = agent.run(_ctx())
    assert not any(f.skill == "tranif-contention" for f in rep.findings)


def test_glitch_is_sim_artifact():
    rep = agent.run(_ctx())
    g = next(f for f in rep.findings if f.skill == "glitch-triage")
    assert g.layer == "verification-env"
    assert "ARTIFACT" in g.title.upper()


def test_driver_error_is_verification_env():
    rep = agent.run(_ctx())
    drv = next(f for f in rep.findings if f.skill == "uvm-env" and "drv" in f.title)
    assert drv.layer == "verification-env"
