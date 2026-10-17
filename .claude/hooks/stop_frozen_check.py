"""Stop / SubagentStop hook: block the end of a turn while any freeze's diff is non-empty (catches shell writes).

It checks the main checkout and, when the event's cwd is another checkout (a subagent's worktree), that one too."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import frozen  # noqa: E402

event = json.load(sys.stdin)
if event.get("stop_hook_active"):  # already blocked once this stop: never loop
    sys.exit(0)
roots = [frozen.ROOT]
here = frozen.checkout_of(event["cwd"]) if event.get("cwd") else None
if here and frozen._norm(str(here)) != frozen._norm(str(frozen.ROOT)):
    roots.append(here)
try:
    dirty = {(r, c): n for r in roots for c, n in frozen.all_diff_lines(r).items() if n}
except frozen.Unverifiable as e:  # fail closed: a crash here would be a silent, non-blocking hook error
    print(json.dumps({"decision": "block", "reason": (
        f"Cannot verify the freeze ({e}; .claude/frozen-paths.txt). Do not treat the frozen files as unchanged: "
        "report this to the designer, and make the commit reachable (e.g. `git fetch --unshallow`).")}))
    sys.exit(0)
if dirty:
    which = ", ".join(f"{n} diff lines against {frozen.short(c)} in {r}" for (r, c), n in dirty.items())
    print(json.dumps({"decision": "block", "reason": (
        f"Frozen files changed ({which}; .claude/frozen-paths.txt). Only the designer lifts a freeze: "
        "restore them (git checkout <commit> -- <path>) until `python3 .claude/hooks/frozen_check.py --all` "
        "prints 0, and report what changed them.")}))
sys.exit(0)
