# aidbg

Autonomous debug assistant for SoC verification. From SVA/UVM failures, it
works out the **root cause** and — most importantly — whether the defect is on
the **design (RTL/netlist)** side or the **verification-environment (UVM/TB)**
side. It only ever *reads* the waveform, log, and source repo; its sole output
is a report. It never edits a file.

## Three layers

aidbg is deliberately thin. The intelligence is the LLM agent; aidbg gives it
**eyes** (precise queries over huge waveforms/logs) and **knowledge** (skill
playbooks), then gets out of the way.

```
1. toolbox (aidbg/toolbox)  — read-only primitives the agent calls (the "eyes")
2. profile + engine         — profiles/<name>/AGENTS.md picks the persona, the
                              read-only rules, the report format, AND which
                              skill playbooks to load; an LLM engine does the
                              judgement
3. skills (skills/*.md)     — domain knowledge as *procedure playbooks* (method
                              + worked example). Swap these → swap the battlefield
```

The judgement lives in the LLM. A **skill is a markdown 手順書** — "do these
queries, read this evidence, here's a worked example, decide design vs TB" — not
code. To target a new kind of verification you write a playbook and a profile;
the toolbox and the core don't change.

## Run

```bash
# pick a profile; it loads its skill playbooks and drives an LLM engine
aidbg auto --profile apb-uvm \
  --wave samples/apb/wave.csv --log samples/apb/run.log --lang ja

# free, no login (bundled free model)
aidbg auto --profile mixed-signal --engine opencode --wave … --log … --source …
# higher quality (uses your Claude Code quota)
aidbg auto --profile apb-uvm --engine claude --wave … --log …
```

`--engine` switches the LLM driver: **opencode** (free models, no API key) or
**claude** (Claude Code CLI). `aidbg profiles` lists what's available.

### The primitive tool box (what the agent calls — Layer 1)

| command | purpose |
|---|---|
| `aidbg env --log L` | understand the environment (loaded files, snapshot, test, sequences, UVM component tree) — the "read the log first" step |
| `aidbg signals --wave W` | list signals |
| `aidbg query --wave W --signal S [--time N]` | value at a time / all change points |
| `aidbg grep-log --log L [--severity E] [--pattern RE]` | filter log events (JSON) |
| `aidbg grep-source --source DIR --pattern RE` | search SV/Verilog (read an assertion's intent by name) |
| `aidbg find-driver --source DIR --signal S` | where a signal is driven in SV |
| `aidbg blame --source DIR --file F --line N` | git blame a line ("who/which commit") |

Deterministic, stdlib-only, JSON out — usable by any agent or a human directly.

## Profiles and skills

A **profile** (`profiles/<name>/AGENTS.md`) is the swappable battlefield. It
states the read-only rules and report order, and lists the playbooks to load:

```markdown
## 読み込む手順書（skills）
- skills/reg-data-mismatch.md
- skills/uvm-env.md
```

Bundled profiles:

- **mixed-signal** — tranif pass-gate contention → X, glitch real-vs-artifact,
  UVM triage. (skills: tranif-contention, glitch-triage, uvm-env)
- **apb-uvm** — APB register read mismatch split into DUT vs TB bug by reading
  the real bus `prdata`. (skills: reg-data-mismatch, uvm-env)

External profiles/skills are first-class: put them on `AIDBG_PROFILES_PATH` /
`AIDBG_SKILLS_PATH` and they're found without touching this repo.

## Principles

- **The toolbox holds no debug knowledge.** It is read-only data access. The
  knowledge is in the skill playbooks; the judgement is the LLM's.
- **aidbg never edits source.** It reads the design/TB and the inputs. Its sole
  output is the report. Fix suggestions are proposals for a human, never applied.
- **The report answers, in order:** what error → which commit/author introduced
  it (git blame) → **the root cause (most important)** → a suggested fix.

## Layout

```
aidbg/
  toolbox/      Layer 1 — read-only primitives (the eyes)
    primitives.py   env / signals / query / grep-log / grep-source / blame / find-driver
    wave.py logs.py repo.py source.py   loaders + git blame + source scan
    models.py       Edge / LogEvent / Attribution
  launcher.py   Layer 2 — resolve a profile, load its skills, drive the engine
  cli.py        `aidbg auto` + the primitives
profiles/<name>/AGENTS.md   Layer 2 — persona, rules, report format, skill list
skills/<name>.md            Layer 3 — procedure playbooks (judgement knowledge)
samples/                    runnable scenarios + a git fixture (planted bug)
tests/                      toolbox + launcher + fixture-attribution tests
```

## Samples

- `samples/fixture/` — a git history fixture that plants a bug at a known commit
  (Alice = good, Bob Hotfix = the bug at `rtl/ctrl.sv:14`). Ground truth for the
  "who/which commit" attribution (`tests/test_fixture_attribution.py`).
- `samples/apb/` — real-format APB scenario: CSV waveform + Xcelium UVM log with
  two scoreboard mismatches that are actually one DUT bug + one TB bug.
- `samples/scenario_tb/` — a verification-env root cause (sim-artifact glitch).
