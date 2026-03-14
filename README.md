# Claude Code Governance — Persistent Context, Multi-Model Reviews, Security Gates, and Browser Verification for Claude Code in VS Code

> Stop losing work to context compaction. Stop fixing the same bug three times. Stop shipping UI bugs that only exist in the browser. Give Claude Code a memory, a second opinion, a security conscience, and visual proof — zero configuration, fully automatic.

<!-- TODO: Add demo GIF here showing WIP recovery + council consultation -->
<!-- ![Demo](docs/assets/demo.gif) -->

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Works with Claude Code](https://img.shields.io/badge/Works%20with-Claude%20Code-blueviolet)](https://docs.anthropic.com/en/docs/claude-code)
[![Hooks: SessionStart + PreCompact](https://img.shields.io/badge/Hooks-SessionStart%20%2B%20PreCompact-green)]()
[![Models: Claude + GPT + Gemini](https://img.shields.io/badge/Models-Claude%20%2B%20GPT%20%2B%20Gemini-orange)]()

---

## Why This Exists

Claude Code is the best AI coding assistant available — but long sessions have a fatal flaw: **context compaction silently destroys your work-in-progress state.** You're mid-refactor across 8 files, the context window fills up, Claude summarizes... and your task context, decisions, and next steps are gone. Start a new session and Claude has zero memory of what you were building 5 minutes ago.

**This framework fixes that** with automatic WIP checkpointing via Claude Code hooks, cross-session memory via Supermemory, multi-model second opinions via OpenRouter, and mandatory security gates for sensitive code — all wired into Claude Code's native settings system. No external tools to run. No manual steps. It just works.

---

## Highlights

- **Never lose work to compaction again** — `PreCompact` hook automatically saves your task state before Claude's context window compresses. `SessionStart` hook restores it in your next session. Fully deterministic, zero manual intervention.
- **Multi-model council breaks fix loops** — after 2 failed bug fix attempts, Claude automatically consults GPT and Gemini via OpenRouter before trying again. Plans get council-validated before execution. Every consultation is logged with performance tracking.
- **Cross-project memory that actually persists** — architectural decisions, coding conventions, and project summaries are stored in Supermemory and queried automatically when planning new builds. Claude knows what you built last month.
- **Security reviews you can't forget to run** — auth, crypto, SQL, and credential-handling code automatically triggers Trail of Bits analysis. Critical findings require multi-model validation before the fix ships.
- **Graceful degradation, not graceful failure** — if Supermemory, OpenRouter, or Trail of Bits is down, the framework logs it, tells you, and keeps working. No service dependency blocks your session.
- **Frontend changes verified visually, not just compiled** — a Stop hook blocks Claude from reporting completion until it takes a browser screenshot via Playwright MCP. TypeScript passing doesn't mean the UI works. Emergency bypass available.
- **40% fewer tokens than the naive approach** — consolidated through council-validated architecture review. Every token in `CLAUDE.md` earns its keep.

---

## How It Compares

| Capability | Vanilla Claude Code | Claude Code + This Framework |
|-----------|-------------------|------------------------------|
| Context survives compaction | No — state is lost | Yes — automatic checkpoint + restore |
| Cross-session memory | None | Full WIP recovery + company memory |
| Bug fix assistance | Single model, can loop | Multi-model council after 2 failures |
| Plan review | Self-review only | GPT + Gemini validate before execution |
| Security enforcement | Manual / opt-in | Automatic on sensitive code paths |
| Frontend verification | "It compiles" = done | Browser screenshot required before completion |
| Convention tracking | Per-session only | Persistent across all projects |

Nothing else in the Claude Code ecosystem combines hooks, multi-model orchestration, persistent memory, and visual verification into a single governance layer. Most Claude Code customizations stop at `CLAUDE.md` rules — this framework makes those rules **enforceable and automatic**.

---

## Installation

**Requires:** [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code), Python 3.10+, [OpenRouter API key](https://openrouter.ai/)

```bash
# 1. Clone and install
git clone https://github.com/FC-FUZ/claude-code-governance.git
cd claude-code-governance && bash install.sh

# 2. Set your API keys
export OPENROUTER_API_KEY="your-key"
export SUPERMEMORY_API_KEY="your-key"

# 3. Restart VS Code — hooks are active immediately
```

<details>
<summary>Manual installation (if you prefer)</summary>

```bash
# Copy hook scripts
mkdir -p ~/.claude/scripts ~/.claude/state
cp scripts/*.sh scripts/*.py ~/.claude/scripts/
chmod +x ~/.claude/scripts/*.sh ~/.claude/scripts/*.py

# Copy governance rules
cp CLAUDE.md ~/.claude/CLAUDE.md

# Copy skills
cp -r skills/council ~/.claude/skills/council
cp -r skills/supermemory ~/.claude/skills/supermemory
cp -r skills/security ~/.claude/skills/security

# Merge hooks from settings.json into your ~/.claude/settings.json
```

</details>

---

## Usage

### WIP Recovery in Action

You're mid-task, the context window fills up, compaction fires:

```
[PreCompact hook] Checkpoint saved: project:a1b2c3d4, branch:feat/auth-rewrite
  Task: Migrating session tokens to Redis
  Files: src/auth/session.ts, src/middleware/validate.ts, src/config/redis.ts
  Next: Write integration tests for token refresh flow
```

Next session, you open Claude Code:

```
SESSION WIP RECOVERED (project:a1b2c3d4):
  Task: Migrating session tokens to Redis
  Status: in_progress
  Files modified: src/auth/session.ts, src/middleware/validate.ts, src/config/redis.ts
  Next action: Write integration tests for token refresh flow

Continue from "Migrating session tokens to Redis"?
```

Claude picks up exactly where it left off. No re-explaining. No lost context.

### Council Consultation

Claude fails to fix a TypeError twice. On the 3rd attempt:

```
Invoking the council — 2 fix attempts have failed.
Consulting Gemini and Codex before trying again.

--- COUNCIL RESPONSE ---
GPT Codex: "The issue is a race condition in the useEffect cleanup.
  The ref is captured at render time but the callback fires after unmount..."
Gemini: "Agree with race condition diagnosis. Additionally, the dependency
  array is missing the callback ref..."

Synthesis: Both models identify the race condition. Gemini caught the
  missing dependency. Applying combined fix...
```

### Security Gate

```
Security-sensitive code detected: modifying src/auth/jwt.ts
Running Trail of Bits static analysis...

Finding: HIGH — JWT secret loaded from environment without validation
  → Cross-referenced: similar issue found in project_api_gateway (2024-11)
  → Council validation required before applying fix...
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Claude Code CLI                       │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ SessionStart │  │  PreCompact  │  │   CLAUDE.md  │  │
│  │    Hook      │  │    Hook      │  │   (7 Rules)  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                  │          │
│         ▼                 ▼                  ▼          │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Skills Layer                        │    │
│  │  ┌───────────┐ ┌────────────┐ ┌──────────────┐  │    │
│  │  ┌───────────┐ ┌────────────┐ ┌────────────┐  │    │
│  │  │  Council   │ │ Supermemory│ │  Security  │  │    │
│  │  │ (OpenRouter│ │ (Company   │ │ (Trail of  │  │    │
│  │  │  fan-out)  │ │  Memory)   │ │  Bits)     │  │    │
│  │  └─────┬─────┘ └─────┬──────┘ └─────┬──────┘  │    │
│  └────────┼──────────────┼──────────────┼─────────┘    │
│           ▼              ▼              ▼               │
│    ┌────────────┐  ┌──────────┐  ┌─────────────┐      │
│    │GPT / Gemini│  │Supermemory│  │Trail of Bits│      │
│    │via OpenRouter│ │  API     │  │  Analyzers  │      │
│    └────────────┘  └──────────┘  └─────────────┘      │
│                                                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │           Browser Verification (Rule 7)          │   │
│  │  PostToolUse → marks dirty │ Stop → blocks turn  │   │
│  │  Playwright MCP / CLI for visual proof            │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## The 7 Rules

| # | Rule | Trigger | What It Does |
|---|------|---------|-------------|
| 1 | **Council Governance** | 2 failed bug fixes; plan finalization | Consults GPT + Gemini, logs model performance |
| 2 | **WIP Lifecycle** | Session start/end, compaction | Checkpoints and recovers work-in-progress state |
| 3 | **Project Context & Synergy** | New build planning | Queries company memory, detects cross-project synergies |
| 4 | **Convention Capture** | User states a decision | Stores architectural decisions with rationale |
| 5 | **Build Completion** | Working build confirmed | Stores structured project summary |
| 6 | **Security Gate** | Sensitive code touched | Trail of Bits analysis + council validation |
| 7 | **Browser Verification Gate** | Frontend files modified | Blocks completion until browser screenshot taken |

See [docs/rules-reference.md](docs/rules-reference.md) for the full breakdown of each rule.

---

## File Structure

```
claude-code-governance/
├── README.md                          # You are here
├── CLAUDE.md                          # The 7 governance rules (copy to ~/.claude/)
├── install.sh                         # One-command installer
├── settings.json                      # Full hook config (copy to ~/.claude/)
├── scripts/
│   ├── rehydrate-wip.sh               # SessionStart hook — recovers WIP (Rule 2)
│   ├── checkpoint-wip.sh              # PreCompact hook — saves WIP (Rule 2)
│   ├── gate-fix-attempt.py            # PreToolUse hook — tracks bug fix attempts (Rule 1)
│   ├── gate-plan-exit.py              # PreToolUse hook — validates council ran (Rule 1)
│   ├── mark-browser-verify-pending.py # PostToolUse hook — marks frontend dirty (Rule 7)
│   ├── gate-browser-verify.py         # Stop hook — blocks until verified (Rule 7)
│   └── setup-shared-env.sh            # Shared environment setup
├── skills/
│   ├── council/                       # Multi-model council (OpenRouter)
│   │   ├── SKILL.md
│   │   ├── references/council_config.json
│   │   └── scripts/council.py
│   ├── supermemory/                   # Company memory (Supermemory API)
│   │   ├── SKILL.md
│   │   └── scripts/company_memory.py
│   └── security/                      # Trail of Bits security analysis
│       └── SKILL.md
├── demo/
│   ├── README.md                      # Recording script + setup guide
│   ├── seed-wip.sh                    # Seeds all 7 demo states
│   ├── auth-service/                  # Backend demo (Rules 1-6)
│   │   └── src/auth/middleware.ts     # Planted bug: flat roles assumption
│   └── user-dashboard/               # Frontend demo (Rule 7)
│       └── src/components/            # Planted bug: visual-only role failure
└── docs/
    ├── rules-reference.md             # Detailed rule breakdown
    └── hook-architecture.md           # Hook internals + failure modes
```

---

## Roadmap

- [ ] Demo GIF / screen recording for README
- [ ] Publish skills as standalone repos (council, supermemory, security)
- [ ] VS Code extension wrapper for one-click install
- [ ] Dashboard UI for council performance analytics
- [ ] Support for additional council models (Llama, Mistral)
- [ ] Webhook notifications on security gate findings

---

## FAQ

**Q: Does this slow down Claude Code?**
No. The `SessionStart` hook has a 5-second timeout and runs once at session start. The `PreCompact` hook runs only before compaction (rare). Neither blocks normal usage.

**Q: What if I don't use Supermemory or OpenRouter?**
The framework degrades gracefully. Without Supermemory, WIP recovery is disabled but everything else works. Without OpenRouter, the council is skipped and Claude works solo. No service is required — they all enhance.

**Q: Can I use this with project-specific CLAUDE.md files?**
Yes. The governance rules go in your global `~/.claude/CLAUDE.md`. Project-specific rules in your repo's `CLAUDE.md` extend or override them. They compose, not conflict.

**Q: How much does the council cost?**
Each consultation makes 2 API calls via OpenRouter (one to GPT, one to Gemini). At typical token counts, this is $0.01-0.05 per consultation. The council only fires on failed bug fixes and plan validation — not on every message.

**Q: Will this work on Mac/Linux?**
Yes. The hook scripts are standard bash. Tested on Windows (Git Bash), macOS, and Ubuntu.

---

## Contributing

PRs welcome — see [issues](https://github.com/FC-FUZ/claude-code-governance/issues) for ideas. The framework is modular: you can contribute to rules, hooks, or skills independently.

Key files to customize:
1. `CLAUDE.md` — the behavioral rules
2. `scripts/*.sh` — the hook implementations
3. The skill directories — external service integrations

---

## License

[MIT](LICENSE) — use it, fork it, ship it.
