#!/bin/bash
# Seeds a fake WIP entry so the SessionStart hook has context to recover
set -e

echo "Seeding demo WIP state into Supermemory..."

PROJECT_KEY="demo1234"

python ~/.claude/skills/supermemory/scripts/company_memory.py store \
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
  --dynamic

echo ""
echo "WIP seeded. When you open Claude Code in the demo/auth-service directory,"
echo "the SessionStart hook will recover this context automatically."
