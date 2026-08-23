# Working Session — 2026-08-22

---

## Outstanding work — pick up here next session

### PRs awaiting Eric's validation (open as of end of session)

| PR | Issue | Branch | What it does |
|---|---|---|---|
| [#37](https://github.com/ericlow/Health-Insurance-News-Agent/pull/37) | AGE-91 | `ericlow/age-91-john-muir-health-newsroom-monitor` | John Muir Health — HTML scraping of press room |
| [#38](https://github.com/ericlow/Health-Insurance-News-Agent/pull/38) | AGE-92 | `ericlow/age-92-hoag-health-newsroom-monitor` | Hoag Health — Google News RSS |
| [#39](https://github.com/ericlow/Health-Insurance-News-Agent/pull/39) | AGE-93 | `ericlow/age-93-city-of-hope-newsroom-monitor` | City of Hope — Google News RSS |

For each: validate → merge → mark Linear Done → confirm GH Actions deploy → trigger Lambda → verify Discord health check.

### Notes on Google News monitors (AGE-92, AGE-93)

Hoag and City of Hope newsrooms can't be scraped directly (Astro SPA / Cloudflare). Google News RSS is the approach — it returns 10 recent articles per query. **Known limitation**: Google News article URLs use JS redirects; no HTTP-resolvable canonical URL exists. Body text is set to the article title so triage has signal to work with. Dedup key is the Google-wrapped URL (stable per article).

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

## What was completed in this session (2026-08-22)

- ✓ Validated and marked Done: AGE-77 (UCI Health), AGE-78 (UCLA Health), AGE-79 (UCSD — rewrote to fix source URL), AGE-80 (UCSF), AGE-81 (Sharp), AGE-82 (Scripps), AGE-86 (Providence CA)
- ✓ Fixed UCSD monitor: was pointing at general university RSS; rewrote to HTML scrape `health.ucsd.edu/news/press-releases/`
- ✓ Created and updated `/new-source` skill at `.claude/skills/new-source/SKILL.md`
  - Added bot protection check (Step 1)
  - Added explicit validation: print all titles from listing, confirm DB records with PKs (Step 6)
- ✓ AGE-91: John Muir Health — HTML scraping, PR #37 open, In Review
- ✓ AGE-92: Hoag Health — Google News RSS, PR #38 open, In Review
- ✓ AGE-93: City of Hope — Google News RSS, PR #39 open, In Review
- ✓ Confirmed PR Newswire has no company-specific RSS feeds; Google News is the workable alternative

---

## Key facts

- **Lambda**: `health-insurance-monitor`, region `us-west-1`
- **Databases**: Neon (production, `DATABASE_URL`), Docker Postgres (local, `DATABASE_URL_LOCAL`) — smoke tests always use `DATABASE_URL_LOCAL`
- **IAM user** `github-actions-deploy`: has Lambda + CloudWatch read access; lacks EventBridge permissions
- **Confidence flagging**: Eric asked for [HIGH]/[MED]/[LOW] on claims in conversation

---

_Last updated: 2026-08-22 overnight — Claude working session_
