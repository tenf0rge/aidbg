"""Ground-truth check for "who/which commit introduced it" at the toolbox level.

Builds the git fixture (bug planted at a known commit) and verifies the
`find-driver` / `blame` primitives attribute the offending control line to the
exact commit/author — and that aidbg never modifies the source (read-only).
"""
import subprocess
from pathlib import Path

import pytest

from aidbg.toolbox import primitives

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


def _head(repo: Path) -> str:
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()


def test_find_driver_attributes_control_to_bug_commit(fixture_repo):
    # the control net SEL0 is driven in the RTL by the buggy commit
    hits = primitives.find_driver(str(fixture_repo), "sel0")
    assert hits, "expected to find where sel0 is driven in the RTL"
    bob = [h for h in hits if h["author"] == "Bob Hotfix"]
    assert bob, f"expected Bob Hotfix among drivers, got {hits}"
    assert any(h["file"].endswith("ctrl.sv") for h in bob)
    assert all(_head(fixture_repo).startswith(h["commit"]) for h in bob)


def test_blame_points_to_bug_line(fixture_repo):
    b = primitives.blame(str(fixture_repo), "rtl/ctrl.sv", 14)
    assert b is not None
    assert b["author"] == "Bob Hotfix"
    assert _head(fixture_repo).startswith(b["commit"])
    assert b["source"].endswith("rtl/ctrl.sv:14")


def test_primitives_are_read_only(fixture_repo):
    """aidbg must never modify the source — the tracked tree stays clean."""
    primitives.find_driver(str(fixture_repo), "sel0")
    primitives.blame(str(fixture_repo), "rtl/ctrl.sv", 14)
    status = subprocess.run(["git", "-C", str(fixture_repo), "status", "--porcelain"],
                            capture_output=True, text=True, check=True).stdout
    assert all(not line.startswith((" M", "M ")) for line in status.splitlines())
