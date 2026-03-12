#!/bin/bash
# SessionStart hook: query Supermemory for active WIP (scoped to current project)
PROJECT_KEY=$(cd "$(pwd)" && git rev-parse --show-toplevel 2>/dev/null | md5sum | cut -c1-8 || echo "unknown")
result=$(timeout 5 python ~/.claude/skills/supermemory/scripts/company_memory.py query \
  --q "active session WIP project:$PROJECT_KEY" \
  --container session_wip 2>/dev/null)
if [ $? -ne 0 ] || [ -z "$result" ] || [ "$result" = "No results found." ]; then
  echo '{"continue":true}'
else
  # Inject compact summary only (first 500 chars)
  compact=$(echo "$result" | head -c 500)
  echo '{"continue":true,"systemMessage":"SESSION WIP RECOVERED (project:'"$PROJECT_KEY"'): '"$compact"'"}'
fi
