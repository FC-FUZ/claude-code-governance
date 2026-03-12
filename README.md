# Claude Code Governance Framework

An automated governance layer for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) that adds multi-model council reviews, persistent WIP lifecycle management, company-wide memory, and security gates — all running inside your existing Claude Code CLI sessions.

## Why This Exists

Claude Code is powerful out of the box, but long sessions hit real-world friction:

- **Context compaction loses work** — when the context window fills up, Claude summarizes and drops detail. Mid-task state can vanish.
- **No cross-session memory** — start a new conversation and Claude has zero context about what you were doing 5 minutes ago.
- **Single-model blind spots** — Claude is great, but every model has biases. A second opinion from GPT or Gemini catches things Claude misses.
- **Security is opt-in** — you have to remember to ask for a security review. On auth and crypto code, that's not good enough.

This framework solves all four with **6 rules + 2 hooks + 3 skills**, configured entirely through Claude Code's native settings and `CLAUDE.md` files.

## Architecture

```
+-----------------------------------------------------------+
|                    Claude Code CLI                         |
|                                                           |
|  +----------------+  +----------------+  +-------------+  |
|  | SessionStart   |  |  PreCompact    |  |  CLAUDE.md  |  |
|  |    Hook        |  |    Hook        |  |  (6 Rules)  |  |
|  +-------+--------+  +-------+--------+  +------+------+  |
|          |                    |                  |         |
|          v                    v                  v         |
|  +-----------------------------------------------------+  |
|  |                  Skills Layer                         |  |
|  |  +-----------+ +------------+ +--------------+       |  |
|  |  |  Council  | | Supermemory| |  Security    |       |  |
|  |  | (OpenRouter| | (Company  | | (Trail of    |       |  |
|  |  |  fan-out) | |  Memory)  | |  Bits)       |       |  |
|  |  +-----+-----+ +-----+-----+ +------+-------+       |  |
|  +---------+-----------+--------------+----------------+  |
|            |            |              |                   |
|            v            v              v                   |
|    +------------+  +----------+  +-------------+          |
|    |GPT / Gemini|  |Supermemory| |Trail of Bits|          |
|    |via OpenRouter| |  API    |  |  Analyzers  |          |
|    +------------+  +----------+  +-------------+          |
+-----------------------------------------------------------+
```

## Features

### 1. Multi-Model Council (Rule 1)
Automatic second opinions from GPT and Gemini via OpenRouter when it matters most:

- **Bug fix guardrail** — after 2 failed fix attempts, Claude automatically consults the council before trying a 3rd time. Prevents fix loops.
- **Plan validation** — before finalizing any implementation plan, the council reviews it for risks, missed edge cases, and alternative approaches.
- **Performance tracking** — every consultation is logged with verdicts (valid/partial/invalid), enabling historical analysis of which models give the best advice for which bug types.

### 2. WIP Lifecycle Hooks (Rule 2)
Zero-intervention work-in-progress persistence using Claude Code's native hook system:

| Event | Hook | What Happens |
|-------|------|-------------|
| **Session start** | `SessionStart` | Queries Supermemory for active WIP scoped to the current project. Injects recovered context automatically. |
| **Before compaction** | `PreCompact` | Instructs Claude to checkpoint current task state to Supermemory before context is compressed. |
| **Manual triggers** | Rule 2b | Checkpoints on subtask completion, 3+ file modifications, pre-test/deploy, or user command. |
| **Task complete** | Rule 2d | Purges WIP entry to prevent stale rehydration in future sessions. |

**Canonical WIP Schema:**
```json
{
  "schema_version": 1,
  "project_key": "<md5 prefix of git root>",
  "branch": "<current branch>",
  "current_task": "...",
  "status": "in_progress|blocked|awaiting_test",
  "files_modified": ["..."],
  "decisions_made": ["..."],
  "next_action": "...",
  "rejected_approaches": ["..."]
}
```

### 3. Company Memory (Rules 3-5)
Persistent knowledge graph across all projects via Supermemory:

- **Project context & synergy detection** (Rule 3) — before planning any new build, queries company memory for related projects, shared components, and integration opportunities.
- **Convention & decision capture** (Rule 4) — architectural decisions and coding conventions are stored immediately when stated, with rationale.
- **Build completion summaries** (Rule 5) — after a working build, stores a structured summary (stack, APIs, data flows) for future cross-project reference.

### 4. Security Gate (Rule 6)
Mandatory security review for sensitive code paths:

- Triggers automatically on auth, crypto, SQL, file system access, or credential-handling code
- Runs Trail of Bits static analysis via the security skill
- Cross-references findings with historical vulnerability data in company memory
- Critical/High findings require council validation before applying fixes
- Scope guard prevents false triggers on CSS changes, test mocks, etc.

### 5. Graceful Degradation
If any external service (Supermemory, OpenRouter, Trail of Bits) is unavailable:
1. Logs the error
2. Notifies the user
3. Continues without the failed service
4. Syncs pending state on next successful connection

## Installation

### Prerequisites
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- Python 3.10+
- [OpenRouter API key](https://openrouter.ai/) (for council)
- [Supermemory](https://supermemory.ai/) account (for company memory)
- Optional: [Trail of Bits](https://www.trailofbits.com/) tools (for security gate)

### Step 1: Clone This Repo
```bash
git clone https://github.com/FC-FUZ/claude-code-governance.git
cd claude-code-governance
```

### Step 2: Install Skills
Copy the skill directories into your Claude Code config:
```bash
cp -r skills/council ~/.claude/skills/council
cp -r skills/supermemory ~/.claude/skills/supermemory
cp -r skills/security ~/.claude/skills/security
```

### Step 3: Install Hook Scripts
```bash
mkdir -p ~/.claude/scripts
cp scripts/rehydrate-wip.sh ~/.claude/scripts/
cp scripts/checkpoint-wip.sh ~/.claude/scripts/
chmod +x ~/.claude/scripts/*.sh
```

### Step 4: Configure Claude Code Settings
Merge the hook configuration into your `~/.claude/settings.json`:
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

### Step 5: Install CLAUDE.md Rules
Copy the governance rules to your global Claude Code config:
```bash
cp CLAUDE.md ~/.claude/CLAUDE.md
```

Or merge the rules into your existing `CLAUDE.md` if you already have project-specific instructions.

### Step 6: Set Environment Variables
```bash
export OPENROUTER_API_KEY="your-openrouter-key"
export SUPERMEMORY_API_KEY="your-supermemory-key"
```

## File Structure

```
claude-code-governance/
├── README.md                          # This file
├── CLAUDE.md                          # The 6 governance rules (copy to ~/.claude/)
├── scripts/
│   ├── rehydrate-wip.sh               # SessionStart hook — recovers WIP state
│   └── checkpoint-wip.sh              # PreCompact hook — saves WIP before compaction
├── settings-example.json              # Hook configuration for ~/.claude/settings.json
└── docs/
    ├── rules-reference.md             # Detailed breakdown of each rule
    └── hook-architecture.md           # How the hooks work under the hood
```

## The 6 Rules

| # | Rule | Trigger | What It Does |
|---|------|---------|-------------|
| 1 | **Council Governance** | 2 failed bug fixes; plan finalization | Consults GPT + Gemini via OpenRouter, logs performance |
| 2 | **WIP Lifecycle** | Session start/end, compaction, manual | Checkpoints and recovers work-in-progress state |
| 3 | **Project Context & Synergy** | New build planning | Queries company memory, detects cross-project synergies |
| 4 | **Convention Capture** | User states a convention/decision | Stores architectural decisions with rationale |
| 5 | **Build Completion** | Working build confirmed | Stores structured project summary for future reference |
| 6 | **Security Gate** | Auth/crypto/SQL/credential code touched | Runs Trail of Bits analysis, council-validates critical fixes |

## Hook Scripts

### `rehydrate-wip.sh` (SessionStart)
```bash
#!/bin/bash
# Queries Supermemory for active WIP scoped to the current project
# Returns JSON with systemMessage if WIP found, or empty continue signal
PROJECT_KEY=$(git rev-parse --show-toplevel 2>/dev/null | md5sum | cut -c1-8)
result=$(timeout 5 python ~/.claude/skills/supermemory/scripts/company_memory.py query \
  --q "active session WIP project:$PROJECT_KEY" \
  --container session_wip 2>/dev/null)
# Injects compact summary (first 500 chars) into session context
```

### `checkpoint-wip.sh` (PreCompact)
```bash
#!/bin/bash
# Fires before context compaction — instructs Claude to save WIP state
# Uses systemMessage to ensure WIP schema is preserved in compacted summary
PROJECT_KEY=$(git rev-parse --show-toplevel 2>/dev/null | md5sum | cut -c1-8)
BRANCH=$(git branch --show-current 2>/dev/null)
# Returns JSON with systemMessage containing checkpoint instructions
```

## Council Performance Tracking

Every council consultation is logged with structured metadata:
```bash
# View performance report for current project
python ~/.claude/skills/council/scripts/council.py report --project-dir "$(pwd)"
```

Tracked metrics per model:
- **Verdict distribution** — valid / partial / invalid rates by bug type
- **Adoption rate** — how often the model's recommendation was used
- **Strengths/weaknesses** — specific patterns (e.g., "Gemini excels at async errors")

This data feeds back into Rule 1c (Historical Insights), so Claude weights future council responses based on each model's track record.

## Customization

### Adding Models to the Council
Edit the council skill's configuration to add or swap models. Any model available on OpenRouter can participate.

### Adjusting WIP Checkpoint Triggers
Modify the manual trigger list in Rule 2b of `CLAUDE.md`. The hook-based triggers (SessionStart, PreCompact) are fixed by the hook configuration.

### Scoping Rules to Specific Projects
Place a project-level `CLAUDE.md` in your repo root to override or extend the global rules. Project rules take precedence.

### Disabling Specific Rules
Comment out or remove individual rules from `CLAUDE.md`. The hooks will still function independently — they just won't have behavioral rules guiding Claude's response to the recovered/checkpointed state.

## Design Decisions

| Decision | Alternative Considered | Rationale |
|----------|----------------------|-----------|
| 6 consolidated rules (from original 10) | Keep all 10 separate rules | Reduced token overhead by ~40%, eliminated WIP rule fragmentation |
| Hooks for WIP mechanics | Purely behavioral rules | Deterministic — hooks fire regardless of Claude's interpretation |
| PreCompact as systemMessage (not API call) | External API call in PreCompact | PreCompact may not reliably execute external tool calls; context preservation is more reliable |
| Project-scoped WIP (md5 prefix) | Global WIP store | Prevents cross-project contamination when switching repos |
| Council after 2nd failure (not 1st) | Immediate council on first failure | Balances cost/latency against genuine need for second opinion |

## License

MIT

## Contributing

This framework was built for a specific workflow (multi-project AI/automation development). If you adapt it, the key files to customize are:
1. `CLAUDE.md` — the behavioral rules
2. `scripts/*.sh` — the hook implementations
3. The skill directories — the external service integrations
