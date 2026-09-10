from bs4 import BeautifulSoup
from datetime import datetime, timezone

from curl_cffi import requests as cffi_requests

from db.connection import get_connection, release_connection

SOURCE = 'cityofhope.org'
LISTING_URL = 'https://www.cityofhope.org/about-city-of-hope/newsroom/press-releases-statements'
BASE_URL = 'https://www.cityofhope.org'

# ponytail: curl-cffi impersonation bypasses Cloudflare; upgrade to rotating proxy if Cloudflare
# starts requiring JS challenges that cffi can't handle


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
        print(f'[city-of-hope-monitor] {len(entries)} found, {len(new_ids)} new.')
        return run_id, new_ids
    except Exception as exc:
        _fail_run(conn, run_id, str(exc))
        print(f'[city-of-hope-monitor] failed: {exc}')
        return run_id, []
    finally:
        release_connection(conn)


def _fetch_listing() -> list[dict]:
    resp = cffi_requests.get(LISTING_URL, impersonate='chrome120', timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    seen = set()
    entries = []
    for card in soup.select('.card__content'):
        link_el = card.select_one('a.article-link')
        title_el = card.select_one('.article-title')
        date_el = card.select_one('.field--name-field-date')
        if not link_el or not title_el:
            continue
        href = link_el.get('href', '')
        url = BASE_URL + href if href.startswith('/') else href
        if url in seen:
            continue
        seen.add(url)
        entries.append({
            'url': url,
            'title': title_el.get_text(strip=True),
            'published_at': _parse_date(date_el.get_text(strip=True) if date_el else None),
            'body_text': None,
            'category': 'Press Release',
            'tags': [],
        })
    return entries


def _fetch_article_body(url: str) -> str | None:
    try:
        resp = cffi_requests.get(url, impersonate='chrome120', timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        main = soup.find('main')
        container = main or soup
        paragraphs = [
            p.get_text(strip=True)
            for p in container.find_all('p')
            if p.get_text(strip=True)
        ]
        return '\n'.join(paragraphs) or None
    except Exception:
        return None


def _parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip(), '%b %d, %Y').replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    try:
        from dateutil import parser as dateparser
        return dateparser.parse(date_str).replace(tzinfo=timezone.utc)
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
