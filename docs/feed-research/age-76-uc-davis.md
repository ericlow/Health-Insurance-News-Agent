# AGE-76: UC Davis Health — Feed Research

## Recommended Approach
RSS (`/health-news/rss/newsroom`) — valid RSS 2.0 feed with full body text inline via `<content:encoded>`; no scraping needed.

## Feed/Endpoint URL
`https://health.ucdavis.edu/health-news/rss/newsroom`

## Sample Article Fields
- title: yes
- url: yes (full absolute URL, e.g. `https://health.ucdavis.edu/news/headlines/<slug>/YYYY/MM`)
- published_at: yes (format: RFC 2822, e.g. `Thu, 30 Jul 2026 07:00:00 GMT`)
- body_text: yes — full HTML body included inline in `<content:encoded>` CDATA block; separate fetch not required

## Article Volume
~11 items per feed request

## Content Signal
Mixed — research announcements, patient stories, clinical program updates, institutional news. Leans press-release in tone. Spanish-language articles also appear on the news homepage but were not observed in the newsroom feed; a separate `/health-news/rss/mindinstitute` or `/health-news/rss/research` feed exists if topic focus is needed.

## Pagination
No pagination in RSS; feed returns the latest ~11 items. No `?page=` or `?offset=` parameter observed. For historical backfill, HTML scraping of the news index would be required.

## Additional Feed URLs (topic-scoped)
All are relative to `https://health.ucdavis.edu`:
- Cancer Center: `/health-news/rss/cancer`
- Children's Hospital: `/health-news/rss/children`
- MIND Institute: `/health-news/rss/mindinstitute`
- Research: `/health-news/rss/research`
- Awards: `/awards/rss/aboutus`

Source page listing these: `https://health.ucdavis.edu/news/social-media/#social-rss-feeds`

## Notes / Gotchas
- Standard WordPress REST API (`/wp-json/wp/v2/posts`) returns 404 — not a standard WP install or the API is disabled.
- Default `/feed/` and `/news/feed/` paths also return 404.
- The feed URL pattern (`/health-news/rss/newsroom`) is non-standard and only discoverable via the social media page, not by convention.
- No bot detection or JS rendering observed. Articles load as static server-rendered HTML.
- Article URLs follow a date-scoped pattern: `/news/headlines/<slug>/YYYY/MM` — useful for deduplication.
