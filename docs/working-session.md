# Working Session — 2026-08-22

---

## Outstanding work — pick up here next session

### TODAY'S SESSION (2026-08-22) — In Progress

#### AGE-91: John Muir Health newsroom monitor
- [ ] **Eric to validate PR #37** — https://github.com/ericlow/Health-Insurance-News-Agent/pull/37
  - Branch: `ericlow/age-91-john-muir-health-newsroom-monitor`
  - HTML scraping of `https://www.johnmuirhealth.com/about-john-muir-health/press-room.html`
  - 8 articles inserted into local DB (PKs 875–882) — all confirmed
  - AGE-91 is In Review in Linear
- [ ] After Eric validates: merge PR, mark AGE-91 Done, confirm GH Actions deploy, trigger Lambda, verify Discord

#### Hoag Health (AGE-83) + City of Hope (AGE-84) — Google News RSS approach
- Direct newsroom scraping blocked (Hoag: Astro SPA, City of Hope: Cloudflare)
- Background research confirmed: **Google News RSS works for both**
  - Hoag: `https://news.google.com/rss/search?q=Hoag+Health&hl=en-US&gl=US&ceid=US:en`
  - City of Hope: `https://news.google.com/rss/search?q=City+of+Hope+hospital&hl=en-US&gl=US&ceid=US:en`
  - Both return 10+ recent items; includes their own wire releases (PR Newswire, GlobeNewswire) + third-party coverage
  - Notable: Hoag feed item "Blue Shield of California Members Have Network Access to Hoag Hospitals and Providers" — exactly the kind of signal this system is built for
  - Google-wrapped URLs redirect to canonical; body text requires follow-on fetch from canonical source
  - PR Newswire has no company-specific RSS; Business Wire timed out; no Hoag newsroom subdomains
- **Claude implemented both overnight** — see AGE-83 and AGE-84 Linear issues and PRs for status

#### Lambda schedule — 1am run removal (Eric's action)
- Eric is doing this in AWS Console UI (IAM user lacks EventBridge permissions)
- EventBridge → Rules → us-west-1 → find the 1am rule (cron is UTC; 1am PT = ~8-9am UTC depending on DST)
- Delete that rule only; leave 7am, 1pm, and 4th run untouched
- Note all 4 rule names/cron expressions before deleting to confirm the right one

---

### PRIOR SESSION CARRY-OVERS (from 2026-07-23)

- [ ] Read `docs/analysis/age-71-session-handoff.md` — context for A2 work
- [ ] Merge PR #24 (market-impact-analysis skill) — check if still open
- [ ] A1 spec review (`docs/specs/event-tracking-agent-a1.md`) — Eric to read and approve
- [ ] A2 spec — write `docs/specs/analysis-agent-a2.md`
- [ ] AWS migration spec — write `docs/specs/aws-migration.md`
- [ ] Update TDD (`docs/technical-design.md`) — reflect Lambda, Neon, EventBridge, API Gateway, A1, A2
- [ ] Update PRD (`docs/prd.md`) — reflect A1 and A2 as new product capabilities
- [ ] Merge AGE-70 PR and close issue

---

## What was completed this session (2026-08-22)

- ✓ Validated AGE-77 (UCI Health), AGE-78 (UCLA Health), AGE-79 (UCSD — rewrote to correct source URL), AGE-80 (UCSF), AGE-81 (Sharp), AGE-82 (Scripps), AGE-86 (Providence CA) — all marked Done in Linear
- ✓ Fixed UCSD monitor: was pointing at general university research RSS; rewrote to HTML scrape `health.ucsd.edu/news/press-releases/`
- ✓ Added smoke test guardrail to `/new-source` skill: always use `DATABASE_URL_LOCAL`, never Neon
- ✓ Created `/new-source` skill at `.claude/skills/new-source/SKILL.md`
- ✓ Updated `/new-source` skill Step 6 validation: prints all article titles + confirms DB records with PKs
- ✓ Feed research: Hoag (SPA/blocked), City of Hope (Cloudflare/blocked), John Muir Health (HTML scraping — works)
- ✓ AGE-91 (John Muir Health) created, implemented, PR #37 opened, In Review

---

## Key facts

- **Lambda function**: `health-insurance-monitor`, region `us-west-1`
- **Schedule**: EventBridge, 4 runs/day — 1am PT (to be deleted by Eric), 7am PT, 1pm PT, + one more
- **IAM user** (`github-actions-deploy`) lacks `events:ListRules` / `events:DeleteRule` — cannot manage EventBridge via CLI
- **Databases**: Neon (production, `DATABASE_URL`), Docker Postgres (local, `DATABASE_URL_LOCAL`) — smoke tests always use `DATABASE_URL_LOCAL`
- **Confidence flagging**: Eric asked for [HIGH]/[MED]/[LOW] confidence flags on claims

---

_Last updated: 2026-08-22 end of session_
