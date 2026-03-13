# Demo: Recording the Governance Framework in Action

This directory contains a pre-built demo project with seeded memory state, designed to showcase all 6 governance rules in a single ~90-second screen recording.

## What the Demo Shows

| Time | Rule | Feature | What Happens |
|------|------|---------|-------------|
| 0:00 | **R3** | Company Memory | Claude queries Supermemory, finds api-gateway project + conventions |
| 0:15 | **R3** | Synergy Detection | "Found 2 related projects. api-gateway already has flat claim extraction you can reuse." |
| 0:25 | **R2** | WIP Recovery | Session restarts, SessionStart hook fires, previous task context auto-restores |
| 0:35 | — | Bug Fix #1 | Claude tries null check on payload.roles — tests still fail |
| 0:45 | — | Bug Fix #2 | Claude tries try/catch wrapper — masks error, breaks role access |
| 0:50 | **R1** | Council Fires | "Invoking the council — 2 fix attempts failed." GPT + Gemini respond |
| 1:00 | **R6** | Security Gate | Fix touches JWT validation — security skill auto-triggers, cross-references past incident |
| 1:10 | **R1** | Council Synthesis | Combined insight: flatten nested claims before extraction |
| 1:15 | **R4** | Convention Capture | User: "Always flatten claims at middleware layer." Claude stores it. |
| 1:20 | **R5** | Build Complete | Claude asks to store project summary in company memory |

All 6 rules visible in one recording.

## Setup (Before Recording)

### Step 1: Seed All Demo State

This pre-loads 5 items into Supermemory:
- 2 past project summaries (for synergy detection)
- 1 coding convention (for context awareness)
- 1 security incident (for cross-referencing)
- 1 WIP entry (for session recovery)

```bash
bash demo/seed-wip.sh
```

### Step 2: Open the Demo Project
```bash
cd demo/auth-service
code .
```

### Step 3: Start Recording

Use OBS, Loom, or any screen recorder. Open Claude Code and follow this script:

**Opening prompt (triggers R3 + R2):**
> "I need to add Keycloak SSO support to this auth service. The JWT validation in middleware.ts is throwing a TypeError on nested claims."

Claude will:
1. Query company memory — finds api-gateway, conventions, security history (**R3**)
2. See recovered WIP and ask to continue (**R2**)
3. Attempt to fix the bug — fails twice
4. Auto-invoke the council (**R1**)
5. Touch JWT code — security gate triggers (**R6**)
6. Apply the fix

**Closing prompt (triggers R4 + R5):**
> "Let's make it a rule: always flatten IDP claims at the middleware layer before passing to handlers."

Claude will:
1. Store the convention in Supermemory (**R4**)
2. Ask to store a build summary (**R5**)

### Step 4: Convert to GIF

```bash
# Standard conversion
ffmpeg -i recording.mp4 -vf "fps=15,scale=800:-1" -gifflags +transdiff docs/assets/demo.gif

# Higher quality (requires gifski)
gifski --fps 12 --width 800 -o docs/assets/demo.gif recording.mp4
```

## The Planted Bug

Located in `auth-service/src/auth/middleware.ts` line 23.

The `validateToken` function destructures `payload.sub` but doesn't handle Keycloak-style tokens where roles are nested under `realm_access.roles` instead of a flat `roles` array.

**Why it's tricky (designed to trigger the council):**

| Fix Attempt | What Happens | Why It Fails |
|------------|-------------|-------------|
| 1. Null check on `payload.roles` | Returns empty roles array | Silently breaks role-based access — no error, just no permissions |
| 2. try/catch around `.map()` | Catches the TypeError | Swallows the error, returns empty roles — same broken access |
| 3. Flatten nested claims (correct) | Extracts from `realm_access.roles` | Works for Keycloak, Auth0, and legacy formats |

The third fix is what the council typically recommends — it matches the seeded convention about flat claim maps.

## Seeded Supermemory State

| Container | Content | Showcases |
|-----------|---------|-----------|
| `project_api_gateway` | Past project with JWT auth + flat claims | R3: Synergy detection |
| `project_user_dashboard` | React app consuming api-gateway | R3: Cross-project data flow |
| `conventions` | "Always use flat claim maps" | R3: Convention awareness, R4: Capture |
| `project_api_gateway` | JWT secret hardcoded incident (2024-11) | R6: Security cross-reference |
| `session_wip` | Auth migration in progress | R2: WIP recovery |
