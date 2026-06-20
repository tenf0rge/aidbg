"""Skill contract + registry. The boundary that keeps skills out of infra.

A skill is any object with this shape (duck-typed)::

    name: str
    description: str
    consumes: set[str]          # {"wave","netlist","log","source","git"}
    def match(self, ctx) -> bool
    def analyze(self, ctx) -> list[Finding]

Skills register themselves with @register so the agent can discover them
without the core importing any skill by name.
"""
from __future__ import annotations

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


def register(cls):
    """Class decorator: instantiate and add to the global skill registry."""
    SKILLS.append(cls())
    return cls
