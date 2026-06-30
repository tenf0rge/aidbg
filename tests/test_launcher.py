"""Tests for the launcher (Layer 2): a profile resolves, loads its skill
playbooks, and assembles a read-only prompt with the right battlefield."""
from pathlib import Path

import pytest

from aidbg import launcher

ROOT = Path(__file__).resolve().parents[1]


def test_profiles_are_discoverable():
    names = launcher.list_profiles()
    assert "mixed-signal" in names and "apb-uvm" in names


def test_resolve_profile_by_name():
    p = launcher.resolve_profile("apb-uvm")
    assert p.name == "AGENTS.md" and p.parent.name == "apb-uvm"


def test_resolve_unknown_profile_raises():
    with pytest.raises(FileNotFoundError):
        launcher.resolve_profile("does-not-exist")


def test_load_skills_reads_referenced_playbooks():
    agents = (ROOT / "profiles" / "apb-uvm" / "AGENTS.md").read_text(encoding="utf-8")
    skills = launcher.load_skills(agents, ROOT / "profiles" / "apb-uvm")
    names = [n for n, _ in skills]
    assert names == ["reg-data-mismatch", "uvm-env"]   # order preserved, de-duped
    body = dict(skills)["reg-data-mismatch"]
    assert "prdata" in body and "VERIFICATION-ENV" in body


def test_build_prompt_embeds_profile_skills_inputs_and_readonly():
    prompt = launcher.build_prompt(
        "apb-uvm", wave="w.csv", log="run.log", source="src",
        aidbg_cmd="aidbg", lang="ja", output="OUTPUT-HERE")
    # profile persona + battlefield skills are present
    assert "APB" in prompt
    assert "skill name=\"reg-data-mismatch\"" in prompt
    assert "skill name=\"uvm-env\"" in prompt
    # mixed-signal-only skills must NOT be loaded as their own block here
    # (a prose cross-reference inside a loaded playbook is fine)
    assert 'skill name="tranif-contention"' not in prompt
    # inputs, tools, output, read-only rule, language
    assert "w.csv" in prompt and "run.log" in prompt
    assert "grep-log" in prompt and "blame" in prompt
    assert "OUTPUT-HERE" in prompt
    assert "read-only" in prompt
    assert "日本語" in prompt


def test_build_prompt_mixed_signal_loads_its_own_skills():
    prompt = launcher.build_prompt(
        "mixed-signal", wave="w.txt", log="uvm.log", source="src",
        aidbg_cmd="aidbg")
    assert "skill name=\"tranif-contention\"" in prompt
    assert "skill name=\"glitch-triage\"" in prompt
    assert 'skill name="reg-data-mismatch"' not in prompt
