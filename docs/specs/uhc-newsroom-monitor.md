# UHC Newsroom Monitor — Feature Spec

_Status: on hold — spec complete, not yet scheduled_
_Last updated: 2026-07-17_
_Linear: [AGE-66](https://linear.app/eric-projects/issue/AGE-66/add-uhc-newsroom-monitor-insurer-newsroom)_

---

## Background

UnitedHealthcare's newsroom (`uhc.com/news-articles/newsroom`) publishes press releases on prior authorization changes, network initiatives, and partnership announcements directly from one of the largest U.S. health insurers. These are high-signal for the types of events the system is designed to catch.

The newsroom listing page is JS-rendered and requires Playwright. Article pages respond fine to plain `requests`.

No RSS feed is available.

---

## What we're building

A monitor that:
1. Uses Playwright to render `https://www.uhc.com/news-articles/newsroom`, extracts article links from the `/news-articles/newsroom/` path
2. Fetches each new article page with plain `requests`
3. Saves to the database

---

## User Story

As an industry analyst, I want the system to monitor UHC's newsroom so that I catch press releases about prior authorization changes, network initiatives, and insurer policy announcements directly from the source.

---

## Acceptance Criteria

1. Given the newsroom at `https://www.uhc.com/news-articles/newsroom`, the monitor renders the page with Playwright and extracts all links whose path matches `/news-articles/newsroom/<slug>` (depth-3 URLs, excluding the `/news-articles/newsroom` category root)
2. Article URLs already in the database are skipped before any article page is fetched
3. For each new article, the page is fetched with plain `requests` and parsed for title, date, and body
4. Articles are saved with: `url`, `title`, `body_text`, `published_at`, `source` (`uhc.com`), `category` (`newsroom`), `tags` (null), `first_seen_at`, `scrape_run_id`
5. A `scrape_runs` row is opened at start and closed with counts

---

## Research findings (2026-07-17)

**Listing page inspection (Playwright-rendered DOM):**
- The page renders ~17 articles total across all categories (Newsroom, Medicare articles, Healthy living, etc.)
- Newsroom-category articles use path `/news-articles/newsroom/<slug>` — reliably filterable by URL pattern
- Article title + link: `div.flex-row-detail.h3 a` — `href` attribute (relative) and `innerText` (title)
- Category label per card: `a.categoryLink` — text is "Newsroom", "Medicare articles", etc.
- No dates on the listing page
- No visible pagination — curated set of ~17 articles with a "Latest articles" carousel at bottom
- The "Latest articles" horizontal scroll at bottom contains the same articles in a different layout

**Article page inspection (plain `requests`, confirmed working):**
- Status 200 to plain `requests` — no Playwright needed for article pages
- Title: `h1` — present and matches the title shown on listing cards
- Date: `<script type="application/ld+json">` where `@type == "NewsArticle"` → `datePublished` field (ISO 8601, e.g. `"2026-05-29T01:00:00Z"`)
- Body: `main p` — 17 paragraphs for the tested press release; concatenated for `body_text`
- No `keywords` field in JSON-LD → `tags` stored as `null`

**Example article verified:** `https://www.uhc.com/news-articles/newsroom/pediatric-prior-authorization-announcement`

---

## Out of Scope

- Non-newsroom articles (Medicare articles, Healthy living, Benefits & coverage categories)
- Pagination (not observed; revisit if the page gains a "load more" control)
- Tags extraction (not available)

---

## Decisions

| Question | Decision |
|---|---|
| Listing page fetch | Playwright (CDP session — JS rendering required) |
| Article page fetch | Plain `requests` (status 200, full content in HTML) |
| Article URL filter | `href` matches `/news-articles/newsroom/` AND path depth == 3 (has a slug beyond the category root) |
| `url` field | Absolute URL: `https://www.uhc.com` + relative href |
| `source` field | `uhc.com` |
| `category` field | `newsroom` |
| `tags` field | `null` |
| Title selector | `h1` |
| Date selector | JSON-LD `<script type="application/ld+json">` with `@type == "NewsArticle"` → `datePublished` |
| Body selector | `main p` elements, concatenated |
| Dedup key | Article URL |
| Playwright session | Reuse same CDP session pattern as Becker's backfill |

---

## Selectors

### Listing page (rendered DOM via Playwright)

| Field | Selector / notes |
|---|---|
| All article title links | `div.flex-row-detail.h3 a` — href + innerText |
| Newsroom-only filter | Keep only hrefs where `path.startsWith('/news-articles/newsroom/')` AND path has a slug (depth 3) |

### Article page (plain `requests` + BeautifulSoup)

| Field | Selector / source |
|---|---|
| Title | `h1` |
| Published date | `script[type="application/ld+json"]` with `@type == "NewsArticle"` → `datePublished` (ISO 8601) |
| Body | All `main p` elements, `.get_text(strip=True)` joined with `\n` |
| Tags | `null` |
| Category | `newsroom` (hardcoded) |

---

## Behavioral specs

### Listing page

- The newsroom page is loaded via Playwright (CDP session required)
- After JS rendering, all `div.flex-row-detail.h3 a` elements are collected
- Only hrefs whose path starts with `/news-articles/newsroom/` and has a slug segment are kept
- The canonical URL is `https://www.uhc.com` + relative href
- URLs already in the `articles` table are skipped before any article page is fetched

### Article page

- Each new article URL is fetched with plain `requests`
- Title is taken from `h1`
- Date is taken from the `NewsArticle` JSON-LD block's `datePublished` field; stored as `null` if absent or unparseable
- Body is all `main p` elements joined with `\n`; entry is skipped if body is empty
- `source` is `uhc.com`, `category` is `newsroom`, `tags` is `null`

### Run tracking

- A `scrape_runs` row is opened at start with `status = 'running'` and source `uhc.com`
- On completion: status `'completed'`, `articles_found` (total newsroom links found) and `articles_new` (inserted) recorded
- On unhandled exception: status `'failed'`, error message recorded

```gherkin
Scenario: Newsroom articles are extracted and saved
  Given the rendered listing page contains 10 links matching /news-articles/newsroom/<slug>
  And none of the URLs are in the articles table
  When run_monitor is called
  Then all 10 article pages are fetched with requests
  And all 10 are saved to the database

Scenario: Non-newsroom articles are excluded
  Given the rendered listing page contains 17 total links
  And 7 links are to /news-articles/medicare-articles/ or /news-articles/healthy-living/
  When run_monitor is called
  Then the 7 non-newsroom links are not fetched or inserted

Scenario: Already-seen articles are skipped
  Given the rendered listing page contains 10 newsroom links
  And 8 of those URLs are already in the articles table
  When run_monitor is called
  Then only 2 article pages are fetched
  And articles_new is recorded as 2

Scenario: Article with no body text is skipped
  Given a candidate newsroom URL is not yet in the database
  And fetching that URL returns a page with no <p> tags in <main>
  When run_monitor processes that URL
  Then the article is not inserted
  And no error is raised

Scenario: Run is marked failed on unhandled exception
  Given the Playwright listing page load raises an exception
  When run_monitor is called
  Then the scrape_runs row is updated to status 'failed'
  And the error message is recorded
```
