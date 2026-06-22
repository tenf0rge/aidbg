"""Tests for the deterministic primitive tool box (the agent-callable layer)."""
from pathlib import Path

from aidbg.core import primitives

ROOT = Path(__file__).resolve().parents[1]
APB = ROOT / "samples" / "apb"


def test_signals_lists_bus_basenames():
    sigs = primitives.signals(str(APB / "wave.csv"))
    assert "tb_top.dut.prdata" in sigs and "tb_top.dut.pready" in sigs


def test_query_value_at_time():
    r = primitives.query(str(APB / "wave.csv"), "prdata", 90)
    assert r["value"] == "deaddead" and r["signal"].endswith("prdata")


def test_query_all_edges_when_no_time():
    r = primitives.query(str(APB / "wave.csv"), "prdata")
    assert "edges" in r and any(e["value"] == "deaddead" for e in r["edges"])


def test_grep_log_filters_errors():
    errs = primitives.grep_log(str(APB / "run.log"), severity="ERROR")
    assert len(errs) == 2
    assert all(e["severity"] == "ERROR" for e in errs)
    assert any("0000_1000" in e["text"] for e in errs)


def test_grep_log_pattern():
    hits = primitives.grep_log(str(APB / "run.log"), pattern="1004")
    assert hits and all("1004" in h["text"] for h in hits)


def test_grep_source_finds_assertion_definition():
    # lets an agent read an assertion's intent by name — no registry needed
    hits = primitives.grep_source(str(ROOT / "samples" / "fixture" / "design"),
                                  "chk_aout_no_glitch")
    assert hits and any("chk_aout_no_glitch" in h["text"] for h in hits)
    assert all(h["file"].endswith((".sv", ".v", ".svh")) for h in hits)
