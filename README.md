# Health Insurance News Agent

A multi-agent system that monitors health insurance industry news for significant relationship changes between major carriers and providers — acquisitions, mergers, partnerships, divestitures, and contract terminations.

## How it works

A **News Monitor Agent** continuously scans industry sources and flags relevant stories. Each flagged story spawns **Analysis Agents** that define the geographic regions impacted, size the entities involved economically, 
and research alternatives for affected parties.

*We are looking for major changes in relationships. Could be the form of acquisitions, mergers, partnerships, divestitures, or terminations of deals between major insurance carriers and providers.* 

Examples:
* https://www.healthaffairs.org/topic/primary-topic/pt_83

## Documentation

- [`docs/inputs.md`](docs/inputs.md) — dated log of domain expert inputs; the source of truth for what this system should look for and why
- [`CLAUDE.md`](CLAUDE.md) — guidance for working in this repo with Claude Code
