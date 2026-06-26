# Fleet Hook Examples

Example shell hooks (`config.yaml hooks:` block) demonstrating how to wire
pre_tool_call and on_session_start guards for a multi-profile Hermes deployment.

## owui-session-tracker.py  (on_session_start)

Writes `{session_id → platform}` to `/tmp/hermes-session-platforms.json`.
Used by other `pre_tool_call` hooks to distinguish OWUI (api_server) sessions
from CLI sessions without modifying the agent core.

## categoryb-guard.py  (pre_tool_call)

Two-layer guard:
1. **OWUI-only MCP tools**: blocks `mcp_filesystem_*` and `mcp_memory_*`
   calls in non-api_server sessions (reads the platform file written by
   owui-session-tracker). context7 and llmwiki are unrestricted.
2. **Category-B data boundary**: blocks cloud-backed profile tool calls
   that reference protected data (email corpus, maildirs, local-only
   profile internals, credential files).

## Wiring (config.yaml)

```yaml
hooks:
  on_session_start:
  - command: python3 /path/to/owui-session-tracker.py
    timeout: 5
  pre_tool_call:
  - command: python3 /path/to/categoryb-guard.py
    timeout: 10
```
