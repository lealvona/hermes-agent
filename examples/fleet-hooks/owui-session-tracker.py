#!/usr/bin/env python3
"""on_session_start hook: record session_id → platform in a shared state file.

Used by categoryb-guard.py to know whether MCP tool calls are originating
from an OWUI api_server session (allowed) or a CLI/other session (blocked
for filesystem and memory MCPs whose roots are OWUI-specific data).

State file: /tmp/hermes-session-platforms.json  (world-readable, session-lived)
"""
import json
import os
import sys
import tempfile

STATE_FILE = "/tmp/hermes-session-platforms.json"
LOCK_FILE = STATE_FILE + ".lock"


def _load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(state):
    # Atomic write via temp file in same dir
    dir_ = os.path.dirname(STATE_FILE)
    fd, tmp = tempfile.mkstemp(dir=dir_, prefix=".hsp-")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f)
        os.replace(tmp, STATE_FILE)
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return

    if payload.get("hook_event_name") != "on_session_start":
        return

    session_id = payload.get("session_id", "")
    platform = payload.get("extra", {}).get("platform", "unknown")

    if not session_id:
        return

    state = _load_state()
    # Prune stale entries (keep last 200)
    if len(state) > 200:
        keys = list(state.keys())
        for k in keys[:-100]:
            del state[k]

    state[session_id] = platform
    _save_state(state)


if __name__ == "__main__":
    main()
