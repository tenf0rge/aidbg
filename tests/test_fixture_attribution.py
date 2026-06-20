"""End-to-end test: build the git fixture (bug planted at a known commit) and
verify aidbg attributes the contention to that exact commit/author.

This is the ground-truth check for the "who/which commit introduced it" feature.
"""
import json
import subprocess
from pathlib import Path

import pytest

from aidbg.core import agent
from aidbg.core.context import Context
from aidbg.core.logs import parse_log
from aidbg.core.netlist import parse_netlist
from aidbg.core.repo import Repo
from aidbg.core.wave import parse_wave

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "samples" / "fixture" / "build_fixture.sh"


@pytest.fixture(scope="module")
def fixture_repo(tmp_path_factory):
    if not BUILD.exists():
        pytest.skip("fixture builder not present")
    target = tmp_path_factory.mktemp("aidbg_fixture") / "repo"
    out = subprocess.run(["bash", str(BUILD), str(target)],
                         capture_output=True, text=True, check=True)
    return Path(out.stdout.strip())


def _ctx(repo: Path) -> Context:
    ctx = Context()
    ctx.wave = parse_wave((repo / "sim" / "wave.txt").read_text())
    ctx.netlist = parse_netlist((repo / "netlist" / "analog_mux.v").read_text(),
                                filename=str(repo / "netlist" / "analog_mux.v"))
    ctx.log = parse_log((repo / "sim" / "uvm.log").read_text())
    ctx.assertions = json.loads((repo / "assertions.json").read_text())["assertions"]
    ctx.source_root = repo
    ctx.repo = Repo.discover(repo)
    return ctx


def _bug_commit(repo: Path) -> str:
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()


def test_attribution_points_to_bug_commit(fixture_repo):
    rep = agent.run(_ctx(fixture_repo))
    f = next(f for f in rep.findings if f.skill == "tranif-contention")
    assert f.attribution is not None, "expected git-blame attribution"
    assert f.attribution.author == "Bob Hotfix"
    assert _bug_commit(fixture_repo).startswith(f.attribution.commit)
    assert f.attribution.source.endswith("rtl/ctrl.sv:14")


def test_fix_is_proposal_only(fixture_repo):
    """aidbg must never modify the source — the working tree stays clean."""
    rep = agent.run(_ctx(fixture_repo))
    f = next(f for f in rep.findings if f.skill == "tranif-contention")
    assert f.fix is not None and "mutually exclusive" in f.fix.description.lower()
    status = subprocess.run(["git", "-C", str(fixture_repo), "status", "--porcelain"],
                            capture_output=True, text=True, check=True).stdout
    # only the untracked sim/ outputs may appear; no tracked source is modified
    assert all(not line.startswith(" M") and not line.startswith("M ")
               for line in status.splitlines())
