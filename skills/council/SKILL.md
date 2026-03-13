---
name: council
description: Get second opinions from competing AI models (OpenAI, Google, MoonshotAI) via OpenRouter, without leaving Claude Code. IMPORTANT — This skill takes priority over gemini-api-dev and claude-developer-platform when the user wants an OPINION from another model, not to BUILD with that model's API. Trigger phrases — "get a second opinion", "ask Gemini", "ask GPT", "ask Codex", "ask Kimi", "consult Gemini", "consult GPT", "consult Codex", "consult Kimi", "get a few opinions", "council", "/council", "what would GPT say", "what would Gemini think", "what would Kimi say", "consult [any model name]", or when the user asks to consult, ask, or get a perspective from another AI model on a task. Uses the council.py script via OpenRouter — never call Gemini or OpenAI APIs directly for council consultations.
---

# Council — Multi-Model Second Opinions

Consult competing AI models from inside Claude Code. One OpenRouter API key, every model.

## Setup

Requires `OPENROUTER_API_KEY` in environment or `~/.env` or project `.env`.

Get a key at https://openrouter.ai/keys

## Three Invocation Modes

### 1. "Get a second opinion" — Auto-routed

User says something like "get a second opinion on this bug" without naming a model.

**Workflow:**
1. Analyze the current conversation context
2. Classify the task into a category using the config keywords in [council_config.json](references/council_config.json)
3. Resolve the category to the default model from config
4. **Play back the plan before executing:**

```
Council Plan:
  1. Fix login redirect loop  →  openai/gpt-5.3-codex  [bug_fix]

Proceed?
```

5. Wait for user confirmation, then run:

```bash
python scripts/council.py consult --category bug_fix --context "FULL CONTEXT HERE"
```

6. Present the response, then synthesize: agree, push back, or cherry-pick the best parts

### 2. "Ask Gemini about this" — Explicit override

User names a specific model or provider.

**Trigger phrases:** "ask Gemini", "ask GPT", "ask Codex", "ask Kimi", "what would Gemini say", "what would Kimi say"

**Provider shortcuts (auto-resolved to current flagship):**
- "Gemini" / "Google" → current Google flagship
- "Codex" / "GPT53" → OpenAI Codex flagship
- "GPT" / "OpenAI" / "ChatGPT" → OpenAI Codex flagship (default)
- "Kimi" / "Moonshot" / "K2" → current MoonshotAI flagship
- "Claude" / "Anthropic" → current Anthropic flagship

Aliases are defined in [council_config.json](references/council_config.json) under each provider's `aliases` array. The script resolves them to the `flagship` model ID automatically.

```bash
python scripts/council.py consult --model gemini --context "CONTEXT"
python scripts/council.py consult --model codex --context "CONTEXT"
```

### 3. "Get a few opinions" — Fan-out

User wants multiple perspectives at once.

**Trigger phrases:** "get a few opinions", "ask everyone", "what do the competitors think"

**Workflow:**
1. Classify each item if there's a laundry list
2. Play back the full plan:

```
Council Plan:
  1. Fix login redirect loop      →  openai/gpt-5.3-codex         [bug_fix]
  2. Redesign settings page       →  google/gemini-3.1-pro-preview [frontend]
  3. Add rate limiting strategy   →  anthropic/claude-opus-4.6     [architecture]

Proceed? (y / edit / cancel)
```

3. Wait for confirmation
4. Execute each consultation (parallel where independent)
5. Present each response labeled clearly, then synthesize across all

For a single question fan-out (not a laundry list):

```bash
python scripts/council.py consult --fan-out --context "CONTEXT"
```

This sends to all models in the `fan_out` list and returns each response.

## Automatic Triggers

These triggers are MANDATORY. They fire automatically without the user asking.

### A. Bug Fix Guardrail — Auto-consult after 2 failed attempts

Track bug fix attempts within a conversation. A "failed attempt" means: the fix was applied but the error persists, a test still fails, or the user says it didn't work.

**After the 2nd failed attempt at fixing the same bug/error, STOP and do this before attempting a 3rd fix:**

1. Announce: "Invoking the council — 2 fix attempts have failed. Consulting Codex, Gemini, and Kimi before trying again."
2. Package context for the council:
   - The bug/error description
   - What was tried in attempt 1 and attempt 2 (code changes + results)
   - The error output or failure evidence
   - The relevant code snippet(s)
3. Fan-out to all models:
```bash
python scripts/council.py consult --fan-out --context "BUG: [description]

ATTEMPT 1: [what was tried + result]
ATTEMPT 2: [what was tried + result]

ERROR OUTPUT: [error]

RELEVANT CODE:
[code snippet]

What is the root cause and what fix do you recommend?"
```
4. Present all responses clearly labeled by model name
5. Synthesize: combine the best insights from all council models and Claude's own analysis
6. Propose a revised fix approach based on the collective input
7. Only THEN attempt the 3rd fix

This applies to any bug, error, test failure, or broken behavior — not just code bugs. If something has been tried twice and isn't working, consult the council.

### B. Plan Mode Validation — Auto-consult before finalizing any plan

When in plan mode and a complete plan has been drafted, BEFORE calling ExitPlanMode:

1. Announce: "Validating this plan with the council before finalizing."
2. Package context for the council:
   - The user's original request (1-2 sentences)
   - Key findings from codebase exploration
   - The complete drafted plan (approach, files to modify, trade-offs)
3. Fan-out to all models:
```bash
python scripts/council.py consult --fan-out --context "TASK: [user's request]

CODEBASE CONTEXT: [key findings]

PROPOSED PLAN:
[the drafted plan]

Review this plan. Is this the best approach? What would you change, add, or do differently? Flag any risks or missed edge cases."
```
4. Present a summary of council feedback:
   - Where they agree with the plan
   - Where they disagree or suggest changes
   - Any risks or edge cases they flagged
5. Revise the plan incorporating the best feedback
6. Write the revised plan to the plan file with a "Council Review" section noting what changed
7. THEN call ExitPlanMode

---

## Category Classification

Infer the category from conversation context using these mappings:

| Category | Routes to | Signals |
|---|---|---|
| `bug_fix` | OpenAI Codex (gpt-5.3-codex) | bug, fix, error, crash, debug, broken, failing |
| `frontend` | Gemini 3.1 Pro | UI, UX, design, CSS, React, component, layout, page |
| `architecture` | Claude Opus 4.6 | architecture, system design, schema, scale, patterns |
| `refactor` | OpenAI Codex (gpt-5.3-codex) | refactor, clean up, optimize, simplify, extract |
| `general` | Gemini 3.1 Pro | Default fallback for anything else |
| `quick_check` | Gemini 3.0 Flash | Quick, fast, simple verification |

**Fan-out models** (consulted via `--fan-out`): OpenAI Codex, Gemini 3.1 Pro, Kimi K2.5

## Context Packaging

When sending context to another model, include:
- The specific question or problem statement
- Relevant code snippets (keep it focused, not the entire codebase)
- What approaches have already been tried
- What kind of answer is needed (diagnosis, code fix, design opinion, etc.)

Do NOT send the entire conversation history. Extract and summarize the relevant parts.

## Synthesis Rules

After receiving a response from the council:
1. **Present the raw response** clearly labeled with the model name
2. **State agreement or disagreement** — don't just parrot the response
3. **If disagreeing**, explain why with specific reasoning
4. **If agreeing**, note any additions or refinements
5. **Execute the best approach** — Claude remains the executor

## Model Discovery

To check what's currently available on OpenRouter:

```bash
python scripts/council.py models
python scripts/council.py models --provider openai
python scripts/council.py models --provider google
python scripts/council.py models --provider moonshotai
```

Use this when the user asks "what models are available" or when updating the config with newer models.

## Keeping Models Current

Auto-discover the latest flagship models from OpenRouter and update the config:

```bash
python scripts/council.py update
```

This queries OpenRouter's model catalog, finds the best model per provider using flagship ranking patterns, and updates `council_config.json` (flagships, defaults, and fan_out list). Run this when models seem outdated or when a user asks for the latest.

## Config

View current config:

```bash
python scripts/council.py config
```

Config lives at [references/council_config.json](references/council_config.json). Edit directly to change default mappings, add providers, or update model IDs.

## Performance Logging

Every council consultation (bug fix guardrail and plan validation) is logged to a per-project JSONL file at `<project-root>/.claude/council-log.jsonl`. Each line is a self-contained JSON entry.

### What Gets Logged

After each council consultation, Claude evaluates each model's response and logs:

- **consultation_type**: `bug_fix` or `plan_validation`
- **bug_type** (bug fixes only): `runtime_error`, `type_error`, `logic_error`, `import_error`, `config_error`, `api_error`, `ui_bug`, `state_bug`, `async_error`, `test_failure`, `build_error`, `other`
- **Per-model assessment**:
  - `verdict`: `valid` (correct and useful), `partial` (some useful parts), `invalid` (wrong or unhelpful)
  - `adopted`: whether Claude used this recommendation
  - `strengths`: specific things the model got right
  - `weaknesses`: specific things the model got wrong
- **outcome**: `resolved`, `partially_resolved`, `unresolved`, `pending`, `plan_improved`, `plan_unchanged`

### Assessment Workflow

After every council consultation:

1. Evaluate each model's response independently
2. Classify the bug type (for bug fixes)
3. Assign a verdict to each model — be honest, not generous
4. Note specific strengths and weaknesses — not vague ("good analysis") but specific ("identified the race condition in the session cookie handler")
5. Log using `council.py log`
6. After the fix works or fails, update the outcome using `--update-id`

### Logging Commands

**Log a new consultation:**
```bash
python scripts/council.py log \
  --project-dir "$(pwd)" \
  --type bug_fix \
  --bug-type runtime_error \
  --context "TypeError in payment handler" \
  --attempt 3 \
  --models '[{"model_id":"openai/gpt-5.3-codex","recommendation_summary":"...","verdict":"valid","adopted":true,"strengths":["identified root cause"],"weaknesses":[]}]' \
  --outcome pending
```

**Update an outcome:**
```bash
python scripts/council.py log \
  --project-dir "$(pwd)" \
  --type bug_fix \
  --bug-type runtime_error \
  --context "outcome update" \
  --update-id "uuid-from-previous-log" \
  --models '[]' \
  --outcome resolved \
  --outcome-notes "Fix worked on first attempt after council input"
```

## Insights & Sync

### Performance Report

Generate a report showing where each model excels and struggles:

```bash
python scripts/council.py report --project-dir .
python scripts/council.py report --project-dir . --format json
python scripts/council.py report --project-dir . --model openai/gpt-5.3-codex
python scripts/council.py report --project-dir . --type bug_fix
```

Reports include per-model stats: valid/partial/invalid rates, adoption rates, top strengths and weaknesses, best and worst bug types (requires minimum 3 samples per bug type to avoid misleading stats).

### Supermemory Sync

Insights are automatically synced to supermemory (container: `council_insights`) every time a log entry is written. This allows Claude to query historical model performance across all projects:

```bash
# Manual sync (also happens automatically on every log)
python scripts/council.py sync --project-dir .

# Query insights from supermemory before evaluating council responses
python ~/.claude/skills/supermemory/scripts/company_memory.py query \
  --q "council model performance runtime_error" \
  --container council_insights
```

Use `--no-sync` on the `log` command to skip auto-sync when needed.
