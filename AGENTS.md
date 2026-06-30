# aidbg — agent guide

aidbg is a read-only debug assistant. **You never edit, create, or delete any
design/TB source file.** You only run the read-only `aidbg` primitives and emit
one report.

This file is the generic note. The *operative* instructions for a run come from
the **profile** you are launched with (`profiles/<name>/AGENTS.md`), which sets
the persona, the read-only rules, the report format, and the skill playbooks to
load. See `aidbg profiles` for the list and `README.md` for the architecture.

## The contract

- Use only the aidbg tool box: `env`, `signals`, `query`, `grep-log`,
  `grep-source`, `find-driver`, `blame`. They are deterministic and JSON-out.
- Read the log first (`env`) to understand the environment before debugging.
- Back every root-cause claim with a query result. Never blame `uvm_pkg.sv`
  (it is a macro location, not the real source).
- The report answers, in order: ① what error → ② which commit/author (git
  blame) → ③ **root cause (most important)** → ④ suggested fix (proposal only).
