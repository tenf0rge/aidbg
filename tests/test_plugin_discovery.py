"""Auto-discovery: built-in skills load without an explicit import list, and an
external skill on AIDBG_SKILLS_PATH is picked up — i.e. dropping a file is enough.
"""
from aidbg.core import registry


def test_builtin_skills_discovered():
    skills = {s.name for s in registry.discover()}
    assert {"tranif-contention", "glitch-triage", "uvm-env", "reg-data-mismatch"} <= skills


def test_discovery_is_idempotent():
    before = len(registry.discover())
    after = len(registry.discover())
    assert before == after   # re-scan must not duplicate


def test_external_skill_path(tmp_path, monkeypatch):
    skill = tmp_path / "my_custom_skill.py"
    skill.write_text(
        "from aidbg.core.registry import register\n"
        "@register\n"
        "class Custom:\n"
        "    name = 'custom-demo'\n"
        "    description = 'external demo skill'\n"
        "    consumes = {'log'}\n"
        "    def match(self, ctx): return False\n"
        "    def analyze(self, ctx): return []\n"
    )
    monkeypatch.setenv("AIDBG_SKILLS_PATH", str(tmp_path))
    names = {s.name for s in registry.discover()}
    assert "custom-demo" in names
