---
name: company-memory
description: "Company-wide AI & automation knowledge base powered by Supermemory. Claude MUST query this before planning new builds to ensure architectural consistency, store summaries after completing them, and proactively flag synergies between projects. Trigger: 'company memory', 'remember this', 'what do we use for', 'store this decision', 'company context', 'review and store this repo'."
---

# Company Memory — AI & Automation Knowledge Base

This skill gives Claude access to a **persistent company-wide knowledge base** of all AI and automation projects via Supermemory. Its purpose:

1. **Architectural consistency** — Every new build MUST align with existing tech stack, frameworks, patterns, and conventions across all company projects. No siloed decisions.
2. **Synergy detection** — When reviewing memory or planning a build, Claude MUST proactively identify when a new component could enhance, integrate with, or supercharge an existing project — and call it out.
3. **Living knowledge graph** — As projects are built and reviewed, the collective knowledge grows, making every subsequent build smarter.

**IMPORTANT:** Never store secrets, API keys, passwords, or credentials in company memory.

## Setup

Requires `SUPERMEMORY_API_KEY` in `~/.env` or environment.
Get a key at https://console.supermemory.ai

SDK: `pip install supermemory`

Verify with:
```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py doctor
```

## Commands

All commands use the script at `~/.claude/skills/supermemory/scripts/company_memory.py`.

### 1. Query — Search company memory

```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py query --q "What framework do we use for web apps?"
```

Options:
- `--q` (required): Search query
- `--container`: Filter to one container (omit to search company + conventions + decisions)
- `--limit`: Max results (default 5)
- `--mode`: "semantic" or "hybrid" (default "hybrid")

### 2. Profile — Get full company profile

```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py profile
python ~/.claude/skills/supermemory/scripts/company_memory.py profile --container conventions
python ~/.claude/skills/supermemory/scripts/company_memory.py profile --container project_invoice_tool --q "tech stack"
```

Options:
- `--container`: Container to profile (default "company")
- `--q`: Optional search query for additional results

### 3. Store — Save new knowledge

```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py store \
  --content "We use Next.js 15 with App Router for all web projects" \
  --container company \
  --type stack

python ~/.claude/skills/supermemory/scripts/company_memory.py store \
  --content "Always use TypeScript strict mode with path aliases" \
  --container conventions \
  --type convention \
  --static

python ~/.claude/skills/supermemory/scripts/company_memory.py store \
  --content "Chose Supabase over Firebase: better Postgres support, row-level security, self-hostable" \
  --container decisions \
  --type decision
```

Options:
- `--content` (required): Text to store
- `--container` (required): Container tag
- `--type` (required): One of `convention`, `decision`, `stack`, `project-summary`, `pattern`, `note`
- `--tags`: Comma-separated tags for metadata
- `--static`: Mark as permanent fact (won't be superseded)

### 4. List — See stored documents

```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py list --container company
```

### 5. Doctor — Validate setup

```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py doctor
```

### 6. Config — View configuration

```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py config
```

## Automatic Triggers (MANDATORY)

### A. Pre-Planning Context Retrieval

Before planning ANY new automation, tool, or project, you MUST:

1. Announce: "Checking company memory for relevant context."
2. Run:
```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py profile
python ~/.claude/skills/supermemory/scripts/company_memory.py query --q "<topic-relevant search>"
python ~/.claude/skills/supermemory/scripts/company_memory.py query --q "<topic-relevant search>" --container conventions
```
3. If a specific past project is relevant, also query its container:
```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py profile --container project_<name>
```
4. Incorporate ALL findings into your plan:
   - **Architecture alignment**: Use the same languages, frameworks, and patterns as existing projects unless there is a compelling reason not to. If deviating, explicitly justify why.
   - **Reuse over rebuild**: If an existing project already solves part of the problem (shared auth, common API patterns, utility libraries), reference it and build on it.
   - **Synergy check**: Review all returned project summaries and ask: "Could this new build enhance, feed data to, or integrate with any existing project?" If yes, include a **Synergies** section in the plan.
5. This happens BEFORE council plan validation.

### B. Synergy Detection (AUTOMATIC — every planning session)

After retrieving company context in Trigger A, you MUST:

1. Compare the new build's purpose against ALL known projects in memory.
2. Look for these synergy patterns:
   - **Data flow**: Could this project produce data another project consumes, or vice versa?
   - **Shared components**: Could an API, service, or module from one project be reused here?
   - **Workflow chaining**: Could this project be a step in an existing automation pipeline?
   - **Feature unlocking**: Could combining this with an existing project create a capability neither has alone?
3. If synergies are found, present them clearly:
   ```
   Synergies Detected:
   - [project_X] could consume the output of this build via [mechanism]
   - [project_Y] already has a [component] that this build could reuse
   - Combining this with [project_Z] would enable [new capability]
   ```
4. Factor synergies into the plan — suggest integration points, shared interfaces, or phased approaches.

### C. Convention / Decision Capture

When the user explicitly states a convention or architectural decision:

1. Immediately store it:
```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py store \
  --content "<the convention or decision>" \
  --container conventions \
  --type convention \
  --static
```
2. Confirm: "Stored in company memory: [brief summary]"

### D. Post-Build Knowledge Storage

After completing a working build (user confirms it works):

1. Ask: "Should I store a summary of this build in company memory?"
2. If yes, generate a structured summary and store it:
```bash
python ~/.claude/skills/supermemory/scripts/company_memory.py store \
  --content "<structured project summary>" \
  --container project_<name> \
  --type project-summary \
  --tags "<framework>,<language>,<key-tech>"
```
3. If new conventions were established during the build, also store those in the `conventions` container.
4. If integration points with other projects were identified, store those as notes in both project containers.

## Container Strategy

| Container | Purpose | When to use |
|---|---|---|
| `company` | Company-wide profile | Tech stack, team size, products, general context |
| `conventions` | Coding standards | Naming patterns, framework choices, style rules |
| `decisions` | Architectural decisions | Why we chose X over Y, ADRs |
| `project_{name}` | Per-project knowledge | After completing or reviewing a project |

Use lowercase, hyphen-separated names for projects: `project_invoice-tool`, `project_data-pipeline`.

## Store Templates

### Project Summary
```
Project: {name}
Description: {one-line description}
Tech Stack: {languages, frameworks, databases, hosting}
Key Patterns: {notable patterns used}
APIs/Interfaces Exposed: {endpoints, events, webhooks, exports other projects could consume}
Data Produced: {what data this project generates that others might use}
Data Consumed: {what external data/APIs this project depends on}
Entry Point: {main file or start command}
Repo Path: {local path or repo URL}
Date: {completion date}
```

### Convention
```
{Clear statement of the rule}
Reason: {why this convention exists}
Applies to: {scope — all projects, web only, Python only, etc.}
```

### Decision
```
Decision: {what was chosen}
Alternatives considered: {what was rejected}
Reason: {why this choice was made}
Date: {when decided}
```

## Repo Review & Store Workflow

When the user asks Claude to review a repo and store it in company memory:

1. **Explore the repo structure:**
   - Read `package.json`, `requirements.txt`, `pyproject.toml`, or equivalent
   - Scan directory structure (src layout, config files, entry points)
   - Read key files: main entry point, config, README if exists

2. **Identify and extract:**
   - Tech stack (language, framework, database, hosting, key libraries)
   - Architectural patterns (API structure, state management, auth approach)
   - Conventions used (file naming, code organization, testing patterns)
   - Notable decisions (why certain libraries/patterns were chosen)
   - **APIs/interfaces exposed** (endpoints, webhooks, events, exports)
   - **Data produced and consumed** (what flows in and out)
   - **Integration points** (how this project connects to or could connect to others)

3. **Cross-reference with existing memory:**
   - Query company memory for all known projects
   - Identify architectural overlaps or inconsistencies with this repo
   - Flag any synergies: shared data, reusable components, pipeline opportunities

4. **Store findings** (multiple store calls):
   - One `project-summary` in `project_{name}` container (include APIs, data flows, integration points)
   - Any new `convention` entries in `conventions` container
   - Any `stack` entries in `company` container (if not already stored)
   - Any `decision` entries in `decisions` container
   - Any `synergy` or `integration-point` notes linking this project to others

5. **Report back** with:
   - What was stored (brief summary)
   - Any synergies or integration opportunities found with existing projects
   - Any architectural inconsistencies with company conventions (e.g., "This repo uses Express but company convention is Fastify")

## Building Apps WITH Supermemory

For building applications that use Supermemory as a feature (not for company memory), see:
- `references/quickstart.md` — Setup guide
- `references/sdk-guide.md` — Full SDK reference
- `references/api-reference.md` — REST API endpoints
- `references/architecture.md` — How the knowledge graph works
- `references/use-cases.md` — 8 implementation examples
