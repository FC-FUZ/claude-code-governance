#!/usr/bin/env python3
"""PreToolUse hook for ExitPlanMode — enforces Rule 1b (council plan validation).

Blocks ExitPlanMode unless a council fan-out consultation occurred AFTER the most
recent plan mode entry in the current session transcript.
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Emergency bypass
if os.environ.get("CLAUDE_BYPASS_COUNCIL") == "1":
    sys.exit(0)


def deny(reason):
    """Output deny JSON and exit 2 to block the tool call."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(2)


def parse_transcript_backwards(transcript_path):
    """Read transcript JSONL and return lines in reverse order (newest first)."""
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, IOError):
        return []
    return reversed(lines)


def check_transcript(transcript_path):
    """Scan transcript backwards for council consult after plan entry.

    Returns True if council validation was found after the most recent
    EnterPlanMode call.
    """
    found_council = False

    for line in parse_transcript_backwards(transcript_path):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        msg = entry.get("message", {})
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue

        for block in content:
            if not isinstance(block, dict):
                continue

            # Check for council consult in Bash commands
            if block.get("type") == "tool_use" and block.get("name") == "Bash":
                cmd = block.get("input", {}).get("command", "")
                if "council.py" in cmd and ("--fan-out" in cmd or "-f" in cmd) and "consult" in cmd:
                    found_council = True

            # Check for EnterPlanMode — this is our boundary
            if block.get("type") == "tool_use" and block.get("name") == "EnterPlanMode":
                # We've reached the plan entry point
                # If we already found a council consult above (more recent), allow
                return found_council

    # No EnterPlanMode found — might be re-entered plan mode via system
    # Fall through to council-log check
    return found_council


def check_council_log(cwd):
    """Fallback: check council-log.jsonl for recent plan_validation entry."""
    # Walk up to find git root
    project_dir = cwd
    check = Path(cwd)
    while check != check.parent:
        if (check / ".git").exists():
            project_dir = str(check)
            break
        check = check.parent

    log_path = Path(project_dir) / ".claude" / "council-log.jsonl"
    if not log_path.exists():
        return False

    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)

    try:
        for line in log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if entry.get("consultation_type") != "plan_validation":
                continue

            ts = entry.get("timestamp", "")
            try:
                entry_time = datetime.fromisoformat(ts)
                if entry_time > cutoff:
                    return True
            except (ValueError, TypeError):
                continue
    except (OSError, IOError):
        pass

    return False


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        # Can't parse input — allow to avoid blocking on hook errors
        sys.exit(0)

    transcript_path = hook_input.get("transcript_path", "")
    cwd = hook_input.get("cwd", os.getcwd())

    # Method A: Check transcript for council consult after plan entry
    if transcript_path and check_transcript(transcript_path):
        sys.exit(0)

    # Method B: Check council-log.jsonl for recent plan_validation
    if check_council_log(cwd):
        sys.exit(0)

    # Neither method found evidence — block
    deny(
        "BLOCKED by Rule 1b: Council plan validation is required before exiting plan mode.\n"
        "Run: python ~/.claude/skills/council/scripts/council.py consult --fan-out "
        "--context \"TASK: [user's request]\\n\\nPROPOSED PLAN:\\n[the plan]\\n\\n"
        "Review this plan. Is this the best approach? What would you change?\"\n"
        "Then log the result and call ExitPlanMode again."
    )


if __name__ == "__main__":
    main()
