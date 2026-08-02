# Stanford Medicine News Monitor — Feature Spec

_Status: ready for implementation_
_Last updated: 2026-07-17_
_Linear: [AGE-65](https://linear.app/eric-projects/issue/AGE-65/add-stanford-medicine-news-monitor-provider-newsroom)_

---

## Background

Stanford Medicine's news center (`med.stanford.edu/news/`) publishes announcements from Stanford Health Care and affiliated institutions — exactly the type of provider-side story the system needs to catch. The example story that triggered this issue (Stanford Health Care + St. Rose Hospital collaboration, April 2026) demonstrates the value: a major network partnership announced on a provider newsroom, not picked up quickly by trade press.

There is no RSS feed. The listing page is AEM-based and JS-rendered. Article pages respond successfully to plain `requests`.

---

## What we're building

A monitor/backfill that:
1. Uses Playwright to render `https://med.stanford.edu/news/all-news.html`, extracts article links
2. Fetches each new article page with plain `requests`
3. Saves to the database

---

## User Story

As an industry analyst, I want the system to monitor Stanford Medicine's news center so that I catch major provider partnership and network announcements from one of California's largest health systems.

---

## Acceptance Criteria

1. Given the listing page at `https://med.stanford.edu/news/all-news.html`, the monitor extracts all article links visible after JS rendering
2. Article URLs already in the database are skipped before any article page is fetched
3. For each new article, the page is fetched with plain `requests` and parsed for title, date, and body
4. Articles are saved with: `url`, `title`, `body_text`, `published_at`, `source` (`med.stanford.edu`), `category` (null), `tags` (null), `first_seen_at`, `scrape_run_id`
5. A `scrape_runs` row is opened at start and closed with counts

---

## Research findings (2026-07-17)

- **Listing page:** `https://med.stanford.edu/news/all-news.html` — AEM page, JS-rendered, no RSS
- **Article URL pattern:** `https://med.stanford.edu/news/all-news/YYYY/MM/slug.html`
- **Article pages:** respond to plain `requests` with status 200 (no Cloudflare)
- **Title:** `<title>` tag or `og:title` meta tag (h1 not present in article body)
- **Date:** `<span class="date">April 09, 2026</span>` — text format, needs `dateutil` parsing
- **Body:** `<article>` element — confirmed present, ~6000 chars for the example article
- **JSON-LD:** not present on article pages
- **Tags/keywords:** not available on article pages → stored as `null`

**Listing page selectors — NEEDS INVESTIGATION:** The AEM listing page requires Playwright to render. Link selectors for the article grid have not yet been confirmed. This must be verified during implementation by inspecting the rendered DOM.

---

## Out of Scope

- Pagination beyond the first listing page (implement as initial scope; add pagination if needed)
- Date-based cutoff filtering
- Tags extraction (not available in the source)

---

## Decisions

| Question | Decision |
|---|---|
| Listing page fetch | Playwright (AEM page requires JS rendering) |
| Article page fetch | Plain `requests` (no Cloudflare) |
| `source` field | `med.stanford.edu` |
| Title selector | `og:title` meta tag; fall back to `<title>` tag |
| Date selector | `<span class="date">` text; parsed with `dateutil` |
| Body selector | `<article>` element |
| `category` field | `null` |
| `tags` field | `null` |
| Playwright session | Reuse same CDP session pattern as the Becker's backfill |
| Dedup key | Article URL |

---

## Selectors

### Listing page (rendered DOM via Playwright)

| Field | Notes |
|---|---|
| Article links | TBD — inspect rendered DOM during implementation; expect `<a href="/news/all-news/...">` links within a card grid |

### Article page (plain requests + BeautifulSoup)

| Field | Selector / source |
|---|---|
| Title | `meta[property="og:title"]` content; fallback: `<title>` text |
| Date | `<span class="date">` text, parsed with `dateutil` |
| Body | `<article>` element, `.get_text(separator='\n', strip=True)` |
| Tags | `null` |
| Category | `null` |

---

## Behavioral specs

### Listing page

- The listing page is loaded via Playwright (CDP session required)
- After JS rendering, all `<a>` elements with href matching `/news/all-news/` are extracted as candidate URLs
- URLs already in the `articles` table are skipped before any article page is fetched

### Article page

- Each new article URL is fetched with plain `requests` (no CDP needed)
- Title is taken from `og:title`; if absent, from `<title>` tag text
- Date is taken from `<span class="date">` text and parsed with `dateutil`; stored as `null` if unparseable
- Body text is extracted from the `<article>` element; entry is skipped if no body found
- `source` is hardcoded to `med.stanford.edu`

### Run tracking

- A `scrape_runs` row is opened at start with `status = 'running'` and source `med.stanford.edu`
- On completion: status `'completed'`, `articles_found` (total links found) and `articles_new` (actually inserted) recorded
- On unhandled exception: status `'failed'`, error message recorded

```gherkin
Scenario: New articles on the listing page are fetched and saved
  Given the rendered listing page contains 5 article links
  And none of the URLs are in the articles table
  When run_monitor is called
  Then all 5 article pages are fetched
  And all 5 are saved to the database

Scenario: Already-seen articles are skipped
  Given the rendered listing page contains 5 article links
  And 3 of those URLs are already in the articles table
  When run_monitor is called
  Then only 2 article pages are fetched
  And articles_new is recorded as 2

Scenario: Article with no body text is skipped
  Given a candidate article URL is not yet in the database
  And fetching that URL returns a page with no <article> element
  When run_monitor processes that URL
  Then the article is not inserted
  And no error is raised

Scenario: Run is marked failed on unhandled exception
  Given the Playwright listing page load raises an exception
  When run_monitor is called
  Then the scrape_runs row is updated to status 'failed'
  And the error message is recorded
```
