# AGE-86: Providence CA — Feed Research

## Recommended Approach
HTML scraping — no RSS feed or WP REST API; the listing page is server-side rendered and delivers all 30 articles as static HTML with title, URL, and date already present in the card markup.

## Feed/Endpoint URL
`https://www.providence.org/business/press-room/press-releases/california`

## Sample Article Fields
- title: yes (`.card-title` div inside each `a.callout-card`)
- url: yes (the `a.callout-card` href; pattern: `https://www.providence.org/news/uf/<ID>?streamid=11272579`)
- published_at: yes (format: `M/D/YYYY` as plain text in `.card-date` div; note: not ISO, not machine-friendly without parsing)
- body_text: requires a two-hop fetch — `/news/uf/<ID>` 302-redirects to `blog.providence.org/<slug>` where the **full article body is present in the HTML, not gated or truncated**. Confirmed working for both standard articles and the UHC contract termination notice.

## Article Volume
30 articles per page load. The `?page=N` query parameter is silently ignored — same 30 articles returned regardless.

## Content Signal
Press-release focused — clinical accolades (stroke/Magnet certifications), facility expansions, clinical milestones. High-signal payer/network items do surface: confirmed article "Contract Termination: UnitedHealthcare Medicare Advantage Plans" (ID 691944933) appears in the feed.

## Pagination
No functional pagination observed. `?page=2` returns the same 30 articles. No "Load More" button. No infinite scroll. The feed appears capped at 30 articles — deeper history may require the Uberflip API (see Notes).

## Notes / Gotchas
- **Uberflip CMS**: Articles are served via Uberflip (IDs in URL, `streamid=11272579`). The page is a Providence-hosted iframe/embed of Uberflip stream 11272579 — content is server-side rendered into the HTML at load time (no XHR observed post-load).
- **Uberflip API**: `https://app.uberflip.com/api/2/streams/11272579/items` is CORS-blocked from the browser. From a server-side Python scraper it may work without auth (Uberflip's v2 API has public endpoints for some streams) — worth attempting: `GET https://app.uberflip.com/api/2/streams/11272579/items?order=-created_at&per_page=25`. If it works, it would return structured JSON with title, date, URL, and possibly body — bypassing HTML parsing entirely.
- **No RSS**: All `/feed/` variants return 404. No `<link rel="alternate" type="application/rss+xml">` in page head.
- **Not WordPress**: No WP REST API (`/wp-json/`), no `wp-content` scripts, no generator meta tag.
- **Date format**: `M/D/YYYY` (e.g. `7/8/2026`) — not ISO 8601; must be parsed. Some cards missing date entirely (3 of 30 observed without `.card-date` text).
- **CSS selectors for scraping**: `a.callout-card[href*="/news/uf/"]` to get all article anchors; `.card-title` for title; `.card-date` for date; `a.href` for URL.
- **Article redirect chain**: `www.providence.org/news/uf/<ID>` → 302 → `blog.providence.org/regional-blog-news/<slug>` (most articles) or `blog.providence.org/california/<slug>`. Both destination domains confirmed accessible without auth.
- **blog.providence.org**: Custom CMS (not WordPress). No `/feed/`, no `/wp-json/`, no JSON-LD `datePublished` in article pages — rely on listing-page dates exclusively.
- **No bot detection observed**: Page loads cleanly with a standard user-agent. No Cloudflare challenge, no login wall, no JS-only rendering (content in raw HTML).
- **Effective history window**: ~24+ articles spanning ~Feb 2025–Jul 2026 (~17 months). For a polling pipeline checking weekly, this is more than sufficient to catch new additions.
- **Confirmed high-signal article**: "Contract Termination: UnitedHealthcare Medicare Advantage Plans" (`/news/uf/691944933`) — PCN exit from UHC MA across 7 CA counties (LA, Orange, San Bernardino, Humboldt, Napa, Sonoma, Ventura) effective Jan 1, 2026; full body available.
