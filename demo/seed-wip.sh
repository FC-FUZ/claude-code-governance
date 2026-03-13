#!/bin/bash
# Seeds demo state into Supermemory so the recording showcases all 6 rules
set -e

PYTHON=$(command -v python3 || command -v python)
SCRIPT="$HOME/.claude/skills/supermemory/scripts/company_memory.py"

echo "=== Seeding Demo State into Supermemory ==="
echo ""

# --- 1. Seed a fake "past project" so Rule 3 (Synergy Detection) has something to find ---
echo "[1/5] Seeding past project: api-gateway..."
$PYTHON "$SCRIPT" store \
  --content "Project: api-gateway
Description: Central API gateway with JWT auth, rate limiting, and request routing
Tech Stack: Node.js, Express, jsonwebtoken, Redis
Key Patterns: Middleware chain, flat claim extraction, role-based access control
APIs/Interfaces Exposed: /auth/validate, /auth/refresh, /gateway/proxy
Data Produced: Auth tokens, session state in Redis
Data Consumed: Keycloak IDP for SSO tokens
Entry Point: src/index.ts
Repo Path: ~/projects/api-gateway" \
  --container project_api_gateway \
  --type project-summary \
  --tags "node,express,jwt,auth" 2>/dev/null && echo "  -> Done" || echo "  -> Failed (non-critical)"

# --- 2. Seed a second project for cross-project synergy ---
echo "[2/5] Seeding past project: user-dashboard..."
$PYTHON "$SCRIPT" store \
  --content "Project: user-dashboard
Description: React admin dashboard consuming api-gateway for auth
Tech Stack: React 18, TypeScript, Zustand, TailwindCSS
Key Patterns: Token refresh interceptor, role-based route guards
APIs/Interfaces Exposed: None (frontend only)
Data Produced: User preference state
Data Consumed: api-gateway /auth/validate and /auth/refresh
Entry Point: src/App.tsx
Repo Path: ~/projects/user-dashboard" \
  --container project_user_dashboard \
  --type project-summary \
  --tags "react,typescript,auth,frontend" 2>/dev/null && echo "  -> Done" || echo "  -> Failed (non-critical)"

# --- 3. Seed a convention so Rule 4 (Convention Capture) has history ---
echo "[3/5] Seeding convention: flat claim maps..."
$PYTHON "$SCRIPT" store \
  --content "Convention: Always use flat claim maps for JWT payloads, never nested objects.
Reason: Keycloak and Auth0 nest roles differently (realm_access vs permissions).
Flattening at the middleware layer normalizes all IDP formats into a single interface.
Established: 2024-09 during api-gateway auth rewrite." \
  --container conventions \
  --type convention \
  --static 2>/dev/null && echo "  -> Done" || echo "  -> Failed (non-critical)"

# --- 4. Seed a past security finding so Rule 6 cross-references it ---
echo "[4/5] Seeding security history: JWT secret incident..."
$PYTHON "$SCRIPT" store \
  --content "Security Incident: api-gateway deployed with hardcoded JWT_SECRET fallback (dev-secret-change-me) in production for 3 days (2024-11-14 to 2024-11-17).
Root cause: Environment variable not set in staging-to-prod promotion script.
Fix: Removed fallback, added startup validation that crashes if JWT_SECRET is missing.
Lesson: Never provide fallback values for security-critical environment variables." \
  --container project_api_gateway \
  --type security-incident \
  --tags "jwt,security,incident" 2>/dev/null && echo "  -> Done" || echo "  -> Failed (non-critical)"

# --- 5. Seed WIP state so SessionStart hook has context to recover ---
echo "[5/5] Seeding WIP state for session recovery..."
PROJECT_KEY="demo1234"
$PYTHON "$SCRIPT" store \
  --content "{
  \"schema_version\": 1,
  \"project_key\": \"$PROJECT_KEY\",
  \"branch\": \"feat/auth-migration\",
  \"current_task\": \"Migrating JWT validation to support Keycloak nested claims\",
  \"status\": \"in_progress\",
  \"files_modified\": [\"src/auth/middleware.ts\", \"src/auth/claims.ts\", \"src/config/keycloak.ts\"],
  \"decisions_made\": [\"Using flat claim map instead of nested objects\", \"Keeping backward compat with legacy tokens\"],
  \"next_action\": \"Fix TypeError on nested claim extraction in middleware.ts line 23\",
  \"rejected_approaches\": [\"Recursive claim flattener — too complex for V1\"]
}" \
  --container session_wip \
  --type wip \
  --dynamic 2>/dev/null && echo "  -> Done" || echo "  -> Failed (non-critical)"

echo ""
echo "=== All demo state seeded ==="
echo ""
echo "What was seeded:"
echo "  - Past project: api-gateway (JWT auth, middleware patterns)"
echo "  - Past project: user-dashboard (consumes api-gateway)"
echo "  - Convention: flat claim maps over nested objects"
echo "  - Security incident: hardcoded JWT secret in api-gateway"
echo "  - WIP state: auth migration in progress"
echo ""
echo "Ready to record. Open demo/auth-service/ in VS Code and start Claude Code."
