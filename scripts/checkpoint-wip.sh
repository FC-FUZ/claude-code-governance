#!/bin/bash
# PreCompact hook: instructs Claude to checkpoint WIP before compaction
# Uses prompt-type (systemMessage) for context preservation in compacted summary
# Note: PreCompact may not reliably execute external API calls, so this focuses
# on ensuring WIP state is preserved in the compaction summary itself.
#
# JSON output is generated via Python to prevent escaping bugs from special
# characters in branch names or project paths.

PROJECT_KEY=$(cd "$(pwd)" && git rev-parse --show-toplevel 2>/dev/null | md5sum | cut -c1-8 || echo "unknown")
BRANCH=$(cd "$(pwd)" && git branch --show-current 2>/dev/null || echo "unknown")

python3 -c "
import json, sys
pk, br = sys.argv[1], sys.argv[2]
msg = (
    f'COMPACTION IMMINENT (project:{pk}, branch:{br}): '
    'You MUST immediately save your current work state. Run: '
    'python ~/.claude/skills/supermemory/scripts/company_memory.py store '
    '--content \"<canonical WIP JSON per Rule 2 schema>\" '
    '--container session_wip --type wip --dynamic. '
    'Then confirm: Session checkpoint saved.'
)
print(json.dumps({'continue': True, 'systemMessage': msg}))
" "$PROJECT_KEY" "$BRANCH"
