# Scenario: verification-environment root cause (sim-artifact glitch)

The counterpart to the top-level `samples/` design-bug scenario. Here the
**design is clean** — `AOUT` is driven by one-hot selects with no contention and
never goes X — yet a glitch checker still fires.

aidbg should conclude:

- `tranif-contention` → **no finding** (no X on the shared node).
- `glitch-triage` → **SIM-ARTIFACT (verification-env)**: the glitch checker
  fired but no physical contention/X corroborates it near the firing time.
- `uvm-env` → the driver `[SYNC]` error is the real **verification-env** root
  cause (0-delay stimulus relative to the sampling edge).

Run:

```bash
python -m aidbg report \
  --wave samples/scenario_tb/wave.txt \
  --netlist samples/scenario_tb/analog_mux.v \
  --log samples/scenario_tb/uvm.log \
  --registry samples/scenario_tb/assertions.json
```

Together with the design-bug scenario, this demonstrates aidbg separating
**design** from **verification-environment** root causes — the core goal.
