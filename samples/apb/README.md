# Scenario: APB register interface (real-format inputs)

Exercises aidbg on the formats a real Xcelium/UVM digital run produces:

- **Waveform** `wave.csv` — CSV table export: header `Time(ns),sigA,sigB[31:0],…`
  then one row per timestep, bus values in hex. aidbg auto-detects this format
  (vs the event-list form) and compresses it to change-point edges.
- **Log** `run.log` — Xcelium UVM log: `UVM_ERROR /src/uvm_pkg.sv(220) @ 95:
  uvm_test_top.env.scb [SCB_CMP] …` (time has no `ns` suffix; the reported file
  is the UVM macro location, not the user's source — aidbg does not blame it).

Two scoreboard read-miscompares are planted to show both directions:

| Addr | bus `prdata` | scoreboard says | aidbg verdict |
|------|--------------|-----------------|---------------|
| `0x1000` | `DEADDEAD` | exp `A5A5B6B6`, got `DEADDEAD` | **DESIGN** — DUT drove wrong data (bus = observed ≠ expected) |
| `0x1004` | `12345678` | exp `1234_5678`, got `BADC0DE1` | **VERIFICATION-ENV** — bus was correct; TB mis-captured/expected |

The `reg-data-mismatch` skill trusts the silicon-level waveform over the
testbench's claim, which is the design-vs-verification-env discriminator for
register interfaces.

Run:

```bash
python -m aidbg report --lang ja --wave samples/apb/wave.csv --log samples/apb/run.log
```
