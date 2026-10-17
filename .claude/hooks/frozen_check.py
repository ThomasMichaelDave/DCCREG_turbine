"""README's frozen-file check: prints the diff's line count against b33baa2, which must be 0.

    python3 .claude/hooks/frozen_check.py          # b33baa2, README's check
    python3 .claude/hooks/frozen_check.py --all    # every freeze in .claude/frozen-paths.txt
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import frozen  # noqa: E402

if "--all" in sys.argv[1:]:
    counts = frozen.all_diff_lines()
    for commit, n in counts.items():
        print(f"{commit} {n}")
    sys.exit(1 if any(counts.values()) else 0)
n = frozen.diff_lines(frozen.README_FREEZE)
print(n)
sys.exit(1 if n else 0)
