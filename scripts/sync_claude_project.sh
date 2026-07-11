#!/usr/bin/env bash
# Sync project context docs to Claude.ai Project.
#
# First-time setup:
#   1. Go to claude.ai, open DevTools → Application → Cookies
#   2. Copy the value of the `sessionKey` cookie
#   3. Run: ./scripts/sync_claude_project.sh init <session_key>
#   4. Run: ./scripts/sync_claude_project.sh create
#
# Subsequent syncs (after docs change):
#   ./scripts/sync_claude_project.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV="$REPO_ROOT/.venv/bin/activate"

if [ ! -f "$VENV" ]; then
  echo "ERROR: venv not found at $VENV. Run: python3 -m venv .venv && pip install -r requirements.txt" >&2
  exit 1
fi

source "$VENV"
cd "$REPO_ROOT"

COMMAND="${1:-update}"

case "$COMMAND" in
  init)
    SESSION_KEY="${2:?Usage: $0 init <session_key>}"
    claude-pyrojects init -K "$SESSION_KEY"
    echo ""
    echo "Next step: run './scripts/sync_claude_project.sh create' to create the Claude project and upload docs."
    ;;
  create)
    claude-pyrojects create -N "Health Insurance News Agent"
    ;;
  update)
    claude-pyrojects update
    ;;
  status)
    claude-pyrojects status
    ;;
  *)
    echo "Usage: $0 [init <session_key> | create | update | status]"
    exit 1
    ;;
esac
