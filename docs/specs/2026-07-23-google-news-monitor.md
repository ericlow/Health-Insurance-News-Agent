# Google News RSS Monitor — Feature Spec

_Status: ready for implementation_
_Last updated: 2026-07-17_
_Linear: [AGE-64](https://linear.app/eric-projects/issue/AGE-64/add-google-news-rss-monitor-for-health-insurance-industry-stories)_

---

## Background

Google News aggregates articles from thousands of publishers and exposes a free RSS feed per search query. This makes it a broad catch-all monitor for any health insurance industry story that appears in the news cycle — acquisitions, network terminations, provider collaborations — across sources the project doesn't monitor directly.

---

## What we're building

A recurring monitor that polls a configurable Google News RSS search query, resolves each Google-proxied article URL to its canonical source URL, and saves new articles to the database.

---

## User Story

As an industry analyst, I want the system to check Google News on schedule for health insurance industry stories so that I catch relevant events from sources not individually monitored.

---

## Acceptance Criteria

1. Given a configured search query, the monitor fetches the corresponding Google News RSS feed
2. For each entry, the Google-proxied link is resolved to the canonical source URL via HTTP redirect
3. The canonical URL is used as the dedup key — articles already in the database are skipped
4. For each new article, a row is saved with: `url`, `title`, `body_text` (RSS summary, HTML stripped), `published_at`, `source` (per-article publisher name from RSS), `category` (null), `tags` (null), `first_seen_at`, `scrape_run_id`
5. A `scrape_runs` row is opened at start and closed with `completed` status and article counts

---

## Research findings (2026-07-17)

- **RSS URL pattern:** `https://news.google.com/rss/search?q=<query>&hl=en-US&gl=US&ceid=US:en`
- **Feed response:** 200, `application/xml`, parseable with feedparser
- **Entry count:** 79 entries for query `health insurance network acquisition merger`
- **Link format:** Google-proxied URL (e.g. `https://news.google.com/rss/articles/CBMi...`) — 302 redirects to canonical article URL
- **Published date:** present in `entry.published` (RFC 822 format), parsed by feedparser as `entry.published_parsed`
- **Summary:** `entry.summary` contains HTML snippet — strip tags for body_text
- **Per-article source:** `entry.source.title` (e.g. `"TribLIVE.com"`) — this is the actual publisher, not "Google News"
- **No Cloudflare:** redirect resolution works with plain `requests`

---

## Out of Scope

- Fetching full article body text from the resolved URL — RSS summary is sufficient for triage
- Filtering by publisher domain
- Deduplicating articles by content similarity

---

## Decisions

| Question | Decision |
|---|---|
| Search query | Configurable in `config.json` as `google_news_query` |
| RSS URL construction | `https://news.google.com/rss/search?q=<query>&hl=en-US&gl=US&ceid=US:en` |
| `url` field | Resolved canonical URL (follow 302 redirect from Google proxy) |
| `body_text` | RSS `summary` with HTML tags stripped |
| `source` field | `entry.source.title` — per-article publisher name |
| `category` field | `null` |
| `tags` field | `null` |
| Redirect resolution | `requests.head(..., allow_redirects=True).url` with 10s timeout |
| Dedup key | Resolved canonical URL |

---

## Selectors / Feed fields

| Field | Source |
|---|---|
| Title | `entry.title` |
| Proxied URL | `entry.link` |
| Canonical URL | Follow 302 redirect from `entry.link` |
| Published date | `entry.published_parsed` (struct_time from feedparser) |
| Body text | `entry.summary` — strip HTML tags |
| Source name | `entry.source.title` |

---

## Behavioral specs

### Feed fetch

- The RSS URL is constructed from the configured `google_news_query` value
- The feed is fetched with `feedparser` using a plain `requests` GET
- Entries with no `link` field are skipped

### URL resolution

- Each entry's Google proxy URL is resolved to a canonical source URL by following the 302 redirect
- Resolution uses `requests.head` with `allow_redirects=True` and a 10-second timeout
- If resolution fails (timeout, connection error), the entry is skipped and a warning is printed
- The resolved canonical URL is the dedup key — if already in `articles`, the entry is skipped

### Article insertion

- `body_text` is the RSS `summary` with HTML stripped via BeautifulSoup
- `source` is set to `entry.source.title` (the publisher name); if absent, falls back to the hostname of the resolved URL
- `category` and `tags` are stored as `null`
- `scrape_run_id` is recorded on every inserted article

### Run tracking

- A `scrape_runs` row is opened at the start with `status = 'running'`
- On completion: status set to `'completed'`, `articles_found` and `articles_new` recorded
- On unhandled exception: status set to `'failed'`, error message recorded

```gherkin
Scenario: New articles are saved and proxied URLs are resolved
  Given the RSS feed contains 3 entries with Google-proxy links
  And all 3 canonical URLs are not yet in the articles table
  When run_monitor is called
  Then each proxy URL is resolved to its canonical URL
  And all 3 articles are inserted with the canonical URL as the url field

Scenario: Already-seen articles are skipped
  Given the RSS feed contains 2 entries
  And one canonical URL is already in the articles table
  When run_monitor is called
  Then only the new article is inserted
  And articles_new is recorded as 1

Scenario: Resolution failure skips the entry
  Given the RSS feed contains 2 entries
  And resolving one proxy URL raises a requests.Timeout
  When run_monitor is called
  Then the failed entry is skipped
  And the other article is inserted normally

Scenario: Run is marked failed on unhandled exception
  Given the RSS feed fetch raises an exception
  When run_monitor is called
  Then the scrape_runs row is updated to status 'failed'
  And the error message is recorded
```
