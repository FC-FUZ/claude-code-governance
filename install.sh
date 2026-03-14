#!/bin/bash
set -euo pipefail

echo "=== Claude Code Governance — Installer ==="
echo ""

# ── Prerequisites ─────────────────────────────────────────────────────────────

check_command() {
  command -v "$1" >/dev/null 2>&1
}

if ! check_command python3 && ! check_command python; then
  echo "ERROR: Python 3.10+ is required but not found."
  echo "  Install: https://www.python.org/downloads/"
  exit 1
fi

if ! check_command bash; then
  echo "ERROR: bash is required but not found."
  exit 1
fi

PYTHON_CMD="python3"
if ! check_command python3; then
  PYTHON_CMD="python"
fi

echo "Prerequisites OK (python: $($PYTHON_CMD --version 2>&1), bash: $(bash --version | head -1))"
echo ""

# ── Paths ─────────────────────────────────────────────────────────────────────

CLAUDE_DIR="$HOME/.claude"
SCRIPTS_DIR="$CLAUDE_DIR/scripts"
SKILLS_DIR="$CLAUDE_DIR/skills"
STATE_DIR="$CLAUDE_DIR/state"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
TIMESTAMP=$(date +%s)
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Step 1: Backup existing files ────────────────────────────────────────────

echo "[1/7] Backing up existing files..."
mkdir -p "$CLAUDE_DIR"

if [ -f "$SETTINGS_FILE" ]; then
  cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup.$TIMESTAMP"
  echo "  -> Backed up settings.json to settings.json.backup.$TIMESTAMP"
fi

if [ -f "$CLAUDE_MD" ]; then
  cp "$CLAUDE_MD" "$CLAUDE_MD.backup.$TIMESTAMP"
  echo "  -> Backed up CLAUDE.md to CLAUDE.md.backup.$TIMESTAMP"
fi

# ── Step 2: Install hook scripts (all 7) ─────────────────────────────────────

echo "[2/7] Installing hook scripts..."
mkdir -p "$SCRIPTS_DIR"

SCRIPTS=(
  "rehydrate-wip.sh"
  "checkpoint-wip.sh"
  "setup-shared-env.sh"
  "gate-fix-attempt.py"
  "gate-plan-exit.py"
  "gate-browser-verify.py"
  "mark-browser-verify-pending.py"
)

copied=0
for script in "${SCRIPTS[@]}"; do
  if [ -f "$REPO_DIR/scripts/$script" ]; then
    cp "$REPO_DIR/scripts/$script" "$SCRIPTS_DIR/$script"
    ((copied++))
  else
    echo "  WARNING: scripts/$script not found in repo — skipping"
  fi
done

chmod +x "$SCRIPTS_DIR"/*.sh 2>/dev/null || true
chmod +x "$SCRIPTS_DIR"/*.py 2>/dev/null || true
echo "  -> Copied $copied scripts to $SCRIPTS_DIR/"

# ── Step 3: Create state directory ───────────────────────────────────────────

echo "[3/7] Creating state directory..."
mkdir -p "$STATE_DIR"
echo "  -> $STATE_DIR/ ready"

# ── Step 4: Install CLAUDE.md rules ──────────────────────────────────────────

echo "[4/7] Installing governance rules..."
cp "$REPO_DIR/CLAUDE.md" "$CLAUDE_MD"
echo "  -> Copied CLAUDE.md to $CLAUDE_MD"

# ── Step 5: Configure settings.json ──────────────────────────────────────────

echo "[5/7] Configuring hooks in settings.json..."

if [ -f "$SETTINGS_FILE" ]; then
  # Check if hooks are already configured (look for our hook scripts)
  if grep -q "gate-browser-verify" "$SETTINGS_FILE" 2>/dev/null && \
     grep -q "rehydrate-wip" "$SETTINGS_FILE" 2>/dev/null && \
     grep -q "gate-plan-exit" "$SETTINGS_FILE" 2>/dev/null; then
    echo "  -> All hooks already configured in settings.json. Skipping."
  else
    echo "  -> Existing settings.json found but hooks are incomplete."
    echo "     A backup was saved to settings.json.backup.$TIMESTAMP"
    echo ""
    echo "     You have two options:"
    echo "     a) Replace with the full governance config (recommended for fresh installs):"
    echo "        cp $REPO_DIR/settings.json $SETTINGS_FILE"
    echo ""
    echo "     b) Manually merge the hooks from settings.json into your existing config."
    echo "        See: $REPO_DIR/settings.json for the complete hook configuration."
    echo ""
    echo "     Overwrite now? (y/N)"
    read -r answer
    if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
      cp "$REPO_DIR/settings.json" "$SETTINGS_FILE"
      echo "  -> Replaced settings.json with governance config"
    else
      echo "  -> Skipped. Merge hooks manually from $REPO_DIR/settings.json"
    fi
  fi
else
  cp "$REPO_DIR/settings.json" "$SETTINGS_FILE"
  echo "  -> Created $SETTINGS_FILE with full hook configuration"
fi

# ── Step 6: Install skills ───────────────────────────────────────────────────

echo "[6/7] Installing skills..."

# Council skill
mkdir -p "$SKILLS_DIR/council/scripts" "$SKILLS_DIR/council/references"
if [ -f "$REPO_DIR/skills/council/SKILL.md" ]; then
  cp "$REPO_DIR/skills/council/SKILL.md" "$SKILLS_DIR/council/SKILL.md"
fi
if [ -f "$REPO_DIR/skills/council/scripts/council.py" ]; then
  cp "$REPO_DIR/skills/council/scripts/council.py" "$SKILLS_DIR/council/scripts/council.py"
  chmod +x "$SKILLS_DIR/council/scripts/council.py"
fi
if [ -f "$REPO_DIR/skills/council/references/council_config.json" ]; then
  cp "$REPO_DIR/skills/council/references/council_config.json" "$SKILLS_DIR/council/references/council_config.json"
fi
echo "  -> Council skill installed"

# Supermemory skill
mkdir -p "$SKILLS_DIR/supermemory/scripts"
if [ -f "$REPO_DIR/skills/supermemory/SKILL.md" ]; then
  cp "$REPO_DIR/skills/supermemory/SKILL.md" "$SKILLS_DIR/supermemory/SKILL.md"
fi
if [ -f "$REPO_DIR/skills/supermemory/scripts/company_memory.py" ]; then
  cp "$REPO_DIR/skills/supermemory/scripts/company_memory.py" "$SKILLS_DIR/supermemory/scripts/company_memory.py"
  chmod +x "$SKILLS_DIR/supermemory/scripts/company_memory.py"
fi
echo "  -> Supermemory skill installed"

# Security skill
mkdir -p "$SKILLS_DIR/security"
if [ -f "$REPO_DIR/skills/security/SKILL.md" ]; then
  cp "$REPO_DIR/skills/security/SKILL.md" "$SKILLS_DIR/security/SKILL.md"
fi
echo "  -> Security skill installed"

# ── Step 7: Post-install verification ────────────────────────────────────────

echo "[7/7] Verifying installation..."
echo ""

errors=0

# Verify scripts
for script in "${SCRIPTS[@]}"; do
  if [ -f "$SCRIPTS_DIR/$script" ]; then
    echo "  [OK] scripts/$script"
  else
    echo "  [FAIL] scripts/$script — missing"
    ((errors++))
  fi
done

# Verify state directory
if [ -d "$STATE_DIR" ]; then
  echo "  [OK] state/ directory"
else
  echo "  [FAIL] state/ directory — missing"
  ((errors++))
fi

# Verify CLAUDE.md
if [ -f "$CLAUDE_MD" ]; then
  echo "  [OK] CLAUDE.md"
else
  echo "  [FAIL] CLAUDE.md — missing"
  ((errors++))
fi

# Verify settings.json
if [ -f "$SETTINGS_FILE" ]; then
  echo "  [OK] settings.json"
else
  echo "  [FAIL] settings.json — missing"
  ((errors++))
fi

# Verify skills
for skill in council supermemory security; do
  if [ -f "$SKILLS_DIR/$skill/SKILL.md" ]; then
    echo "  [OK] skills/$skill/SKILL.md"
  else
    echo "  [FAIL] skills/$skill/SKILL.md — missing"
    ((errors++))
  fi
done

echo ""
if [ "$errors" -eq 0 ]; then
  echo "=== Installation complete — all files verified ==="
else
  echo "=== Installation complete with $errors warning(s) ==="
fi

echo ""
echo "Next steps:"
echo "  1. Set environment variables (add to ~/.bashrc or ~/.zshrc):"
echo "     export OPENROUTER_API_KEY=\"your-key\"    # Required for council (Rule 1)"
echo "     export SUPERMEMORY_API_KEY=\"your-key\"    # Required for memory (Rules 2-5)"
echo "  2. Optional: pip install supermemory       # For company memory features"
echo "  3. Restart VS Code"
echo "  4. Open a new Claude Code session — all 7 rules are active immediately"
echo ""
echo "Emergency bypasses (env vars):"
echo "  CLAUDE_BYPASS_BROWSER_VERIFY=1  # Skip Rule 7 browser gate"
echo "  CLAUDE_BYPASS_COUNCIL=1         # Skip Rule 1b plan validation gate"
echo ""
