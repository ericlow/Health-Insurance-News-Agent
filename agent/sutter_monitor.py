import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

from db.connection import get_connection, release_connection

FEED_URL = 'https://vitals.sutterhealth.org/wp-json/wp/v2/posts?categories=542&orderby=date&order=desc&per_page=10'
_API_URL = FEED_URL + '&_fields=title,date,link,slug,content'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; HealthInsuranceNewsAgent/1.0)'}


def run_monitor() -> tuple[int, list[int]]:
    """Regular monitor run — fetches the Sutter Health press releases via WordPress REST API.

    Returns (run_id, new_article_ids) so the orchestrator can pass them to triage.
    """
    conn = get_connection()
    run_id = _open_run(conn, datetime.now(timezone.utc))
    try:
        entries = _fetch_feed()
        new_ids = []
        for entry in entries:
            if _already_seen(conn, entry['url']):
                continue
            article_id = _insert_article(conn, entry, run_id)
            if article_id:
                new_ids.append(article_id)
        _close_run(conn, run_id, 'completed', len(entries), len(new_ids))
        print(f'[sutter-monitor] {len(entries)} found, {len(new_ids)} new.')
        return run_id, new_ids
    except Exception as exc:
        _fail_run(conn, run_id, str(exc))
        print(f'[sutter-monitor] failed: {exc}')
        return run_id, []
    finally:
        release_connection(conn)


def _fetch_feed() -> list[dict]:
    resp = requests.get(_API_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    posts = resp.json()
    entries = []
    for post in posts:
        entries.append({
            'url': post['link'],
            'title': _strip_html(post['title']['rendered']),
            'published_at': _parse_date(post['date']),
            'body_text': _strip_html(post['content']['rendered']),
        })
    return entries


def _parse_date(date_str: str) -> datetime | None:
    """Parse ISO 8601 date string from WordPress API."""
    if not date_str:
        return None
    try:
        # WordPress returns local time without timezone; treat as UTC
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _strip_html(html: str) -> str:
    return BeautifulSoup(html, 'html.parser').get_text(separator='\n', strip=True)


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
             FEED_URL, None, None,
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
