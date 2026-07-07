# Dev Log

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
