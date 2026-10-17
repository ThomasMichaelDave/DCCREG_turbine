"""Stop hook: block the end of a turn while any freeze's diff is non-empty (catches shell writes)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import frozen  # noqa: E402

event = json.load(sys.stdin)
if event.get("stop_hook_active"):  # already blocked once this stop: never loop
    sys.exit(0)
dirty = {c: n for c, n in frozen.all_diff_lines().items() if n}
if dirty:
    which = ", ".join(f"{n} diff lines against {c}" for c, n in dirty.items())
    print(json.dumps({"decision": "block", "reason": (
        f"Frozen files changed ({which}; .claude/frozen-paths.txt). Only the designer lifts a freeze: "
        "restore them (git checkout <commit> -- <path>) until `python3 .claude/hooks/frozen_check.py --all` "
        "prints 0, and report what changed them.")}))
sys.exit(0)
