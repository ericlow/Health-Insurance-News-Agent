# AGE-80: UCSF — Feed Research

## Recommended Approach
HTML scraping — no WordPress REST API, RSS, or Atom feed exists; the news listing at `/news?page=N` renders full HTML server-side with no JS required, and individual article pages contain complete body text.

## Feed/Endpoint URL
`https://www.ucsf.edu/news?page=N`

## Sample Article Fields
- title: yes
- url: yes (relative path, e.g. `/news/2026/07/432266/article-slug`)
- published_at: yes (format: `July 28, 2026`)
- category: yes (e.g. Research, Patient Care, Campus News)
- author: yes (on article page)
- body_text: yes — requires separate fetch of article URL, but full text is available in static HTML (no JS rendering needed)

## Article Volume
~5 featured articles on page 1; ~9 additional articles in "Latest News" section starting page 2. Roughly 9 net-new articles per paginated page.

## Content Signal
Mixed — research findings, clinical/patient care stories, institutional announcements (leadership, awards). Primarily press-release and research-highlight focused. Not a wire service; articles are UCSF-authored.

## Pagination
Query string: `?page=N` (1-indexed). Page 1 shows 5 featured articles; page 2 onward adds a "Latest News" section with ~9 articles per page. Pages continue indefinitely back through the archive (sitemap confirms articles dating to 1999).

## Notes / Gotchas
- No WordPress REST API (`/wp-json/wp/v2/posts` → 404), no RSS feed (`/feed/` and `/news/feed/` → 404), no sitemap index (`/sitemap_index.xml` → 404). Only `/sitemap.xml` exists but covers older archive (1999–~2011 in the excerpt seen).
- The top 5 featured articles repeat on every page (they appear on both `/news` and `/news?page=2`). Dedup by URL is required to avoid re-processing featured items.
- Article URLs include a numeric ID (e.g. `432266`) which can serve as a stable dedup key.
- Some articles link off-domain (e.g. `campuslifeserviceshome.ucsf.edu`) — check hostname before fetching body text.
- No bot-detection or login wall observed. Static HTML, WebFetch-compatible.
- For a monitoring pipeline, fetching page 1 (`/news`) on a schedule and comparing article IDs against a seen-set is sufficient to detect new articles without pagination.
