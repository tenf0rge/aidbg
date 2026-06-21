"""APB scenario: real-format CSV waveform + Xcelium/UVM log, register mismatch."""
from pathlib import Path

from aidbg.core import agent
from aidbg.core.context import Context
from aidbg.core.logs import parse_log
from aidbg.core.wave import parse_wave

APB = Path(__file__).resolve().parents[1] / "samples" / "apb"


def _ctx() -> Context:
    ctx = Context()
    ctx.wave = parse_wave((APB / "wave.csv").read_text())
    ctx.log = parse_log((APB / "run.log").read_text())
    return ctx


def test_csv_autodetected_and_bus_values():
    wf = parse_wave((APB / "wave.csv").read_text())
    assert wf.value_at(wf.resolve("prdata"), 90).value == "deaddead"
    assert wf.value_at(wf.resolve("prdata"), 110).value == "12345678"
    # change-compression: prdata has far fewer edges than rows
    assert len(wf.edges_of(wf.resolve("prdata"))) < 10


def test_design_mismatch_when_bus_is_wrong():
    rep = agent.run(_ctx())
    f = next(f for f in rep.findings
             if f.skill == "reg-data-mismatch" and "1000" in f.title)
    assert f.layer == "design"
    assert "deaddead" in f.root_cause.lower()


def test_verification_env_mismatch_when_bus_is_right():
    rep = agent.run(_ctx())
    f = next(f for f in rep.findings
             if f.skill == "reg-data-mismatch" and "1004" in f.title)
    assert f.layer == "verification-env"


def test_uvm_error_not_blamed_on_library_file():
    rep = agent.run(_ctx())
    for f in rep.findings:
        if f.skill == "uvm-env":
            assert f.attribution is None   # uvm_pkg.sv is the macro location
