# Scraper Behavioral Specs

Plain English behavioral statements for `agent/scraper.py`. Each statement should become a named test.
Pattern: `test_<function>_<expected outcome>_<when condition>`

---

## Run Tracking

Applies to both RSS runs and backfill runs.

- A scrape run record is opened at the start of every execution with status `running` and the current timestamp in a field called `start_time`
- When the run completes without error, status is updated to `completed`
- When the run raises an unhandled exception, status is updated to `failed` and the error message is recorded
- The source name is recorded on every scrape run (the url of the RSS feed or the backfill url)
- The count of articles found and articles newly inserted is recorded when the run completes
- when the run completes with completed or failed status, write the timestamp of the completed time in `end_time` and write a `duration` in seconds

---

## RSS Ingestion

- the list of rss feeds is configurable and defined in a file
- The feed is fetched from the RSS URL — no calls are made to individual article pages
- Each entry in the feed produces one candidate article
- The article URL is taken from the RSS `link` field
- The article title is taken from the RSS `title` field
- The article publication date is taken from the RSS `published` field
- The article body text is taken from `content:encoded`, with all HTML tags stripped
- The article category is taken from the RSS feed's category tags — not parsed from the URL
- The article tags are all taxonomy terms returned by the RSS feed for that entry
- An article with no category tag in the RSS feed is still stored, with category set to null
- An article with multiple tags stores all of them as a list
- An article whose URL is already in the database is skipped entirely — no re-insert
- A new article is inserted with source set to the feed's source name

---


## Backfill Acceptance Criteria

The backfill crawls category listing pages (e.g. `/executive-moves/`) to discover articles and their dates before fetching full article content. This avoids loading article pages that are outside the date range.

The system prints the article URL, title, and date of publication stdio with a simple print.




### Category listing pages

- The list of category listing page URLs is loaded from config — not hardcoded
- Listing pages are fetched without a CDP session (not Cloudflare-blocked)
- Each article entry on a listing page exposes a URL (`h3 a`), title (`h3 a` text), and publish date (`time[datetime]` attribute — always ISO 8601)
- The publish date is read from the `datetime` attribute before any article page is fetched
- An article whose listing date is older than the cutoff date is skipped — its page is never fetched
- When all articles on a listing page are older than the cutoff, pagination stops for that category
- The system paginates through `/page/2/`, `/page/3/`, etc. until the cutoff is reached or no more pages exist
- URLs already present in the articles table are skipped before any CDP session is opened

### Article page fetching

- Individual article pages are loaded using a Chrome CDP session — not headless Playwright
- A single browser session is reused across all article fetches in one backfill run
- A short delay is added between page loads
- When fewer articles than the configured minimum are available after filtering, the backfill returns what was retrieved

### Article extraction

- The article body is extracted from the `.entry-content` selector
- The article title is extracted from the `article h1` selector
- The article date is taken from the `<time>` element's `datetime` attribute
- When the `datetime` attribute is absent, the date falls back to the `<time>` element's inner text
- Tags are extracted from the `NewsArticle` JSON-LD block's `keywords` field
- Category is stored as null for backfilled articles
- Source is set to the domain of the category listing page (e.g. `beckerspayer.com`)

---
## Configuration (`load_config`)

Config is loaded from a configurable source (local file in development; SSM Parameter Store or S3 in production).

- `load_config` returns the list of RSS feed URLs
- `load_config` returns the list of backfill category listing page URLs (e.g. `https://www.beckerspayer.com/executive-moves/`)
- `load_config` returns the minimum article count for backfill
- `load_config` returns the backfill cutoff date
- `load_config` raises an error when the config source cannot be read
- `load_config` raises an error when a required field is missing from the config
- `load_config` raises an error when the backfill category listing URL list is empty

--- 

## Date Parsing

Both listing pages and article pages use a `<time datetime="...">` element with an ISO 8601 value.
No text parsing of human-readable or relative date strings is needed.

- An ISO 8601 date string (e.g. `2026-06-22T14:44:17-05:00`) is parsed to a UTC-aware datetime
- A human-readable date string (e.g. `Thursday, June 9th, 2026`) is parsed to a datetime (article page fallback only)
- A null input returns null
- An empty string returns null
- A malformed string that matches no known format returns null

---

## Deduplication

- For RSS: an article whose URL is already in the articles table is skipped before any insert is attempted
- For backfill: an article whose URL is already in the articles table is skipped on the listing page — its article page is never fetched via CDP

---

## Article Insert

- `_insert_article` returns true when the article is newly inserted
- `_insert_article` returns false when the URL conflicts with an existing row (ON CONFLICT DO NOTHING)
- All fields — url, title, published_at, body_text, source, category, tags — are passed to the insert statement
- The scrape_run_id is recorded on every inserted article
