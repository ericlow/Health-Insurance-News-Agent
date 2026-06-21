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

<<<<<<< HEAD
This project follows **spec-driven development**: specs are written and agreed upon before code is written. Type `/sdd` to enter interactive coaching mode.

### Spec locations:
- `docs/prd.md` — Product Requirements Doc
- `docs/technical-design.md` — Technical Design Doc
- `docs/inputs.md` — Domain expert input log (never paraphrase or compress entries — original framing contains signal)
- `docs/specs/*.md` — Feature specs, one per story/Linear issue, written before implementation
- `docs/sdd-playbook.md` — Full SDD reference: spec template, Gherkin format, execution modes, anti-patterns

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
=======
This project follows **spec-driven development**: specs are written and agreed upon before code is written. Claude acts as a coach in this process — proactively telling Eric what spec work needs to happen next and what decisions need to be made before implementation can proceed.

### Specs live here:
- `docs/prd.md` — **Product Requirements Doc (PRD)**: what we're building and why, user needs, success metrics, scope boundaries
- `docs/technical-design.md` — **Technical Design Doc (TDD)**: architecture, data models, component design, technology choices
- `docs/inputs.md` — **Domain expert input log**: raw dated inputs from Eric; source of truth for domain knowledge

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
>>>>>>> 51a6ba1 (Complete Phase 1: Becker's Payer ingestion pipeline)

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

**Known issue:** `pytest` currently fails with `ModuleNotFoundError: No module named 'agent'` for all tests. Root cause: no `conftest.py` or `pyproject.toml` to add the project root to `sys.path`. Fix needed before any tests can run: add a `conftest.py` at the project root with `sys.path` configuration, or add `[tool.pytest.ini_options] pythonpath = ["."]` to a `pyproject.toml`.


