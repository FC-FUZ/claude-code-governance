---
name: security
description: "Unified security skill — runs Trail of Bits security analysis on code changes. Trigger phrases: 'security review', 'security audit', 'the security skill', 'run security', 'check for vulnerabilities', 'security scan', 'vulnerability check', 'audit this code', 'is this secure', 'security check'. Orchestrates differential-review, audit-context-building, static-analysis, and supply-chain-risk-auditor from Trail of Bits."
---

# The Security Skill

Unified security analysis powered by Trail of Bits skills. One trigger, full coverage.

## What's Included

| Sub-Skill | Purpose | When It's Used |
|-----------|---------|----------------|
| **differential-review** | Security-focused code review with risk classification (Critical/High/Medium/Low) | Default for any code change touching sensitive areas |
| **audit-context-building** | Deep architectural analysis using first-principles methodology | When exploring unfamiliar code before making security changes |
| **static-analysis** | CodeQL, Semgrep, and SARIF integration | When static analysis rules are available for the language |
| **supply-chain-risk-auditor** | Dependency exploitation and takeover risk assessment | When adding or updating dependencies |

All sub-skills live at `~/.claude/plugins/marketplaces/skills/plugins/`.

## How to Use

### Manual Invocation

Say any of these:
- "Run the security skill on this code"
- "Security review these changes"
- "Check for vulnerabilities"
- "Audit this code"
- "Is this secure?"

### Workflow

When invoked (manually or via Rule 7 auto-trigger):

1. **Classify the request** — determine which sub-skill(s) to run:
   - Code changes in a PR/commit/diff → `differential-review`
   - Exploring unfamiliar codebase → `audit-context-building`
   - Language has CodeQL/Semgrep rules → also run `static-analysis`
   - Adding/updating dependencies → `supply-chain-risk-auditor`

2. **Run the appropriate sub-skill(s)** — follow their full methodology:
   - For `differential-review`: Read its [SKILL.md](~/.claude/plugins/marketplaces/skills/plugins/differential-review/skills/differential-review/SKILL.md) and supporting docs (methodology.md, adversarial.md, reporting.md, patterns.md)
   - For `audit-context-building`: Read its [SKILL.md](~/.claude/plugins/marketplaces/skills/plugins/audit-context-building/skills/audit-context-building/SKILL.md)
   - For `static-analysis`: Read the relevant sub-skill ([codeql](~/.claude/plugins/marketplaces/skills/plugins/static-analysis/skills/codeql/SKILL.md), [semgrep](~/.claude/plugins/marketplaces/skills/plugins/static-analysis/skills/semgrep/SKILL.md), or [sarif-parsing](~/.claude/plugins/marketplaces/skills/plugins/static-analysis/skills/sarif-parsing/SKILL.md))
   - For `supply-chain-risk-auditor`: Read its [SKILL.md](~/.claude/plugins/marketplaces/skills/plugins/supply-chain-risk-auditor/skills/supply-chain-risk-auditor/SKILL.md)

3. **Cross-reference with company memory** for past vulnerabilities:
   ```bash
   python ~/.claude/skills/supermemory/scripts/company_memory.py query --q "security vulnerabilities past incidents"
   ```

4. **For Critical or High findings**, consult the council before applying fixes:
   ```bash
   python ~/.claude/skills/council/scripts/council.py consult --fan-out --context "SECURITY FINDING: [describe the vulnerability]

   CODE: [the relevant code]

   PROPOSED FIX: [your intended fix]

   Is this fix correct and complete? Are there additional attack vectors we're missing?"
   ```

5. **Present findings** with severity classification and recommended fix
6. **Apply fixes** only after council validation for Critical/High issues

## Automatic Trigger (Rule 7 in CLAUDE.md)

This skill auto-triggers when writing or modifying code that handles:
- Authentication or authorization
- Cryptography or hashing
- Raw user input parsing
- SQL/database queries
- File system access with user-controlled paths
- External API credentials or secrets

**Scope guard — does NOT trigger on:**
- Trivial frontend changes (React placeholders, CSS, labels, UI text)
- Read-only data display components
- Test files that mock auth/crypto for testing purposes
- Configuration changes that don't affect security boundaries

## Severity Classification

| Severity | Description | Action Required |
|----------|-------------|-----------------|
| **Critical** | Actively exploitable, no auth required | Council validation + immediate fix |
| **High** | Exploitable with some preconditions | Council validation + fix in same session |
| **Medium** | Potential vulnerability, needs specific conditions | Fix recommended, no council needed |
| **Low** | Best practice improvement, defense in depth | Note in report, fix optional |

## Integration with Other Skills

- **Council** (Rule 7 step 4): Validates Critical/High security fixes with Gemini + Codex before applying
- **Supermemory** (Rule 7 step 3): Cross-references findings against past company vulnerabilities and stores new patterns
- **Existing security-guidance plugin**: Remains as baseline OWASP hook — this skill provides deeper Trail of Bits analysis on top

## Phase 2 Skills (Available for Later)

These are installed but not in the default workflow. Invoke them explicitly when needed:

- **insecure-defaults** — "Check for insecure defaults" — detects insecure default configurations
- **seatbelt-sandboxer** — "Sandbox this" — sandboxing and permission hardening
- **sharp-edges** — "Check for sharp edges" — identifies dangerous API usage patterns

Located at `~/.claude/plugins/marketplaces/skills/plugins/{skill-name}/`.
