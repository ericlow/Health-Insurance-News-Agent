#!/usr/bin/env bash
# start-agents.sh — bootstrap two Claude agent sessions (worker + spy)
# Run from anywhere; project root is resolved relative to this script.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORKER_LOG="/tmp/worker-agent.log"

echo "Project: $PROJECT_DIR"
echo "Worker log: $WORKER_LOG"

# Create sessions if they don't already exist
tmux new-session -d -s worker -c "$PROJECT_DIR" 2>/dev/null \
  && echo "Created session: worker" \
  || echo "Session 'worker' already exists — skipping."

tmux new-session -d -s spy -c "$PROJECT_DIR" 2>/dev/null \
  && echo "Created session: spy" \
  || echo "Session 'spy' already exists — skipping."

# Launch Claude in each session
tmux send-keys -t worker "claude" Enter
tmux send-keys -t spy "claude" Enter

# Give Claude time to initialize before sending messages
echo "Waiting for Claude to initialize..."
sleep 6

# Pipe worker output to a log file so spy can tail it
tmux pipe-pane -t worker "cat >> $WORKER_LOG"

# Brief worker
tmux send-keys -t worker "[bootstrap] You are the worker agent — role: executor. Session name: worker. Protocol: prefix all messages with [worker]. Send to spy with two calls: tmux send-keys -t spy \"[worker] message\" Enter, then tmux send-keys -t spy \"\" Enter. Read the Multi-Agent Protocol section in CLAUDE.md. Wait for task assignments."
tmux send-keys -t worker "" Enter

# Brief spy
tmux send-keys -t spy "[bootstrap] You are the spy agent — role: monitor and coordinator. Session name: spy. Protocol: prefix all messages with [spy]. Send to worker with two calls: tmux send-keys -t worker \"[spy] message\" Enter, then tmux send-keys -t worker \"\" Enter. Worker output is logged to $WORKER_LOG — to monitor run: tail -f $WORKER_LOG. Read the Multi-Agent Protocol section in CLAUDE.md. Coordinate tasks with worker; escalate dangerous decisions to the user."
tmux send-keys -t spy "" Enter

echo "Agents started. Attaching to spy (coordination session)..."
tmux attach-session -t spy
