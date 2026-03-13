#!/usr/bin/env python3
"""PreToolUse hook for Edit/Write — enforces Rule 1a (bug fix guardrail).

Blocks code edits after 2+ failed fix attempts (edit-then-fail patterns)
without a council consultation in between. Scans the session transcript
backwards — fully stateless.
"""

import json
import os
import sys
from pathlib import Path

# Emergency bypass
if os.environ.get("CLAUDE_BYPASS_COUNCIL") == "1":
    sys.exit(0)

# Error patterns in test/build output that indicate a failure
ERROR_PATTERNS = [
    "FAIL", "FAILED", "Error:", "error:", "Traceback",
    "AssertionError", "AssertionError", "TypeError", "SyntaxError",
    "ReferenceError", "RuntimeError", "ImportError", "ModuleNotFoundError",
    "panic:", "Build failed", "build failed", "test failed",
    "npm ERR!", "exit code 1", "Exit code: 1",
    "ERRORS", "CalledProcessError",
]

# Bash commands that are likely test/build/run (not exploratory)
TEST_BUILD_PATTERNS = [
    "test", "build", "run", "start", "check", "lint", "compile",
    "node ", "python ", "npm ", "npx ", "cargo ", "go ", "make",
    "pytest", "jest", "mocha", "vitest", "tsc", "eslint",
]

# Bash commands that are exploratory (never count as fix verification)
EXPLORATORY_PATTERNS = [
    "cat ", "ls ", "git ", "grep ", "rg ", "find ", "head ", "tail ",
    "echo ", "pwd", "which ", "type ", "where ", "wc ",
    "council.py",  # council invocations handled separately
]


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


def is_test_build_command(cmd):
    """Check if a bash command looks like a test/build/run command."""
    cmd_lower = cmd.lower()
    for pat in EXPLORATORY_PATTERNS:
        if cmd_lower.lstrip().startswith(pat):
            return False
    for pat in TEST_BUILD_PATTERNS:
        if pat in cmd_lower:
            return True
    return False


def has_error_output(text):
    """Check if tool result text contains error indicators."""
    for pat in ERROR_PATTERNS:
        if pat in text:
            return True
    return False


def extract_tool_result_text(block):
    """Extract text from a tool_result content block."""
    content = block.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(parts)
    return ""


def count_fix_failures(transcript_path):
    """Scan transcript backwards, counting edit-then-fail patterns.

    Returns the number of fix-then-fail cycles found since the last
    council consultation.

    A fix-then-fail = Edit/Write tool_use followed within ~5 messages
    by a Bash tool_use (test/build) whose result contains error patterns.
    """
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, IOError):
        return 0

    # Parse all entries into a flat list of events
    events = []
    for line in lines:
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
            btype = block.get("type", "")

            if btype == "tool_use":
                name = block.get("name", "")
                inp = block.get("input", {})
                events.append({"kind": "tool_use", "name": name, "input": inp})

            elif btype == "tool_result":
                text = extract_tool_result_text(block)
                events.append({"kind": "tool_result", "text": text})

    # Walk backwards through events
    failure_count = 0
    i = len(events) - 1

    while i >= 0:
        ev = events[i]

        # Council consult resets everything
        if ev["kind"] == "tool_use" and ev["name"] == "Bash":
            cmd = ev["input"].get("command", "")
            if "council.py" in cmd and "consult" in cmd:
                break  # stop counting — council was invoked

        # Look for a failing Bash test/build result
        if ev["kind"] == "tool_result" and has_error_output(ev["text"]):
            # Walk back to find the Bash tool_use that produced this result
            j = i - 1
            bash_cmd = None
            while j >= max(0, i - 3):
                if events[j]["kind"] == "tool_use" and events[j]["name"] == "Bash":
                    bash_cmd = events[j]["input"].get("command", "")
                    break
                j -= 1

            if bash_cmd and is_test_build_command(bash_cmd):
                # Check if there was an Edit/Write within ~5 events before the bash
                # (skip tool_results — they always sit between tool_use pairs)
                found_edit = False
                k = j - 1
                while k >= max(0, j - 8):
                    if (events[k]["kind"] == "tool_use"
                            and events[k]["name"] in ("Edit", "Write", "MultiEdit", "NotebookEdit")):
                        failure_count += 1
                        i = k - 1  # jump past this pattern
                        found_edit = True
                        break
                    # Another Bash test/build means a different attempt — stop looking
                    if (events[k]["kind"] == "tool_use"
                            and events[k]["name"] == "Bash"
                            and is_test_build_command(events[k]["input"].get("command", ""))):
                        break
                    k -= 1
                if found_edit:
                    continue

        i -= 1

    return failure_count


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    transcript_path = hook_input.get("transcript_path", "")
    if not transcript_path:
        sys.exit(0)

    failures = count_fix_failures(transcript_path)

    if failures >= 2:
        deny(
            f"BLOCKED by Rule 1a: {failures} failed fix attempts detected without "
            "consulting the council.\n"
            "You MUST run the council before attempting another fix:\n"
            "python ~/.claude/skills/council/scripts/council.py consult --fan-out "
            "--context \"BUG: [describe the bug]\\n\\n"
            "ATTEMPT 1: [what was changed + result]\\n"
            "ATTEMPT 2: [what was changed + result]\\n\\n"
            "ERROR OUTPUT: [the error]\\n\\n"
            "RELEVANT CODE:\\n[code snippet]\\n\\n"
            "What is the root cause and what fix do you recommend?\""
        )

    # Allow the edit
    sys.exit(0)


if __name__ == "__main__":
    main()
