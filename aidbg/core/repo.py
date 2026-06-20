"""Read-only git access: answer "who/which commit introduced this line".

Infrastructure layer. Uses `git blame` via subprocess. NEVER writes to the
repository — there are no mutating operations here by construction.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from .models import Attribution


class Repo:
    def __init__(self, root: Path):
        self.root = Path(root)

    @classmethod
    def discover(cls, start: Path) -> "Repo | None":
        try:
            out = subprocess.run(
                ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, check=True,
            )
            return cls(Path(out.stdout.strip()))
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def blame(self, file: str, line: int) -> Attribution | None:
        """Blame a single line. `file` may be absolute or repo-relative."""
        p = Path(file)
        rel = p if not p.is_absolute() else p
        try:
            out = subprocess.run(
                ["git", "-C", str(self.root), "blame", "-L", f"{line},{line}",
                 "--porcelain", "--", str(rel)],
                capture_output=True, text=True, check=True,
            ).stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

        commit = author = date = summary = None
        for ln in out.splitlines():
            if commit is None and ln and ln[0] != "\t":
                commit = ln.split()[0][:12]
            elif ln.startswith("author "):
                author = ln[len("author "):].strip()
            elif ln.startswith("author-time "):
                import datetime
                ts = int(ln.split()[1])
                date = datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
            elif ln.startswith("summary "):
                summary = ln[len("summary "):].strip()
        if commit is None:
            return None
        return Attribution(commit=commit, author=author, date=date,
                           summary=summary, source=f"{file}:{line}")
