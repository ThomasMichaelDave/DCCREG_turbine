"""The frozen set, read from .claude/frozen-paths.txt: the one definition every check and hook uses."""
import fnmatch
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIST = ROOT / ".claude" / "frozen-paths.txt"
README_FREEZE = "b33baa2"  # the freeze README's check reports


def freezes():
    """{commit: [pathspec, ...]} in file order."""
    out, commit = {}, None
    for raw in LIST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            commit = line[1:-1]
            out[commit] = []
        elif commit is None:
            raise ValueError(f"{LIST}: path before any [commit] header: {line}")
        else:
            out[commit].append(line)
    return out


def _norm(p):
    return p.lower() if sys.platform == "win32" else p


def _matches(rel, spec):
    rel, spec = _norm(rel), _norm(spec)
    if spec.endswith("/"):
        return rel.startswith(spec)
    if any(c in spec for c in "*?["):
        return fnmatch.fnmatchcase(rel, spec)
    return rel == spec or rel.startswith(spec + "/")


def freeze_of(path):
    """The commit that freezes `path` (absolute or relative to the repo root), or None."""
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    try:
        rel = Path(os.path.realpath(p)).relative_to(Path(os.path.realpath(ROOT)))
    except ValueError:
        if sys.platform != "win32":
            return None
        try:  # a drive letter or case mismatch on Windows
            rel = Path(_norm(os.path.realpath(p))).relative_to(Path(_norm(os.path.realpath(ROOT))))
        except ValueError:
            return None
    rel = rel.as_posix()
    for commit, specs in freezes().items():
        if any(_matches(rel, s) for s in specs):
            return commit
    return None


def diff_lines(commit):
    """`git diff <commit> -- <its paths> | wc -l`, as README's check counts it."""
    specs = freezes()[commit]
    r = subprocess.run(["git", "diff", commit, "--", *specs], cwd=ROOT,
                       capture_output=True, check=True)
    return len(r.stdout.splitlines())


def all_diff_lines():
    return {c: diff_lines(c) for c in freezes()}
