"""aidbg CLI — autonomous debug run that emits a report.

    python -m aidbg report \
        --wave samples/wave.txt --netlist samples/analog_mux.v \
        --log samples/uvm.log --registry samples/assertions.json \
        --source samples/design_repo [--out report.md] [--json report.json]

aidbg only reads its inputs and the source repo; it never edits them. The sole
output is the report.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import agent, report as report_mod
from .context import Context
from .logs import parse_log
from .netlist import parse_netlist
from .repo import Repo
from .wave import parse_wave


def _load_registry(path: str | None) -> dict:
    if not path:
        return {}
    return json.loads(Path(path).read_text()).get("assertions", {})


def cmd_report(args: argparse.Namespace) -> int:
    inputs: dict[str, str] = {}
    ctx = Context()

    if args.wave:
        ctx.wave = parse_wave(Path(args.wave).read_text()); inputs["wave"] = args.wave
    if args.netlist:
        ctx.netlist = parse_netlist(Path(args.netlist).read_text(), filename=args.netlist)
        inputs["netlist"] = args.netlist
    if args.log:
        ctx.log = parse_log(Path(args.log).read_text()); inputs["log"] = args.log
    if args.registry:
        ctx.assertions = _load_registry(args.registry); inputs["registry"] = args.registry
    if args.source:
        ctx.source_root = Path(args.source); inputs["source"] = args.source
        ctx.repo = Repo.discover(Path(args.source))
        if ctx.repo:
            inputs["repo"] = str(ctx.repo.root)
    ctx.lang = args.lang

    if not any([ctx.wave, ctx.netlist, ctx.log]):
        print("Provide at least one of --wave / --netlist / --log.", file=sys.stderr)
        return 2

    rep = agent.run(ctx, inputs)

    if args.json:
        js = report_mod.render_json(rep)
        if args.json == "-":
            print(js)
        else:
            Path(args.json).write_text(js, encoding="utf-8")
            print(f"wrote {args.json}")
        if not args.out:
            return 0

    md = report_mod.render_markdown(rep, lang=args.lang)
    if args.out and args.out != "-":
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(md)
    return 0


def cmd_skills(args: argparse.Namespace) -> int:
    """List available skills so an agent/front-end can discover capabilities."""
    from .registry import SKILLS, discover
    discover()

    if args.json:
        manifest = [{"name": s.name, "description": s.description,
                     "consumes": sorted(s.consumes)} for s in SKILLS]
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
    else:
        for s in SKILLS:
            print(f"{s.name}\n    {s.description}\n    consumes: {', '.join(sorted(s.consumes))}")
    return 0


def cmd_env(args: argparse.Namespace) -> int:
    from . import primitives
    print(json.dumps(primitives.env(args.log), ensure_ascii=False, indent=2))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    from . import primitives
    print(json.dumps(primitives.query(args.wave, args.signal, args.time),
                     ensure_ascii=False, indent=2))
    return 0


def cmd_signals(args: argparse.Namespace) -> int:
    from . import primitives
    print(json.dumps(primitives.signals(args.wave), ensure_ascii=False, indent=2))
    return 0


def cmd_grep_log(args: argparse.Namespace) -> int:
    from . import primitives
    print(json.dumps(primitives.grep_log(args.log, args.severity, args.pattern),
                     ensure_ascii=False, indent=2))
    return 0


def cmd_grep_source(args: argparse.Namespace) -> int:
    from . import primitives
    print(json.dumps(primitives.grep_source(args.source, args.pattern),
                     ensure_ascii=False, indent=2))
    return 0


def cmd_blame(args: argparse.Namespace) -> int:
    from . import primitives
    print(json.dumps(primitives.blame(args.source, args.file, args.line),
                     ensure_ascii=False, indent=2))
    return 0


def cmd_find_driver(args: argparse.Namespace) -> int:
    from . import primitives
    print(json.dumps(primitives.find_driver(args.source, args.signal),
                     ensure_ascii=False, indent=2))
    return 0


_PLAYBOOK = """You are aidbg, an autonomous debug assistant for SoC verification.
You must NEVER edit, create, or delete any design or testbench source file. Only
READ — run the read-only `aidbg` query commands below — then deliver ONE report.

Inputs:
- waveform: {wave}
- log: {log}
- source repo (optional): {source}

Tool commands (run them in the shell; each prints JSON):
- understand the environment: {aidbg} env --log {log}
- failing log events:        {aidbg} grep-log --log {log} --severity ERROR
- signal value at a time:    {aidbg} query --wave {wave} --signal <NAME> --time <NS>
- list signals:              {aidbg} signals --wave {wave}
- blame a source line:       {aidbg} blame --source {source} --file <F> --line <N>
- where a signal is driven:  {aidbg} find-driver --source {source} --signal <NAME>
- search SV source (regex):  {aidbg} grep-source --source {source} --pattern <REGEX>

Procedure:
0. FIRST understand the environment: run `env` to see what was loaded (flist /
   compiled files / snapshot), the test and sequences, and the UVM component
   tree (driver/monitor/scoreboard/...). Also `signals` to see the DUT interface.
   Build a mental model of the testbench and the protocol before debugging.
1. Run grep-log to get the failing events.
2. For each failure, gather evidence with query / find-driver / blame. For a
   register read mismatch, find when the read actually completes (e.g. pready=1
   and pwrite=0 for that address) and query the data bus AT THAT cycle to decide
   DESIGN (bus carried wrong data) vs VERIFICATION-ENV (bus was right).
3. For a failed ASSERTION, infer its intent yourself — do NOT rely on any config.
   Read its definition (grep-source for the assertion name) and judge from the
   name/message whether it is a GLITCH checker (firing means a glitch was seen)
   or a normal spec check. For a glitch checker, decide real (DESIGN: a physical
   contention/X on the relevant net at that time) vs sim-artifact
   (VERIFICATION-ENV: no physical cause near the firing time — suspect a 0-delay
   race / delta-cycle ordering).
4. Decide the root cause layer: DESIGN or VERIFICATION-ENV, justified by evidence.

The report (Markdown) must contain, per finding: the error, git attribution if
any, the ROOT CAUSE (most important), and a suggested fix (proposal only — never
applied).{lang_line}
{output}
Do not modify any file."""

# engine -> (resolve binary, build argv(prompt,model), how to read the report)
_ENGINE_DEFAULT_BIN = {
    "opencode": "~/.opencode/bin/opencode",
    "claude": "~/.local/bin/claude",
}


def cmd_auto(args: argparse.Namespace) -> int:
    """Entry point: aidbg drives an LLM engine that uses the aidbg tools to debug."""
    import os
    import shutil
    import subprocess
    import tempfile

    engine = args.engine
    binary = shutil.which(engine) or os.path.expanduser(_ENGINE_DEFAULT_BIN[engine])
    if not os.path.exists(binary):
        print(f"engine '{engine}' not found. Install it or add it to PATH.", file=sys.stderr)
        return 3

    aidbg = f"{sys.executable} -m aidbg"
    workdir = tempfile.mkdtemp(prefix="aidbg_auto_")
    report_path = os.path.join(workdir, "report.md")
    lang_line = " Write the report in Japanese." if args.lang == "ja" else ""

    if engine == "opencode":
        output = f"Write the report as Markdown to this exact path and nothing else: {report_path}"
        argv = [binary, "run", "--model", args.model, "{prompt}"]
        note = f"opencode ({args.model}), free"
    else:  # claude
        output = "Output the complete Markdown report as your final message. Write no files."
        argv = [binary, "-p", "{prompt}", "--allowedTools", "Bash"]
        note = "claude (Claude Code — uses your Claude usage)"

    prompt = _PLAYBOOK.format(
        aidbg=aidbg, wave=args.wave or "(none)", log=args.log or "(none)",
        source=args.source or "(none)", lang_line=lang_line, output=output)
    argv = [prompt if a == "{prompt}" else a for a in argv]

    env = os.environ.copy()
    env["PATH"] = os.path.dirname(binary) + os.pathsep + env.get("PATH", "")
    print(f"[aidbg auto] driving {note}…", file=sys.stderr)
    try:
        proc = subprocess.run(argv, cwd=workdir, env=env, capture_output=True,
                              text=True, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        print(f"{engine} timed out after {args.timeout}s.", file=sys.stderr)
        return 4

    if engine == "opencode" and os.path.exists(report_path):
        md = Path(report_path).read_text(encoding="utf-8")
    else:
        md = proc.stdout.strip()
    if not md:
        print(f"[aidbg auto] no report produced. {engine} stderr:", file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        return 5

    if args.out and args.out != "-":
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(md)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="aidbg", description="autonomous mixed-signal SoC debug assistant")
    sub = p.add_subparsers(dest="cmd", required=True)

    au = sub.add_parser("auto", help="drive an LLM engine to debug using the aidbg tools")
    au.add_argument("--engine", choices=("opencode", "claude"), default="opencode",
                    help="LLM engine: opencode (free models) or claude (Claude Code, uses your quota)")
    au.add_argument("--wave")
    au.add_argument("--log")
    au.add_argument("--source")
    au.add_argument("--lang", choices=("en", "ja"), default="en")
    au.add_argument("--model", default="opencode/north-mini-code-free",
                    help="opencode model (provider/model); ignored for --engine claude")
    au.add_argument("--timeout", type=int, default=300, help="seconds (default 300)")
    au.add_argument("--out", help="write report to this path")
    au.set_defaults(func=cmd_auto)

    # ---- primitives (the tool box an agent calls) ----
    ev = sub.add_parser("env", help="understand the verification environment from the log (JSON)")
    ev.add_argument("--log", required=True)
    ev.set_defaults(func=cmd_env)

    q = sub.add_parser("query", help="value of a signal at a time (or all change points)")
    q.add_argument("--wave", required=True)
    q.add_argument("--signal", required=True)
    q.add_argument("--time", type=int)
    q.set_defaults(func=cmd_query)

    sg = sub.add_parser("signals", help="list signals in a waveform")
    sg.add_argument("--wave", required=True)
    sg.set_defaults(func=cmd_signals)

    gl = sub.add_parser("grep-log", help="filter log events by severity/pattern (JSON)")
    gl.add_argument("--log", required=True)
    gl.add_argument("--severity")
    gl.add_argument("--pattern")
    gl.set_defaults(func=cmd_grep_log)

    gs = sub.add_parser("grep-source", help="search SV source for a regex (JSON)")
    gs.add_argument("--source", required=True)
    gs.add_argument("--pattern", required=True)
    gs.set_defaults(func=cmd_grep_source)

    bl = sub.add_parser("blame", help="git blame a source line (JSON)")
    bl.add_argument("--source", required=True)
    bl.add_argument("--file", required=True)
    bl.add_argument("--line", type=int, required=True)
    bl.set_defaults(func=cmd_blame)

    fd = sub.add_parser("find-driver", help="where a signal is driven in SV source (JSON)")
    fd.add_argument("--source", required=True)
    fd.add_argument("--signal", required=True)
    fd.set_defaults(func=cmd_find_driver)

    s = sub.add_parser("skills", help="list available debug skills (capabilities)")
    s.add_argument("--json", action="store_true", help="emit machine-readable manifest")
    s.set_defaults(func=cmd_skills)

    r = sub.add_parser("report", help="run skills over the evidence and emit a debug report")
    r.add_argument("--wave")
    r.add_argument("--netlist")
    r.add_argument("--log")
    r.add_argument("--registry", help="assertion registry JSON (circuit_spec vs glitch)")
    r.add_argument("--source", help="design/TB source root (read-only; enables git blame)")
    r.add_argument("--lang", choices=("en", "ja"), default="en", help="report language (default: en)")
    r.add_argument("--out", help="write Markdown report to this path")
    r.add_argument("--json", help="also write JSON report to this path")
    r.set_defaults(func=cmd_report)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
