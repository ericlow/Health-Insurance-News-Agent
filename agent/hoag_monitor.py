from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

from agent import http_utils
from db.connection import get_connection, release_connection

SOURCE = 'hoag.org'
LISTING_URL = 'https://www.hoag.org/sitemap.xml'

_LOOKBACK_DAYS = 30


def run_monitor() -> tuple[int, list[int]]:
    entries = _fetch_listing()
    conn = get_connection()
    run_id = _open_run(conn, datetime.now(timezone.utc))
    try:
        new_ids = []
        for entry in entries:
            if _already_seen(conn, entry['url']):
                continue
            result = _fetch_article_body(entry['url'])
            if result is None:
                continue
            entry['title'], entry['body_text'] = result
            article_id = _insert_article(conn, entry, run_id)
            if article_id:
                new_ids.append(article_id)
        _close_run(conn, run_id, 'completed', len(entries), len(new_ids))
        print(f'[hoag-monitor] {len(entries)} found, {len(new_ids)} new.')
        return run_id, new_ids
    except Exception as exc:
        _fail_run(conn, run_id, str(exc))
        raise
    finally:
        release_connection(conn)


def _fetch_listing() -> list[dict]:
    resp = http_utils.get(LISTING_URL)
    soup = BeautifulSoup(resp.content, 'xml')
    cutoff = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)
    entries = []
    for url_el in soup.find_all('url'):
        loc = url_el.find('loc')
        lastmod = url_el.find('lastmod')
        if not loc:
            continue
        url = loc.text.strip()
        if '/articles/' not in url or url.rstrip('/') == 'https://www.hoag.org/articles':
            continue
        published_at = None
        if lastmod:
            try:
                published_at = datetime.fromisoformat(lastmod.text.replace('Z', '+00:00'))
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
                if published_at < cutoff:
                    continue
            except ValueError:
                pass
        entries.append({
            'url': url,
            'title': None,
            'published_at': published_at,
            'body_text': None,
            'category': None,
            'tags': [],
        })
    return entries


def _fetch_article_body(url: str) -> tuple[str, str] | None:
    try:
        resp = http_utils.get(url)
        soup = BeautifulSoup(resp.content, 'html.parser')
        h1 = soup.find('h1')
        title = h1.get_text(strip=True) if h1 else None
        rich = soup.find('div', class_='rich-text')
        if rich:
            paragraphs = [p.get_text(strip=True) for p in rich.find_all('p') if p.get_text(strip=True)]
        else:
            paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]
        body_text = '\n'.join(paragraphs) or None
        if not title and not body_text:
            return None
        return title, body_text
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
