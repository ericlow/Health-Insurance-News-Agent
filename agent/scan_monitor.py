import json
from bs4 import BeautifulSoup
from datetime import datetime, timezone

from agent import http_utils
from db.connection import get_connection, release_connection

SOURCE = 'scanhealthplan.com'
LISTING_URL = 'https://www.scanhealthplan.com/about-scan/press-releases'
BASE_URL = 'https://www.scanhealthplan.com'



def run_monitor() -> tuple[int, list[int]]:
    conn = get_connection()
    run_id = _open_run(conn, datetime.now(timezone.utc))
    try:
        entries = _fetch_listing()
        new_ids = []
        for entry in entries:
            if _already_seen(conn, entry['url']):
                continue
            # body_text already extracted from __NEXT_DATA__; no second fetch needed
            article_id = _insert_article(conn, entry, run_id)
            if article_id:
                new_ids.append(article_id)
        _close_run(conn, run_id, 'completed', len(entries), len(new_ids))
        print(f'[scan-monitor] {len(entries)} found, {len(new_ids)} new.')
        return run_id, new_ids
    except Exception as exc:
        _fail_run(conn, run_id, str(exc))
        print(f'[scan-monitor] failed: {exc}')
        return run_id, []
    finally:
        release_connection(conn)


def _fetch_listing() -> list[dict]:
    resp = http_utils.get(LISTING_URL)
    soup = BeautifulSoup(resp.content, 'html.parser')
    next_data_tag = soup.find('script', id='__NEXT_DATA__')
    if not next_data_tag:
        raise RuntimeError('__NEXT_DATA__ not found on SCAN press releases page')
    data = json.loads(next_data_tag.string)
    items = _extract_items(data)
    entries = []
    for item in items:
        fields = item.get('fields', {})
        title = fields.get('Title', {}).get('value', '').strip()
        date_str = fields.get('Date', {}).get('value', '')
        content_html = fields.get('Content', {}).get('value', '')
        url_path = item.get('url', '')
        if not title or not url_path:
            continue
        url = BASE_URL + url_path if url_path.startswith('/') else url_path
        entries.append({
            'url': url,
            'title': title,
            'published_at': _parse_date(date_str),
            'body_text': _fetch_article_body(content_html),
            'category': 'Press Release',
            'tags': [],
        })
    return entries


def _extract_items(next_data: dict) -> list[dict]:
    """Walk headless-main placeholders to find the press-release items list."""
    try:
        placeholders = (
            next_data['props']['pageProps']['layoutData']
            ['sitecore']['route']['placeholders']
        )
    except KeyError:
        return []
    main = placeholders.get('headless-main', [])
    for component in main:
        if not isinstance(component, dict):
            continue
        items = component.get('fields', {}).get('items', [])
        if (
            isinstance(items, list)
            and items
            and isinstance(items[0], dict)
            and 'press-release' in items[0].get('url', '')
        ):
            return items
    return []


def _fetch_article_body(content_html: str) -> str | None:
    """Strip HTML tags from the Content field already in __NEXT_DATA__."""
    if not content_html:
        return None
    soup = BeautifulSoup(content_html, 'html.parser')
    paragraphs = soup.find_all('p')
    text = '\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
    return text or BeautifulSoup(content_html, 'html.parser').get_text(separator='\n', strip=True) or None


def _parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except Exception:
        return None


def _already_seen(conn, url: str) -> bool:
    with conn.cursor() as cur:
        cur.execute('SELECT 1 FROM articles WHERE url = %s', (url,))
        return cur.fetchone() is not None


def _open_run(conn, started_at: datetime) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO scrape_runs (source, started_at, status) VALUES (%s, %s, 'running') RETURNING id",
            (LISTING_URL, started_at),
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
