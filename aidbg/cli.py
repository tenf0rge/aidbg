"""aidbg CLI — first skill: explain an X-contention from wave + netlist + log.

Usage:
    python -m aidbg.cli triage --wave samples/wave.txt \
        --netlist samples/analog_mux.v --log samples/sim.log [--net AOUT]

If --net is omitted, the offending net is inferred from the sim log.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analyze import find_x_contention
from .netlist import parse_netlist
from .simlog import parse_log
from .wave import parse_wave


def _infer_net(logs) -> str | None:
    for m in logs:
        if m.severity in ("E", "F") or "contention" in m.text.lower():
            if m.nets:
                return m.nets[0]
    for m in logs:
        if m.nets:
            return m.nets[0]
    return None


def cmd_triage(args: argparse.Namespace) -> int:
    wf = parse_wave(Path(args.wave).read_text())
    gates = parse_netlist(Path(args.netlist).read_text(), filename=args.netlist)
    logs = parse_log(Path(args.log).read_text()) if args.log else []

    net = args.net or _infer_net(logs)
    if not net:
        print("Could not determine which net to analyze; pass --net.", file=sys.stderr)
        return 2

    print(f"== aidbg triage ==\nTarget net: {net}\n")

    if logs:
        print("Sim-log signals:")
        for m in logs:
            loc = f" {m.file}:{m.line}" if m.file else ""
            t = f" @t={m.time}ns" if m.time is not None else ""
            print(f"  [{m.severity}/{m.code}]{t}{loc} {m.text}")
        print()

    finding = find_x_contention(wf, gates, net)
    if finding is None:
        print(f"No X transition found on '{net}' in the waveform.")
        return 0
    print(finding.render())
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="aidbg", description="AI debug assistant for mixed-signal SoC")
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("triage", help="explain an X-contention")
    t.add_argument("--wave", required=True)
    t.add_argument("--netlist", required=True)
    t.add_argument("--log")
    t.add_argument("--net", help="net to analyze (basename or full path); inferred from log if omitted")
    t.set_defaults(func=cmd_triage)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
