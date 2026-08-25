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
- [ ] A1 spec review (`docs/specs/2026-07-19-event-tracking-agent-a1.md`) — Eric to read and approve
- [ ] A2 spec — write `docs/specs/2026-08-25-analysis-agent-a2.md`
- [ ] AWS migration spec — write `docs/specs/2026-07-26-aws-migration.md`
- [ ] Update TDD (`docs/technical-design.md`) — reflect Lambda, Neon, EventBridge, API Gateway, A1, A2
- [ ] Update PRD (`docs/prd.md`) — reflect A1 and A2 as new product capabilities
- [ ] Merge AGE-70 PR and close issue

---

## Analysis Agent design — in progress (2026-08-23)

Design conversation on the on-demand analysis agent (A2). Not yet spec'd or implemented.

### Trigger
Matt requests analysis via Discord: e.g. "analyze SCAN/Costco partnership impact on Anthem Medicare."

### Two-phase workflow
1. **Research phase** — agent searches for related news (our article DB first, then web) to build situational context, the way Matt would Google News. Fills gaps the triggering article leaves open.
2. **Analysis phase** — once picture is clear, pulls primary structured data, models impact, posts findings with per-claim citations and confidence levels.

### Tools identified
- `search_news(query)` — searches local article DB + web for context on entities/event
- `fetch_page(url)` — plain web fetch for press releases, trade press (wraps existing http_utils)
- `download_and_parse(url)` — downloads and parses structured files (XLSX, PDF); produces HIGH-confidence claims
- `get_enrollment_by_region(region, year)` — Covered CA Active Member Profile; returns carrier enrollment by rating region
- `get_sb260_default_carrier(county, year)` — reads Covered CA SB-260 county table; returns who holds the auto-enrollment default slot
- `get_ra_transfers(state, year)` — CMS Appendix C; returns issuer-level RA payer/receiver positions
- `lookup_regulatory_rules(member_flow_type)` — searches curated rules layer for standing mechanisms governing the relevant member flow

### Rules layer
A curated markdown knowledge base (`docs/regulatory-rules.md` — not yet created) of standing regulatory mechanisms that govern member flows. These don't appear in news or data:
- Auto-enrollment statutes (SB 260, crosswalk rules)
- Benchmark Silver mechanics (how APTC pegs)
- RA program design
- Medicare Advantage marketing rules, CMS approval process
- Medi-Cal eligibility transition rules
Agent always calls `lookup_regulatory_rules` as first step before pulling data. Matt seeds and maintains this layer.

### Why each decision was made

- **Two-phase (research then analysis):** Matt said his first step on the SCAN/Costco article would be to "google news and try to understand the situation." He doesn't jump to structured analysis — he builds context first. The agent replicates that.
- **Rules layer:** In AGE-71, the agent missed SB 260 entirely because it only retrieved news and data — standing regulatory mechanisms (a 2019 statute) generate no 2026 headlines and aren't in any dataset. Matt caught it immediately. The rules layer is a hard requirement so this class of miss doesn't recur. See `docs/analysis/age-71-caloptima-oc.md` §0 for the full post-mortem.
- **`lookup_regulatory_rules` as forced first step:** The SB 260 error happened because no step in the analysis plan asked "which standing rules govern this member flow?" Making it mandatory prevents the same structural omission.
- **Matt as critic in v1:** Matt caught the SB 260 miss, validated membership figures against his own knowledge, and had the CalOptima CFO's number. He's a better critic than any automated layer we could build now. Defer the automated critic until v1 proves the analysis quality.
- **`download_and_parse` as core tool:** AGE-71's HIGH-confidence claims all came from files Claude downloaded and parsed directly (Covered CA XLSX, CMS XLSX). Web-fetched content was MEDIUM at best. The distinction matters for credibility.
- **Search our DB first:** We're already collecting from 14 newsroom sources. Before hitting the web, the agent should check what we've already scraped about the entities involved.

### Source documents (read these to understand the design)
- `docs/AGE-71 — CalOptima OC Entry Analysis - Discord conversation.txt` — primary evidence for Matt's workflow, what he caught, how he thinks, and what his customers actually want (personnel changes, not financial modeling)
- `docs/analysis/age-71-caloptima-oc.md` — full analysis with §0 SB 260 post-mortem and Postscript (A2 requirements already written out there)
- `docs/A look inside the expanded partnership between SCAN and Costco.txt` — second test case article; SCAN/Costco Medicare Advantage partnership, Fierce Healthcare (paywalled, saved locally)

### Critic layer
Deferred — Matt acts as critic in v1. Agent posts findings, Matt validates.

### Data sources
- Covered CA (Active Member Profile XLSX, SB-260 county table PDF, rate announcements)
- CMS (RA transfer summary PDF, Appendix C XLSX, MA enrollment by plan/county)
- Trade press (Becker's, CalMatters, ACA Signups, Fierce Healthcare)
- Costco membership demographics (public: ~76M US households, skews Medicare-eligible)

### Pre-cache vs. fetch on demand
Undecided. AGE-71 fetched live and worked; added latency and bot-block risk. Covered CA enrollment updates monthly — cron pull is an option.

### Test cases
- AGE-71: CalOptima entering OC Covered CA market (completed manually; template for agent)
- SCAN/Costco Medicare Advantage partnership (new; article saved to docs/)

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
