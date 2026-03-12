#!/bin/bash
set -e

echo "=== Claude Code Governance — Installer ==="
echo ""

# Check prerequisites
command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1 || { echo "ERROR: Python 3.10+ is required."; exit 1; }

CLAUDE_DIR="$HOME/.claude"
SCRIPTS_DIR="$CLAUDE_DIR/scripts"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

# Step 1: Install hook scripts
echo "[1/3] Installing hook scripts..."
mkdir -p "$SCRIPTS_DIR"
cp scripts/rehydrate-wip.sh "$SCRIPTS_DIR/"
cp scripts/checkpoint-wip.sh "$SCRIPTS_DIR/"
chmod +x "$SCRIPTS_DIR"/*.sh
echo "  -> Copied to $SCRIPTS_DIR/"

# Step 2: Install CLAUDE.md rules
echo "[2/3] Installing governance rules..."
if [ -f "$CLAUDE_DIR/CLAUDE.md" ]; then
  echo "  -> Existing CLAUDE.md found. Backing up to CLAUDE.md.backup"
  cp "$CLAUDE_DIR/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md.backup"
fi
cp CLAUDE.md "$CLAUDE_DIR/CLAUDE.md"
echo "  -> Copied to $CLAUDE_DIR/CLAUDE.md"

# Step 3: Configure hooks in settings.json
echo "[3/3] Configuring hooks..."
if [ -f "$SETTINGS_FILE" ]; then
  # Check if hooks are already configured
  if grep -q "rehydrate-wip" "$SETTINGS_FILE" 2>/dev/null; then
    echo "  -> Hooks already configured in settings.json. Skipping."
  else
    echo "  -> Existing settings.json found. Please merge hooks manually from settings-example.json"
    echo "  -> See: settings-example.json for the hook configuration to add"
  fi
else
  cp settings-example.json "$SETTINGS_FILE"
  echo "  -> Created $SETTINGS_FILE with hook configuration"
fi

echo ""
echo "=== Installation complete ==="
echo ""
echo "Next steps:"
echo "  1. Set environment variables:"
echo "     export OPENROUTER_API_KEY=\"your-key\""
echo "     export SUPERMEMORY_API_KEY=\"your-key\""
echo "  2. Restart VS Code"
echo "  3. Open a new Claude Code session — hooks are active immediately"
echo ""
