"""Waveform parser regression tests for real-world format variation."""
from aidbg.toolbox.wave import parse_wave


def test_multibit_value_uses_sized_literal():
    wf = parse_wave("40 tb.chan St0 2'b01\n45 tb.bus 8'hff\n")
    assert wf.value_at("tb.chan", 40).value == "01"
    assert wf.value_at("tb.bus", 45).value == "ff"


def test_multibit_x_detected():
    wf = parse_wave("35 tb.aout 8'hxx\n")
    e = wf.value_at("tb.aout", 35)
    assert "x" in e.value and e.value == "xx"


def test_strength_only_stripped_for_legal_values():
    wf = parse_wave("0 a St0\n0 b HiZ\n0 c Mem\n")  # "Mem" is not a strength+value
    assert wf.value_at("a", 0).value == "0"
    assert wf.value_at("b", 0).value == "z"
    assert wf.value_at("c", 0).value == "mem"   # left intact, not mis-split
