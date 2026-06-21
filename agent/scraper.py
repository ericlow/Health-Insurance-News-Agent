import time
import xml.etree.ElementTree as ET
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from time import mktime

from playwright.sync_api import sync_playwright

from config import BECKERS_PAYER_FEED_URL, BECKERS_PAYER_SITEMAP_INDEX
from db.connection import get_connection, release_connection

SOURCE = 'beckerspayer.com'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; HealthInsuranceNewsAgent/1.0)'}
BACKFILL_YEARS = 5
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
    """Backfill using sitemap + Chrome CDP. Fetches all articles from the last 5 years.

    Requires Chrome running with --remote-debugging-port=9222.
    """
    import urllib.request
    try:
        urllib.request.urlopen(f'{CDP_URL}/json/version', timeout=3)
    except Exception:
        print(f'[backfill] ERROR: cannot reach Chrome CDP at {CDP_URL}.')
        print(CDP_LAUNCH_HINT)
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=365 * BACKFILL_YEARS)
    sitemap_urls = _get_post_sitemap_urls()

    article_urls = []
    for sitemap_url in sitemap_urls:
        article_urls.extend(_get_urls_from_sitemap(sitemap_url, cutoff))

    conn = get_connection()
    run_id = _open_run(conn, datetime.now(timezone.utc), label='backfill')
    try:
        new_urls = [u for u in article_urls if not _already_seen(conn, u)]
        print(f'[backfill] {len(article_urls)} in sitemap (last {BACKFILL_YEARS}y), {len(new_urls)} new.')

        new_count = 0
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            context = browser.contexts[0]
            page = context.new_page()
            for i, url in enumerate(new_urls, 1):
                try:
                    entry = _fetch_article_playwright(page, url)
                    if entry and _insert_article(conn, entry, run_id):
                        new_count += 1
                        print(f'  [{i}/{len(new_urls)}] + {url}')
                    else:
                        print(f'  [{i}/{len(new_urls)}] skip (no body): {url}')
                except Exception as exc:
                    print(f'  [{i}/{len(new_urls)}] failed: {url} — {exc}')
                time.sleep(BACKFILL_DELAY_SECONDS)
            page.close()

        _close_run(conn, run_id, 'completed', len(article_urls), new_count)
        print(f'[backfill] done. {new_count} new articles added.')
    except Exception as exc:
        _fail_run(conn, run_id, str(exc))
        raise
    finally:
        release_connection(conn)


# --- RSS feed (monitor) ---

def _extract_category(url: str) -> str | None:
    """Extract category from first URL path segment.

    /contracting/article-slug/         → 'contracting'
    /payer/medicaid/article-slug/      → 'payer'
    """
    from urllib.parse import urlparse
    segments = [s for s in urlparse(url).path.split('/') if s]
    return segments[0] if segments else None


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
            'category': _extract_category(e.link),
            'tags': [t.term for t in e.get('tags', [])],
        })
    return entries


def _parse_feed_date(entry) -> datetime | None:
    if entry.get('published_parsed'):
        return datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
    return None


# --- Sitemap (backfill) ---

def _get_post_sitemap_urls() -> list[str]:
    resp = requests.get(BECKERS_PAYER_SITEMAP_INDEX, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    return [
        loc.text for loc in root.findall('.//sm:loc', ns)
        if loc.text and 'post-sitemap' in loc.text
    ]


def _get_urls_from_sitemap(sitemap_url: str, cutoff: datetime) -> list[str]:
    resp = requests.get(sitemap_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    urls = []
    for url_el in root.findall('.//sm:url', ns):
        loc = url_el.findtext('sm:loc', namespaces=ns)
        lastmod = url_el.findtext('sm:lastmod', namespaces=ns)
        if not loc:
            continue
        if lastmod:
            try:
                mod_date = datetime.fromisoformat(lastmod).replace(tzinfo=timezone.utc)
                if mod_date < cutoff:
                    continue
            except ValueError:
                pass
        urls.append(loc)
    return urls


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
        'category': _extract_category(url),
        'tags': result.get('tags'),  # from NewsArticle JSON-LD keywords field
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
