# AGE-85: John Muir Health — Feed Research

## Recommended Approach
HTML scraping — no RSS feed or WP REST API exists; press releases are in static HTML at predictable `/about-john-muir-health/press-room/Press-releases/YYYY-MM-DD-slug.html` paths, body text is fully available without a second fetch.

## Feed/Endpoint URL
`https://www.johnmuirhealth.com/about-john-muir-health/press-room`

## Sample Article Fields
- title: yes (in page listing and article `<h1>`)
- url: yes (relative path in listing, pattern: `/about-john-muir-health/press-room/Press-releases/YYYY-MM-DD-slug.html`)
- published_at: yes (format: `Month DD, YYYY` as plain text in article body; not in structured metadata or listing)
- body_text: yes — full press release body is in static HTML; no separate fetch required

## Article Volume
~7 articles visible per load on the press room listing page (split across a NEWS section and an ANNOUNCEMENTS section, each with a "Load More" button)

## Content Signal
Press-release focused — community health initiatives, service expansions, clinical milestones, physician appointments. Network/contract/payer news would surface here if it exists.

## Pagination
"Load More" buttons on the listing page — JS-triggered, likely appends additional items. No URL-based pagination observed. For automated ingestion, scrape visible articles first; use a headless browser or intercept the XHR behind "Load More" if deeper history is needed.

## Notes / Gotchas
- WordPress REST API (`/wp-json/wp/v2/posts`) returns 404 — not a WP site or the API is disabled
- `/feed/` and `/about-john-muir-health/press-room/feed/` both return 404
- No `<link rel="alternate" type="application/rss+xml">` in page `<head>`
- Publication date appears only as plain text in the article body (e.g., "July 16 2026"), not in structured metadata (no JSON-LD, no OpenGraph date tags) — parse from body or infer from URL slug
- Article URLs embed the date (`YYYY-MM-DD-slug`), making the slug a reliable publication date source even without parsing body text
- No login wall, no bot-detection issues observed, no JS rendering required for visible content
