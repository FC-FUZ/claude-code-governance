#!/usr/bin/env python3
"""
Council — Get second opinions from competing AI models via OpenRouter.

Usage:
    # Single model consultation
    python council.py consult --category bug_fix --context "description of the problem"

    # Explicit model override
    python council.py consult --model google/gemini-3.1-pro-preview --context "question here"

    # Fan out to all competitors
    python council.py consult --fan-out --context "question here"

    # Discover latest models from OpenRouter
    python council.py models

    # Show current config
    python council.py config

    # Log a council consultation assessment
    python council.py log --project-dir . --type bug_fix --bug-type runtime_error --context "desc" --models '[...]'

    # Generate model performance report
    python council.py report --project-dir .

    # Sync insights to supermemory
    python council.py sync --project-dir .
"""

import argparse
import concurrent.futures
import io
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows console encoding for Unicode (emoji, etc.)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

CONFIG_PATH = Path(__file__).parent.parent / "references" / "council_config.json"
SUPERMEMORY_SCRIPT = Path(__file__).parent.parent.parent / "supermemory" / "scripts" / "company_memory.py"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

BUG_TYPES = [
    "runtime_error", "type_error", "logic_error", "import_error",
    "config_error", "api_error", "ui_bug", "state_bug",
    "async_error", "test_failure", "build_error", "other",
]

VERDICTS = ["valid", "partial", "invalid"]

OUTCOMES = [
    "resolved", "partially_resolved", "unresolved", "pending",
    "plan_improved", "plan_unchanged",
]


# ---------------------------------------------------------------------------
# Log file helpers (JSONL format)
# ---------------------------------------------------------------------------

def _lock_file(f):
    """Cross-platform advisory file lock."""
    try:
        import msvcrt
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
    except ImportError:
        import fcntl
        fcntl.flock(f, fcntl.LOCK_EX)


def _unlock_file(f):
    """Cross-platform advisory file unlock."""
    try:
        import msvcrt
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
    except ImportError:
        import fcntl
        fcntl.flock(f, fcntl.LOCK_UN)


def get_log_path(project_dir):
    """Return the council log path, ensuring the .claude/ dir exists."""
    log_dir = Path(project_dir) / ".claude"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "council-log.jsonl"


def load_log(project_dir):
    """Read all entries from the JSONL log. Returns list of dicts."""
    path = get_log_path(project_dir)
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # skip corrupt lines
    return entries


def append_entry(project_dir, entry):
    """Append a single entry to the JSONL log (fast path, no full read)."""
    path = get_log_path(project_dir)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def save_log(project_dir, entries):
    """Rewrite the entire log (used for --update-id). Uses file locking."""
    path = get_log_path(project_dir)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        _lock_file(f)
        try:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        finally:
            _unlock_file(f)
    tmp.replace(path)


def get_api_key():
    key = os.environ.get("OPENROUTER_API_KEY")

    # Check ~/.env
    if not key:
        env_file = Path.home() / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("OPENROUTER_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    # Check project .env
    if not key:
        project_env = Path.cwd() / ".env"
        if project_env.exists():
            for line in project_env.read_text().splitlines():
                if line.startswith("OPENROUTER_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if not key:
        _setup_api_key()

    return key


def _setup_api_key():
    """First-run setup: create ~/.env template and guide the user."""
    env_file = Path.home() / ".env"

    # Create or append to ~/.env with a placeholder if not already there
    if env_file.exists():
        content = env_file.read_text()
        if "OPENROUTER_API_KEY" not in content:
            with open(env_file, "a") as f:
                f.write("\n# Council Skill — get your key at https://openrouter.ai/keys\n")
                f.write("OPENROUTER_API_KEY=your-key-here\n")
    else:
        env_file.write_text(
            "# Council Skill — get your key at https://openrouter.ai/keys\n"
            "OPENROUTER_API_KEY=your-key-here\n"
        )

    print("\n" + "="*60)
    print("  COUNCIL SKILL — FIRST TIME SETUP")
    print("="*60)
    print()
    print("You need a free OpenRouter API key to use this skill.")
    print()
    print("  1. Go to: https://openrouter.ai/keys")
    print("  2. Sign up (free) and create an API key")
    print("  3. Open this file:")
    print(f"       {env_file}")
    print("  4. Replace 'your-key-here' with your actual key")
    print("  5. Come back and try again")
    print()
    print("OpenRouter gives you access to GPT, Gemini, and 200+ other")
    print("models through one key. You only pay for what you use.")
    print()
    print(f"  Template created at: {env_file}")
    print("="*60 + "\n")
    sys.exit(0)


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Config saved to {CONFIG_PATH}")


def fetch_models():
    """Fetch all available models from OpenRouter."""
    req = urllib.request.Request(OPENROUTER_MODELS_URL)
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    return data.get("data", [])


def _resolve_provider_bucket(model_id, tracked_providers):
    """Map an OpenRouter model ID to the correct logical provider ID.

    Handles cases where multiple logical providers share the same OpenRouter
    prefix (e.g. openai-codex and openai-pro both use 'openai/' models).
    """
    prefix = model_id.split("/")[0] if "/" in model_id else ""

    # Direct match — provider ID equals the OpenRouter prefix
    if prefix in tracked_providers:
        return prefix

    # Check for logical providers whose ID starts with the prefix
    # (e.g. "openai-codex", "openai-pro" for prefix "openai")
    candidates = [pid for pid in tracked_providers if pid.startswith(prefix + "-")]
    if not candidates:
        return prefix  # unknown provider, return raw prefix

    if len(candidates) == 1:
        return candidates[0]

    # Multiple candidates — route based on model name heuristics
    mid = model_id.lower()
    if prefix == "openai":
        if "codex" in mid:
            return "openai-codex"
        if "pro" in mid and "-mini" not in mid:
            return "openai-pro"
        return "openai-codex"  # default bucket for other openai models

    # Fallback: return first candidate
    return candidates[0]


def discover_latest(provider_filter=None):
    """Discover latest flagship models, optionally filtered by provider."""
    models = fetch_models()
    config = load_config()
    tracked_providers = {p["id"] for p in config["providers"]}

    results = {}
    for model in models:
        model_id = model.get("id", "")
        prefix = model_id.split("/")[0] if "/" in model_id else ""

        if provider_filter and prefix != provider_filter:
            continue

        provider = _resolve_provider_bucket(model_id, tracked_providers)

        if not provider_filter and provider not in tracked_providers:
            continue

        if provider not in results:
            results[provider] = []
        results[provider].append({
            "id": model_id,
            "name": model.get("name", model_id),
            "context_length": model.get("context_length", 0),
            "pricing": model.get("pricing", {}),
        })

    # Sort: flagship models first, then by ID descending
    def sort_key(m):
        mid = m["id"].lower()
        if "codex" in mid or "gpt-5" in mid:
            return (0, mid)
        if "gemini" in mid:
            return (0, mid)
        if "claude" in mid:
            return (0, mid)
        if "kimi" in mid:
            return (0, mid)
        return (1, mid)

    for provider in results:
        results[provider].sort(key=sort_key)

    return results


def resolve_alias(name):
    """Resolve a provider alias (e.g. 'gemini', 'codex') to the flagship model ID.
    Returns the original name if no alias matches (assumes it's a full model ID)."""
    config = load_config()
    name_lower = name.lower().strip()
    for provider in config.get("providers", []):
        aliases = [a.lower() for a in provider.get("aliases", [])]
        if name_lower in aliases or name_lower == provider["id"]:
            return provider["flagship"]
    return name


def resolve_model(category):
    """Resolve a category to a concrete model ID using config defaults."""
    config = load_config()
    defaults = config.get("defaults", {})

    if category not in defaults:
        print(f"Unknown category: {category}", file=sys.stderr)
        print(f"Available: {', '.join(defaults.keys())}", file=sys.stderr)
        sys.exit(1)

    return defaults[category]


def get_fan_out_models():
    """Get the list of models for multi-opinion fan-out."""
    config = load_config()
    return config.get("fan_out", [])


def get_model_timeout(model_id):
    """Get the configured timeout for a specific model."""
    config = load_config()
    timeouts = config.get("timeouts", {})
    return timeouts.get(model_id, timeouts.get("default", 120))


def consult_model(model_id, context, system_prompt=None, timeout=None):
    """Send a consultation request to a model via OpenRouter.

    Always returns a result dict — never raises for network/API errors.
    """
    if timeout is None:
        timeout = get_model_timeout(model_id)

    api_key = get_api_key()

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": context})

    payload = json.dumps({
        "model": model_id,
        "messages": messages,
        "temperature": 0.3,
    }).encode()

    req = urllib.request.Request(OPENROUTER_CHAT_URL, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("HTTP-Referer", "https://claude-code-council.local")
    req.add_header("X-Title", "Claude Code Council")

    _error = lambda msg: {
        "model": model_id,
        "content": msg,
        "usage": {"prompt_tokens": 0, "completion_tokens": 0},
    }

    try:
        t0 = time.monotonic()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        elapsed = time.monotonic() - t0
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        usage = data.get("usage", {})
        model_used = data.get("model", model_id)
        return {
            "model": model_used,
            "content": content,
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            },
            "elapsed_s": round(elapsed, 1),
        }
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        return _error(f"ERROR ({e.code}): {error_body}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return _error(f"TIMEOUT/CONNECTION ERROR: {e}")
    except Exception as e:
        return _error(f"UNEXPECTED ERROR: {type(e).__name__}: {e}")


def cmd_models(args):
    """Show latest available models from tracked providers."""
    provider = getattr(args, "provider", None)
    results = discover_latest(provider)

    if not results:
        print("No models found.")
        return

    for provider, models in sorted(results.items()):
        print(f"\n{'='*60}")
        print(f"  {provider.upper()}")
        print(f"{'='*60}")
        for m in models[:8]:  # Show top 8 per provider
            price_in = m["pricing"].get("prompt", "?")
            price_out = m["pricing"].get("completion", "?")
            ctx = f"{m['context_length']:,}" if m["context_length"] else "?"
            print(f"  {m['id']:<45} ctx:{ctx:<10} ${price_in}/{price_out}")


def cmd_update(args):
    """Auto-discover latest flagship models from OpenRouter and update config."""
    config = load_config()
    models = fetch_models()

    # Build a lookup: logical_provider_id -> list of models sorted by preference
    tracked_providers = {p["id"] for p in config["providers"]}
    provider_models = {}
    for model in models:
        model_id = model.get("id", "")
        if "/" not in model_id:
            continue
        provider = _resolve_provider_bucket(model_id, tracked_providers)
        if provider not in provider_models:
            provider_models[provider] = []
        provider_models[provider].append({
            "id": model_id,
            "name": model.get("name", ""),
            "created": model.get("created", 0),
            "context_length": model.get("context_length", 0),
        })

    # Flagship ranking patterns per logical provider (higher priority first)
    # These must match as substrings in the model ID (after the provider prefix)
    flagship_patterns = {
        "openai-codex": ["codex", "gpt-5", "gpt-4", "o4", "o3"],
        "openai-pro": ["gpt-5.4", "gpt-5-pro", "pro", "gpt-5", "gpt-4"],
        "google": ["gemini-3", "gemini-2.5", "gemini-2", "gemini-1.5"],
        "anthropic": ["opus", "sonnet"],
        "moonshotai": ["kimi-k2.5", "kimi-k2", "kimi"],
    }

    # Models to exclude — small/open/experimental models that aren't flagships
    # NOTE: avoid "mini" because it matches "gemini" — use "-mini" instead
    skip_patterns = [":free", "-mini", "nano", "lite", "8b", "thinking", "gemma",
                     "learnlm", "imagen", "flash", "-image", "customtools"]

    changes = []
    for provider in config.get("providers", []):
        pid = provider["id"]
        available = provider_models.get(pid, [])
        if not available:
            continue

        patterns = flagship_patterns.get(pid, [])

        # Score each model: lower pattern index = better, then prefer newer (higher created)
        def score(m):
            mid = m["id"].lower()
            # Skip non-flagship variants
            for skip in skip_patterns:
                if skip in mid:
                    return (999, 0)
            for i, pat in enumerate(patterns):
                if pat in mid:
                    # Within same family, prefer the one without "preview" in name
                    preview_penalty = 0.5 if "preview" in mid else 0
                    return (i + preview_penalty, -m.get("created", 0))
            return (len(patterns), -m.get("created", 0))

        available.sort(key=score)
        best = available[0]
        best_score = score(best)
        if best_score[0] >= 999:
            continue  # all models were skipped

        old = provider["flagship"]
        if best["id"] != old:
            changes.append((pid, old, best["id"]))
            provider["flagship"] = best["id"]
        print(f"  {pid:<12} flagship: {provider['flagship']}")

    if changes:
        # Also update defaults and fan_out that referenced old model IDs
        for pid, old_id, new_id in changes:
            for cat, model_id in config["defaults"].items():
                if model_id == old_id:
                    config["defaults"][cat] = new_id
            config["fan_out"] = [new_id if m == old_id else m for m in config["fan_out"]]

        save_config(config)
        print(f"\nUpdated {len(changes)} flagship(s):")
        for pid, old_id, new_id in changes:
            print(f"  {pid}: {old_id} → {new_id}")
    else:
        print("\nAll flagships are already up to date.")


def cmd_config(args):
    """Show current council config."""
    config = load_config()
    print(json.dumps(config, indent=2))


def cmd_consult(args):
    """Consult one or more models."""
    context = args.context
    if not context:
        # Read from stdin if no context provided
        context = sys.stdin.read().strip()
    if not context:
        print("ERROR: No context provided. Use --context or pipe via stdin.", file=sys.stderr)
        sys.exit(1)

    system_prompt = (
        "You are a senior engineer giving a second opinion. "
        "Be direct, specific, and actionable. "
        "If you see issues, call them out. "
        "If the approach is sound, say so briefly and suggest any improvements. "
        "Keep your response concise and focused."
    )

    if args.fan_out:
        # Fan out to all competitor models concurrently
        models = get_fan_out_models()
        print(f"\n--- COUNCIL: Consulting {len(models)} models (concurrent) ---\n")
        for mid in models:
            print(f">> Queuing {mid} (timeout: {get_model_timeout(mid)}s)")

        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(models)) as executor:
            futures = {
                executor.submit(consult_model, mid, context, system_prompt): mid
                for mid in models
            }
            for future in concurrent.futures.as_completed(futures):
                mid = futures[future]
                results[mid] = future.result()
                elapsed = results[mid].get("elapsed_s", "?")
                print(f"<< {mid} responded ({elapsed}s)")

        # Print results in original model order
        print()
        for model_id in models:
            result = results[model_id]
            print(f"{'='*60}")
            print(f"  MODEL: {result['model']}")
            print(f"  TOKENS: {result['usage']['prompt_tokens']} in / {result['usage']['completion_tokens']} out")
            print(f"{'='*60}")
            print(result["content"])
            print()
    elif args.model:
        # Explicit model override — resolve aliases like "gemini" or "codex"
        model_id = resolve_alias(args.model)
        print(f"\n>> Asking {model_id}...")
        result = consult_model(model_id, context, system_prompt)
        print(f"\n{'='*60}")
        print(f"  MODEL: {result['model']}")
        print(f"  TOKENS: {result['usage']['prompt_tokens']} in / {result['usage']['completion_tokens']} out")
        print(f"{'='*60}")
        print(result["content"])
    elif args.category:
        # Route by category
        model_id = resolve_model(args.category)
        print(f"\n>> Category '{args.category}' → {model_id}")
        result = consult_model(model_id, context, system_prompt)
        print(f"\n{'='*60}")
        print(f"  MODEL: {result['model']}")
        print(f"  TOKENS: {result['usage']['prompt_tokens']} in / {result['usage']['completion_tokens']} out")
        print(f"{'='*60}")
        print(result["content"])
    else:
        print("ERROR: Specify --category, --model, or --fan-out", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# cmd_log — Log a council consultation assessment
# ---------------------------------------------------------------------------

def cmd_log(args):
    """Log a council consultation assessment to the project's JSONL log."""
    project_dir = args.project_dir

    # --- Update existing entry mode ---
    if args.update_id:
        entries = load_log(project_dir)
        found = False
        for entry in entries:
            if entry.get("id") == args.update_id:
                if args.outcome:
                    entry["outcome"] = args.outcome
                if args.outcome_notes:
                    entry["outcome_notes"] = args.outcome_notes
                found = True
                break
        if not found:
            print(f"ERROR: Entry {args.update_id} not found in log.", file=sys.stderr)
            sys.exit(1)
        save_log(project_dir, entries)
        print(f"Updated entry {args.update_id} → outcome={args.outcome}")
        return

    # --- New entry mode ---
    consultation_type = args.type
    bug_type = getattr(args, "bug_type", None)

    if consultation_type == "bug_fix" and not bug_type:
        print("ERROR: --bug-type is required when --type=bug_fix", file=sys.stderr)
        sys.exit(1)

    # Parse models JSON
    try:
        models = json.loads(args.models)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON for --models: {e}", file=sys.stderr)
        sys.exit(1)

    entry_id = str(uuid.uuid4())
    entry = {
        "id": entry_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "consultation_type": consultation_type,
        "bug_type": bug_type,
        "context_summary": args.context,
        "attempt_number": args.attempt,
        "models": models,
        "outcome": args.outcome or "pending",
        "outcome_notes": args.outcome_notes or "",
    }

    append_entry(project_dir, entry)
    print(f"\nLogged council entry: {entry_id}")
    print(f"  type={consultation_type}, bug_type={bug_type or 'n/a'}, models={len(models)}, outcome={entry['outcome']}")

    # Auto-sync to supermemory
    if not args.no_sync:
        _try_sync(project_dir)


def _try_sync(project_dir):
    """Attempt to sync insights to supermemory. Warn on failure, never crash."""
    try:
        entries = load_log(project_dir)
        if len(entries) < 3:
            return  # not enough data to aggregate yet
        _do_sync(project_dir, entries)
    except Exception as e:
        print(f"  (sync warning: {e})", file=sys.stderr)


# ---------------------------------------------------------------------------
# aggregate_log — Shared aggregation logic for report and sync
# ---------------------------------------------------------------------------

def aggregate_log(entries, model_filter=None, type_filter=None):
    """Aggregate log entries into per-model performance stats.

    Returns dict:
    {
        "total": int,
        "by_type": {"bug_fix": int, "plan_validation": int},
        "models": {
            "model_id": {
                "total": int,
                "verdicts": {"valid": int, "partial": int, "invalid": int},
                "adopted": int,
                "strengths": Counter,
                "weaknesses": Counter,
                "by_bug_type": {
                    "runtime_error": {"valid": int, "partial": int, "invalid": int, "total": int},
                    ...
                },
            }
        },
        "outcomes": Counter,
    }
    """
    # Filter entries
    filtered = entries
    if type_filter:
        filtered = [e for e in filtered if e.get("consultation_type") == type_filter]

    stats = {
        "total": len(filtered),
        "by_type": Counter(),
        "models": {},
        "outcomes": Counter(),
    }

    for entry in filtered:
        ctype = entry.get("consultation_type", "unknown")
        stats["by_type"][ctype] += 1
        stats["outcomes"][entry.get("outcome", "unknown")] += 1

        for m in entry.get("models", []):
            mid = m.get("model_id", "unknown")
            if model_filter and mid != model_filter:
                continue

            if mid not in stats["models"]:
                stats["models"][mid] = {
                    "total": 0,
                    "verdicts": Counter(),
                    "adopted": 0,
                    "strengths": Counter(),
                    "weaknesses": Counter(),
                    "by_bug_type": {},
                }

            ms = stats["models"][mid]
            ms["total"] += 1
            verdict = m.get("verdict", "unknown")
            ms["verdicts"][verdict] += 1
            if m.get("adopted"):
                ms["adopted"] += 1
            for s in m.get("strengths", []):
                ms["strengths"][s] += 1
            for w in m.get("weaknesses", []):
                ms["weaknesses"][w] += 1

            # Bug type breakdown
            bt = entry.get("bug_type")
            if bt:
                if bt not in ms["by_bug_type"]:
                    ms["by_bug_type"][bt] = Counter()
                ms["by_bug_type"][bt][verdict] += 1

    return stats


# ---------------------------------------------------------------------------
# cmd_report — Generate model performance report
# ---------------------------------------------------------------------------

MIN_SAMPLE_THRESHOLD = 3  # minimum samples for "best/worst" claims


def cmd_report(args):
    """Generate a human-readable or JSON performance report from the council log."""
    entries = load_log(args.project_dir)
    if not entries:
        print("No council log entries found.")
        return

    stats = aggregate_log(
        entries,
        model_filter=getattr(args, "model", None),
        type_filter=getattr(args, "type", None),
    )

    if args.format == "json":
        # Convert Counters to dicts for JSON serialization
        out = {
            "total": stats["total"],
            "by_type": dict(stats["by_type"]),
            "outcomes": dict(stats["outcomes"]),
            "models": {},
        }
        for mid, ms in stats["models"].items():
            out["models"][mid] = {
                "total": ms["total"],
                "verdicts": dict(ms["verdicts"]),
                "adopted": ms["adopted"],
                "strengths": dict(ms["strengths"]),
                "weaknesses": dict(ms["weaknesses"]),
                "by_bug_type": {bt: dict(v) for bt, v in ms["by_bug_type"].items()},
            }
        print(json.dumps(out, indent=2))
        return

    # Text format
    bf = stats["by_type"].get("bug_fix", 0)
    pv = stats["by_type"].get("plan_validation", 0)
    print(f"\n{'='*60}")
    print(f"  COUNCIL PERFORMANCE REPORT")
    print(f"{'='*60}")
    print(f"Total consultations: {stats['total']} ({bf} bug_fix, {pv} plan_validation)")

    resolved = stats["outcomes"].get("resolved", 0) + stats["outcomes"].get("plan_improved", 0)
    total_resolved = stats["total"] - stats["outcomes"].get("pending", 0)
    if total_resolved > 0:
        print(f"Resolution rate: {resolved}/{total_resolved} ({100*resolved//total_resolved}%)")
    print()

    for mid, ms in sorted(stats["models"].items()):
        print(f"--- {mid} ---")
        total = ms["total"]
        v = ms["verdicts"]
        valid = v.get("valid", 0)
        partial = v.get("partial", 0)
        invalid = v.get("invalid", 0)

        def pct(n):
            return f"{100*n//total}%" if total > 0 else "0%"

        print(f"  Consultations: {total} | Valid: {valid} ({pct(valid)}) | Partial: {partial} ({pct(partial)}) | Invalid: {invalid} ({pct(invalid)})")
        adoption_pct = f"{100*ms['adopted']//total}%" if total > 0 else "0%"
        print(f"  Adoption rate: {ms['adopted']}/{total} ({adoption_pct})")

        # Top strengths
        if ms["strengths"]:
            top_s = ms["strengths"].most_common(5)
            s_str = ", ".join(f"{s} ({c}x)" for s, c in top_s)
            print(f"  Strengths: {s_str}")

        # Top weaknesses
        if ms["weaknesses"]:
            top_w = ms["weaknesses"].most_common(5)
            w_str = ", ".join(f"{w} ({c}x)" for w, c in top_w)
            print(f"  Weaknesses: {w_str}")

        # Best/worst bug types (only with enough samples)
        if ms["by_bug_type"]:
            bt_rates = {}
            for bt, counts in ms["by_bug_type"].items():
                bt_total = sum(counts.values())
                if bt_total >= MIN_SAMPLE_THRESHOLD:
                    bt_rates[bt] = counts.get("valid", 0) / bt_total

            if bt_rates:
                best = sorted(bt_rates.items(), key=lambda x: -x[1])[:3]
                worst = sorted(bt_rates.items(), key=lambda x: x[1])[:3]
                best_str = ", ".join(f"{bt} ({100*r:.0f}%)" for bt, r in best)
                worst_str = ", ".join(f"{bt} ({100*r:.0f}%)" for bt, r in worst)
                print(f"  Best at: {best_str}")
                if worst != best:
                    print(f"  Worst at: {worst_str}")

        print()


# ---------------------------------------------------------------------------
# cmd_sync — Push aggregated insights to supermemory
# ---------------------------------------------------------------------------

def _do_sync(project_dir, entries=None):
    """Internal sync logic, shared by cmd_sync and auto-sync."""
    if entries is None:
        entries = load_log(project_dir)
    if not entries:
        print("No entries to sync.")
        return

    stats = aggregate_log(entries)

    # Detect project name from directory
    project_name = Path(project_dir).resolve().name

    # Build structured insight content
    lines = [
        f"Council Performance Insights — {project_name}",
        f"Total consultations: {stats['total']}",
        f"Bug fixes: {stats['by_type'].get('bug_fix', 0)}, Plan validations: {stats['by_type'].get('plan_validation', 0)}",
        "",
    ]

    for mid, ms in sorted(stats["models"].items()):
        total = ms["total"]
        v = ms["verdicts"]
        valid = v.get("valid", 0)
        partial = v.get("partial", 0)
        invalid = v.get("invalid", 0)
        adopted = ms["adopted"]
        lines.append(f"Model: {mid}")
        lines.append(f"  Valid: {valid}/{total}, Partial: {partial}/{total}, Invalid: {invalid}/{total}")
        lines.append(f"  Adoption rate: {adopted}/{total}")

        if ms["strengths"]:
            top = ms["strengths"].most_common(5)
            lines.append(f"  Top strengths: {', '.join(f'{s} ({c}x)' for s, c in top)}")
        if ms["weaknesses"]:
            top = ms["weaknesses"].most_common(5)
            lines.append(f"  Top weaknesses: {', '.join(f'{w} ({c}x)' for w, c in top)}")

        # Bug type breakdown
        if ms["by_bug_type"]:
            best_types = []
            worst_types = []
            for bt, counts in ms["by_bug_type"].items():
                bt_total = sum(counts.values())
                if bt_total >= MIN_SAMPLE_THRESHOLD:
                    rate = counts.get("valid", 0) / bt_total
                    best_types.append((bt, rate, bt_total))
                    worst_types.append((bt, rate, bt_total))
            best_types.sort(key=lambda x: -x[1])
            worst_types.sort(key=lambda x: x[1])
            if best_types:
                lines.append(f"  Excels at: {', '.join(f'{bt} ({100*r:.0f}% valid, n={n})' for bt, r, n in best_types[:3])}")
            if worst_types:
                lines.append(f"  Struggles with: {', '.join(f'{bt} ({100*r:.0f}% valid, n={n})' for bt, r, n in worst_types[:3])}")

        lines.append("")

    content = "\n".join(lines)

    # Shell out to company_memory.py
    if not SUPERMEMORY_SCRIPT.exists():
        print("  (sync skipped: supermemory script not found)", file=sys.stderr)
        return

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(SUPERMEMORY_SCRIPT),
                "store",
                "--content", content,
                "--container", "council_insights",
                "--type", "pattern",
                "--tags", f"council,model-performance,{project_name}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print(f"  Synced insights to supermemory (council_insights)")
        else:
            print(f"  (sync warning: {result.stderr.strip()})", file=sys.stderr)
    except Exception as e:
        print(f"  (sync warning: {e})", file=sys.stderr)


def cmd_sync(args):
    """Push aggregated council insights to supermemory."""
    _do_sync(args.project_dir)


# ---------------------------------------------------------------------------
# main — Argument parser and command dispatch
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Council — Multi-model second opinions")
    sub = parser.add_subparsers(dest="command")

    # consult
    p_consult = sub.add_parser("consult", help="Consult a model for a second opinion")
    p_consult.add_argument("--category", "-c", help="Task category (bug_fix, frontend, architecture, refactor, general, quick_check)")
    p_consult.add_argument("--model", "-m", help="Explicit model ID override (e.g., google/gemini-3.1-pro-preview)")
    p_consult.add_argument("--fan-out", "-f", action="store_true", help="Consult all competitor models")
    p_consult.add_argument("--context", "-x", help="The question or context to send. Can also pipe via stdin.")
    p_consult.set_defaults(func=cmd_consult)

    # models
    p_models = sub.add_parser("models", help="Discover latest models from OpenRouter")
    p_models.add_argument("--provider", "-p", help="Filter by provider (openai, google, anthropic)")
    p_models.set_defaults(func=cmd_models)

    # update
    p_update = sub.add_parser("update", help="Auto-discover latest flagship models and update config")
    p_update.set_defaults(func=cmd_update)

    # config
    p_config = sub.add_parser("config", help="Show current council config")
    p_config.set_defaults(func=cmd_config)

    # log
    p_log = sub.add_parser("log", help="Log a council consultation assessment")
    p_log.add_argument("--project-dir", required=True, help="Path to the project root")
    p_log.add_argument("--type", required=True, choices=["bug_fix", "plan_validation"], help="Consultation type")
    p_log.add_argument("--bug-type", choices=BUG_TYPES, help="Bug classification (required for bug_fix)")
    p_log.add_argument("--context", required=True, help="Brief description of what was consulted on")
    p_log.add_argument("--attempt", type=int, help="Which fix attempt triggered this consultation")
    p_log.add_argument("--models", required=True, help="JSON array of model assessments")
    p_log.add_argument("--outcome", choices=OUTCOMES, default="pending", help="Consultation outcome")
    p_log.add_argument("--outcome-notes", default="", help="Details about the outcome")
    p_log.add_argument("--update-id", help="Update an existing entry's outcome by UUID")
    p_log.add_argument("--no-sync", action="store_true", help="Skip auto-sync to supermemory")
    p_log.set_defaults(func=cmd_log)

    # report
    p_report = sub.add_parser("report", help="Generate model performance report from council log")
    p_report.add_argument("--project-dir", required=True, help="Path to the project root")
    p_report.add_argument("--model", help="Filter to a specific model ID")
    p_report.add_argument("--type", choices=["bug_fix", "plan_validation"], help="Filter by consultation type")
    p_report.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p_report.set_defaults(func=cmd_report)

    # sync
    p_sync = sub.add_parser("sync", help="Sync aggregated insights to supermemory")
    p_sync.add_argument("--project-dir", required=True, help="Path to the project root")
    p_sync.set_defaults(func=cmd_sync)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
