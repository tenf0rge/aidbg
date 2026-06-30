"""Launcher (Layer 2): turn a *profile* into a running debug agent.

A profile is a directory under `profiles/<name>/` with an `AGENTS.md` that
defines the persona, the read-only rules, the report format, and — crucially —
*which skill playbooks to load*. The launcher reads that AGENTS.md, pulls in the
referenced `skills/*.md` playbooks (Layer 3), fills in the input paths and the
tool-command cheatsheet, and hands the whole prompt to an LLM engine.

aidbg itself does no debugging here: it only assembles the prompt and starts the
engine read-only. The judgement is the agent's; the skill playbooks are its
knowledge. Swap the profile → swap the battlefield.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# repo root = parent of the aidbg package (works for `pip install -e .` dev use)
ROOT = Path(__file__).resolve().parents[1]

_ENGINE_DEFAULT_BIN = {
    "opencode": "~/.opencode/bin/opencode",
    "claude": "~/.local/bin/claude",
}

_SKILL_REF = re.compile(r"skills/([\w-]+)\.md")


def _profile_search_dirs() -> list[Path]:
    dirs = [ROOT / "profiles"]
    raw = os.environ.get("AIDBG_PROFILES_PATH", "")
    dirs += [Path(p) for p in raw.replace(";", os.pathsep).split(os.pathsep) if p.strip()]
    return dirs


def resolve_profile(name: str) -> Path:
    """Return the AGENTS.md for `name`. Accepts a profile name, a profile dir,
    or a direct path to an AGENTS.md."""
    p = Path(name).expanduser()
    if p.is_file():
        return p
    if p.is_dir() and (p / "AGENTS.md").is_file():
        return p / "AGENTS.md"
    for d in _profile_search_dirs():
        cand = d / name / "AGENTS.md"
        if cand.is_file():
            return cand
    raise FileNotFoundError(
        f"profile '{name}' not found. Looked in: "
        + ", ".join(str(d) for d in _profile_search_dirs()))


def load_skills(agents_md: str, base: Path) -> list[tuple[str, str]]:
    """Find `skills/<name>.md` references in an AGENTS.md and read each playbook.

    Resolution order per skill: `<base>/skills/<name>.md` (profile-local),
    then `<ROOT>/skills/<name>.md`, then any dir on AIDBG_SKILLS_PATH.
    Returns [(name, body), ...] preserving first-seen order, de-duplicated.
    """
    roots = [base, ROOT]
    raw = os.environ.get("AIDBG_SKILLS_PATH", "")
    roots += [Path(p) for p in raw.replace(";", os.pathsep).split(os.pathsep) if p.strip()]

    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name in _SKILL_REF.findall(agents_md):
        if name in seen:
            continue
        seen.add(name)
        for r in roots:
            cand = (r / "skills" / f"{name}.md") if r.name != "skills" else (r / f"{name}.md")
            if cand.is_file():
                out.append((name, cand.read_text(encoding="utf-8")))
                break
        else:
            out.append((name, f"(skill playbook '{name}' not found)"))
    return out


def build_prompt(profile: str, *, wave: str | None, log: str | None,
                 source: str | None, aidbg_cmd: str, lang: str = "en",
                 output: str = "") -> str:
    """Assemble the full agent prompt from a profile + its skill playbooks."""
    agents_path = resolve_profile(profile)
    agents_md = agents_path.read_text(encoding="utf-8")
    skills = load_skills(agents_md, agents_path.parent)

    w, lg, src = wave or "(none)", log or "(none)", source or "(none)"
    tools = "\n".join([
        f"- 環境理解 (read the log first): {aidbg_cmd} env --log {lg}",
        f"- 失敗ログ抽出:                  {aidbg_cmd} grep-log --log {lg} --severity ERROR",
        f"- 信号の値:                      {aidbg_cmd} query --wave {w} --signal <NAME> [--time <NS>]",
        f"- 信号一覧:                      {aidbg_cmd} signals --wave {w}",
        f"- ソース検索 (regex):            {aidbg_cmd} grep-source --source {src} --pattern <REGEX>",
        f"- 駆動箇所:                      {aidbg_cmd} find-driver --source {src} --signal <NAME>",
        f"- git blame:                     {aidbg_cmd} blame --source {src} --file <F> --line <N>",
    ])
    playbooks = "\n\n".join(
        f"<skill name=\"{n}\">\n{body.strip()}\n</skill>" for n, body in skills)

    lang_line = "\nレポートは日本語で書くこと。" if lang == "ja" else ""
    parts = [
        agents_md.strip(),
        "## デバッグ対象の入力\n"
        f"- waveform: {w}\n- log: {lg}\n- source repo: {src}",
        "## 使える道具（aidbg のみ・全て read-only。シェルで実行し、各 JSON を返す）\n" + tools,
        "## 適用する手順書（skills — 下記の手順と例に従って事実を集め、推論せよ）\n" + playbooks,
    ]
    if output:
        parts.append(output)
    parts.append(
        "いかなる設計/TBファイルも編集・作成・削除しないこと（read-only）。"
        "出力はレポート1つのみ。" + lang_line)
    return "\n\n".join(parts)


def run(*, engine: str, profile: str, wave: str | None, log: str | None,
        source: str | None, lang: str, model: str, timeout: int,
        out: str | None) -> int:
    """Drive an LLM engine with the assembled prompt; emit the report it writes."""
    binary = shutil.which(engine) or os.path.expanduser(_ENGINE_DEFAULT_BIN[engine])
    if not os.path.exists(binary):
        print(f"engine '{engine}' not found. Install it or add it to PATH.", file=sys.stderr)
        return 3

    aidbg_cmd = f"{sys.executable} -m aidbg"
    workdir = tempfile.mkdtemp(prefix="aidbg_auto_")
    report_path = os.path.join(workdir, "report.md")

    if engine == "opencode":
        output = ("最終成果物のMarkdownレポートを、次の正確なパスにだけ書き出すこと"
                  f"（他のファイルは書かない）: {report_path}")
        argv = [binary, "run", "--model", model, "{prompt}"]
        note = f"opencode ({model}), free"
    else:  # claude
        output = "完成したMarkdownレポートを最終メッセージとして出力すること（ファイルは書かない）。"
        argv = [binary, "-p", "{prompt}", "--allowedTools", "Bash"]
        note = "claude (Claude Code — uses your Claude usage)"

    try:
        prompt = build_prompt(profile, wave=wave, log=log, source=source,
                              aidbg_cmd=aidbg_cmd, lang=lang, output=output)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 3
    argv = [prompt if a == "{prompt}" else a for a in argv]

    env = os.environ.copy()
    env["PATH"] = os.path.dirname(binary) + os.pathsep + env.get("PATH", "")
    print(f"[aidbg auto] profile '{profile}' → driving {note}…", file=sys.stderr)
    try:
        proc = subprocess.run(argv, cwd=workdir, env=env, capture_output=True,
                              text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"{engine} timed out after {timeout}s.", file=sys.stderr)
        return 4

    if engine == "opencode" and os.path.exists(report_path):
        md = Path(report_path).read_text(encoding="utf-8")
    else:
        md = proc.stdout.strip()
    if not md:
        print(f"[aidbg auto] no report produced. {engine} stderr:", file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        return 5

    if out and out != "-":
        Path(out).write_text(md, encoding="utf-8")
        print(f"wrote {out}")
    else:
        print(md)
    return 0


def list_profiles() -> list[str]:
    names = []
    for d in _profile_search_dirs():
        if d.is_dir():
            for sub in sorted(d.iterdir()):
                if (sub / "AGENTS.md").is_file():
                    names.append(sub.name)
    return names
