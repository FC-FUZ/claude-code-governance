# Global Rules

## Graceful Degradation Policy

If Supermemory, OpenRouter, or Trail of Bits APIs timeout or fail:
1. Log error to console
2. Notify user: "[Service] unavailable — proceeding with local context only."
3. Continue without the failed service. Do NOT retry in a loop.
4. On next successful connection, sync any pending state.

---

## Rule 1: Council Governance (MANDATORY)

The council skill (`~/.claude/skills/council/`) provides multi-model second opinions via OpenRouter. All sub-rules below are NON-NEGOTIABLE.

### 1a: Bug Fix Guardrail — SELF-MONITOR REQUIRED
Track your own bug fix attempts within each conversation. A "failed attempt" = the fix was applied but the error persists, a test still fails, or the user says it didn't work.

**After the 2nd failed attempt at the same bug, you MUST STOP and do ALL of this before trying a 3rd fix:**

1. Announce to the user: "Invoking the council — 2 fix attempts have failed. Consulting Gemini and Codex before trying again."
2. Run this command (fill in the bracketed sections with actual context from the conversation):
```bash
python ~/.claude/skills/council/scripts/council.py consult --fan-out --context "BUG: [describe the bug/error]

ATTEMPT 1: [what was changed + what happened]
ATTEMPT 2: [what was changed + what happened]

ERROR OUTPUT: [paste the actual error]

RELEVANT CODE:
[paste the relevant code snippet]

What is the root cause and what fix do you recommend?"
```
3. Present both model responses clearly labeled
4. Synthesize: state where you agree/disagree with each model, then propose a revised approach combining the best insights
5. Only THEN attempt the 3rd fix using the collective insight
6. **Log the consultation** — evaluate each model's response and log the assessment:
```bash
python ~/.claude/skills/council/scripts/council.py log \
  --project-dir "$(pwd)" \
  --type bug_fix \
  --bug-type "[classify: runtime_error|type_error|logic_error|import_error|config_error|api_error|ui_bug|state_bug|async_error|test_failure|build_error|other]" \
  --context "[brief bug description]" \
  --attempt 3 \
  --models '[{"model_id":"openai/gpt-5.3-codex","recommendation_summary":"[1-2 sentence summary]","verdict":"[valid|partial|invalid]","adopted":[true|false],"strengths":["[specific strength]"],"weaknesses":["[specific weakness]"]},{"model_id":"google/gemini-3.1-pro-preview","recommendation_summary":"[1-2 sentence summary]","verdict":"[valid|partial|invalid]","adopted":[true|false],"strengths":["[specific]"],"weaknesses":["[specific]"]}]' \
  --outcome pending
```
Note the returned UUID — you will need it for the outcome update.
7. **After the fix resolves or fails**, update the outcome:
```bash
python ~/.claude/skills/council/scripts/council.py log \
  --project-dir "$(pwd)" \
  --type bug_fix \
  --bug-type "[same as step 6]" \
  --context "outcome update" \
  --update-id "[UUID from step 6]" \
  --models '[]' \
  --outcome [resolved|partially_resolved|unresolved] \
  --outcome-notes "[what happened]"
```

### 1b: Plan Validation — AUTO-CONSULT BEFORE EXITING PLAN MODE
When in plan mode and you have drafted a complete plan, you MUST do ALL of this BEFORE calling ExitPlanMode:

1. Announce: "Validating this plan with the council before finalizing."
2. Run this command (fill in the bracketed sections):
```bash
python ~/.claude/skills/council/scripts/council.py consult --fan-out --context "TASK: [user's request in 1-2 sentences]

CODEBASE CONTEXT: [key findings from exploration]

PROPOSED PLAN:
[the complete plan you drafted]

Review this plan. Is this the best approach? What would you change, add, or do differently? Flag any risks or missed edge cases."
```
3. Present a summary of council feedback (agreements, disagreements, suggestions)
4. Revise the plan incorporating the best feedback
5. **Log the consultation** — evaluate each model's feedback and log:
```bash
python ~/.claude/skills/council/scripts/council.py log \
  --project-dir "$(pwd)" \
  --type plan_validation \
  --context "[brief plan description]" \
  --models '[{"model_id":"openai/gpt-5.3-codex","recommendation_summary":"[1-2 sentence summary]","verdict":"[valid|partial|invalid]","adopted":[true|false],"strengths":["[specific]"],"weaknesses":["[specific]"]},{"model_id":"google/gemini-3.1-pro-preview","recommendation_summary":"[1-2 sentence summary]","verdict":"[valid|partial|invalid]","adopted":[true|false],"strengths":["[specific]"],"weaknesses":["[specific]"]}]' \
  --outcome [plan_improved|plan_unchanged]
```
6. Write the revised plan to the plan file with a "Council Review" section noting what changed
7. THEN call ExitPlanMode

### 1c: Historical Insights — LEARN FROM HISTORY
Before evaluating council responses (in both 1a and 1b), query supermemory for historical model performance insights:

```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py query \
  --q "council model performance [bug_type or 'plan validation']" \
  --container council_insights
```

Use these insights to inform your verdict assessment. For example:
- If Codex historically struggles with `ui_bug` (low valid rate), weight its UI recommendations more skeptically
- If Gemini excels at `async_error`, give its async debugging advice higher credibility
- If a model has a pattern of over-engineering fixes, watch for that tendency

**Verdict guidelines — be honest, not generous:**
- `valid`: The model correctly identified the root cause or gave actionable, correct advice
- `partial`: Some useful insights mixed with incorrect or irrelevant parts
- `invalid`: Wrong diagnosis, unhelpful advice, or harmful suggestion

**Strengths/weaknesses must be specific**, not vague:
- Good: "identified the race condition in session cookie handler"
- Bad: "good analysis"

**To view the current performance report for a project:**
```bash
python ~/.claude/skills/council/scripts/council.py report --project-dir "$(pwd)"
```

---

## Rule 2: WIP Lifecycle (MANDATORY)

Hooks handle the mechanical checkpoint/rehydrate cycle automatically. This rule defines the *behavioral expectations* Claude must follow.

### Canonical WIP Schema
Defined once, used everywhere:
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

### 2a: Rehydrate (automatic via SessionStart hook)
The `SessionStart` hook queries Supermemory `session_wip` scoped to the current project. When injected WIP context appears in a system message:
1. Display the recovered state to the user (task, status, files, next action)
2. Ask: "Continue from [task]?" before proceeding
3. If user declines, proceed normally without the recovered context

### 2b: Checkpoint (automatic via PreCompact hook + manual triggers)
The `PreCompact` hook fires before context compaction and instructs Claude to save WIP state. When the compaction system message appears, immediately store WIP using the canonical schema:
```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py store \
  --content "<canonical WIP JSON>" \
  --container session_wip \
  --type wip \
  --dynamic
```

**Also checkpoint manually when:**
- Completing a subtask marked in todo list
- After modifying 3+ files
- Before running test suites or deployments
- User says "pause", "hold on", "save your place"

After storing, confirm: "Session checkpoint saved."

### 2c: Interrupt
When user pivots mid-task or says "finish later", store WIP state using the canonical schema before switching context.

### 2d: Complete
When a build is confirmed working, purge the `session_wip` entry to prevent stale rehydration:
```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py store \
  --content "COMPLETED: <task description>" \
  --container session_wip \
  --type wip \
  --dynamic
```

---

## Rule 3: Project Context & Synergy (MANDATORY)

The company memory skill (`~/.claude/skills/supermemory/`) provides persistent context across ALL company AI and automation projects via Supermemory. Before planning ANY new automation, tool, or project, you MUST:

1. Announce: "Checking company memory for relevant context."
2. Run these commands:
```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py profile
python ~/.claude/skills/supermemory/scripts/company_memory.py query --q "<topic-relevant search>"
python ~/.claude/skills/supermemory/scripts/company_memory.py query --q "<topic-relevant search>" --container conventions
```
3. If a specific past project is relevant, also run:
```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py profile --container project_<name>
```
4. Incorporate ALL findings into your plan:
   - **Architecture alignment**: Use the same languages, frameworks, and patterns as existing projects. If deviating, explicitly justify why.
   - **Reuse over rebuild**: If an existing project already solves part of the problem, reference it and build on it.
5. **Synergy check** — compare the new build against ALL known projects in memory. Look for:
   - **Data flow**: Could this project produce data another consumes, or vice versa?
   - **Shared components**: Could an API, service, or module from another project be reused?
   - **Workflow chaining**: Could this be a step in an existing automation pipeline?
   - **Feature unlocking**: Could combining this with an existing project create a capability neither has alone?
6. If synergies are found, present them and factor into the plan:
```
Synergies Detected:
- [project_X] could consume the output of this build via [mechanism]
- [project_Y] already has a [component] that this build could reuse
- Combining this with [project_Z] would enable [new capability]
```
7. This happens BEFORE council plan validation (Rule 1b).

This is NON-NEGOTIABLE. Do NOT skip the memory check. Do NOT start planning without it.

---

## Rule 4: Convention & Decision Capture (MANDATORY)

When the user explicitly states a new convention or architectural decision during a conversation, you MUST immediately store it:

```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py store \
  --content "<the convention or decision>" \
  --container conventions \
  --type convention \
  --static
```

For architectural decisions (choosing X over Y), use this format:
```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py store \
  --content "Decision: <what was chosen>
Alternatives considered: <what was rejected>
Reason: <why this choice was made>" \
  --container decisions \
  --type decision
```

Confirm after storing: "Stored in company memory: [brief summary]"

---

## Rule 5: Build Completion (MANDATORY)

After completing a working build (user confirms it works), you MUST:

1. Ask: "Should I store a summary of this build in company memory?"
2. If yes, generate and store a structured summary:
```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py store \
  --content "Project: <name>
Description: <one-line description>
Tech Stack: <languages, frameworks, databases, hosting>
Key Patterns: <notable patterns used>
APIs/Interfaces Exposed: <endpoints, events, webhooks, exports>
Data Produced: <what data this project generates>
Data Consumed: <what external data/APIs this depends on>
Entry Point: <main file or start command>
Repo Path: <local path or repo URL>" \
  --container project_<name> \
  --type project-summary \
  --tags "<framework>,<language>,<key-tech>"
```
3. Store any new conventions established during the build in the `conventions` container.
4. Store any integration points with other projects as notes in both project containers.
5. Purge stale WIP via Rule 2d.

---

## Rule 6: Security Gate (MANDATORY)

The security skill (`~/.claude/skills/security/`) orchestrates Trail of Bits security analysis. The existing Anthropic `security-guidance` plugin remains as a baseline OWASP hook — the security skill provides deeper analysis on top.

When you are writing or modifying code that handles **authentication, cryptography, raw user input parsing, SQL/database queries, file system access with user-controlled paths, or external API credentials**, you MUST:

1. Announce: "Security-sensitive code detected. Running the security skill."
2. Follow the full workflow in the security skill's SKILL.md:
   - Run the appropriate sub-skill(s): `differential-review`, `audit-context-building`, `static-analysis`, or `supply-chain-risk-auditor`
   - Classify findings as Critical/High/Medium/Low
3. Cross-reference findings with company memory:
```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py query --q "security vulnerabilities past incidents"
```
4. If Critical or High findings are identified, consult the council before applying a fix:
```bash
python ~/.claude/skills/council/scripts/council.py consult --fan-out --context "SECURITY FINDING: [describe the vulnerability]

CODE: [the relevant code]

PROPOSED FIX: [your intended fix]

Is this fix correct and complete? Are there additional attack vectors we're missing?"
```
5. Present findings with severity classification and the fix approach
6. Apply the fix only after council validation for Critical/High issues

**Scope guard — do NOT trigger on:**
- Trivial frontend changes (React placeholders, CSS, labels, UI text)
- Read-only data display components
- Test files that mock auth/crypto for testing purposes
- Configuration changes that don't affect security boundaries

This is NON-NEGOTIABLE. If you touch auth, crypto, input parsing, SQL, or credential-handling code, you must run the security skill.
