# AGE-79: UCSD Health — Feed Research

## Recommended Approach
RSS (`/rss/research`) — valid RSS 2.0 feed, current as of today, static HTML articles with full body text; no health-specific category feed exists, so use the research feed filtered by category tag post-fetch.

## Feed/Endpoint URL
`https://today.ucsd.edu/rss/research`

Secondary (broader, but older content in practice):
`https://today.ucsd.edu/rss/topstories`

## Sample Article Fields
- title: yes
- url: yes (in `<link>` and `<guid>`)
- published_at: yes (format: `dc:date` — ISO 8601, e.g. `2026-07-30T17:48:00+00:00`)
- body_text: no (in feed) — requires separate fetch of article URL; full static HTML body available at article URL, no JS rendering required
- category: yes (`<category>` and `<dc:subject>`)
- enclosure: yes (image attachment)

## Article Volume
10 items per feed request; `?page=N` parameter accepted but returns the same 10 items — no working pagination.

## Content Signal
Research-grant and academic announcement focused — faculty grants, NSF/NIH awards, university research milestones. Health-related articles (e.g., liver research, substance use disorders) appear mixed with non-health science. No clinical operations, provider network, or insurance content observed. Relevance to health insurance monitoring is low-to-moderate; useful mainly for catching academic partnerships or large health-system grants that signal market moves.

## Pagination
None functional. `?page=2` returns identical 10 items. Feed is capped at 10 most-recent articles. To backfill, scrape the category page HTML (if it becomes accessible — currently 404s) or poll the feed on a schedule to accumulate history.

## Notes / Gotchas
- `https://today.ucsd.edu/health` returns HTTP 404 — no health landing page at that URL.
- `https://today.ucsd.edu/wp-json/wp/v2/posts` returns 404 — not a WordPress site; no REST API.
- Category-specific feed slugs (`/rss/health`, `/rss/medicine`, `/rss/science`) all redirect to the generic site HTML, not category-filtered RSS. Only `topstories` and `research` are functioning named feeds.
- Top stories feed (`/rss/topstories`) showed 2022 dates during testing — may not update as frequently as the research feed; research feed confirmed current (today's date).
- Article body text is complete and static-HTML-renderable; a second fetch per article is needed to get it.
- `dc:date` field carries the timestamp; standard `<pubDate>` may not be present — confirm element name when parsing.
