"""Skill contract + registry + auto-discovery. The boundary that keeps skills
out of infra.

A skill is any object with this shape (duck-typed)::

    name: str
    description: str
    consumes: set[str]          # {"wave","netlist","log","source","git"}
    def match(self, ctx) -> bool
    def analyze(self, ctx) -> list[Finding]

Skills register themselves with @register. They are auto-discovered: every
module under `aidbg.skills` is imported, plus any directory listed in the
`AIDBG_SKILLS_PATH` env var. Adding a skill means dropping a file — no core
edit, and skills can live entirely outside this repo.
"""
from __future__ import annotations

import importlib
import importlib.util
import os
import pkgutil
from pathlib import Path
from typing import Protocol, runtime_checkable

from .context import Context
from .models import Finding


@runtime_checkable
class Skill(Protocol):
    name: str
    description: str
    consumes: set[str]

    def match(self, ctx: Context) -> bool: ...
    def analyze(self, ctx: Context) -> list[Finding]: ...


SKILLS: list[Skill] = []
_names: set[str] = set()


def register(cls):
    """Class decorator: instantiate and add to the registry (idempotent by name)."""
    inst = cls()
    if inst.name not in _names:
        _names.add(inst.name)
        SKILLS.append(inst)
    return cls


def _env_paths() -> list[str]:
    raw = os.environ.get("AIDBG_SKILLS_PATH", "")
    return [p for p in raw.replace(";", os.pathsep).split(os.pathsep) if p.strip()]


def _load_path_dir(directory: str) -> None:
    d = Path(directory).expanduser()
    if not d.is_dir():
        return
    for f in sorted(d.glob("*.py")):
        if f.name.startswith("_"):
            continue
        mod_name = f"aidbg_ext_skill_{f.stem}"
        spec = importlib.util.spec_from_file_location(mod_name, f)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)   # @register runs on import


def discover(extra_paths: list[str] | None = None) -> list[Skill]:
    """Import all built-in + external skill modules so they self-register."""
    import aidbg.skills as pkg
    for m in pkgutil.iter_modules(pkg.__path__):
        if not m.name.startswith("_"):
            importlib.import_module(f"aidbg.skills.{m.name}")
    for directory in (extra_paths or []) + _env_paths():
        _load_path_dir(directory)
    return SKILLS
