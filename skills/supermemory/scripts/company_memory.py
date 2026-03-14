#!/usr/bin/env python3
"""
Company Memory — Centralized company knowledge base powered by Supermemory.

Usage:
    # Validate environment
    python company_memory.py doctor

    # Store a memory
    python company_memory.py store --content "We use Next.js 15" --container company --type stack

    # Query company memory
    python company_memory.py query --q "What framework do we use?"

    # Get company profile
    python company_memory.py profile

    # List stored documents
    python company_memory.py list --container company

    # Batch store from JSON
    python company_memory.py bootstrap --file context.json

    # Show config
    python company_memory.py config
"""

import argparse
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows console encoding for Unicode
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

CONFIG_PATH = Path(__file__).parent.parent / "references" / "company_memory_config.json"
SCRIPT_DIR = Path(__file__).parent


def get_api_key():
    """Load SUPERMEMORY_API_KEY from env, ~/.env, or project .env."""
    key = os.environ.get("SUPERMEMORY_API_KEY")

    if not key:
        env_file = Path.home() / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("SUPERMEMORY_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if not key:
        project_env = Path.cwd() / ".env"
        if project_env.exists():
            for line in project_env.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("SUPERMEMORY_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    return key


def get_contributor():
    """Get contributor ID for metadata attribution.

    Fallback chain: SUPERMEMORY_USER env → os.getlogin() → 'claude_code'
    """
    user = os.environ.get("SUPERMEMORY_USER")
    if user:
        return user
    try:
        return os.getlogin()
    except OSError:
        return "claude_code"


def load_config():
    """Load company memory config."""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {
        "defaults": {"search_mode": "hybrid", "search_limit": 5, "threshold": 0.3},
        "default_query_containers": ["company", "conventions", "decisions"],
    }


def get_client():
    """Create and return a Supermemory client."""
    try:
        from supermemory import Supermemory
    except ImportError:
        print("ERROR: supermemory SDK not installed.", file=sys.stderr)
        print("Fix: pip install supermemory", file=sys.stderr)
        sys.exit(1)

    key = get_api_key()
    if not key:
        print("ERROR: SUPERMEMORY_API_KEY not found.", file=sys.stderr)
        print("Add it to ~/.env:  SUPERMEMORY_API_KEY=your_key_here", file=sys.stderr)
        print("Get a key at:      https://console.supermemory.ai", file=sys.stderr)
        sys.exit(1)

    return Supermemory(api_key=key)


# ─── Commands ────────────────────────────────────────────────────────────────


def cmd_doctor(args):
    """Validate environment: API key, SDK, connectivity."""
    print("--- COMPANY MEMORY: Doctor ---\n")

    # Check SDK
    try:
        from supermemory import Supermemory
        print("[OK] supermemory SDK installed")
    except ImportError:
        print("[FAIL] supermemory SDK not installed")
        print("  Fix: pip install supermemory")
        sys.exit(1)

    # Check API key
    key = get_api_key()
    if key:
        masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
        print(f"[OK] SUPERMEMORY_API_KEY found ({masked})")
    else:
        print("[FAIL] SUPERMEMORY_API_KEY not found")
        print("  Add to ~/.env:  SUPERMEMORY_API_KEY=your_key_here")
        sys.exit(1)

    # Check connectivity
    try:
        client = Supermemory(api_key=key)
        result = client.search.memories(q="test", limit=1)
        print("[OK] API connectivity verified")
    except Exception as e:
        print(f"[WARN] API connectivity test: {e}")
        print("  This may be normal if no memories are stored yet.")

    # Check config
    if CONFIG_PATH.exists():
        print(f"[OK] Config found at {CONFIG_PATH}")
    else:
        print(f"[WARN] Config not found at {CONFIG_PATH}")

    print("\nAll checks passed.")


def cmd_store(args):
    """Store a memory in company knowledge base."""
    client = get_client()
    config = load_config()

    metadata = {
        "type": args.type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stored_by": get_contributor(),
    }
    if args.tags:
        metadata["tags"] = [t.strip() for t in args.tags.split(",")]
    if args.dynamic:
        metadata["persistence"] = "dynamic"
    elif args.static:
        metadata["persistence"] = "static"

    # For static facts, use the memories endpoint directly
    if args.static:
        try:
            result = client.memories.create(
                container_tag=args.container,
                memories=[{
                    "content": args.content,
                    "is_static": True,
                    "metadata": metadata,
                }],
            )
            print(f"Stored (static) in [{args.container}]: {args.content[:100]}...")
            return
        except Exception:
            # Fall back to add() if memories endpoint isn't available
            pass

    # Default: use add()
    try:
        result = client.add(
            content=args.content,
            container_tag=args.container,
            metadata=metadata,
        )
        static_label = " (static)" if args.static else ""
        preview = args.content[:100] + ("..." if len(args.content) > 100 else "")
        print(f"Stored{static_label} in [{args.container}] type={args.type}: {preview}")
    except Exception as e:
        print(f"ERROR storing memory: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_query(args):
    """Search company memory."""
    client = get_client()
    config = load_config()

    containers = (
        [args.container]
        if args.container
        else config.get("default_query_containers", ["company", "conventions", "decisions"])
    )
    limit = args.limit or config.get("defaults", {}).get("search_limit", 5)
    mode = args.mode or config.get("defaults", {}).get("search_mode", "hybrid")

    print(f"--- COMPANY MEMORY: Query ---")
    print(f"Query: {args.q}")
    print(f"Containers: {', '.join(containers)}")
    print(f"Mode: {mode} | Limit: {limit}\n")

    all_results = []
    for container in containers:
        try:
            response = client.search.memories(
                q=args.q,
                container_tag=container,
                search_mode=mode,
                limit=limit,
            )
            results = response.results if hasattr(response, "results") else (response.get("results", []) if isinstance(response, dict) else [])
            for r in results:
                memory = getattr(r, "memory", None) or getattr(r, "chunk", None) or (r.get("memory") or r.get("chunk") if isinstance(r, dict) else None) or str(r)
                similarity = getattr(r, "similarity", None) or (r.get("similarity") if isinstance(r, dict) else None) or "?"
                all_results.append({
                    "container": container,
                    "content": memory,
                    "score": similarity,
                })
        except Exception as e:
            print(f"  [{container}] Error: {e}")

    if not all_results:
        print("No results found.")
        return

    # Sort by score descending
    all_results.sort(key=lambda x: float(x["score"]) if x["score"] != "?" else 0, reverse=True)

    for i, r in enumerate(all_results[:limit], 1):
        print(f"  {i}. [{r['container']}] (score: {r['score']})")
        print(f"     {r['content']}")
        print()


def cmd_profile(args):
    """Get company profile."""
    client = get_client()
    container = args.container or "company"

    print(f"--- COMPANY MEMORY: Profile [{container}] ---\n")

    try:
        kwargs = {"container_tag": container}
        if args.q:
            kwargs["q"] = args.q

        response = client.profile(**kwargs)

        # Handle both object and dict responses
        if hasattr(response, "profile"):
            profile = response.profile
            static = getattr(profile, "static", []) if hasattr(profile, "static") else []
            dynamic = getattr(profile, "dynamic", []) if hasattr(profile, "dynamic") else []
        elif isinstance(response, dict):
            profile = response.get("profile", {})
            static = profile.get("static", [])
            dynamic = profile.get("dynamic", [])
        else:
            print(f"Unexpected response: {response}")
            return

        if static:
            print("Static Facts (permanent):")
            for fact in static:
                print(f"  - {fact}")
            print()

        if dynamic:
            print("Dynamic Context (recent):")
            for fact in dynamic:
                print(f"  - {fact}")
            print()

        # Search results if q was provided
        search_results = None
        if hasattr(response, "searchResults"):
            search_results = response.searchResults
        elif isinstance(response, dict):
            search_results = response.get("searchResults")

        if search_results:
            results = getattr(search_results, "results", None) or (search_results.get("results") if isinstance(search_results, dict) else None) or []
            if results:
                print("Related Search Results:")
                for r in results[:5]:
                    memory = getattr(r, "memory", None) or (r.get("memory") if isinstance(r, dict) else str(r))
                    print(f"  - {memory}")
                print()

        if not static and not dynamic:
            print("No memories found in this container yet.")
            print("Use 'store' to add company context.")

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_list(args):
    """List stored documents."""
    client = get_client()

    print("--- COMPANY MEMORY: List ---\n")

    try:
        kwargs = {}
        if args.container:
            kwargs["container_tag"] = args.container
        kwargs["limit"] = args.limit or 20

        response = client.documents.list(**kwargs)
        documents = response.documents if hasattr(response, "documents") else (response.get("documents", []) if isinstance(response, dict) else [])

        if not documents:
            print("No documents found.")
            return

        for doc in documents:
            doc_id = getattr(doc, "id", None) or (doc.get("id") if isinstance(doc, dict) else "?")
            status = getattr(doc, "status", None) or (doc.get("status") if isinstance(doc, dict) else "?")
            content = getattr(doc, "content", None) or (doc.get("content") if isinstance(doc, dict) else "")
            preview = str(content)[:80] + "..." if len(str(content)) > 80 else str(content)
            print(f"  [{status}] {doc_id}: {preview}")

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_bootstrap(args):
    """Batch store memories from JSON."""
    client = get_client()

    # Read JSON from file or stdin
    if args.file:
        data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    else:
        print("Reading JSON from stdin...")
        data = json.loads(sys.stdin.read())

    if not isinstance(data, list):
        data = [data]

    print(f"--- COMPANY MEMORY: Bootstrap ({len(data)} items) ---\n")

    success = 0
    for i, item in enumerate(data, 1):
        content = item.get("content", "")
        container = item.get("container", "company")
        mem_type = item.get("type", "note")
        tags = item.get("tags", [])
        static = item.get("static", False)

        metadata = {
            "type": mem_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stored_by": get_contributor(),
        }
        if tags:
            metadata["tags"] = tags

        try:
            client.add(
                content=content,
                container_tag=container,
                metadata=metadata,
            )
            preview = content[:60] + ("..." if len(content) > 60 else "")
            print(f"  {i}. [{container}] {mem_type}: {preview}")
            success += 1
        except Exception as e:
            print(f"  {i}. FAILED: {e}")

    print(f"\nStored {success}/{len(data)} memories.")


def cmd_config(args):
    """Show current config."""
    config = load_config()
    print("--- COMPANY MEMORY: Config ---\n")
    print(json.dumps(config, indent=2))


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Company Memory — Centralized knowledge base powered by Supermemory"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # doctor
    subparsers.add_parser("doctor", help="Validate environment")

    # store
    store_parser = subparsers.add_parser("store", help="Store a memory")
    store_parser.add_argument("--content", required=True, help="Memory content text")
    store_parser.add_argument("--container", required=True, help="Container tag (company, conventions, decisions, project_*)")
    store_parser.add_argument("--type", required=True, choices=["convention", "decision", "stack", "project-summary", "pattern", "note", "wip", "security-incident"], help="Memory type")
    store_parser.add_argument("--tags", help="Comma-separated tags")
    store_parser.add_argument("--static", action="store_true", help="Mark as permanent/static fact")
    store_parser.add_argument("--dynamic", action="store_true", help="Mark as ephemeral/dynamic (e.g. WIP state)")

    # query
    query_parser = subparsers.add_parser("query", help="Search company memory")
    query_parser.add_argument("--q", required=True, help="Search query")
    query_parser.add_argument("--container", help="Filter to specific container (omit to search defaults)")
    query_parser.add_argument("--limit", type=int, help="Max results (default: 5)")
    query_parser.add_argument("--mode", choices=["semantic", "hybrid"], help="Search mode (default: hybrid)")

    # profile
    profile_parser = subparsers.add_parser("profile", help="Get company profile")
    profile_parser.add_argument("--container", help="Container to profile (default: company)")
    profile_parser.add_argument("--q", help="Optional search query to include results")

    # list
    list_parser = subparsers.add_parser("list", help="List stored documents")
    list_parser.add_argument("--container", help="Filter by container")
    list_parser.add_argument("--limit", type=int, help="Max results (default: 20)")

    # bootstrap
    bootstrap_parser = subparsers.add_parser("bootstrap", help="Batch store from JSON")
    bootstrap_parser.add_argument("--file", help="JSON file path (or read from stdin)")

    # config
    subparsers.add_parser("config", help="Show current config")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "doctor": cmd_doctor,
        "store": cmd_store,
        "query": cmd_query,
        "profile": cmd_profile,
        "list": cmd_list,
        "bootstrap": cmd_bootstrap,
        "config": cmd_config,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
