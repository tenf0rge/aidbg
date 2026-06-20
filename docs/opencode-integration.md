# Driving aidbg from opencode

aidbg is the *skills + report* layer; opencode (or any agent CLI) is the
*autonomy* layer that decides what to run and explains the result. The seam is
intentionally thin: aidbg exposes a capability manifest and a JSON report, and
never touches the design source.

## 1. Register aidbg as a tool

opencode reads `AGENTS.md` for project conventions (already in the repo root)
and supports custom commands. Add a command that shells out to aidbg, e.g. in
`opencode.json`:

```json
{
  "command": {
    "aidbg-report": {
      "description": "Run aidbg over the current sim outputs and print findings",
      "command": "aidbg report --wave $WAVE --netlist $NETLIST --log $LOG --registry $REG --source $SRC --json -"
    },
    "aidbg-skills": {
      "description": "List aidbg debug skills",
      "command": "aidbg skills --json"
    }
  }
}
```

## 2. Agent loop

1. `aidbg skills --json` — discover what aidbg can detect.
2. Resolve the run's artifacts (waveform text export, Xcelium/UVM log,
   extracted netlist, assertion registry, source repo root).
3. `aidbg report --json …` — get ranked `Finding`s.
4. Read the findings and present: **error → commit/author (blame) → root cause
   → proposed fix**. For a fired glitch checker, relay whether it was rated a
   *real* glitch (design) or a *sim-artifact* (verification-env).
5. Stop. aidbg and the agent must not modify the DUT/TB.

## 3. Why the split

- **Infrastructure vs skills**: `aidbg/core` (loaders, git, agent, report)
  carries no debug knowledge; `aidbg/skills` carries only debug knowledge.
  A new failure mode is one new file in `aidbg/skills/` — opencode picks it up
  automatically via `aidbg skills`.
- **Read-only by construction**: the `Context` handed to skills exposes no
  mutating API, so neither aidbg nor the orchestrating agent can edit source.

## Status

The manifest (`aidbg skills`) and JSON report (`aidbg report --json`) are the
stable integration points today. A native opencode plugin packaging is future
work; the command-wrapper approach above works now.
