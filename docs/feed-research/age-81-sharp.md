# AGE-81: Sharp Health System — Feed Research

## Recommended Approach
HTML scraping of `/media-center/press-releases` — WordPress REST API and all RSS endpoints return 404; the press release index is only available as a rendered HTML page.

## Feed/Endpoint URL
`https://www.sharp.com/media-center/press-releases`

## Sample Article Fields
- title: yes
- url: yes (relative paths, e.g. `/media-center/sharp-tri-city-medical-center-dedication`)
- published_at: yes (format: `M/D/YY`, e.g. `7/1/26`)
- body_text: requires separate fetch per article URL (full press release text is available at the article page, ~170–275 words per article)

## Article Volume
~11–13 per index page (no pagination controls observed)

## Content Signal
Press-release focused — announcements of affiliations, awards, workforce changes, partnerships, and facility expansions. High-signal for network/affiliation events relevant to the monitoring pipeline. Notable recent items:
- Sharp + Tri-City Healthcare District 30-year affiliation (Dec 2025, live Jul 2026)
- Sharp Community Medical Group + Integrated Health Partners merger (Feb 2025)
- Sharp workforce reduction announcement (Jun 2025)

## Pagination
None observed. The index appears to show the ~11 most recent press releases with no "load more" or page controls. Older releases may not be accessible from this page.

## Notes / Gotchas
- **No RSS or Atom feed** — no `<link rel="alternate">` feed tags in the HTML head.
- **WordPress REST API returns 404** — `https://www.sharp.com/wp-json/wp/v2/posts` is unavailable; the site may not be running WordPress, or the API is blocked.
- **Sitemap `news-article.xml`** covers 892 consumer health blog articles at `/health-news/[slug]` — these are NOT press releases and are low signal for network monitoring.
- **Press releases are not in any sitemap** — `/media-center/` URLs are absent from all 13 sub-sitemaps.
- **Article body is available via separate fetch** — each press release URL returns the full text (no JS rendering required, WebFetch works cleanly).
- **Relative URLs on index page** — article URLs scraped from the index will need `https://www.sharp.com` prepended.
- **Date format is ambiguous** — `7/1/26` requires year-expansion logic (assume 2000s).
