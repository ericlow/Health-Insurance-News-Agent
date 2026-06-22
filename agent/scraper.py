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
    'Quit Chrome, then run:\n'
    '  open -a "Google Chrome" --args --remote-debugging-port=9222\n'
    'Then re-run the backfill.'
)


def run_backfill():
    """Backfill stub — not yet implemented. See docs/specs/scraper.md."""
    raise NotImplementedError("Backfill not yet implemented. See docs/specs/scraper.md")


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
    if len(sys.argv) > 1 and sys.argv[1] == 'backfill':
        run_backfill()
    else:
        run_scrape()
