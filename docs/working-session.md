# Working Session — 2026-08-23

---

## Outstanding work — pick up here next session

### What's running in production (all merged and deployed)

| Source | Approach |
|---|---|
| Becker's Payer | RSS |
| KFF Health News | RSS |
| Cigna Newsroom | RSS |
| Sutter Health | RSS |
| UC Davis Health | RSS |
| UCSD Health | HTML scraping |
| UCI Health | HTML scraping |
| UCLA Health | HTML scraping |
| UCSF | HTML scraping |
| Sharp Health | HTML scraping |
| Scripps Health | HTML scraping |
| Providence CA | HTML scraping |
| Hoag Health | Sitemap (AGE-92) |
| John Muir Health | HTML scraping (AGE-91) |

### Lambda schedule — 1am run removal (Eric's action, still pending)

Eric is deleting the 1am EventBridge rule manually in AWS Console. IAM user `github-actions-deploy` lacks `events:*` permissions.
- EventBridge → Rules → us-west-1 → find the 1am cron rule → Delete
- 1am PT = cron(0 8 * * ? *) or cron(0 9 * * ? *) depending on DST
- Leave 7am, 1pm, and 4th run untouched

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

- ✓ AGE-92: Hoag Health — sitemap-based monitor, PR #40 + hotfix #41 merged, verified in Discord
- ✓ AGE-91: John Muir Health — HTML scraping with date parsing from `span.date`; PR #37 merged; verified in Discord
- ✓ AGE-93: City of Hope — closed as unsupported (Cloudflare-blocked); PR #39 closed, Linear Canceled
- ✓ `/new-source` skill updated: prohibits Google News RSS, adds sitemap/robots.txt/embedded JSON approaches

---

## Key facts

- **Lambda**: `health-insurance-monitor`, region `us-west-1`
- **Databases**: Neon (production, `DATABASE_URL`), Docker Postgres (local, `DATABASE_URL_LOCAL`) — smoke tests always use `DATABASE_URL_LOCAL`
- **IAM user** `github-actions-deploy`: has Lambda + CloudWatch read access; lacks EventBridge permissions
- **Confidence flagging**: Eric asked for [HIGH]/[MED]/[LOW] on claims in conversation

---

_Last updated: 2026-08-23 — session complete_
