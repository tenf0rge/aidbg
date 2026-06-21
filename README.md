# aidbg

Autonomous debug assistant for mixed-signal SoC verification.

Targets designs where the control path is RTL (SystemVerilog) and the
functional path is analog, brought in as a schematic-extracted netlist
(library cells, pass gates modeled with `tranif`). Simulated with Xcelium in a
UVM environment. aidbg correlates **waveform** (FSDB → text), **simulation /
UVM log**, and the **source repository** to produce a debug report.

## Kernel + plugins

The goal: **swap the skills, debug any verification**. `aidbg/core` is a fixed
kernel; all domain knowledge is a plugin skill. Skills are **auto-discovered** —
every module under `aidbg/skills/` is imported automatically, and any directory
on the `AIDBG_SKILLS_PATH` env var is scanned too. Adding a skill is dropping a
file; no core edit, and skills can live entirely outside this repo.

A skill is self-contained: it carries its own logic, its own message catalog
(`add_messages(...)`, so translations don't live in core), and ideally its own
sample fixture and test. The kernel discovers it, feeds it a read-only `Context`,
runs it, and folds its findings into the report.

```bash
AIDBG_SKILLS_PATH=~/my-org-skills aidbg report --wave … --log …
```

## Two ways to run

**Deterministic** (`aidbg report`) — Python skills parse the inputs and emit a
ranked report. No LLM, fast, reproducible, CI-friendly.

**Autonomous** (`aidbg auto`) — aidbg drives an LLM agent (opencode) that calls
aidbg's primitive tools to gather facts and writes the report itself. The LLM
does the judgement; aidbg gives it precise, queryable access to huge
waveforms/logs so it never has to ingest them wholesale.

```bash
aidbg auto --wave samples/apb/wave.csv --log samples/apb/run.log --lang ja
```

### Primitive tool box (what the agent calls)

| command | purpose |
|---|---|
| `aidbg signals --wave W` | list signals |
| `aidbg query --wave W --signal S [--time N]` | value at a time / all change points |
| `aidbg grep-log --log L [--severity E] [--pattern RE]` | filter log events (JSON) |
| `aidbg blame --source DIR --file F --line N` | git blame a line |
| `aidbg find-driver --source DIR --signal S` | where a signal is driven in SV |

These are deterministic and stdlib-only — usable by any agent (opencode, Claude
Code, …) or directly by a human.

## Principles

- **Infrastructure and skills are separate.** `aidbg/core` is the
  infrastructure (loaders, git access, agent, report) and holds *no*
  debug-specific knowledge. `aidbg/skills` holds the debug heuristics as
  plugins. The seam between them is the read-only `Context` + the skill
  contract.
- **aidbg never edits source.** It only reads the design/TB and the inputs.
  Its sole output is the report. Fix suggestions are proposals for a human,
  never applied.
- **The report answers, in order:** what error → which commit/author
  introduced it (git blame) → **the root cause (most important)** → a
  suggested fix.

## Run

```bash
python -m aidbg report \
  --wave samples/wave.txt \
  --netlist samples/analog_mux.v \
  --log samples/uvm.log \
  --registry samples/assertions.json \
  --source samples \
  --lang ja \
  --out report.md --json report.json
```

`--lang {en,ja}` selects the report language (default `en`). Translations live
in `aidbg/core/i18n.py`; skills reference message keys, so adding a language is
a catalog edit, not a skill change.

The bundled `samples/` contain a self-consistent scenario: an RTL control bug
(`ctrl.sv` drives both selects high at reset) makes two `tranif1` pass gates in
`analog_mux.v` fight on the shared analog node `AOUT`. aidbg traces the X back
through the gates to the control statement, blames the commit, and proposes a
fix — and corroborates the glitch checker as a *real* (not sim-artifact) glitch.

## Layout

```
aidbg/
  core/                 infrastructure only (no bug knowledge)
    models.py           Finding / Evidence / FixProposal / Attribution / Report
    wave.py netlist.py logs.py   loaders (waveform / netlist / Xcelium+UVM log)
    repo.py             read-only git blame  ("who/which commit")
    context.py          read-only view handed to skills (the infra⊥skill seam)
    registry.py         skill contract + plugin registration
    agent.py            run matching skills, aggregate into a Report
    report.py           Markdown / JSON renderers
    cli.py              `aidbg report`
  skills/               debug knowledge as plugins (depend only on core API)
    tranif_contention.py    X from simultaneously-conducting tranif gates
    glitch_triage.py        fired glitch checker: real (design) vs sim-artifact
    uvm_env.py              UVM ERROR/FATAL triage by component role
    reg_data_mismatch.py    scoreboard read miscompare vs the actual bus prdata
samples/                runnable example scenarios + assertion registry
  fixture/              git-history fixture (planted bug at a known commit)
  scenario_tb/          verification-env root cause (sim-artifact glitch)
  apb/                  real-format APB scenario (CSV waveform + Xcelium UVM log)
```

## Waveform formats

Two text forms are auto-detected by `--wave`:

- **CSV table** — `Time(ns),sigA,sigB[31:0],…` then one row per timestep, bus
  values in hex (typical of an FSDB→CSV export). Compressed to change-points.
- **Event list** — `time scope.signal value(strength)`, one change per line
  (strength-aware, for mixed-signal `tranif` debugging).

### Assertion registry

Which SVA is a glitch checker is not guessed from naming — it is declared in a
user-maintained registry (`samples/assertions.json`), mapping each assertion to
`circuit_spec` or `glitch`. A fired glitch checker means a glitch was detected;
`glitch-triage` then decides real (design) vs sim-artifact (verification-env).

## Status

Working MVP of the core/skills architecture with three skills and an end-to-end
report (incl. git attribution). Next: a git-history sample fixture that plants a
bug at a known commit (to verify attribution), more skills, and an agent CLI
(opencode-based) front-end.
