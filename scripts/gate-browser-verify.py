#!/usr/bin/env python3
"""Stop hook — enforces Rule 7 (Browser Verification Gate).

Blocks Claude from completing its turn if frontend files were modified
without browser verification evidence (Playwright MCP, Puppeteer MCP, or Playwright CLI tests).
Uses ~/.claude/state/browser-verify.json as the source of truth.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Emergency bypass
if os.environ.get("CLAUDE_BYPASS_BROWSER_VERIFY") == "1":
    sys.exit(0)

STATE_FILE = Path.home() / ".claude" / "state" / "browser-verify.json"

# Evidence signatures in transcript — MCP tool names
# Playwright MCP (@playwright/mcp) tools
PLAYWRIGHT_MCP_TOOLS = [
    "browser_navigate",
    "browser_screenshot",
    "browser_snapshot",
    "mcp__playwright__browser_navigate",
    "mcp__playwright__browser_screenshot",
    "mcp__playwright__browser_snapshot",
]
# Legacy Puppeteer MCP tools (kept for backward compat)
PUPPETEER_TOOL_NAMES = [
    "puppeteer_navigate",
    "puppeteer_screenshot",
    "mcp__puppeteer__puppeteer_navigate",
    "mcp__puppeteer__puppeteer_screenshot",
]

# CLI Playwright commands as fallback evidence
PLAYWRIGHT_COMMANDS = [
    "playwright test",
    "test:screenshots",
]


def read_state():
    """Read current state file."""
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"frontend_dirty": False}


def clear_state():
    """Reset state file to clean."""
    state = {
        "frontend_dirty": False,
        "touched_at": None,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "touched_paths": [],
        "verification_type": None,
    }
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def block(reason):
    """Output block JSON and exit 2 to prevent Claude from stopping."""
    print(json.dumps({
        "decision": "block",
        "reason": reason,
    }))
    sys.exit(2)


def check_transcript_for_evidence(transcript_path, touched_at):
    """Scan transcript for Puppeteer or Playwright evidence after touched_at."""
    if not transcript_path:
        return False, None

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, IOError):
        return False, None

    found_mcp_navigate = False
    found_mcp_screenshot = False  # Visual proof (browser_screenshot)
    found_mcp_snapshot = False    # DOM text only (browser_snapshot)
    found_playwright_cli = False

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

        for block_item in content:
            if not isinstance(block_item, dict):
                continue

            if block_item.get("type") == "tool_use":
                tool_name = block_item.get("name", "")

                # Check for Playwright MCP tool calls
                for pw_name in PLAYWRIGHT_MCP_TOOLS:
                    if pw_name in tool_name:
                        if "navigate" in tool_name:
                            found_mcp_navigate = True
                        if "screenshot" in tool_name:
                            found_mcp_screenshot = True
                        if "snapshot" in tool_name and "screenshot" not in tool_name:
                            found_mcp_snapshot = True

                # Check for legacy Puppeteer MCP tool calls
                for pup_name in PUPPETEER_TOOL_NAMES:
                    if pup_name in tool_name:
                        if "navigate" in tool_name:
                            found_mcp_navigate = True
                        if "screenshot" in tool_name:
                            found_mcp_screenshot = True

            # Check for Playwright CLI in Bash commands
            if block_item.get("type") == "tool_use" and block_item.get("name") == "Bash":
                cmd = block_item.get("input", {}).get("command", "")
                for pw_cmd in PLAYWRIGHT_COMMANDS:
                    if pw_cmd in cmd:
                        found_playwright_cli = True

    # Primary: navigate + screenshot (full visual proof)
    if found_mcp_navigate and found_mcp_screenshot:
        return True, "playwright_mcp"

    # Fallback: navigate + snapshot only (DOM text, not visual)
    if found_mcp_navigate and found_mcp_snapshot:
        return True, "playwright_mcp_snapshot_only"

    if found_playwright_cli:
        return True, "playwright_cli"

    return False, None


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        # Can't parse input — allow to avoid blocking on hook errors
        sys.exit(0)

    # Read state
    state = read_state()

    # If no frontend files were modified, allow
    if not state.get("frontend_dirty", False):
        sys.exit(0)

    # Frontend files are dirty — check for verification evidence
    transcript_path = hook_input.get("transcript_path", "")
    touched_at = state.get("touched_at")

    found, verify_type = check_transcript_for_evidence(transcript_path, touched_at)

    if found:
        # Update state with verification info and clear dirty flag
        state["frontend_dirty"] = False
        state["verified_at"] = datetime.now(timezone.utc).isoformat()
        state["verification_type"] = verify_type
        try:
            STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass

        # Warn (but allow) when only DOM snapshot was used, not a real screenshot
        if verify_type == "playwright_mcp_snapshot_only":
            print(json.dumps({
                "decision": "allow",
                "reason": (
                    "Rule 7 WARNING: browser_snapshot (DOM text) was used instead of "
                    "browser_screenshot (visual proof). Visual rendering was NOT fully "
                    "verified. Consider re-running with browser_screenshot for chart/UI changes."
                ),
            }))
        sys.exit(0)

    # No evidence found — block
    touched_paths = state.get("touched_paths", [])
    paths_str = "\n  - ".join(touched_paths[:10]) if touched_paths else "(unknown)"

    block(
        "BLOCKED by Rule 7: Browser verification required.\n"
        f"Frontend files modified:\n  - {paths_str}\n\n"
        "You MUST verify with Playwright MCP before completing:\n"
        "1. Ensure dev server is running (e.g. npm run dev)\n"
        "2. browser_navigate to the local dev URL\n"
        "3. browser_screenshot of the affected view\n"
        "4. Report verification results using Rule 7d format\n\n"
        "If Playwright MCP is unavailable, run:\n"
        "  npx playwright test\n\n"
        "To bypass (emergency only): set CLAUDE_BYPASS_BROWSER_VERIFY=1"
    )


if __name__ == "__main__":
    main()
