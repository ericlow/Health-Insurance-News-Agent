import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

from db.connection import get_connection, release_connection

SOURCE = 'newsroom.cigna.com'
FEED_URL = 'https://newsroom.cigna.com/latest-press-releases?pagetemplate=rss'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; HealthInsuranceNewsAgent/1.0)'}
MAX_ENTRIES = 5


def run_monitor() -> tuple[int, list[int]]:
    """Regular monitor run — fetches the Cigna newsroom RSS feed.

    Returns (run_id, new_article_ids) so the orchestrator can pass them to triage.
    """
    entries = _fetch_feed()
    conn = get_connection()
    run_id = _open_run(conn, datetime.now(timezone.utc))
    try:
        new_ids = []
        for entry in entries:
            if _already_seen(conn, entry['url']):
                continue
            body_text = _fetch_article_body(entry['url'])
            entry['body_text'] = body_text
            article_id = _insert_article(conn, entry, run_id)
            if article_id:
                new_ids.append(article_id)
        _close_run(conn, run_id, 'completed', len(entries), len(new_ids))
        print(f'[cigna-monitor] {len(entries)} found, {len(new_ids)} new.')
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
    for e in feed.entries[:MAX_ENTRIES]:
        entries.append({
            'url': e.link,
            'title': e.title,
            'published_at': _parse_feed_date(e),
            'body_text': None,  # fetched separately from article page
            'category': None,
            'tags': [t.term for t in e.get('tags', [])],
        })
    return entries


def _fetch_article_body(url: str) -> str | None:
    """Fetch article body text from the Cigna newsroom article page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        paragraphs = soup.find_all('p')
        text = '\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        return text or None
    except Exception:
        return None


def _parse_feed_date(entry) -> datetime | None:
    if entry.get('published_parsed'):
        from time import mktime
        return datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
    return None


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
    """Insert article and return its id, or None if it was a duplicate."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO articles (url, title, published_at, body_text, source, category, tags, first_seen_at, scrape_run_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
            RETURNING id
            """,
            (entry['url'], entry['title'], entry['published_at'], entry['body_text'],
             SOURCE, entry.get('category'), entry.get('tags'),
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
