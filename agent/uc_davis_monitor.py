import feedparser
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

log = logging.getLogger(__name__)

from db.connection import get_connection, release_connection

SOURCE = 'health.ucdavis.edu'
FEED_URL = 'https://health.ucdavis.edu/health-news/rss/newsroom'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; HealthInsuranceNewsAgent/1.0)'}


def run_monitor() -> tuple[int, list[int]]:
    entries = _fetch_feed()
    conn = get_connection()
    run_id = _open_run(conn, datetime.now(timezone.utc))
    try:
        new_ids = []
        for entry in entries:
            if _already_seen(conn, entry['url']):
                continue
            article_id = _insert_article(conn, entry, run_id)
            if article_id:
                new_ids.append(article_id)
        _close_run(conn, run_id, 'completed', len(entries), len(new_ids))
        print(f'[uc-davis-monitor] {len(entries)} found, {len(new_ids)} new.')
        return run_id, new_ids
    except Exception as exc:
        _fail_run(conn, run_id, str(exc))
        raise
    finally:
        release_connection(conn)


def _fetch_feed() -> list[dict]:
    resp = requests.get(FEED_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    entries = []
    for e in feed.entries:
        body_html = e.content[0].value if e.get('content') else e.get('summary', '')
        entries.append({
            'url': e.link,
            'title': e.title,
            'published_at': _parse_feed_date(e),
            'body_text': _extract_body(body_html, e.link),
            'tags': [t.term for t in e.get('tags', [])],
        })
    return entries


def _parse_feed_date(entry) -> datetime | None:
    if entry.get('published_parsed'):
        from time import mktime
        return datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
    return None


def _extract_body(html: str, url: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    body_div = soup.find('div', class_='article-body')
    if body_div:
        return body_div.get_text(separator='\n', strip=True)
    # Some feed entries are already plain article HTML with no page chrome — use as-is.
    # Warn only if page structure is present but article-body is missing (selector broke).
    # ponytail: warn if chrome changes and selector stops working
    if soup.find('div', class_='news-article-container'):
        log.warning('[uc-davis-monitor] article-body selector missed on %s, falling back to full text', url)
    return soup.get_text(separator='\n', strip=True)


def _already_seen(conn, url: str) -> bool:
    with conn.cursor() as cur:
        cur.execute('SELECT 1 FROM articles WHERE url = %s', (url,))
        return cur.fetchone() is not None


def _open_run(conn, started_at: datetime) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO scrape_runs (source, started_at, status) VALUES (%s, %s, 'running') RETURNING id",
            (FEED_URL, started_at),
        )
        run_id = cur.fetchone()[0]
    conn.commit()
    return run_id


def _insert_article(conn, entry: dict, run_id: int) -> int | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO articles (url, title, published_at, body_text, source, category, tags, first_seen_at, scrape_run_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
            RETURNING id
            """,
            (entry['url'], entry['title'], entry['published_at'], entry['body_text'],
             SOURCE, None, entry.get('tags'),
             datetime.now(timezone.utc), run_id),
        )
        row = cur.fetchone()
    conn.commit()
    return row[0] if row else None


def _close_run(conn, run_id: int, status: str, articles_found: int, articles_new: int) -> None:
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


def _fail_run(conn, run_id: int, error_message: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE scrape_runs SET status = 'failed', completed_at = %s, error_message = %s WHERE id = %s",
            (datetime.now(timezone.utc), error_message, run_id),
        )
    conn.commit()


if __name__ == '__main__':
    run_monitor()
