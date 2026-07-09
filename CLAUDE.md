# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

This is a multi-agent system that monitors health insurance industry news for significant relationship changes between major insurance carriers and healthcare providers — acquisitions, mergers, partnerships, divestitures, and contract terminations. The intended user is an industry analyst who wants to be alerted to shifts that affect health plan networks.

## Domain Context

Relationships to watch:
- **Network agreements**: when a provider (hospital system, physician group) joins or exits an insurer's network
- **Acquisitions/mergers**: between insurers (e.g., carrier buys carrier) or between providers (e.g., hospital buys clinic chain)
- **Divestiture/termination**: an insurer dropping a major provider or vice versa
- **Third-party administrator (TPA) shifts**: a self-funded employer switching its claims processor (e.g., CalPERS/Anthem dynamic)

Key signals to look for:
- Soft RFP language from large purchasers (e.g., CalPERS signaling intent to switch carriers)
- Layoffs of carrier account teams serving a specific client — a strong leading indicator of contract loss
- Provider systems announcing their own network/insurance products (e.g., Sutter building its own plan backed by Anthem's network)

## Planned Architecture

The system is a **hierarchical multi-agent pipeline**:

1. **News Monitor Agent** — scrapes/searches for relevant news across industry sources, flags candidate articles
2. **Analysis Agents** (spawned per story) — each flagged story triggers sub-agents that:
   - Define the geographic regions impacted
   - Size the entities involved economically (membership count, revenue, market share)
   - Research alternatives available to affected parties

Sources to integrate: insurer newsrooms (e.g., `newsroom.cigna.com`), health industry trade press, Yahoo Finance/Healthcare, state insurance department filings.

## Development Philosophy: Spec-Driven Development

This project follows **spec-driven development**: specs are written and agreed upon before code is written. Type `/sdd` to enter interactive coaching mode. Claude acts as a coach — proactively telling Eric what spec work needs to happen next and what decisions need to be made before implementation can proceed.

### Spec locations:
- `docs/prd.md` — **Product Requirements Doc (PRD)**: what we're building and why, user needs, success metrics, scope boundaries
- `docs/technical-design.md` — **Technical Design Doc (TDD)**: architecture, data models, component design, technology choices
- `docs/inputs.md` — **Domain expert input log**: raw dated inputs from Eric; source of truth for domain knowledge
- `docs/specs/*.md` — Feature specs, one per story/Linear issue, written before implementation
- `docs/sdd-playbook.md` — Full SDD reference: spec template, Gherkin format, execution modes, anti-patterns

### The workflow:
1. New direction or feature idea comes in from Eric (verbally or as notes)
2. Claude identifies which spec(s) need to be updated or created, and prompts Eric for any missing decisions
3. Specs are updated and agreed upon before any code is written
4. Code is written to satisfy the spec — not the other way around

### Claude's coaching responsibilities:
- Flag when a conversation is moving toward implementation without a completed spec
- Identify open questions in the specs that must be resolved before building
- Tell Eric explicitly what the next spec action is at the end of each significant decision
- When domain expert input arrives, append it to `docs/inputs.md` first, then surface what PRD or TDD sections it affects

Never paraphrase or compress entries in `docs/inputs.md` — the expert's original framing often contains signal that gets lost in synthesis.

### Branch and issue strategy:
- All implementation work happens on a feature branch, never directly on `main`
- Before branching: create a Linear issue in the **Agents** team, **Health Insurance News Agent** project, assigned to the relevant phase milestone
- Use Linear's auto-generated branch name to link the branch to the issue automatically
- One story = one branch; target branch lifetime ≤ 1 day
- Merge via PR when work is complete and tests pass; `main` must always be in a working state

**Linear workspace:**
- Team: `Agents`
- Project: `Health Insurance News Agent`
- Milestones: Phase 1 — Ingestion | Phase 2 — Prompt Development | Phase 3 — Analysis Pipeline

## Multi-Agent Protocol

Claude agent pairs run in parallel via tmux. Start a new pair with `scripts/start-agents.sh`.

Multiple pairs can run simultaneously. Each pair gets a numeric ID (1, 2, 3, …) assigned automatically, or you can pass one explicitly:

```bash
scripts/start-agents.sh        # auto-assigns next available pair ID
scripts/start-agents.sh 2      # explicitly start pair 2
```

**Sessions and roles (per pair N):**
- `spy-N` — monitor and coordinator; user's primary vantage point
- `worker-N` — executor; runs headless

Attach to a pair's coordinator: `tmux attach-session -t spy-N`

**Messaging protocol:**
- Each agent knows its own session name (`worker-N` / `spy-N`) from the bootstrap briefing
- Prefix every message with your session name: `[worker-N] message` or `[spy-N] message`
- Send text and Enter in two calls — one for the message, one blank Enter to submit:
  ```
  tmux send-keys -t <target-session> "[sender] message" Enter
  tmux send-keys -t <target-session> "" Enter
  ```
- Avoid `$` signs in messages — the shell interprets them before tmux sees them. Write `0.02 USD` not `$0.02`.
- Do not poll — only message when there is something to coordinate
- Escalate dangerous or irreversible actions to the user before proceeding

**Monitoring worker output:**
- Worker output is piped to `/tmp/worker-agent-N.log` by the bootstrap script
- Spy can tail it with: `tail -f /tmp/worker-agent-N.log`

## Git Worktrees

Use worktrees to work on a branch in isolation without disturbing the main checkout. The `.claude/worktrees/` directory is the standard location for worktrees in this repo.

```bash
# Create a worktree for a feature branch
git worktree add .claude/worktrees/<branch-name> <branch-name>

# Work inside it
cd .claude/worktrees/<branch-name>
source ../../.venv/bin/activate   # reuse the root venv
```

The root `.venv` is shared across worktrees — no need to create a new one per worktree.

Remove a worktree when done:

```bash
git worktree remove .claude/worktrees/<branch-name>
```

List active worktrees:

```bash
git worktree list
```

## Python Environment

Use `.venv/` in the project root (created with `python3 -m venv .venv`). Activate before running anything:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run tests:

```bash
pytest
```

Run a single test:

```bash
pytest tests/path/to/test_file.py::test_function_name
```
