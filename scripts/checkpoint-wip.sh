#!/bin/bash
# PreCompact hook: instructs Claude to checkpoint WIP before compaction
# Uses prompt-type (systemMessage) for context preservation in compacted summary
# Note: PreCompact may not reliably execute external API calls, so this focuses
# on ensuring WIP state is preserved in the compaction summary itself.
PROJECT_KEY=$(cd "$(pwd)" && git rev-parse --show-toplevel 2>/dev/null | md5sum | cut -c1-8 || echo "unknown")
BRANCH=$(cd "$(pwd)" && git branch --show-current 2>/dev/null || echo "unknown")
echo '{"continue":true,"systemMessage":"COMPACTION IMMINENT (project:'"$PROJECT_KEY"', branch:'"$BRANCH"'): You MUST immediately save your current work state. Run: python ~/.claude/skills/supermemory/scripts/company_memory.py store --content \"project_key: '"$PROJECT_KEY"', branch: '"$BRANCH"', current_task: [describe current task], status: [in_progress|blocked], files_modified: [list files], next_action: [next step], schema_version: 1\" --container session_wip --type wip --dynamic. Then confirm: Session checkpoint saved."}'
