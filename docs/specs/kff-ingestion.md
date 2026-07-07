# KFF Health News Ingestion — Feature Spec

_Status: ready for implementation_
_Last updated: 2026-07-05_

---

## Background

KFF Health News is a standard industry resource that health insurance professionals use to monitor financial events and developments across the industry. Unlike Becker's (the project's first ingestion source), KFF provides broad industry-wide coverage, making it better suited for building a representative prompt-tuning dataset. The California listing page is the starting point because the domain expert's current focus is California coverage.

---

## What we're building

Add KFF Health News (`kffhealthnews.org`) as a second ingestion source for Phase 1 backfill. Initial run: 3 pages (60 articles) from the California state listing page. No date cutoff — paginate by page count only.

---

## User Story

As a data scientist, I want to pull articles from KFF Health News California coverage so that I have a database of articles to tune my LLM prompts.

## Acceptance Criteria

1. Given the URL `https://kffhealthnews.org/state/california/`, the backfill should pull articles from the listing pages
2. Parse 3 pages worth of articles (60 articles)
3. For each article retrieved, save it to the database
4. Articles in the database should have all fields from the existing schema: `url`, `title`, `published_at`, `body_text`, `source`, `category`, `tags`, `first_seen_at`, `scrape_run_id`

---

## Research findings (2026-06-26)

- **Listing page:** `https://kffhealthnews.org/state/california/`
- **Total articles available:** 1,934 across 97 pages (20 per page)
- **Cloudflare:** None. Both listing pages and article pages respond to plain `requests` with status 200. No CDP or headed Chrome needed.
- **Spanish sidebar:** `<aside class="term-sidebar">` contains 5 Spanish-language articles per page. Excluded by selecting `article:not(aside *)`.
- **Pagination:** `/page/2/`, `/page/3/`, etc. Next page link: `a.next.page-numbers`.
- **Date format:** `<time datetime="2026-06-18T00:00:00+00:00">` — ISO 8601 in the `datetime` attribute. No text parsing needed.

---

## Out of Scope

- Date-based filtering — articles are not filtered by publish date; backfill stops by page count only
- Listing pages other than `/state/california/` — other states, topics, or KFF sections are excluded
- Ongoing monitoring — this is a one-time backfill, not a recurring scrape
- Article dedup beyond URL match — no content-similarity dedup

---

## Decisions

| Question | Decision |
|---|---|
| Listing pages | `/state/california/` only for now |
| Page limit | 3 pages (60 articles) — no date cutoff |
| `source` field | `kffhealthnews.org` |
| `category` field | First path segment of article URL (e.g. `mental-health` from `.../mental-health/article-slug/`) |
| `tags` field | JSON-LD `keywords` array from article page (confirmed present); fall back to `null` if absent |
| Ongoing monitoring | Out of scope — backfill only |
| Article body selector | `main p` — locked in |

---

## Selectors

### Listing page (`/state/california/`, `/state/california/page/2/`, etc.)

| Field | Selector |
|---|---|
| Article container | `article:not(aside *)` |
| Title | `h2` inside article container |
| URL | first `a[href]` inside article container |
| Date | `time[datetime]` attribute (ISO 8601) |

### Article page

| Field | Selector / source |
|---|---|
| Title | `h1` |
| Date | `time[datetime]` attribute |
| Body | `main p` elements, concatenated |
| Tags | JSON-LD `keywords` from `<script type="application/ld+json">`, `@type: Article` node |
| Category | First path segment of the article URL |

---

## Behavioral specs

### Listing page

- KFF listing pages are fetched with plain `requests` — no CDP session required
- Only `article:not(aside *)` elements are parsed — Spanish sidebar articles inside `aside.term-sidebar` are excluded
- Each article entry exposes a URL, title, and date
- The publish date is read from the `time[datetime]` attribute (ISO 8601)
- Pagination follows `/page/2/`, `/page/3/`, etc. and stops after 3 pages
- URLs already in the `articles` table are skipped before any article page fetch

### Article page

- Article pages are fetched with plain `requests` — no CDP session required
- Body text is extracted from all `main p` elements, concatenated, stripped of leading/trailing whitespace
- Title is extracted from `h1`
- Date is taken from the `time[datetime]` attribute
- Tags are extracted from the `keywords` field of the `Article` node in the JSON-LD block; `null` if the field is absent
- Category is the first path segment of the article URL (e.g. `mental-health` from `https://kffhealthnews.org/mental-health/article-slug/`)

### Source identity

- `source` is set to `kffhealthnews.org` for all KFF articles
- `scrape_run_id` is recorded on every inserted article
- Dedup: an article whose URL is already in `articles` is skipped — its page is never fetched

### run_backfill

```gherkin
Scenario: Backfill saves articles from all pages when last page has no next_url
  Given page 1 has articles and a next_url pointing to page 2
  And page 2 has articles and a next_url pointing to page 3
  And page 3 has articles and no next_url
  When run_backfill is called with page_limit=3
  Then articles from pages 1, 2, and 3 are all saved to the database

Scenario: Backfill stops at page limit even when next_url exists
  Given pages 1, 2, and 3 each have articles and a next_url pointing to the next page
  When run_backfill is called with page_limit=3
  Then articles from pages 1, 2, and 3 are saved to the database
  And page 4's articles are not saved to the database

Scenario: Backfill stops early when pages run out before the limit
  Given page 1 has articles and a next_url pointing to page 2
  And page 2 has articles and no next_url
  When run_backfill is called with page_limit=3
  Then articles from pages 1 and 2 are saved to the database
  And page 3's articles are not saved to the database
```
