# Hook Architecture

How the WIP lifecycle hooks work under the hood.

## Overview

Claude Code supports hooks -- shell commands that execute in response to lifecycle events. This framework uses two hook events:

| Event | When It Fires | Our Script |
|-------|---------------|------------|
| `SessionStart` | Beginning of every new conversation | `rehydrate-wip.sh` |
| `PreCompact` | Before context window compression | `checkpoint-wip.sh` |

## SessionStart: Rehydrate

### Flow
```
Session starts
  -> Hook fires: bash ~/.claude/scripts/rehydrate-wip.sh
    -> Compute project fingerprint (md5 of git root)
    -> Query Supermemory session_wip container
    -> If WIP found: inject as systemMessage (first 500 chars)
    -> If not found: return {"continue": true} (no-op)
  -> Claude sees recovered WIP in system context
  -> Claude asks user: "Continue from [task]?"
```

### Script Details
```bash
#!/bin/bash
PROJECT_KEY=$(cd "$(pwd)" && git rev-parse --show-toplevel 2>/dev/null | md5sum | cut -c1-8 || echo "unknown")
result=$(timeout 5 python ~/.claude/skills/supermemory/scripts/company_memory.py query \
  --q "active session WIP project:$PROJECT_KEY" \
  --container session_wip 2>/dev/null)
```

**Key design choices:**
- `timeout 5` -- hard 5-second cap prevents session hangs if Supermemory is slow
- `md5sum | cut -c1-8` -- 8-char project fingerprint, sufficient for uniqueness
- `head -c 500` -- caps injected context to prevent token bloat
- Falls back to `{"continue": true}` on any failure (graceful degradation)

### Output Format
The hook returns JSON that Claude Code interprets:
```json
{"continue": true}

{"continue": true, "systemMessage": "SESSION WIP RECOVERED (project:abc123de): ..."}
```

## PreCompact: Checkpoint

### Flow
```
Context window nearing limit
  -> Claude Code triggers compaction
  -> Hook fires: bash ~/.claude/scripts/checkpoint-wip.sh
    -> Compute project fingerprint + branch name
    -> Return systemMessage instructing Claude to save WIP
  -> Claude receives instruction as system message
  -> Claude executes Supermemory store command
  -> Claude confirms: "Session checkpoint saved."
  -> Compaction proceeds
```

### Why Not a Direct API Call?

During compaction, Claude Code's tool execution pipeline may be in a transitional state. A command-type hook that calls an external API could:
1. Timeout if the API is slow
2. Fail silently if the tool pipeline is not fully available
3. Block compaction if it hangs

By using a systemMessage, we ensure the checkpoint instruction is always delivered. Claude then saves WIP through its normal tool execution flow, which is reliable.

## Project Scoping

Both scripts compute a PROJECT_KEY from the git root path:
```bash
PROJECT_KEY=$(git rev-parse --show-toplevel | md5sum | cut -c1-8)
```

This means:
- WIP for Project A is never accidentally loaded in Project B
- Multiple projects can have active WIP simultaneously
- The key is stable across sessions (same repo = same key)

## Failure Modes

| Failure | Behavior |
|---------|----------|
| Supermemory API down | Hook returns `{"continue": true}`, session starts normally |
| Git not initialized | PROJECT_KEY = "unknown", WIP still functions but is not project-scoped |
| Script timeout (>15s) | Claude Code's hook timeout kills the process, session continues |
| Python not found | Script fails, hook returns non-zero, session continues |
| Malformed JSON response | Claude Code ignores the output, session continues |

All failure modes result in the session continuing normally -- no failure blocks the user.

## Configuration

Hooks are configured in `~/.claude/settings.json`:
```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/scripts/rehydrate-wip.sh",
            "timeout": 15
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/scripts/checkpoint-wip.sh",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

- `matcher: "*"` -- fires for all conversations (can be scoped to specific paths)
- `timeout: 15` -- 15-second maximum execution time
- `type: "command"` -- executes as a shell command and reads stdout as JSON
