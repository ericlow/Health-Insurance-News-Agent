# AGE-83: Hoag Health — Feed Research

## Recommended Approach
Sitemap polling (`/sitemap.xml`) for new article discovery, followed by individual HTML fetches for body text — no RSS, no WordPress REST API; the site runs Contentful CMS with no public delivery API access.

## Feed/Endpoint URL
`https://www.hoag.org/sitemap.xml`

All article URLs follow the pattern: `https://www.hoag.org/articles/<slug>/`

## Sample Article Fields
- title: yes (in `<title>` tag and page `<h1>`)
- url: yes (from sitemap `<loc>`)
- published_at: **no** — no JSON-LD, no Open Graph `article:published_time`, no visible byline date; sitemap `<lastmod>` reflects CMS update time, not original publication date
- body_text: yes — full article body is available in static HTML on individual article pages (no JS rendering required)

## Article Volume
~480 total articles in sitemap. No reliable way to enumerate only "news" vs. health education content without fetching each article; the sitemap mixes institutional announcements with patient stories and general health education.

## Content Signal
Mixed — the `/articles/` namespace combines press-release/institutional news (hospital rankings, clinical program launches, awards) with patient stories and general consumer health education. No separate namespace or tag visible in the sitemap to filter by content type without fetching articles.

The `/newsroom/` path returned 404 — that sitemap entry appears to be a navigational stub with no dedicated listing page.

## Pagination
Sitemap is a single flat XML file (~480 entries). Poll by diffing `<loc>` + `<lastmod>` against a seen-URLs store to detect new or updated articles.

## Notes / Gotchas
- **No RSS feed exists** — `/feed/` and `/about-hoag/news/feed/` both return 404
- **Not WordPress** — site runs on Contentful; WP REST API endpoints return 404
- **Contentful delivery API requires auth** — space ID `8u2cuf59smsh` is known but the CDN API (`cdn.contentful.com`) returns 401 without a token; Hoag has not exposed a public token
- **No publication date in HTML** — articles fetched (stroke survivor: July 2, 2025; hospital ratings: July 30, 2020) show no date in structured data or meta tags; date must be scraped from visible body text if present, which is inconsistent
- **Static HTML** — article body content renders server-side; no JS execution required for scraping
- **`/about-hoag/news/` returns 404** — the original target URL does not resolve; actual content lives at `/articles/`
