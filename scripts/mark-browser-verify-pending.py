#!/usr/bin/env python3
"""PostToolUse hook for Edit/Write — marks browser verification pending when frontend files are modified.

Updates ~/.claude/state/browser-verify.json with dirty state when frontend files are edited.
Does NOT inject context into Claude's conversation to avoid token bloat.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path.home() / ".claude" / "state" / "browser-verify.json"

FRONTEND_PATTERNS = [
    "overwatch-dashboard/src/",
    "pbi-chat-visual/src/",
]

EXCLUDE_PATTERNS = [
    ".test.", ".spec.", "__tests__", ".d.ts",
    "types/", "README", ".md",
]


def normalize_path(p):
    """Normalize Windows backslashes to forward slashes."""
    return p.replace("\\", "/")


def is_frontend_file(file_path):
    """Check if the file path matches frontend patterns and is not excluded."""
    norm = normalize_path(file_path)
    # Check exclusions first
    for exc in EXCLUDE_PATTERNS:
        if exc in norm:
            return False
    # Check frontend patterns
    for pat in FRONTEND_PATTERNS:
        if pat in norm:
            return True
    return False


def read_state():
    """Read current state file, return default if missing/corrupt."""
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "frontend_dirty": False,
            "touched_at": None,
            "verified_at": None,
            "touched_paths": [],
            "verification_type": None,
        }


def write_state(state):
    """Write state file atomically."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    # Extract file path from tool input
    tool_input = hook_input.get("toolInput", {})
    file_path = tool_input.get("file_path", "")

    if not file_path or not is_frontend_file(file_path):
        sys.exit(0)

    # Update state file
    state = read_state()
    state["frontend_dirty"] = True
    state["touched_at"] = datetime.now(timezone.utc).isoformat()
    norm_path = normalize_path(file_path)
    if norm_path not in state.get("touched_paths", []):
        state.setdefault("touched_paths", []).append(norm_path)
    state["verified_at"] = None
    state["verification_type"] = None
    write_state(state)

    # Output minimal response — no additionalContext to avoid spam
    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
