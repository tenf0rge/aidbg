# aidbg

AI debug assistant for mixed-signal SoC verification.

Targets designs where the control path is RTL (Verilog/SystemVerilog) and the
functional path is analog, brought in as a schematic-extracted netlist
(library cells, pass gates modeled with `tranif`). It correlates three inputs —
**waveform** (FSDB exported to text), **simulation log** (Xcelium), and the
**source repository** — to explain failures automatically.

## First skill: `triage`

Explains an X-contention end-to-end:

```
sim log  → infer offending net
waveform → find where the net first goes X
netlist  → back-trace the tranif pass gates driving that net
         → flag simultaneously-conducting gates with conflicting values
         → report root cause (strength conflict → X) and where to look next
```

### Run

```bash
python -m venv .venv && . .venv/bin/activate
python -m aidbg.cli triage \
    --wave samples/wave.txt \
    --netlist samples/analog_mux.v \
    --log samples/sim.log
```

The bundled `samples/` contain a self-consistent scenario: an RTL control bug
(`ctrl.sv` drives both selects high at reset) causes two `tranif1` pass gates in
`analog_mux.v` to fight on the shared analog node `AOUT`.

## Layout

```
aidbg/
  wave.py      FSDB-text waveform parser (strength-aware, swappable format)
  netlist.py   tranif extraction + connectivity trace
  simlog.py    Xcelium log parser
  analyze.py   X-origin detection + contention reasoning (core)
  cli.py       command-line entry point
samples/       runnable example scenario
```

## Status

Early MVP. Roadmap: extend the causal chain into the RTL source (locate the
driving statement, not just the control net), adapt parsers to the real
exporter formats, and expose skills to an agent CLI (opencode-based).
