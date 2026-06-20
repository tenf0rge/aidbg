# Agent guide for aidbg

aidbg is an **autonomous debug assistant** for mixed-signal SoC verification.
An AI agent (e.g. opencode) drives it; aidbg supplies the debug *skills* and a
*report*. This file tells the agent how to operate it.

## Hard rules

1. **Never edit the design or testbench source.** aidbg is read-only over the
   DUT/TB repository. Fix suggestions are *proposals* for a human; the agent
   must not apply them.
2. **The deliverable is the report**, nothing else. Do not open PRs or modify
   files in the target repo.

## Capabilities

Discover skills (machine-readable):

```bash
aidbg skills --json
```

Each skill declares what it `consumes` (`wave`, `netlist`, `log`, `source`,
`git`) and produces `Finding`s.

## Running a debug pass

```bash
aidbg report \
  --wave   <fsdb-text-export> \
  --netlist <extracted-netlist.v> \
  --log     <xcelium-or-uvm.log> \
  --registry <assertions.json> \
  --source  <design/TB repo root> \
  --json report.json --out report.md
```

`--source` enables git blame so the report can name the commit/author that
introduced the defect. The JSON output is the agent's primary input.

## Report contract (per finding)

- `error` — what was observed
- `attribution` — commit / author / date / `file:line` (git blame), when found
- `root_cause` — **the most important field**
- `fix` — a proposal, never applied
- `layer` — `design` | `verification-env` | `unknown`
- `confidence` — 0..1 (findings are ranked by this)

## Suggested agent loop

1. `aidbg skills --json` → know what can be detected.
2. Collect the run's wave/log/netlist/source paths.
3. `aidbg report --json` → read findings.
4. If a glitch checker fired, check whether `glitch-triage` rated it
   `design` (real) or `verification-env` (sim-artifact) and explain why.
5. Summarize for the human: error → attribution → root cause → proposed fix.
   Do **not** edit anything.
