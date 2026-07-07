import json
import time
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from time import mktime

from playwright.sync_api import sync_playwright

from config import BECKERS_PAYER_FEED_URL
from db.connection import get_connection, release_connection

SOURCE = 'beckerspayer.com'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; HealthInsuranceNewsAgent/1.0)'}
BACKFILL_DELAY_SECONDS = 1


def run_scrape():
    """Regular monitor run — fetches the RSS feed (most recent ~10 articles)."""
    entries = _fetch_feed()
    conn = get_connection()
    run_id = _open_run(conn, datetime.now(timezone.utc))
    try:
        new_count = 0
        for entry in entries:
            if _already_seen(conn, entry['url']):
                continue
            if _insert_article(conn, entry, run_id):
                new_count += 1
        _close_run(conn, run_id, 'completed', len(entries), new_count)
        print(f'[monitor] {len(entries)} found, {new_count} new.')
    except Exception as exc:
        _fail_run(conn, run_id, str(exc))
        raise
    finally:
        release_connection(conn)


CDP_URL = 'http://localhost:9222'
CDP_LAUNCH_HINT = (
    'Chrome must be running with remote debugging enabled.\n'
    'Quit Chrome completely, then run:\n'
    "  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' "
    '--remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug\n'
    'Then re-run the backfill.'
)


def run_backfill(config_path: str = 'config.json'):
    """Crawls category listing pages and fetches new articles via Chrome CDP."""
    import urllib.request
    try:
        urllib.request.urlopen(f'{CDP_URL}/json/version', timeout=3)
    except Exception:
        print(f'[backfill] ERROR: cannot reach Chrome CDP at {CDP_URL}.')
        print(CDP_LAUNCH_HINT)
        return

    config = load_config(config_path)
    cutoff = config['cutoff_date']

    conn = get_connection()
    run_id = _open_run(conn, datetime.now(timezone.utc), label='backfill')
    try:
        new_count = 0
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            context = browser.contexts[0]
            page = context.new_page()

            seen_urls: set[str] = set()
            candidate_urls = []
            for listing_url in config['backfill_urls']:
                url = listing_url
                while url:
                    articles, next_url = _fetch_listing_page(url, cutoff=cutoff, conn=conn, page=page)
                    new_articles = [a for a in articles if a['url'] not in seen_urls]
                    for a in new_articles:
                        seen_urls.add(a['url'])
                        print(f'  found: {a["title"]} — {a["date"]} — {a["url"]}')
                        candidate_urls.append(a['url'])
                    # Stop if no new URLs appeared — all were cross-page sticky duplicates
                    url = next_url if new_articles else None

            print(f'[backfill] {len(candidate_urls)} new articles to fetch via CDP.')
            for i, url in enumerate(candidate_urls, 1):
                try:
                    entry = _fetch_article_playwright(page, url)
                    if entry and _insert_article(conn, entry, run_id):
                        new_count += 1
                        print(f'  [{i}/{len(candidate_urls)}] saved: {url}')
                    else:
                        print(f'  [{i}/{len(candidate_urls)}] skip: {url}')
                except Exception as exc:
                    print(f'  [{i}/{len(candidate_urls)}] failed: {url} — {exc}')
                time.sleep(BACKFILL_DELAY_SECONDS)
            page.close()

        _close_run(conn, run_id, 'completed', len(candidate_urls), new_count)
        print(f'[backfill] done. {new_count} articles saved.')
    except Exception as exc:
        _fail_run(conn, run_id, str(exc))
        raise
    finally:
        release_connection(conn)


# --- Config ---

def load_config(source: str) -> dict:
    try:
        with open(source) as f:
            data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {source}")

    for field in ('rss_feeds', 'backfill_urls', 'min_articles', 'cutoff_date'):
        if field not in data:
            raise ValueError(f"Missing required config field: '{field}'")

    if not data['backfill_urls']:
        raise ValueError("backfill_urls must not be empty")

    data['cutoff_date'] = _parse_date_str(data['cutoff_date'])
    if data['cutoff_date'] is None:
        raise ValueError("cutoff_date could not be parsed")

    return data


# --- RSS feed (monitor) ---

def _fetch_feed() -> list[dict]:
    resp = requests.get(BECKERS_PAYER_FEED_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    entries = []
    for e in feed.entries:
        body_html = e.content[0].value if e.get('content') else e.get('summary', '')
        entries.append({
            'url': e.link,
            'title': e.title,
            'published_at': _parse_feed_date(e),
            'body_text': _strip_html(body_html),
            'category': e.tags[0].term if e.get('tags') else None,
            'tags': [t.term for t in e.get('tags', [])],
        })
    return entries


def _parse_feed_date(entry) -> datetime | None:
    if entry.get('published_parsed'):
        return datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
    return None


# --- Backfill listing page crawl ---

def _fetch_listing_page(url: str, cutoff: datetime, conn=None, page=None) -> tuple[list[dict], str | None]:
    if page is not None:
        page.goto(url, timeout=30000, wait_until='domcontentloaded')
        soup = BeautifulSoup(page.content(), 'html.parser')
    else:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')

    articles = []
    any_within_cutoff = False

    for article_el in soup.select('.entry-main__posts article'):
        link_el = article_el.select_one('h3 a')
        time_el = article_el.select_one('time[datetime]')
        if not link_el or not time_el:
            continue

        article_url = link_el.get('href', '')
        title = link_el.get_text(strip=True)
        date = _parse_date_str(time_el.get('datetime'))
        if date is None or date < cutoff:
            continue

        any_within_cutoff = True

        if conn and _already_seen(conn, article_url):
            continue

        articles.append({'url': article_url, 'title': title, 'date': date})

    next_url = None
    if any_within_cutoff:
        next_el = soup.select_one('a.next')
        if next_el:
            next_url = next_el.get('href')

    return articles, next_url


# --- Playwright article fetch (backfill) ---

def _fetch_article_playwright(page, url: str) -> dict | None:
    page.goto(url, timeout=30000, wait_until='domcontentloaded')
    result = page.evaluate("""() => {
        const title = document.querySelector('article h1')?.innerText?.trim();
        const body = document.querySelector('.entry-content')?.innerText?.trim();
        const time = document.querySelector('time');
        const date = time?.getAttribute('datetime') || time?.innerText?.trim();

        // Extract keywords from NewsArticle JSON-LD structured data
        let tags = null;
        for (const el of document.querySelectorAll('script[type=\"application/ld+json\"]')) {
            try {
                const data = JSON.parse(el.innerText);
                const article = [data, ...(data['@graph'] || [])].find(n => n['@type'] === 'NewsArticle');
                if (article?.keywords?.length) { tags = article.keywords; break; }
            } catch {}
        }
        return { title, body, date, tags };
    }""")
    if not result.get('body'):
        return None
    return {
        'url': url,
        'title': result.get('title') or '',
        'published_at': _parse_date_str(result.get('date')),
        'body_text': result['body'],
        'category': None,
        'tags': result.get('tags'),
    }


def _parse_date_str(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        from dateutil import parser as dateparser
        return dateparser.parse(date_str).replace(tzinfo=timezone.utc)
    except Exception:
        return None


# --- Shared helpers ---

def _strip_html(html: str) -> str:
    return BeautifulSoup(html, 'html.parser').get_text(separator='\n', strip=True)


def _open_run(conn, started_at, label: str = 'monitor'):
    source = f'{SOURCE} [{label}]'
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO scrape_runs (source, started_at, status) VALUES (%s, %s, 'running') RETURNING id",
            (source, started_at),
        )
        run_id = cur.fetchone()[0]
    conn.commit()
    return run_id


def _already_seen(conn, url: str) -> bool:
    with conn.cursor() as cur:
        cur.execute('SELECT 1 FROM articles WHERE url = %s', (url,))
        return cur.fetchone() is not None


def _insert_article(conn, entry: dict, run_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO articles (url, title, published_at, body_text, source, category, tags, first_seen_at, scrape_run_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
            """,
            (entry['url'], entry['title'], entry['published_at'], entry['body_text'],
             SOURCE, entry.get('category'), entry.get('tags'),
             datetime.now(timezone.utc), run_id),
        )
        inserted = cur.rowcount > 0
    conn.commit()
    return inserted


def _close_run(conn, run_id, status, articles_found, articles_new):
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE scrape_runs
            SET status = %s, completed_at = %s, articles_found = %s, articles_new = %s
            WHERE id = %s
            """,
            (status, datetime.now(timezone.utc), articles_found, articles_new, run_id),
        )
    conn.commit()


def _fail_run(conn, run_id, error_message):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE scrape_runs SET status = 'failed', completed_at = %s, error_message = %s WHERE id = %s",
            (datetime.now(timezone.utc), error_message, run_id),
        )
    conn.commit()


if __name__ == '__main__':
    import sys
    # Run as a module from the project root: python -m agent.scraper [backfill]
    if len(sys.argv) > 1 and sys.argv[1] == 'backfill':
        run_backfill()
    else:
        run_scrape()
