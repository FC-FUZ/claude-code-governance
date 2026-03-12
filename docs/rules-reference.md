# Rules Reference

Detailed breakdown of each governance rule.

## Rule 1: Council Governance

### Purpose
Prevents single-model blind spots by automatically consulting GPT and Gemini when Claude is stuck or about to commit to a plan.

### Sub-rules

#### 1a: Bug Fix Guardrail
- **Trigger**: 2 consecutive failed fix attempts for the same bug
- **Action**: Claude stops, consults the council, synthesizes responses, then attempts a 3rd fix
- **Logging**: Every consultation is logged with verdict assessments and bug type classification

**Bug type taxonomy**: `runtime_error`, `type_error`, `logic_error`, `import_error`, `config_error`, `api_error`, `ui_bug`, `state_bug`, `async_error`, `test_failure`, `build_error`, `other`

#### 1b: Plan Validation
- **Trigger**: Plan mode complete plan drafted, before ExitPlanMode
- **Action**: Council reviews the plan for risks, edge cases, and alternatives
- **Output**: Revised plan with Council Review section

#### 1c: Historical Insights
- **Trigger**: Before evaluating any council response
- **Action**: Queries Supermemory for past model performance data
- **Purpose**: Weight model recommendations based on their track record

### Verdict Guidelines
- `valid` -- correctly identified root cause or gave actionable, correct advice
- `partial` -- some useful insights mixed with incorrect or irrelevant parts
- `invalid` -- wrong diagnosis, unhelpful advice, or harmful suggestion

---

## Rule 2: WIP Lifecycle

### Purpose
Ensures work-in-progress state survives context compaction and session boundaries.

### Mechanics vs Behavior Split
- **Hooks** handle the mechanical checkpoint/rehydrate cycle (deterministic, always fires)
- **Rule 2** defines the behavioral expectations (what Claude does when WIP is recovered or needs saving)

### Checkpoint Triggers
| Trigger | Mechanism | Reliability |
|---------|-----------|-------------|
| Context compaction | PreCompact hook | Deterministic |
| Session start | SessionStart hook | Deterministic |
| Subtask completion | Manual (Rule 2b) | Behavioral |
| 3+ files modified | Manual (Rule 2b) | Behavioral |
| Pre-test/deploy | Manual (Rule 2b) | Behavioral |
| User command | Manual (Rule 2b) | Behavioral |

### Project Scoping
WIP entries are keyed by project_key (md5 prefix of git root path). This prevents cross-project contamination when switching between repositories.

---

## Rule 3: Project Context and Synergy

### Purpose
Before planning any new build, query company memory to find related projects, reusable components, and integration opportunities.

### Synergy Detection Categories
1. **Data flow** -- could this project produce data another consumes?
2. **Shared components** -- could an existing API/module be reused?
3. **Workflow chaining** -- could this be a step in an existing pipeline?
4. **Feature unlocking** -- could combining projects create new capabilities?

### Execution Order
Rule 3 (memory check) runs BEFORE Rule 1b (council plan validation).

---

## Rule 4: Convention and Decision Capture

### Purpose
Immediately persists architectural decisions and coding conventions when the user states them.

### Storage Containers
- `conventions` -- coding standards, patterns, naming conventions
- `decisions` -- architectural choices with alternatives considered and rationale

---

## Rule 5: Build Completion

### Purpose
After a confirmed working build, stores a structured summary for future cross-project reference.

### Summary Schema
- Project name and description
- Tech stack
- Key patterns used
- APIs/interfaces exposed
- Data produced and consumed
- Entry point
- Repo path

### Cleanup
Purges stale WIP entries (Rule 2d) to prevent false rehydration in future sessions.

---

## Rule 6: Security Gate

### Purpose
Mandatory security review for code that handles sensitive operations.

### Trigger Conditions
- Authentication code
- Cryptographic operations
- Raw user input parsing
- SQL/database queries
- File system access with user-controlled paths
- External API credentials

### Scope Guard (Does NOT trigger on)
- CSS/UI text changes
- Read-only display components
- Test files mocking auth/crypto
- Configuration changes outside security boundaries

### Escalation Path
1. Trail of Bits static analysis
2. Cross-reference with historical vulnerabilities
3. Council validation for Critical/High findings
4. Fix applied only after validation
