"""aidbg CLI (v2 — 3-layer).

Two kinds of subcommand:

  auto      Layer 2 launcher: pick a profile, which loads its skill playbooks,
            and drive an LLM engine that debugs by calling the primitives below.
  <prims>   Layer 1 toolbox: deterministic, read-only queries an agent (or a
            human) calls — env / signals / query / grep-log / grep-source /
            blame / find-driver.

aidbg only ever reads its inputs and the source repo. It never edits them; the
sole output is the report.
"""
from __future__ import annotations

import argparse
import json
import sys

from . import launcher
from .toolbox import primitives


def cmd_auto(args: argparse.Namespace) -> int:
    return launcher.run(
        engine=args.engine, profile=args.profile, wave=args.wave, log=args.log,
        source=args.source, lang=args.lang, model=args.model,
        timeout=args.timeout, out=args.out, mode=args.mode)


def cmd_profiles(args: argparse.Namespace) -> int:
    names = launcher.list_profiles()
    if args.json:
        print(json.dumps(names, ensure_ascii=False))
    else:
        for n in names:
            print(n)
    return 0


def _emit(obj) -> int:
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    return 0


def cmd_env(a):          return _emit(primitives.env(a.log))
def cmd_signals(a):      return _emit(primitives.signals(a.wave))
def cmd_query(a):        return _emit(primitives.query(a.wave, a.signal, a.time))
def cmd_grep_log(a):     return _emit(primitives.grep_log(a.log, a.severity, a.pattern))
def cmd_grep_source(a):  return _emit(primitives.grep_source(a.source, a.pattern))
def cmd_blame(a):        return _emit(primitives.blame(a.source, a.file, a.line))
def cmd_find_driver(a):  return _emit(primitives.find_driver(a.source, a.signal))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="aidbg", description="autonomous SoC verification debug assistant (3-layer)")
    sub = p.add_subparsers(dest="cmd", required=True)

    # ---- Layer 2: launcher ----
    au = sub.add_parser("auto", help="pick a profile and drive an LLM engine to debug")
    au.add_argument("--profile", required=True,
                    help="profile name (profiles/<name>/AGENTS.md), a dir, or an AGENTS.md path")
    au.add_argument("--engine", choices=("opencode", "claude"), default="opencode",
                    help="LLM engine: opencode (free) or claude (Claude Code, uses your quota)")
    au.add_argument("--mode", choices=("readonly", "safe-edit", "edit"), default="readonly",
                    help="permission tier enforced on the engine (default: readonly; "
                         "safe-edit/edit relax the read-only guarantee)")
    au.add_argument("--wave")
    au.add_argument("--log")
    au.add_argument("--source")
    au.add_argument("--lang", choices=("en", "ja"), default="en")
    au.add_argument("--model", default="opencode/north-mini-code-free",
                    help="opencode model (provider/model); ignored for --engine claude")
    au.add_argument("--timeout", type=int, default=300, help="seconds (default 300)")
    au.add_argument("--out", help="write report to this path (default: stdout)")
    au.set_defaults(func=cmd_auto)

    pr = sub.add_parser("profiles", help="list available debug profiles")
    pr.add_argument("--json", action="store_true")
    pr.set_defaults(func=cmd_profiles)

    # ---- Layer 1: primitive tool box ----
    ev = sub.add_parser("env", help="understand the verification environment from the log (JSON)")
    ev.add_argument("--log", required=True)
    ev.set_defaults(func=cmd_env)

    sg = sub.add_parser("signals", help="list signals in a waveform")
    sg.add_argument("--wave", required=True)
    sg.set_defaults(func=cmd_signals)

    q = sub.add_parser("query", help="value of a signal at a time (or all change points)")
    q.add_argument("--wave", required=True)
    q.add_argument("--signal", required=True)
    q.add_argument("--time", type=int)
    q.set_defaults(func=cmd_query)

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

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
