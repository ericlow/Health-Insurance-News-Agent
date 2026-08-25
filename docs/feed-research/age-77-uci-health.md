# AGE-77: UCI Health — Feed Research

## Recommended Approach
HTML scraping — no RSS feed, WordPress REST API, or news sitemap exists; the listing page is server-rendered and article body text is fully available on individual article pages.

## Feed/Endpoint URL
`https://www.ucihealth.org/about-us/news`

## Sample Article Fields
- title: yes (visible on listing page and article page)
- url: yes (relative path, e.g. `/about-us/news/2026/07/rehabilitation-hospital-ribbon-cutting`)
- published_at: yes — visible as inline text on article pages in `MM.DD.YYYY` format (e.g. `07.21.2026`); **not** available as a structured meta tag (`article:published_time`, `og:published_time`, `datePublished` schema.org — all absent)
- body_text: yes, but requires separate fetch per article — not present on listing page

## Article Volume
~6 articles visible on the `/about-us/news` listing page per load (no standard numeric pagination).

## Content Signal
Press-release focused — institution milestones, awards, clinical research announcements, executive commentary. Relevant signal types: joint ventures, facility openings, partnership announcements.

## Pagination
Non-standard. The listing page links to `https://www.ucihealth.org/search?searchType=news` for older articles, but that search page requires JavaScript to render results (returns empty content to a plain HTTP fetch). **Effective pagination: listing page only**, ~6 most-recent articles accessible without JS.

## Notes / Gotchas
- WordPress REST API (`/wp-json/wp/v2/posts`) returns 404 — site does not expose it.
- Both RSS feed paths (`/feed/`, `/about-us/news/feed/`) return 404.
- Sitemap (`/sitemap.xml`) exists but contains no news-specific sitemap or `/news/` path entries.
- Published date must be parsed from article page body text (`MM.DD.YYYY`), not from meta tags.
- Article URLs follow a predictable pattern: `/about-us/news/YYYY/MM/<slug>` — can be used to deduplicate across runs.
- The search/pagination endpoint requires JS rendering (Playwright or similar) to access articles older than ~6 items.
- No bot detection or login wall observed on listing or article pages.
