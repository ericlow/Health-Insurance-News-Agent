# AGE-84: City of Hope — Feed Research

## Recommended Approach
Google News RSS — the entire `cityofhope.org` domain returns HTTP 403 to non-browser user-agents (Cloudflare/WAF), blocking all direct access. Google News RSS is the only viable read-only endpoint that surfaces City of Hope press releases without authentication or a headless browser.

## Feed/Endpoint URL
General press-release query (broader):
`https://news.google.com/rss/search?q=%22City+of+Hope%22+press+release&hl=en-US&gl=US&ceid=US:en`

Network/partnership signal query (better for this pipeline):
`https://news.google.com/rss/search?q=%22City+of+Hope%22+%28partnership+OR+network+OR+contract+OR+acquisition+OR+alliance%29&hl=en-US&gl=US&ceid=US:en`

## Sample Article Fields
- title: yes
- url: **Google redirect URL only** — `<link>` values are `https://news.google.com/rss/articles/CBMi...` wrappers, not direct article URLs. The `<source url="...">` attribute contains the original domain (e.g., `cityofhope.org`, `businesswire.com`), but the resolved article URL is not in the feed XML.
- published_at: yes (format: `Mon, 23 Feb 2026 08:00:00 GMT` — RFC 822)
- body_text: **not in feed**; requires a separate fetch of the resolved source URL. `cityofhope.org` article pages are 403. Third-party sources (wire services, trade press) vary in accessibility.

## Article Volume
~50 results per query (Google News RSS hard cap). The press-release query returned 28/50 from `cityofhope.org` and 22 from external wire/trade sources including BusinessWire, GlobeNewswire, FierceHealthcare, HealthLeaders, ModernHealthcare.

## Content Signal
Mixed — press-release query returns genuine institutional announcements (hospital openings, care alliances, executive appointments, cancer center rankings) alongside some patient education content. The partnership/network query filters more usefully to signal-relevant items; sample hits include:

- "City of Hope Cancer Center Atlanta and Upson Regional Medical Center to Launch Cancer Care Alliance" (Feb 2026)
- "COH and Humboldt Park Health Unite to Expand Cancer Care on West Side" (Jan 2026)
- "City of Hope Opens Only Cancer Specialty Hospital in Orange County, Calif" (Nov 2025)

## Pagination
None — Google News RSS returns a fixed window of ~50 recent articles. No `page` parameter exists. Poll on a schedule (daily recommended) and diff by `<guid>` to detect new items.

## Notes / Gotchas
- **cityofhope.org is fully WAF-blocked** — every path tested returns HTTP 403: WP REST API, `/feed/`, `/news`, `/news/feed/`, `/robots.txt`, `/sitemap.xml`, and individual article pages. Direct scraping requires a headless browser.
- **Google News links are redirect wrappers** — `<link>` and `<guid>` in the feed are Google-internal URLs (`news.google.com/rss/articles/CBMi...`). To get the real article URL, the pipeline must follow the redirect at fetch time (may need a browser-like user-agent) or parse `<source url="...">` domain + reconstruct separately.
- **Body text requires per-source handling** — since cityofhope.org articles are inaccessible, body text must come from third-party sources indexed by Google News. Wire services (BusinessWire, GlobeNewswire) carry full press release text when accessible; trade press (FierceHealthcare, ModernHealthcare) may be paywalled.
- **BusinessWire as secondary option** — City of Hope appears to syndicate press releases to BusinessWire. A direct org RSS (`https://www.businesswire.com/rss/home/?rss=G22&org=cityofhope`) timed out during testing but is worth retesting with a longer timeout; BusinessWire article pages have been accessible in other feed research in this project.
- **No press-release-only filter in Google News** — use query keyword tuning (`press release`, `partnership`, `alliance`) to narrow signal. Expect some research/clinical trial noise regardless.
- **Not confirmed WordPress** — WP REST API returns 403 (not 404), so CMS type is unknown; WAF blocks before any CMS response.
