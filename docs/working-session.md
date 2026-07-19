# Working Session — 2026-07-18

_Auto-updated every 10 minutes. Delete this file once all decisions are saved to Linear issues, milestones, PRD, and TDD._

---

## Context

We are in a planning session to define two new agents (A1 and A2) and an AWS infrastructure migration. No implementation has started. Three milestones and three spec issues were created in Linear.

---

## Milestones created (Linear)

| Milestone | Linear |
|---|---|
| Phase 5 — Event Tracking Agent (A1) | aab591d5 |
| Phase 6 — Analysis Agent (A2) | c06cd2c8 |
| Infrastructure — AWS Migration | 2d167435 |

## Issues created (Linear)

| Issue | Title | Status |
|---|---|---|
| AGE-67 | Spec: Event Tracking Agent (A1) — named-party monitor + conversational interface | Backlog |
| AGE-68 | Spec: Analysis Agent (A2) — multi-tool analysis + conversational interface | Backlog |
| AGE-69 | Spec: AWS migration — EC2 + RDS deployment design | Backlog |
| AGE-70 | Architecture planning — ADRs, specs, and infrastructure decisions | In Progress |

## Active branch

`ericlow/age-70-architecture-planning-adrs-specs-and-infrastructure`

---

## Decisions made

- Created 3 new Linear milestones: Phase 5 (A1), Phase 6 (A2), Infrastructure — AWS Migration
- Created 4 spec issues: AGE-67 (A1), AGE-68 (A2), AGE-69 (AWS), AGE-70 (planning branch)
- Session notes auto-updated every 10 minutes via Claude Code cron job (ID: d8261789)
- **Branch created**: `ericlow/age-70-architecture-planning-adrs-specs-and-infrastructure`
- **Lambda confirmed viable for conversational agents** — conversation history stored in Neon per turn; each user message = one Lambda invocation; Claude API is stateless
- **Lambda + EventBridge Scheduler** for scheduled pipeline; **Lambda + API Gateway** for conversational agent turns
- **Fly.io evaluated and set aside** — Lambda handles use case without containerization overhead
- **ADR practice adopted** — `docs/decisions/` folder, numbered ADR files, immutable once written
- **Neon vs Supabase compared** — Neon preferred: Supabase free tier pauses inactive projects after 1 week (breaks scheduled pipeline); Neon auto-suspends per-connection (wakes in ~500ms, no project-level pause); Supabase extras (auth, REST API, realtime) are irrelevant to this stack
- **Neon auto-suspend clarified**: compute suspends after 5 min inactivity; wakes in ~500ms-1s; psycopg2 blocks during wake — no failure, no code changes needed
- **Neon vs Supabase resolved**: essentially equivalent for this use case; Neon chosen over Supabase because no project-level pause risk; cold start acceptable at 8-hour pipeline intervals
- **ADR directory renamed** from `docs/decisions/` to `docs/adr/`
- **ADR-001 written**: `docs/adr/ADR-001-database-host.md` — status: Accepted. Updated to include: why Neon won (project-level pause tiebreaker), Supabase near-equivalence acknowledged, CockroachDB/PlanetScale noted as not evaluated, vendor risk + Supabase fallback noted in Consequences
- **ADR-002 written and accepted**: `docs/adr/ADR-002-compute-platform.md` — AWS Lambda chosen; full due diligence documented across 7 options:
  - EC2: eliminated (12-month free tier, server management)
  - Fly.io: eliminated (containerization overhead, persistent process not needed)
  - Cloudflare Workers: eliminated (JS/TS edge tool, not a data pipeline platform; psycopg2 won't run)
  - Vercel: eliminated (free cron minimum once/day; need 8-hour; 10s timeout)
  - Render: eliminated (30s cold start — spins down after 15 min idle)
  - Google Cloud Functions: close runner-up (more generous free tier, simpler HTTP/cron); eliminated on AWS ecosystem preference
  - **Lambda chosen**: EventBridge Scheduler for cron, API Gateway for HTTP, CloudWatch for logs, Lambda env vars for secrets, GitHub Actions for deployment
- **Cost ceiling**: $10/month — stop and reassess if exceeded
- **Data migration**: full history migrated to Neon via pg_dump + restore
- **Backfill**: laptop-only — one-time historical scrape; Lambda/cloud complexity not justified for a one-off operation; browser-based backfill stays on laptop or GitHub Actions if needed

---

## Open questions (by area)

### Infrastructure — COMPLETE ✓
- ~~ADR-001~~: Neon ✓
- ~~ADR-002~~: AWS Lambda ✓
- ~~Secrets~~: Lambda env vars ✓
- ~~Deployment~~: GitHub Actions ✓
- ~~Logging~~: CloudWatch ✓
- ~~Cost ceiling~~: $10/month ✓
- ~~Data migration~~: full history, pg_dump + restore to Neon ✓
- ~~Backfill~~: laptop-only ✓

### A1 — Event Tracking Agent
- **Party configuration**: ✓ DB table (`watched_pairs`) — fields: party_a, party_b, active, created_at; add/remove pairs without config changes; conversational agent can manage pairs too
- ADR vs spec order clarified: ADR first for architectural decisions, spec first for behavioral; A1 has no new architectural blockers
- TDD relationship clarified: ADRs are immutable decision records; TDD is living system overview; both needed; TDD updated after spec decisions
- **Entity matching model confirmed**: two retrieval paths per watched pair:
  1. DB search — alias-based SQL query against existing collected articles
  2. Fresh scrape — Google News query auto-built from aliases; newsroom pages scraped and filtered by alias mention
  - Aliases serve both paths: SQL WHERE clauses for DB search, query construction for fresh scrape
- **Notification channel**: ✓ Discord only
- **Notification trigger**: ✓ Triage-filtered (LLM confirms relevance to relationship before notifying) — same pattern as existing pipeline
- ~~Notification channel~~: ✓ Discord
- ~~Notification trigger~~: ✓ Triage-filtered
- ~~Conversational interface~~: ✓ Discord (reply to bot in same channel as notifications)
- ~~Context accumulation~~: ✓ Neon DB, persisted per watched pair, available across sessions and to A2
- ~~Google News monitor relationship~~: ✓ Separate monitor, shared scraper code
- **A1 spec written**: `docs/specs/event-tracking-agent-a1.md`

### A2 — Analysis Agent
- Invocation model: manual, auto-triggered by A1, or both?
- Article search tool: what filters? (source, date, entity mentions?)
- External data providers: which ones specifically? (CMS, KFF, state filings, financial?)
- Output format: structured briefing to DB, freeform chat, or both?

---

## Next actions

1. ~~Create Linear issue + branch~~ ✓ AGE-70, branch active
2. ~~Confirm Neon decision → write ADR-001~~ ✓ Done
3. ~~Reopen ADR-002 — decide Lambda vs Google Cloud Functions, then rewrite~~ ✓ Done
4. Work through A1 open questions ← next
5. Work through A2 open questions
6. Update PRD and TDD once decisions are made
7. Write specs: docs/specs/event-tracking-agent-a1.md, docs/specs/analysis-agent-a2.md, docs/specs/aws-migration.md
8. Delete this file when all decisions are captured in Linear/specs

---

_Last updated: 2026-07-19 00:06_
