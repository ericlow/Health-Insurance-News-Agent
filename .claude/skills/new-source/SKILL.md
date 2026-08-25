You are implementing a new newsroom monitor for the Health Insurance News Agent. Follow these steps in order. Do not skip steps.

## Step 1 — Feed research

Before writing any code, investigate the target URL to determine the best ingestion approach. Try in order:

1. **RSS/Atom**: check `/feed/`, `/rss/`, `/news/feed/`, `/?feed=rss2`, `/atom.xml`. If found and returning current articles, use it.
2. **WordPress REST API**: check `/wp-json/wp/v2/posts`. If returning JSON with articles, use it.
3. **Sitemap**: check `/robots.txt` first (it often lists sitemap locations), then try `/news-sitemap.xml`, `/sitemap.xml`, `/sitemap_index.xml`. If a sitemap is found, look for article URLs (typically matching a pattern like `/news/`, `/press-releases/`, `/articles/`). Fetch individual article pages for body text. Sitemaps include `<lastmod>` timestamps — use these to skip old articles on subsequent runs if needed.
4. **Embedded JSON in page source**: fetch the listing page HTML and look for `<script type="application/json">`, `window.__NEXT_DATA__`, or similar framework data blobs. Next.js, Astro, and similar frameworks often pre-embed page content in the HTML shell even when the visual rendering requires JS. If you find article data in a script tag, parse it directly.
5. **HTML scraping**: if none of the above work, scrape the listing page directly, looking for article links.

For whichever approach works, confirm:
- Article URLs are available and stable (good dedup keys)
- Title is available
- Published date is available
- Body text is fetchable via plain HTTP GET (no JS rendering required)

**Bot/scraping protection check**: verify the response contains actual article content — not a Cloudflare challenge page, CAPTCHA, or empty body. Signs of blocking: HTTP 403, response body containing "Just a moment", "Checking your browser", or no article links found.

If blocked, try once with a realistic `User-Agent` header (e.g. `Mozilla/5.0 ...`). If still blocked, document it as unsupported and stop — do not attempt Playwright, Google News RSS, or any JS rendering. Google News RSS is explicitly off the table: it provides aggregated coverage (not guaranteed), Google-wrapped URLs (no canonical article URL accessible via HTTP), and title-only body text.

Document your findings before proceeding.

## Step 2 — Create Linear issue

Create a Linear issue in the **Agents** team, **Health Insurance News Agent** project, **Phase 1 — Ingestion** milestone with:
- Title: `<Name> newsroom monitor`
- Description: the feed research findings (approach chosen, URL, fields available, gotchas)
- Priority: set appropriately (Urgent for large/strategic systems, High for regional anchors, Medium otherwise)

Note the issue ID (e.g. AGE-XX).

## Step 3 — Create branch

```bash
git checkout main && git checkout -b ericlow/age-XX-<slug>-newsroom-monitor
```

## Step 4 — Implement the monitor

Create `agent/<slug>_monitor.py`. Follow the existing pattern exactly — do not invent new structure.

**For RSS sources**, use `feedparser` to parse the feed. Follow `agent/cigna_monitor.py`.

**For HTML scraping sources**, use `requests` (via `agent.http_utils.get`) + `BeautifulSoup` to:
1. Fetch the listing page and extract article links and titles
2. For each unseen article, fetch the article page and extract body text from `<p>` tags

Follow `agent/ucsf_monitor.py`. Do not use Playwright, Selenium, or any JS rendering — if a page requires JS, document it as a blocker and stop.

Required constants:
- `SOURCE` — bare domain (e.g. `'sharp.com'`)
- `LISTING_URL` (HTML) or `FEED_URL` (RSS) — the URL being polled

Required functions (copy signatures exactly):
- `run_monitor() -> tuple[int, list[int]]`
- `_fetch_listing()` or `_fetch_feed()`
- `_fetch_article_body(url)`
- `_already_seen(conn, url)`
- `_open_run(conn, started_at)`
- `_insert_article(conn, entry, run_id)`
- `_close_run(conn, run_id, status, articles_found, articles_new)`
- `_fail_run(conn, run_id, error_message)`

The `entry` dict must have keys: `url`, `title`, `published_at`, `body_text`, `category`, `tags`.

## Step 5 — Wire into scheduler.py

Add to `scheduler.py`:
1. Import at top: `from agent.<slug>_monitor import run_monitor as <slug>_run_monitor, LISTING_URL as <SLUG>_LISTING_URL`
2. Call in `run_pipeline()`: `_<slug>_run_id, <slug>_new_ids = <slug>_run_monitor()`
3. Add to `combined_ids`
4. Add count to the log line
5. Add `post_health_check(...)` call

## Step 6 — Smoke test against LOCAL database

**Critical: always test against the local Docker Postgres, never against Neon.**

**Part A — Listing check**: fetch the listing page and print ALL article titles and URLs the source returns.

```bash
source .venv/bin/activate
DATABASE_URL=$DATABASE_URL_LOCAL python3 -c "
from agent.<slug>_monitor import _fetch_listing
entries = _fetch_listing()
print(f'{len(entries)} articles found on source:')
for e in entries:
    print(f'  {e[\"title\"]}')
    print(f'  {e[\"url\"]}')
    print()
"
```

Confirm: articles found > 0, URLs look correct, titles are human-readable (not empty, not HTML garbage).

**Part B — End-to-end insert**: run the full monitor against local DB, then query the DB to confirm the records landed with their PKs.

```bash
DATABASE_URL=$DATABASE_URL_LOCAL python3 -c "
import os, psycopg2
from agent.<slug>_monitor import run_monitor
run_id, new_ids = run_monitor()
print(f'run_id={run_id}, {len(new_ids)} inserted: {new_ids}')
if new_ids:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()
    cur.execute('SELECT id, title, url FROM articles WHERE id = ANY(%s) ORDER BY id', (new_ids,))
    rows = cur.fetchall()
    print(f'\n{len(rows)} records confirmed in DB:')
    for id_, title, url in rows:
        print(f'  [{id_}] {title}')
        print(f'       {url}')
    conn.close()
"
```

Confirm: every ID in `new_ids` appears in the DB output with a matching title. Note: if you run this twice, `new_ids` will be empty on the second run (articles already seen) — that is correct behavior, not a bug.

## Step 7 — Commit and open PR

```bash
git add agent/<slug>_monitor.py scheduler.py
git commit -m "AGE-XX: Add <Name> newsroom monitor"
git push -u origin ericlow/age-XX-<slug>-newsroom-monitor
gh pr create ...
```

PR body format:
```
## Summary
1-2 sentences: what changed and why.

[AGE-XX — <Name> newsroom monitor](https://linear.app/eric-projects/issue/AGE-XX/...)

## Changes
- Added `agent/<slug>_monitor.py` — <approach: RSS / HTML scraping> of <URL>
- Wired into `scheduler.py`

## Test plan
- [x] `_fetch_listing()` returns N articles with correct titles and URLs
- [x] End-to-end `run_monitor()` inserted N articles into local DB
- [x] `scheduler.py` imports cleanly
```

## Step 8 — Mark Linear issue In Review

After the PR is open, move the Linear issue to **In Review** and wait for Eric to validate.

## Step 9 — After Eric validates

1. Merge the PR
2. Mark Linear issue **Done**
3. Confirm GitHub Actions deploy succeeded (`gh run list --limit 3`)
4. Trigger Lambda to verify the new source appears in Discord health check:
   ```bash
   export $(grep -v '^#' .env | grep -v '&' | xargs)
   AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
     aws lambda invoke --function-name health-insurance-monitor --region us-west-1 \
     --payload '{}' /tmp/lambda-response.json && cat /tmp/lambda-response.json
   ```
   Check Discord for the health check message confirming the new source ran.
