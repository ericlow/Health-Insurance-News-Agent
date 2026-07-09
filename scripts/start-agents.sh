#!/usr/bin/env bash
# start-agents.sh — bootstrap a worker+spy Claude agent pair
# Usage: ./start-agents.sh [PAIR_ID]
#   PAIR_ID defaults to the next available integer (1, 2, 3, …)
# Sessions are named worker-N and spy-N.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Resolve pair ID: use argument if given, otherwise find next free slot
if [[ $# -gt 0 ]]; then
  PAIR_ID="$1"
else
  PAIR_ID=1
  while tmux has-session -t "worker-${PAIR_ID}" 2>/dev/null \
     || tmux has-session -t "spy-${PAIR_ID}" 2>/dev/null; do
    PAIR_ID=$((PAIR_ID + 1))
  done
fi

WORKER_SESSION="worker-${PAIR_ID}"
SPY_SESSION="spy-${PAIR_ID}"
WORKER_LOG="/tmp/worker-agent-${PAIR_ID}.log"

echo "Project:        $PROJECT_DIR"
echo "Pair ID:        $PAIR_ID"
echo "Worker session: $WORKER_SESSION"
echo "Spy session:    $SPY_SESSION"
echo "Worker log:     $WORKER_LOG"

# Abort if either session in this pair already exists
if tmux has-session -t "$WORKER_SESSION" 2>/dev/null; then
  echo "ERROR: session '$WORKER_SESSION' already exists. Choose a different pair ID." >&2
  exit 1
fi
if tmux has-session -t "$SPY_SESSION" 2>/dev/null; then
  echo "ERROR: session '$SPY_SESSION' already exists. Choose a different pair ID." >&2
  exit 1
fi

tmux new-session -d -s "$WORKER_SESSION" -c "$PROJECT_DIR"
echo "Created session: $WORKER_SESSION"

tmux new-session -d -s "$SPY_SESSION" -c "$PROJECT_DIR"
echo "Created session: $SPY_SESSION"

# Launch Claude in each session
tmux send-keys -t "$WORKER_SESSION" "claude" Enter
tmux send-keys -t "$SPY_SESSION" "claude" Enter

echo "Waiting for Claude to initialize..."
sleep 6

# Pipe worker output to a log file so spy can tail it
tmux pipe-pane -t "$WORKER_SESSION" "cat >> $WORKER_LOG"

# Brief worker
tmux send-keys -t "$WORKER_SESSION" "[bootstrap] You are the worker agent in pair ${PAIR_ID} — role: executor. Your tmux session name is ${WORKER_SESSION}. Protocol: prefix all messages with [${WORKER_SESSION}]. Send to spy with two calls: tmux send-keys -t ${SPY_SESSION} \"[${WORKER_SESSION}] message\" Enter, then tmux send-keys -t ${SPY_SESSION} \"\" Enter. Read the Multi-Agent Protocol section in CLAUDE.md. Wait for task assignments." ""
tmux send-keys -t "$WORKER_SESSION" "" Enter

# Brief spy
tmux send-keys -t "$SPY_SESSION" "[bootstrap] You are the spy agent in pair ${PAIR_ID} — role: monitor and coordinator. Your tmux session name is ${SPY_SESSION}. Protocol: prefix all messages with [${SPY_SESSION}]. Send to worker with two calls: tmux send-keys -t ${WORKER_SESSION} \"[${SPY_SESSION}] message\" Enter, then tmux send-keys -t ${WORKER_SESSION} \"\" Enter. Worker output is logged to ${WORKER_LOG} — to monitor run: tail -f ${WORKER_LOG}. Read the Multi-Agent Protocol section in CLAUDE.md. Coordinate tasks with worker; escalate dangerous decisions to the user." ""
tmux send-keys -t "$SPY_SESSION" "" Enter

echo ""
echo "Pair ${PAIR_ID} started."
echo "  Attach to spy:    tmux attach-session -t ${SPY_SESSION}"
echo "  Attach to worker: tmux attach-session -t ${WORKER_SESSION}"
echo "  Tail worker log:  tail -f ${WORKER_LOG}"
echo ""
echo "Attaching to ${SPY_SESSION} (coordination session)..."
tmux attach-session -t "$SPY_SESSION"
