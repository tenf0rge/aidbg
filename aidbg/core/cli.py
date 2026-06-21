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
    import aidbg.skills  # noqa: F401  (populates the registry)
    from .registry import SKILLS

    if args.json:
        manifest = [{"name": s.name, "description": s.description,
                     "consumes": sorted(s.consumes)} for s in SKILLS]
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
    else:
        for s in SKILLS:
            print(f"{s.name}\n    {s.description}\n    consumes: {', '.join(sorted(s.consumes))}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="aidbg", description="autonomous mixed-signal SoC debug assistant")
    sub = p.add_subparsers(dest="cmd", required=True)

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
