# Dev Log

---

## 2026-07-10 — Session 6

### Four PRs merged — triage overhaul and operational visibility

**AGE-51** (PR #10): Health check Discord notification after each scraper run. Posts `[Becker's Payer](url) N new articles — HH:MM AM PDT` to a dedicated health check channel (`DISCORD_HEALTH_CHECK_WEBHOOK_URL`) after each source scrapes. Timestamps in America/Los_Angeles. 3-attempt retry with exponential backoff; never raises. PR template (`.github/pull_request_template.md`) and PR format documented in CLAUDE.md also added in this PR.

**AGE-52** (PR #11): Two-stage triage with updated prompts. Title screened first — articles returning `no` skipped without article API call. Both prompts updated with target states (CA, NV, CO, MO, WI, NY, NJ), national vs. state scope classification, and 16 numbered signal categories (ACA, MFA/single-payer, mergers, network exits, GLP-1, labor unions, mental health mandates, Cigna/UC Health, etc.). New `triage_results` columns: `confidence` (1–5), `scope`, `reason`.

**AGE-53** (PR #12): Health check message now shows a clickable Discord hyperlink `[Becker's Payer](https://www.beckerspayer.com/feed/)` instead of a plain source name.

**AGE-54** (PR #13): Every article now gets a `triage_results` row regardless of outcome — including articles previously dropped silently at the title stage. Schema renamed existing columns with `article_` prefix and added `title_flag`, `title_confidence`, `title_scope`, `title_reason`. `article_flag` is now nullable (NULL = never reached article eval). Full decision trail now queryable.

### Braintrust — PermissiveRecall scorer

Discussed and defined a permissive scorer for the Braintrust triage eval:
- Expected `yes`: `yes` or `uncertain` → pass (don't miss real signals)
- Expected `no`: anything → pass (false alarms are acceptable, analyst reviews)

Only fails when expected is `yes` and model returns `no`. User is implementing this in Braintrust alongside AGE-48/49/50 (prompt iteration).

### PR format standardised

All PRs now follow: **Summary** (1–2 sentences + Linear link) → **Changes** (detail bullets) → **Test plan** (checklist). Documented in CLAUDE.md and `.github/pull_request_template.md`.

---

## 2026-07-09 — Session 5

### Pipeline running on launchd (hourly, macOS)

Registered the scheduler as a launchd agent so it runs automatically every hour without manual intervention. Survives reboots and fires on wake if the machine was asleep at the scheduled time (unlike cron).

**Plist location:** `~/Library/LaunchAgents/com.ericlow.health-insurance-monitor.plist`
**Log:** `tail -f /tmp/health-insurance-monitor.log`
**Test fire:** `launchctl start com.ericlow.health-insurance-monitor`
**Stop:** `launchctl unload ~/Library/LaunchAgents/com.ericlow.health-insurance-monitor.plist`

### Other changes this session

- **AGE-42** (PR #8): README developer setup guide — 6-step install, cron/launchd section, tests section; `.env.example` updated with `DISCORD_WEBHOOK_URL` and placeholder password; `CLAUDE.md` updated with two-call tmux protocol, dollar-sign warning, and git worktree guidance
- **AGE-43** (PR #9, merged): `scrape_runs.source` now stores the actual RSS feed URL (e.g. `https://www.beckerspayer.com/feed/`) instead of a domain label, so runs are directly verifiable
- **Discord fix** (included in AGE-42): sends one POST per briefing to stay under Discord's 2000-character limit
- **Tmux protocol fix**: two `send-keys` calls required (message + blank Enter); dollar signs must be avoided in messages (shell interprets them)

---

## 2026-07-08 — Session 4

### Phase 3 complete — full monitor pipeline implemented and merged

All five Phase 3 issues (AGE-37 through AGE-41) implemented by a multi-agent pair (worker-1 + worker-2) and merged to main as individual PRs.

**What was built:**

| Issue | File | What it does |
|-------|------|-------------|
| AGE-37 | `db/schema.sql`, `agent/scraper.py`, `agent/kff_monitor.py` | Schema migration (triage_results + briefings tables); Becker's + KFF RSS monitors returning new article IDs |
| AGE-38 | `agent/triage.py` | Calls Claude Haiku with v1 prompt; writes flag + 2-sentence summary to triage_results; returns yes/uncertain IDs |
| AGE-39 | `agent/summarizer.py` | Calls Claude Sonnet for flagged articles; writes 4-field structured brief to briefings |
| AGE-40 | `agent/discord.py` | Formats unsent briefings, POSTs to Discord webhook, sets discord_sent_at on success |
| AGE-41 | `scheduler.py` | Orchestrator — runs full pipeline in sequence; entry point for hourly cron |

**To run the pipeline manually:**
```bash
source .venv/bin/activate
python -m scheduler
```

**Cron entry (hourly):**
```
0 * * * * cd /path/to/app && .venv/bin/python -m scheduler >> /var/log/monitor.log 2>&1
```

**Environment variables required:** `DATABASE_URL`, `ANTHROPIC_API_KEY`, `DISCORD_WEBHOOK_URL`

**Test count:** 82 tests passing across all modules.

---

### Multi-agent protocol updates

- Established spy-N / worker-N pair naming for parallel agent sessions
- Corrected `tmux send-keys` to single-call form: `tmux send-keys -t <target> "[sender] message" Enter`
- Clarified coordination boundaries: worker agents do not relay cross-pair messages — that's the spy's responsibility

---

## 2026-07-07 — Session 3

### AGE-8 deferred — manual triage serves as adequate prompt for now

AGE-8 (Phase 2 data collection: Braintrust setup, hand-labeling, dataset load) is on hold. The manual triage pass over all 211 articles produced a working classification rubric and an adequate triage prompt. Formal Braintrust evaluation setup deferred until there is a clear need to iterate beyond the current prompt quality.

**Output preserved:** `/tmp/articles_for_labeling_2000.csv` — 211 articles with `llm_flag` (yes/uncertain/no), 2000-char body preview, and 2-sentence summaries for flagged articles. Ready to resume Braintrust setup if needed later.

---

### Phase 2: Article triage experiment — 200-char vs 2000-char body preview

**Context:** 211 articles in DB (Becker's Payer + KFF Health News). Goal is to build a triage prompt that replicates domain expert judgment (<10% hit rate expected). Before labeling, ran a manual triage pass to pre-filter articles for expert review.

**Experiment:** Triaged all 211 articles twice — once with the first 200 chars of body text visible, once with 2000 chars — to measure whether preview length changes classification outcomes.

**Results:**
- Both runs produced the same 11 `yes` articles (all Becker's Payer contract disputes/agreements — the relationship change is always stated in the headline and opening sentence)
- 200-char run flagged 8 `uncertain` articles; 2000-char run flagged only 2
- 6 articles were downgraded from `uncertain → no` with more context:
  - *Cheaper Alternative Health Plans Are Having a Moment* — market dynamics, not a specific deal
  - *Eroding ACA Enrollment Portends Higher Insurance Rates* — enrollment trend, not a relationship change
  - *Big Companies Position Themselves for $50B Rural Health Fund* — federal contracting competition
  - *Red and Blue States Alike Want To Limit AI in Insurance* — regulatory policy
  - *Complaints About Gaps in Medicare Advantage Networks Are Common* — systemic enforcement story, no specific split
  - *Blockbuster Deal Will Wipe Out $30 Billion in Medical Debt* — nonprofit/debt collector deal, not insurer-provider

**Key insight:** 200 chars is sufficient to identify clear hits (relationship changes are stated immediately). It is *not* sufficient to confidently rule out borderline cases — those require ~2000 chars. The false positive risk is concentrated in the `uncertain` band, not the `yes` band.

**Decision:** Use 2000-char body preview as the standard for triage prompts going forward. 200 chars may still be useful as a fast first-pass filter if latency/cost is a concern, but uncertain calls should always be resolved with more context.

**Output:** `/tmp/articles_for_labeling_2000.csv` — all 211 articles with `llm_flag` column (yes/uncertain/no), sorted flags-first, ready for domain expert labeling in Google Sheets.

---

## 2026-06-21 — Session 2

### beckerspayer.com added as v1 source

Investigating how the Cigna/UC Health network dispute story would be discovered surfaced `beckerspayer.com` — a Becker's Healthcare publication focused specifically on health insurance payers (contracting, network changes, M&A). Distinct from `beckershospitalreview.com` investigated last session.

Key findings:
- `beckerspayer.com/feed/` is open — no Cloudflare block, returns full article HTML in `content:encoded`. No Playwright required.
- `/contracting/feed/` category feed is blocked (403), but the main feed covers all categories; triage LLM handles relevance filtering.
- `?paged=N` pagination is blocked — no historical backfill possible. Ongoing monitoring is fine since 8-hour schedule catches articles before they scroll off the default feed window.
- Article body lives in `content:encoded` in the feed itself — no second HTTP request needed per article.

**Decision:** Added to v1. Cigna newsroom dropped from v1 — trade press is broader and more discovery-oriented; carrier newsrooms moved to future sources. PRD and TDD updated.

---

## 2026-06-20 — Session 1

### What was built (Phase 1 complete)

- `requirements.txt`, `config.py`, `.env`, `.env.example`
- `db/schema.sql` — `scrape_runs` + `articles` tables in PostgreSQL (`health_insurance_news` DB)
- `db/connection.py` — psycopg2 connection pool
- `db/init_db.py` — creates the DB and applies schema (run once)
- `agent/scraper.py` — scrapes Cigna newsroom, deduplicates, fetches article bodies, logs to `scrape_runs`

To run:
```bash
source .venv/bin/activate
PYTHONPATH=. python3 agent/scraper.py           # regular monitor run (10 most recent)
PYTHONPATH=. python3 agent/scraper.py backfill  # full historical backfill
PYTHONPATH=. python3 db/init_db.py              # first-time DB setup only
```

---

### Cigna newsroom (newsroom.cigna.com) — scraping findings

- **No Playwright needed** — site is static HTML, plain `requests` + `BeautifulSoup` works
- **RSS feed** (`/latest-press-releases?pagetemplate=rss`) — only 5 items, hard-capped, no params change it. Not used.
- **HTML listing** (`/latest-press-releases`) — 10 items per page
- **Pagination**: `?o=10`, `?o=20`, etc. (offset param). 16 pages total = **153 articles** spanning 2019–2026
- **Year filter**: `?year=YYYY` works but only returns 10 per year — not useful for backfill vs. offset pagination
- **Category filter** (discovered but not yet used in scraper):
  - `?category=776` — Business & Financial
  - `?category=773` — Partnerships
  - `?category=779` — Products & Services
  - `?category=774` — Leadership Announcements
  - `?category=775` — Community Engagement
- **Article body selector**: `.wd_body`
- **Article date selector**: `.wd_date`
- **DB state**: 153 articles loaded as of end of session

### Cigna newsroom — "dark" dispute pages (important discovery)

`newsroom.cigna.com/uc-health` is a standalone page Cigna created for active contract negotiations with UC Health (University of California Health):
- **Deadline: July 1, 2026** — UC Health goes out of network if no deal
- Issue: UC Health seeking significant reimbursement increases
- Body class: `wd_pageid_34200` — unique CMS page ID, not queryable
- **Not discoverable** via press release listing, homepage, sitemap (no sitemap exists), or any CMS API
- These "What You Need to Know" pages appear to be Cigna's standard template for active network disputes
- `wd_pageid_` is a CSS class only — `wd_id=` URL param does not route to pages
- `/all-stories` listing contains editorial/blog content only, not dispute pages
- **Open question**: how to discover these pages. Best option identified: web search API for `site:newsroom.cigna.com "what you need to know"`. Deferred — no decision yet.

---

### Becker's Hospital Review (beckershospitalreview.com/finance/) — investigation

**Open question: add as v1 source or v2?**

Findings:
- **Behind Cloudflare bot protection** — plain HTTP requests get 403. Only works in a real browser. **Playwright required.**
- **RSS feed**: `beckershospitalreview.com/finance/feed/` — works in browser, 10 items per page
- **RSS pagination**: `?paged=N` — goes back years:

| RSS Page | Oldest Article Date |
|----------|-------------------|
| 1 | Jun 19, 2026 |
| 100 | Dec 18, 2025 |
| 200 | Mar 21, 2025 |
| 500 | Aug 24, 2023 |
| 750 | Oct 4, 2022 |
| 1,000 | Dec 29, 2020 |
| 1,200 | Nov 7, 2019 |
| 1,500 | Sep 24, 2018 |

- For 5-year backfill (back to 2021): ~pages 1–1,000 = ~10,000 articles
- HTML listing also paginates: `/finance/page/N/` works
- Article body structure: not yet inspected (need to do before building scraper)

**Open decisions before building Becker's scraper:**
1. v1 or v2 source?
2. How far back for the initial backfill? (Full 5 years = ~10k articles)
3. Playwright adds back to the stack — update TDD before building

---

### TDD changes made this session

- Dropped Playwright in favor of `requests` + `BeautifulSoup` + `feedparser` (Cigna is static HTML)
- Then dropped `feedparser` in favor of HTML listing scraping (RSS only returned 5 items)
- Category filter documented but not yet wired into scraper
- Becker's will re-introduce Playwright if added as a source
