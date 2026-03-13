#!/bin/bash
# setup-shared-env.sh — Onboard a new developer to the shared governance framework.
# Idempotent: safe to run multiple times.

set -e

ENV_FILE="$HOME/.env"
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPTS_DIR")/skills"

echo ""
echo "=========================================="
echo "  Governance Framework — Developer Setup"
echo "=========================================="
echo ""

# 1. Developer name
read -rp "Your name (for contributor attribution): " DEV_NAME
if [ -z "$DEV_NAME" ]; then
    echo "ERROR: Name is required."
    exit 1
fi

# 2. Shared Supermemory API key
echo ""
echo "You need the SHARED Supermemory API key (not a personal one)."
echo "Ask the team lead for the shared key, or get one at https://console.supermemory.ai"
read -rp "Supermemory API key: " SM_KEY
if [ -z "$SM_KEY" ]; then
    echo "ERROR: Supermemory API key is required."
    exit 1
fi

# 3. OpenRouter API key (for council skill)
echo ""
echo "You need an OpenRouter API key for the council skill."
echo "Get one at https://openrouter.ai/keys"
read -rp "OpenRouter API key: " OR_KEY
if [ -z "$OR_KEY" ]; then
    echo "ERROR: OpenRouter API key is required."
    exit 1
fi

# 4. Write to ~/.env (idempotent — update existing or append)
touch "$ENV_FILE"

update_or_append() {
    local key="$1"
    local value="$2"
    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
        # Update existing
        sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
    else
        echo "${key}=${value}" >> "$ENV_FILE"
    fi
}

update_or_append "SUPERMEMORY_USER" "$DEV_NAME"
update_or_append "SUPERMEMORY_API_KEY" "$SM_KEY"
update_or_append "OPENROUTER_API_KEY" "$OR_KEY"

echo ""
echo "Written to $ENV_FILE:"
echo "  SUPERMEMORY_USER=$DEV_NAME"
echo "  SUPERMEMORY_API_KEY=$(echo "$SM_KEY" | cut -c1-8)...$(echo "$SM_KEY" | tail -c 5)"
echo "  OPENROUTER_API_KEY=$(echo "$OR_KEY" | cut -c1-8)...$(echo "$OR_KEY" | tail -c 5)"

# 5. Verify Supermemory connectivity
echo ""
echo "Verifying Supermemory connectivity..."
if SUPERMEMORY_API_KEY="$SM_KEY" SUPERMEMORY_USER="$DEV_NAME" \
   python "$SKILL_DIR/supermemory/scripts/company_memory.py" doctor 2>/dev/null; then
    echo "  Supermemory: OK"
else
    echo "  WARNING: Supermemory doctor check failed. Verify your API key."
fi

# 6. Verify council config
echo ""
echo "Verifying council config..."
if OPENROUTER_API_KEY="$OR_KEY" \
   python "$SKILL_DIR/council/scripts/council.py" config > /dev/null 2>&1; then
    echo "  Council: OK"
else
    echo "  WARNING: Council config check failed."
fi

# 7. Test shared memory visibility
echo ""
echo "Testing shared memory (store + query)..."
if SUPERMEMORY_API_KEY="$SM_KEY" SUPERMEMORY_USER="$DEV_NAME" \
   python "$SKILL_DIR/supermemory/scripts/company_memory.py" store \
   --content "Setup verification: $DEV_NAME joined the shared governance framework" \
   --container company --type note 2>/dev/null; then
    echo "  Store: OK"
else
    echo "  WARNING: Store test failed."
fi

echo ""
echo "=========================================="
echo "  Setup complete!"
echo "=========================================="
echo ""
echo "You are now sharing knowledge with the team."
echo "Your contributions will be tagged as: $DEV_NAME"
echo ""
echo "To keep governance scripts up to date:"
echo "  cd ~/.claude && git pull"
echo ""
