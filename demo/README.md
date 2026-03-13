# Demo: Recording the Governance Framework in Action

This directory contains a pre-built demo project with a planted bug, designed to showcase all three governance features in a single 60-second screen recording.

## What the Demo Shows

| Timestamp | Feature | What Happens |
|-----------|---------|-------------|
| 0:00-0:10 | **WIP Recovery** | New session opens, SessionStart hook fires, previous task context auto-restores |
| 0:10-0:15 | **User confirms** | "Yes, continue from the auth migration" |
| 0:15-0:30 | **Bug fix attempt 1** | Claude tries to fix the planted TypeError — fix doesn't work |
| 0:30-0:40 | **Bug fix attempt 2** | Claude tries a different approach — still fails |
| 0:40-0:55 | **Council fires** | "Invoking the council — 2 fix attempts failed." GPT + Gemini respond, Claude synthesizes |
| 0:55-1:05 | **Security gate** | The fix touches JWT validation — security skill auto-triggers |
| 1:05-1:15 | **Resolution** | Combined council insight + security review = correct fix |

## Setup (Before Recording)

### Step 1: Seed WIP State
This pre-loads a fake "previous session" into Supermemory so the SessionStart hook has something to recover:

```bash
bash demo/seed-wip.sh
```

### Step 2: Open the Demo Project
```bash
cd demo/auth-service
code .
```

### Step 3: Start Recording
Use any screen recorder (OBS, Loom, or VS Code's built-in). Open Claude Code and say:

> "The JWT validation in auth/middleware.ts is throwing a TypeError on line 23 when the token payload has nested claims. Can you fix it?"

Claude will:
1. First see the recovered WIP and ask to continue
2. Try to fix the bug (will fail — the bug is designed to be tricky)
3. Try again (will fail again — the second obvious fix has a different edge case)
4. Auto-invoke the council on attempt 3
5. The fix touches JWT code, so the security gate triggers

### Step 4: Convert to GIF
```bash
# If using OBS, convert the .mp4:
ffmpeg -i demo-recording.mp4 -vf "fps=15,scale=800:-1" -gifflags +transdiff docs/assets/demo.gif

# Or use gifski for better quality:
gifski --fps 12 --width 800 -o docs/assets/demo.gif demo-recording.mp4
```

## The Planted Bug

The bug is in `auth-service/src/auth/middleware.ts` line 23. The `validateToken` function destructures `payload.sub` but doesn't handle the case where the payload has nested claim objects (e.g., `payload.realm_access.roles`). When a Keycloak-style token comes in, `JSON.parse` succeeds but the nested object access throws because the middleware assumes flat claims.

The first obvious fix (adding a null check on `payload.sub`) doesn't work because the real issue is in the claim extraction loop at line 31. The second obvious fix (wrapping in try/catch) masks the error but breaks role-based access. The correct fix requires flattening nested claims before extraction — which is what the council typically catches.
