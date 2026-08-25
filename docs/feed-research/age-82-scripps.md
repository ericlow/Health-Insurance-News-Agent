# AGE-82: Scripps Health — Feed Research

## Recommended Approach
HTML scraping of `/news_items` listing pages — no RSS or WordPress REST API exists; the site runs a custom CMS with clean paginated HTML and full article body text available on individual article pages.

## Feed/Endpoint URL
`https://www.scripps.org/news_items?utf8=%E2%9C%93&query=&categories=131&page=N`

Two categories of interest:
- **Category 131** — Press releases / official news (992 total articles as of 2026-07-30)
- **Category 46** — "Scripps in the News" / media coverage (1,573 total articles)

## Sample Article Fields
- title: yes (in listing page `<a>` text)
- url: yes (relative path, e.g. `/news_items/8165-partners-in-care-foundation-honors-scripps-health-ceo`)
- published_at: yes (format: `May 29, 2026` — human-readable date on listing page)
- body_text: requires separate fetch — listing page shows title + date only; full body available inline on the individual article page (no truncation observed)

## Article Volume
10 per page (listing); ~992 press releases + ~1,573 media coverage items total

## Content Signal
Press-release focused (category 131): awards, financial milestones, facility openings, clinical achievements — high signal for network/partnership moves.
Media coverage (category 46): syndicated TV/radio clips, Becker's/Modern Healthcare features — useful for corroboration.

## Pagination
`?page=N` parameter (1-indexed). Example:
```
https://www.scripps.org/news_items?utf8=%E2%9C%93&query=&categories=131&page=2
```
Navigation links confirm standard `« Previous / Next »` pattern.

## Notes / Gotchas
- **No RSS, no WordPress API, no JSON endpoint** — all 404. Custom CMS only.
- Article URLs follow a numeric ID + slug pattern (`/news_items/<id>-<slug>`); IDs appear sequential, so the highest ID on page 1 can serve as a high-water mark for incremental polling.
- `.json` suffix on article URLs returns 404 — no Rails-style JSON serialization.
- No bot detection or login walls observed on public newsroom pages.
- No bylines on press releases — articles are attributed to "Scripps Health" generically.
- The `utf8=%E2%9C%93` query param appears to be a Rails CSRF artifact; it appears required for category filtering but is otherwise harmless.
- Category 46 ("Scripps in the News") articles are mostly summaries of TV segments with little body text signal — category 131 is the higher-value source for substantive news.
