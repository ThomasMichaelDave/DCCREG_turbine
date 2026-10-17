"""PreToolUse hook: deny Edit / Write / MultiEdit / NotebookEdit on a frozen path."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import frozen  # noqa: E402

event = json.load(sys.stdin)
args = event.get("tool_input") or {}
path = args.get("file_path") or args.get("notebook_path")
commit = frozen.freeze_of(path, event.get("cwd")) if path else None
if commit:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"{path} is frozen: byte-identical with commit {commit} (.claude/frozen-paths.txt). "
            "Only the designer lifts a freeze; do not edit it or work around this."),
    }}))
sys.exit(0)
