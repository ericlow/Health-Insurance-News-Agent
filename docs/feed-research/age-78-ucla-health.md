# AGE-78: UCLA Health — Feed Research

## Recommended Approach
HTML scraping of `https://www.uclahealth.org/news` — no RSS feed or WP REST API available; listing page is server-rendered with full body text available on individual article pages via plain HTTP fetch.

## Feed/Endpoint URL
`https://www.uclahealth.org/news`

## Sample Article Fields
- title: yes (visible on listing page and article page)
- url: yes (relative path, e.g. `/news/release/first-human-bladder-transplant-performed-ucla`)
- published_at: yes — present on individual article pages as inline text (e.g. `May 18, 2025`); not tested for structured meta tags
- body_text: yes, but requires separate fetch per article — not present on listing page

## Article Volume
~20–25 articles visible on the `/news` listing page across several content-type sections (releases, articles, stories).

## Content Signal
Mixed — press releases and research announcements (`/news/release/`) are the highest-signal content type for network/payer monitoring. Also includes health education articles (`/news/article/`), patient stories (`/news/story/`), and Q&A columns. Filter to `/news/release/` paths for institutional/partnership signal.

## Pagination
Non-standard. The listing page includes "View all news releases" and "View all stories" links that resolve to `/news/search?f%5B0%5D=type%3A80076` (releases) and `type%3A80071` (stories), but those search URLs return HTTP 403. Effective pagination: listing page only, most-recent ~20–25 articles accessible without additional calls.

## Notes / Gotchas
- `newsroom.uclahealth.org` (the originally targeted subdomain) returns ECONNREFUSED — domain does not resolve or is decommissioned. The live newsroom is at `www.uclahealth.org/news`.
- WordPress REST API (`/wp-json/wp/v2/posts`) returns HTTP 403 — blocked server-side.
- RSS feed (`/feed/`) returns HTTP 404.
- Sitemap exists (`/sitemap.xml`, Drupal-generated, 14 pages) but is not sorted by date and mixes all content types — not useful for polling new releases.
- News search/filter URLs (`/news/search?f[0]=type:...`) return HTTP 403 — cannot be used for type-filtered pagination.
- Individual article pages (`/news/release/<slug>`, `/news/article/<slug>`) load cleanly with full body text via plain HTTP GET — no JS rendering required, no bot detection observed.
- URL path prefix (`/news/release/` vs `/news/article/` vs `/news/story/`) reliably distinguishes content type — can filter at the listing-parse stage.
- Deduplication key: full URL slug (unique and stable per article).
