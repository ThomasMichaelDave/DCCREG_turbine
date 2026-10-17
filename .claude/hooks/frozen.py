"""The frozen set, read from .claude/frozen-paths.txt: the one definition every check and hook uses."""
import fnmatch
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIST = ROOT / ".claude" / "frozen-paths.txt"
README_FREEZE = "b33baa2ae67f0ba62356efadc17c783e252cecd1"  # the freeze README's check reports


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


def checkout_of(path):
    """The git checkout (main or worktree, wherever it lives) that holds `path`, or None."""
    p = Path(os.path.realpath(path))
    for d in (p, *p.parents):
        if (d / ".git").exists():
            return d
    return None


def freeze_of(path, cwd=None):
    """The commit that freezes `path` in whichever checkout holds it, or None.

    A relative path is taken against `cwd` (the hook event's) or the repo root. Matching is per checkout, so a
    worktree's copy of a frozen file (e.g. under .claude/worktrees/) is frozen too."""
    p = Path(path)
    if not p.is_absolute():
        p = Path(cwd or ROOT) / p
    root = checkout_of(p)
    if root is None:
        return None
    rel = Path(_norm(os.path.realpath(p))).relative_to(Path(_norm(str(root)))).as_posix()
    for commit, specs in freezes().items():
        if any(_matches(rel, s) for s in specs):
            return commit
    return None


def short(commit):
    """The 7-character form every message names a freeze by."""
    return commit[:7]


class Unverifiable(Exception):
    """A freeze that cannot be checked (its commit is absent and cannot be fetched): callers fail closed."""


def _git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def ensure_commit(commit, root=ROOT):
    """Make `commit` present in checkout `root`, fetching it from origin if absent (a shallow cloud clone)."""
    if _git(root, "cat-file", "-e", f"{commit}^{{commit}}").returncode == 0:
        return
    shallow = _git(root, "rev-parse", "--is-shallow-repository").stdout.strip() == "true"
    fetch = _git(root, "fetch", "--quiet", *(["--depth=1"] if shallow else []), "origin", commit)
    if _git(root, "cat-file", "-e", f"{commit}^{{commit}}").returncode != 0:
        raise Unverifiable(f"freeze commit {short(commit)} is not in {root} and `git fetch origin {commit}` "
                           f"failed: {fetch.stderr.strip() or 'no output'}")


def diff_lines(commit, root=ROOT):
    """`git diff <commit> -- <its paths> | wc -l` in checkout `root`, as README's check counts it."""
    specs = freezes()[commit]
    ensure_commit(commit, root)
    r = subprocess.run(["git", "diff", commit, "--", *specs], cwd=root, capture_output=True)
    if r.returncode:
        raise Unverifiable(f"`git diff {short(commit)}` failed in {root}: {r.stderr.decode(errors='replace').strip()}")
    return len(r.stdout.splitlines())


def all_diff_lines(root=ROOT):
    return {c: diff_lines(c, root) for c in freezes()}
