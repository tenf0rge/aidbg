# aidbg debug report

**Inputs**
- wave: `samples/wave.txt`
- netlist: `samples/analog_mux.v`
- log: `samples/uvm.log`
- registry: `samples/assertions.json`
- source: `samples`
- repo: `/home/yuki/projects/aidbg`

**5 finding(s)**, ranked by confidence.

## 1. tranif contention on AOUT → X
- **Layer**: DESIGN  ·  **Confidence**: 90%  ·  **Skill**: `tranif-contention`

**Error observed**

Node 'AOUT' becomes X at t=35ns; sim/assertion flags multi-driver strength conflict.

**Root cause (most important)**

2 pass gates conduct simultaneously because controls (SEL0, SEL1) are asserted together, so conflicting analog inputs fight on 'AOUT' → strength conflict → X. The defect is in the control logic that allows the enables to overlap.

**Attribution (git blame)**

- Commit `6aa18a403bd4` by tenf0rge (2026-06-20)
  - Initial commit: aidbg MVP with triage skill and sample scenario
  - introduced at `samples/ctrl.sv:15`

**Evidence**

- [t=35ns, net=tb.dut.u_mux.AOUT] AOUT goes X
- [t=35ns, `samples/analog_mux.v:15`] tranif1 conducting (ctrl SEL0=on), drives IN0=St0
- [t=35ns, `samples/analog_mux.v:16`] tranif1 conducting (ctrl SEL1=on), drives IN1=St1
- [`samples/ctrl.sv:15`] SEL0 driven: sel0 <= 1'b1;
- [`samples/ctrl.sv:18`] SEL0 driven: sel0 <= (chan == 2'd0);
- [`samples/fixture/bug/ctrl.sv:14`] SEL0 driven: sel0 <= 1'b1;
- [`samples/fixture/bug/ctrl.sv:17`] SEL0 driven: sel0 <= (chan == 2'd0);
- [`samples/fixture/design/rtl/ctrl.sv:12`] SEL0 driven: sel0 <= 1'b0;
- [`samples/fixture/design/rtl/ctrl.sv:15`] SEL0 driven: sel0 <= (chan == 2'd0);
- [`samples/ctrl.sv:16`] SEL1 driven: sel1 <= 1'b1;
- [`samples/ctrl.sv:19`] SEL1 driven: sel1 <= (chan == 2'd1);
- [`samples/fixture/bug/ctrl.sv:15`] SEL1 driven: sel1 <= 1'b1;
- [`samples/fixture/bug/ctrl.sv:18`] SEL1 driven: sel1 <= (chan == 2'd1);
- [`samples/fixture/design/rtl/ctrl.sv:13`] SEL1 driven: sel1 <= 1'b0;
- [`samples/fixture/design/rtl/ctrl.sv:16`] SEL1 driven: sel1 <= (chan == 2'd1);

**Suggested fix (proposal — not applied)**

- at `samples/ctrl.sv:15`
- Make SEL0, SEL1 mutually exclusive (one-hot). Ensure reset/default drives all enables inactive so the pass gates never overlap.


## 2. glitch 'chk_aout_no_glitch' is REAL (design)
- **Layer**: DESIGN  ·  **Confidence**: 80%  ·  **Skill**: `glitch-triage`

**Error observed**

Glitch checker 'chk_aout_no_glitch' fired at t=35ns.

**Root cause (most important)**

Corroborated by a physical contention/X event on 'AOUT' at t=35ns → this is a real glitch from the design (see tranif-contention finding for the driving logic).

**Evidence**

- [t=35ns] glitch checker fired
- [t=35ns, net=AOUT] contention/X on shared node

**Suggested fix (proposal — not applied)**

- Fix the contention root cause in the control logic; the glitch checker is correctly reporting a real design defect.


## 3. UVM ERROR [NOITEM] @ uvm_test_top.env.agent.seqr
- **Layer**: VERIFICATION-ENV  ·  **Confidence**: 65%  ·  **Skill**: `uvm-env`

**Error observed**

response fifo empty (t=95ns)

**Root cause (most important)**

Error originates in the stimulus/transport path → most likely a VERIFICATION-ENV defect (sequence/driver/TLM wiring).

**Evidence**

- [t=95ns, `./tb/seq/mux_seq.sv:33`] response fifo empty

**Suggested fix (proposal — not applied)**

- at `./tb/seq/mux_seq.sv:33`
- Inspect the sequence/driver: item generation, response handling, TLM port connections.


## 4. UVM ERROR [MISCMP] @ uvm_test_top.env.sb
- **Layer**: UNKNOWN  ·  **Confidence**: 45%  ·  **Skill**: `uvm-env`

**Error observed**

AOUT mismatch: exp=1 got=x (t=40ns)

**Root cause (most important)**

Mismatch reported by a checker — a symptom, not a root cause. Trace expected vs actual back to the DESIGN output; separately confirm the reference/expected value is itself correct (TB).

**Evidence**

- [t=40ns, `./tb/env/scoreboard.sv:142`] AOUT mismatch: exp=1 got=x

**Suggested fix (proposal — not applied)**

- at `./tb/env/scoreboard.sv:142`
- Compare DUT output against the reference model at the mismatch time; verify the predictor.


## 5. UVM FATAL [TLM] @ uvm_test_top.env.sb
- **Layer**: UNKNOWN  ·  **Confidence**: 45%  ·  **Skill**: `uvm-env`

**Error observed**

null transaction handle (t=100ns)

**Root cause (most important)**

Mismatch reported by a checker — a symptom, not a root cause. Trace expected vs actual back to the DESIGN output; separately confirm the reference/expected value is itself correct (TB).

**Evidence**

- [t=100ns, `./tb/env/scoreboard.sv:150`] null transaction handle

**Suggested fix (proposal — not applied)**

- at `./tb/env/scoreboard.sv:150`
- Compare DUT output against the reference model at the mismatch time; verify the predictor.

