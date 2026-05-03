#!/usr/bin/env bash
# stigmem/adapters/paperclip/hook.sh
#
# Paperclip hook that emits lifecycle facts to Stigmem.
#
# Configure in .claude/settings.json:
#
#   "hooks": {
#     "PostToolUse": [{
#       "matcher": "Bash",
#       "hooks": [{
#         "type": "command",
#         "command": "bash stigmem/adapters/paperclip/hook.sh post_tool_use"
#       }]
#     }]
#   }
#
# Environment variables required:
#   STIGMEM_URL             — Stigmem node base URL
#   STIGMEM_API_KEY         — API key (optional)
#   STIGMEM_SOURCE_ENTITY   — e.g. "agent:cto"
#   PAPERCLIP_TASK_ID       — set by Paperclip harness

set -euo pipefail

EMIT="node $(dirname "$0")/emit-fact.js"
TASK="${PAPERCLIP_TASK_ID:-}"
SOURCE="${STIGMEM_SOURCE_ENTITY:-agent:unknown}"
EVENT="${1:-unknown}"

if [[ -z "${STIGMEM_URL:-}" ]]; then
  exit 0  # Stigmem not configured; skip silently
fi

case "$EVENT" in
  checkout)
    if [[ -n "$TASK" ]]; then
      $EMIT assert \
        --entity "issue:${TASK}" \
        --relation "paperclip:checkout" \
        --value '{"type":"string","v":"in_progress"}' \
        --source "$SOURCE" \
        --scope company || true
    fi
    ;;

  complete)
    if [[ -n "$TASK" ]]; then
      $EMIT assert \
        --entity "issue:${TASK}" \
        --relation "paperclip:issue_status" \
        --value '{"type":"string","v":"done"}' \
        --source "$SOURCE" \
        --scope company || true
    fi
    ;;

  blocked)
    BLOCKING="${2:-}"
    if [[ -n "$TASK" ]]; then
      $EMIT assert \
        --entity "issue:${TASK}" \
        --relation "paperclip:issue_status" \
        --value '{"type":"string","v":"blocked"}' \
        --source "$SOURCE" \
        --scope company || true
      if [[ -n "$BLOCKING" ]]; then
        $EMIT assert \
          --entity "issue:${TASK}" \
          --relation "paperclip:blocked_by" \
          --value "{\"type\":\"ref\",\"v\":\"issue:${BLOCKING}\"}" \
          --source "$SOURCE" \
          --scope company || true
      fi
    fi
    ;;

  post_tool_use)
    # Called by Paperclip PostToolUse hook — emit a lightweight heartbeat ping
    # so other agents can see this agent is active on the task.
    # Only emits if PAPERCLIP_TASK_ID is set (i.e., inside a heartbeat).
    if [[ -n "$TASK" ]]; then
      TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
      $EMIT assert \
        --entity "issue:${TASK}" \
        --relation "paperclip:last_active" \
        --value "{\"type\":\"datetime\",\"v\":\"${TIMESTAMP}\"}" \
        --source "$SOURCE" \
        --scope local || true
    fi
    ;;

  *)
    echo "Unknown event: $EVENT" >&2
    exit 1
    ;;
esac
