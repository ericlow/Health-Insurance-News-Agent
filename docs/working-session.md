# Working Session — 2026-08-23

---

## Outstanding work — pick up here next session

### PRs awaiting Eric's validation (open as of end of session)

| PR | Issue | Branch | What it does |
|---|---|---|---|
| [#37](https://github.com/ericlow/Health-Insurance-News-Agent/pull/37) | AGE-91 | `ericlow/age-91-john-muir-health-newsroom-monitor` | John Muir Health — HTML scraping of press room |
| [#40](https://github.com/ericlow/Health-Insurance-News-Agent/pull/40) | AGE-92 | `ericlow/age-92-hoag-sitemap-monitor` | Hoag Health — sitemap-based (replaced Google News RSS) |

For each: validate → merge → mark Linear Done → confirm GH Actions deploy → trigger Lambda → verify Discord health check.

### City of Hope (AGE-93) — closed as unsupported

Fully Cloudflare-blocked on all endpoints (robots.txt, sitemap, newsroom listing). PR #39 closed, AGE-93 Canceled in Linear.

### Lambda schedule — 1am run removal (Eric's action)

Eric is deleting the 1am EventBridge rule manually in AWS Console. IAM user `github-actions-deploy` lacks `events:*` permissions.
- EventBridge → Rules → us-west-1 → find the 1am cron rule → Delete
- 1am PT = cron(0 8 * * ? *) or cron(0 9 * * ? *) depending on DST
- Leave 7am, 1pm, and 4th run untouched

### CLAUDE.md has uncommitted changes

`CLAUDE.md` shows as modified on main — check `git diff CLAUDE.md` to see if it needs committing.

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

## What was completed in this session (2026-08-23)

- ✓ Replaced Hoag Google News RSS monitor (PR #38 closed) with sitemap-based monitor
  - `agent/hoag_monitor.py`: parses `hoag.org/sitemap.xml`, filters `/articles/` with lastmod within 30 days, fetches article pages for h1 title + `div.rich-text` body paragraphs
  - 16 articles inserted in smoke test (PKs 903–918), includes both press releases and consumer health content (triage LLM filters the latter)
  - PR #40 open, AGE-92 In Review
- ✓ Closed PR #39 (City of Hope Google News RSS), AGE-93 Canceled in Linear
- ✓ `/new-source` skill updated to prohibit Google News RSS and add sitemap/robots.txt/embedded JSON approaches
- ✓ Updated `docs/working-session.md`

## Key technical notes for Hoag monitor

- Sitemap has 974 `/articles/` URLs total; 30-day lastmod filter gives ~16/run
- July 2026 spike (186 articles on 2026-07-23) = bulk content import, not genuine publications — 30-day filter naturally avoids it
- Article pages are fully SSR'd (Astro): h1 has clean title, `div.rich-text` has body paragraphs only (no nav/footer noise)
- Consumer health content (recipes, symptom guides) will pass through to triage LLM which should filter them out

---

## Key facts

- **Lambda**: `health-insurance-monitor`, region `us-west-1`
- **Databases**: Neon (production, `DATABASE_URL`), Docker Postgres (local, `DATABASE_URL_LOCAL`) — smoke tests always use `DATABASE_URL_LOCAL`
- **IAM user** `github-actions-deploy`: has Lambda + CloudWatch read access; lacks EventBridge permissions
- **Confidence flagging**: Eric asked for [HIGH]/[MED]/[LOW] on claims in conversation

---

_Last updated: 2026-08-23 — Claude working session_
