#!/usr/bin/env python3
"""Category-B data-boundary guard (pre_tool_call shell hook).

Two enforcement layers:

1. OWUI-only MCP tools (filesystem, memory):
   mcp_filesystem_* and mcp_memory_* tools are sandboxed to OWUI-specific
   data roots. They are blocked for non-api_server sessions (CLI, etc.) so
   that only OWUI-originated requests can touch those roots.
   Platform is resolved from /tmp/hermes-session-platforms.json, written by
   the on_session_start hook (owui-session-tracker.py).

2. Category-B data-boundary (cloud-backed profiles):
   Blocks tool calls that reference protected Category-B resources (email
   corpus, maildirs, local-only profile files, hermes credential files).
   Complements the kanban board->assignee policy. Tune PROTECTED below.

Test with:  hermes hooks test pre_tool_call --for-tool terminal --payload-file <f>
"""
import json
import re
import sys

# ── OWUI-only MCP tools ──────────────────────────────────────────────────────

STATE_FILE = "/tmp/hermes-session-platforms.json"

# Tools whose roots are OWUI-specific — block outside api_server sessions
OWUI_ONLY_PREFIXES = ("mcp_filesystem_", "mcp_memory_")


def _session_platform(session_id: str) -> str:
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        return state.get(session_id, "unknown")
    except Exception:
        return "unknown"


# ── Category-B patterns ──────────────────────────────────────────────────────

PROTECTED = [
    r"email_corpus",                        # corpus Postgres DB / DSN
    r"[Mm]aildir",                          # raw mail stores
    r"\.hermes/profiles/local-only/",       # local-only profile internals
    r"\.hermes(/profiles/[^/]+)?/\.env",    # hermes credential files
    r"shell-hooks-allowlist\.json",         # the consent file itself
]


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    if payload.get("hook_event_name") != "pre_tool_call":
        return

    tool_name = payload.get("tool_name", "")
    session_id = payload.get("session_id", "")

    # ── Check OWUI-only MCP tools ────────────────────────────────────────────
    if any(tool_name.startswith(p) for p in OWUI_ONLY_PREFIXES):
        platform = _session_platform(session_id)
        if platform != "api_server":
            print(json.dumps({
                "action": "block",
                "message": (
                    f"OWUI-only guard: '{tool_name}' is restricted to OWUI "
                    f"(api_server) sessions. This session platform is "
                    f"'{platform}'. Use Open WebUI to "
                    f"access the filesystem and memory MCP tools."
                ),
            }))
            return

    # ── Check Category-B patterns ────────────────────────────────────────────
    blob = json.dumps(payload.get("tool_input") or {}, ensure_ascii=False)
    for pat in PROTECTED:
        if re.search(pat, blob):
            print(json.dumps({
                "action": "block",
                "message": (
                    "Category-B guard: this tool call references a protected "
                    "resource (pattern: %s). Cloud-backed profiles must not "
                    "touch the email corpus, maildirs, local-only profile "
                    "files, or hermes credential files. Do NOT retry this "
                    "call. Delegate to a local-only Hermes profile instead: "
                    "create a private kanban task assigned to a local-only "
                    "profile — it will pick up and run the work without "
                    "exposing the data to cloud providers."
                ) % pat,
            }))
            return


if __name__ == "__main__":
    main()
