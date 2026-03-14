# Demo: Recording the Governance Framework in Action

This directory contains two pre-built demo projects with seeded memory state, designed to showcase all 7 governance rules in a single ~2-minute screen recording.

## What the Demo Shows

| Time | Rule | Feature | What Happens |
|------|------|---------|-------------|
| 0:00 | **R3** | Company Memory | Claude queries Supermemory, finds api-gateway project + conventions |
| 0:15 | **R3** | Synergy Detection | "Found 2 related projects. api-gateway already has flat claim extraction you can reuse." |
| 0:25 | **R2** | WIP Recovery | Session restarts, SessionStart hook fires, previous task context auto-restores |
| 0:35 | — | Bug Fix #1 | Claude tries null check on payload.roles — tests still fail |
| 0:45 | — | Bug Fix #2 | Claude tries try/catch wrapper — masks error, breaks role access |
| 0:50 | **R1** | Council Fires | "Invoking the council — 2 fix attempts failed." GPT + Gemini + Kimi respond |
| 1:00 | **R6** | Security Gate | Fix touches JWT validation — security skill auto-triggers, cross-references past incident |
| 1:10 | **R1** | Council Synthesis | Combined insight: flatten nested claims before extraction |
| 1:15 | **R7** | Browser Gate Blocks | Claude fixes frontend — tries to say "done" — Stop hook blocks (no browser evidence) |
| 1:25 | **R7** | Browser Verification | Claude opens dashboard in browser, takes screenshot, sees Keycloak user has "No roles" |
| 1:35 | **R7** | Visual Bug Caught | Screenshot proves the fix is incomplete — role badges missing for Keycloak token |
| 1:45 | **R7** | Verification Report | Claude files browser evidence report: URL, screenshot, console errors, verdict |
| 1:50 | **R4** | Convention Capture | User: "Always flatten claims at middleware layer." Claude stores it. |
| 1:55 | **R5** | Build Complete | Claude asks to store project summary in company memory |

All 7 rules visible in one recording.

## Demo Projects

### `auth-service/` — Backend (Rules 1, 2, 3, 4, 5, 6)

Minimal Express + JWT middleware with a **planted bug**: `extractRoles()` assumes roles is always a flat `string[]` array. Keycloak tokens nest roles under `realm_access.roles`, causing a silent access control failure or a TypeError on object-shaped roles.

### `user-dashboard/` — Frontend (Rule 7)

Minimal React + Vite dashboard that displays user info and role-based access. Has the **same planted bug** on the frontend side:

- `UserPanel.tsx` reads `user.roles` directly — shows "No roles assigned" for Keycloak tokens
- `RoleGuard.tsx` checks `user.roles` directly — blocks Keycloak admins from the admin panel
- A token switcher lets you toggle between Legacy (works) and Keycloak (broken) in the UI

**Why this bug needs a browser**: TypeScript compiles fine (`roles` is optional). Tests can pass. The bug is **only visible** when you click "Keycloak Token" and see "No roles assigned" + "Access denied" in the rendered UI.

## Setup (Before Recording)

### Step 1: Seed All Demo State

This pre-loads 7 items:
- 1 browser-verify state file (arms the Stop hook for Rule 7)
- 2 past project summaries (for synergy detection)
- 1 coding convention (for context awareness)
- 1 security incident (for cross-referencing)
- 1 WIP entry (for session recovery)
- 1 user-dashboard project context (for frontend bug context)

```bash
bash demo/seed-wip.sh
```

### Step 2: Install Frontend Dependencies

```bash
cd demo/user-dashboard && npm install
```

### Step 3: Open the Demo Projects

```bash
# Terminal 1 — Backend
cd demo/auth-service && code .

# Terminal 2 — Frontend
cd demo/user-dashboard && npm run dev
```

### Step 4: Start Recording

Use OBS, Loom, or any screen recorder. Open Claude Code and follow this script:

**Opening prompt (triggers R3 + R2):**
> "I need to add Keycloak SSO support to this auth service. The JWT validation in middleware.ts is throwing a TypeError on nested claims. The user-dashboard also needs to handle the new token format."

Claude will:
1. Query company memory — finds api-gateway, user-dashboard, conventions, security history (**R3**)
2. See recovered WIP and ask to continue (**R2**)
3. Attempt to fix the backend bug — fails twice
4. Auto-invoke the council (**R1**)
5. Touch JWT code — security gate triggers (**R6**)
6. Apply the backend fix
7. Fix the frontend components (UserPanel + RoleGuard)
8. Try to say "done" — **Stop hook blocks** (**R7**) — no browser evidence yet
9. Open `http://localhost:5173` — take screenshot
10. Click "Keycloak Token" — see if roles render correctly
11. File browser verification report with screenshot evidence (**R7**)

**Closing prompt (triggers R4 + R5):**
> "Let's make it a rule: always flatten IDP claims at the middleware layer before passing to handlers."

Claude will:
1. Store the convention in Supermemory (**R4**)
2. Verify browser evidence exists before proceeding (**R5** requires **R7**)
3. Ask to store a build summary (**R5**)

### Step 5: Convert to GIF

```bash
# Standard conversion
ffmpeg -i recording.mp4 -vf "fps=15,scale=800:-1" -gifflags +transdiff docs/assets/demo.gif

# Higher quality (requires gifski)
gifski --fps 12 --width 800 -o docs/assets/demo.gif recording.mp4
```

## The Planted Bugs

### Backend Bug — `auth-service/src/auth/middleware.ts` line 32

The `extractRoles` function assumes `payload.roles` is always a flat `string[]`. Keycloak tokens nest roles under `realm_access.roles`.

**Why it's tricky (designed to trigger the council):**

| Fix Attempt | What Happens | Why It Fails |
|------------|-------------|-------------|
| 1. Null check on `payload.roles` | Returns empty roles array | Silently breaks role-based access — no error, just no permissions |
| 2. try/catch around `.map()` | Catches the TypeError | Swallows the error, returns empty roles — same broken access |
| 3. Flatten nested claims (correct) | Extracts from `realm_access.roles` | Works for Keycloak, Auth0, and legacy formats |

The third fix is what the council typically recommends.

### Frontend Bug — `user-dashboard/src/components/UserPanel.tsx` + `RoleGuard.tsx`

Both components read `user.roles` directly (line `const roles = user.roles ?? [];`). For Keycloak tokens, this is `undefined`, so:

- **UserPanel** renders "No roles assigned" in red italic text
- **RoleGuard** shows "Access denied" with a red background

**Why it needs a browser (designed to trigger Rule 7):**

| What Passes | What's Actually Broken |
|------------|----------------------|
| `tsc` — TypeScript compiles (roles is optional) | Role badges don't render for Keycloak users |
| `npm run build` — production build succeeds | Admin panel shows "Access denied" for Keycloak admins |
| Unit tests (if mocking flat tokens) | Only visible by clicking "Keycloak Token" button in the browser |

The Stop hook enforces that Claude can't claim completion without a browser screenshot proving the fix works visually.

## Seeded Supermemory State

| Container | Content | Showcases |
|-----------|---------|-----------|
| `~/.claude/state/` | `browser-verify.json` — clean state | R7: Stop hook armed |
| `project_api_gateway` | Past project with JWT auth + flat claims | R3: Synergy detection |
| `project_user_dashboard` | React dashboard consuming api-gateway + known frontend bug | R3: Cross-project data flow, R7: Frontend context |
| `conventions` | "Always use flat claim maps" | R3: Convention awareness, R4: Capture |
| `project_api_gateway` | JWT secret hardcoded incident (2024-11) | R6: Security cross-reference |
| `session_wip` | Auth migration in progress | R2: WIP recovery |

## File Structure

```
demo/
├── README.md                              # You are here
├── seed-wip.sh                            # Seeds all 7 demo states
├── auth-service/                          # Backend demo (Rules 1-6)
│   ├── package.json
│   └── src/auth/
│       ├── middleware.ts                   # Planted bug: flat roles assumption
│       └── middleware.test.ts              # Tests proving the bug
└── user-dashboard/                        # Frontend demo (Rule 7)
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx                         # Token switcher (Legacy vs Keycloak)
        ├── types/user.ts                   # UserToken interface
        └── components/
            ├── UserPanel.tsx               # Planted bug: shows "No roles" for Keycloak
            └── RoleGuard.tsx               # Planted bug: blocks Keycloak admins
```
