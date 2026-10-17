"""README's frozen-file check: prints the diff's line count against b33baa2, which must be 0.

    python3 .claude/hooks/frozen_check.py          # b33baa2, README's check
    python3 .claude/hooks/frozen_check.py --all    # every freeze in .claude/frozen-paths.txt

A freeze commit missing from a shallow clone is fetched; if it cannot be, the check fails (exit 2), never passes.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import frozen  # noqa: E402

try:
    if "--all" in sys.argv[1:]:
        counts = frozen.all_diff_lines()
        for commit, n in counts.items():
            print(f"{frozen.short(commit)} {n}")
        sys.exit(1 if any(counts.values()) else 0)
    n = frozen.diff_lines(frozen.README_FREEZE)
except frozen.Unverifiable as e:
    print(f"FROZEN CHECK UNVERIFIABLE: {e}", file=sys.stderr)
    sys.exit(2)
print(n)
sys.exit(1 if n else 0)
