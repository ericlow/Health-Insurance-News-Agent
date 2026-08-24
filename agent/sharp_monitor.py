import re
from bs4 import BeautifulSoup
from datetime import datetime, timezone

from agent import http_utils
from db.connection import get_connection, release_connection

SOURCE = 'sharp.com'
LISTING_URL = 'https://www.sharp.com/media-center/press-releases'
BASE_URL = 'https://www.sharp.com'

_DATE_RE = re.compile(r'- (\d{1,2}/\d{1,2}/\d{2})$')


def run_monitor() -> tuple[int, list[int]]:
    conn = get_connection()
    run_id = _open_run(conn, datetime.now(timezone.utc))
    try:
        entries = _fetch_listing()
        new_ids = []
        for entry in entries:
            if _already_seen(conn, entry['url']):
                continue
            body_text = _fetch_article_body(entry['url'])
            if body_text is None:
                continue
            entry['body_text'] = body_text
            article_id = _insert_article(conn, entry, run_id)
            if article_id:
                new_ids.append(article_id)
        _close_run(conn, run_id, 'completed', len(entries), len(new_ids))
        print(f'[sharp-monitor] {len(entries)} found, {len(new_ids)} new.')
        return run_id, new_ids
    except Exception as exc:
        _fail_run(conn, run_id, str(exc))
        print(f'[sharp-monitor] failed: {exc}')
        return run_id, []
    finally:
        release_connection(conn)


def _fetch_listing() -> list[dict]:
    resp = http_utils.get(LISTING_URL)
    soup = BeautifulSoup(resp.content, 'html.parser')
    seen = set()
    entries = []
    for a in soup.select('a[href^="/media-center/"]'):
        href = a['href']
        if href.startswith('/es/') or href == '/media-center/press-releases':
            continue
        url = BASE_URL + href
        if url in seen:
            continue
        seen.add(url)
        title = a.get_text(strip=True)
        if not title:
            continue
        p_text = a.parent.get_text(strip=True) if a.parent else ''
        entries.append({
            'url': url,
            'title': title,
            'published_at': _parse_date(p_text),
            'body_text': None,
            'category': None,
            'tags': [],
        })
    return entries


def _parse_date(p_text: str) -> datetime | None:
    match = _DATE_RE.search(p_text)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), '%m/%d/%y').replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _fetch_article_body(url: str) -> str | None:
    try:
        resp = http_utils.get(url)
        soup = BeautifulSoup(resp.content, 'html.parser')
        main = soup.find('main')
        if not main:
            return None
        paragraphs = main.find_all('p')
        text = '\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        return text or None
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
