from bs4 import BeautifulSoup
from datetime import datetime, timezone
from urllib.parse import urlparse

from agent import http_utils
from db.connection import get_connection, release_connection

SOURCE = 'ucsf.edu'
LISTING_URL = 'https://www.ucsf.edu/news'
BASE_URL = 'https://www.ucsf.edu'


def run_monitor() -> tuple[int, list[int]]:
    entries = _fetch_listing()
    conn = get_connection()
    run_id = _open_run(conn, datetime.now(timezone.utc))
    try:
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
        print(f'[ucsf-monitor] {len(entries)} found, {len(new_ids)} new.')
        return run_id, new_ids
    except Exception as exc:
        _fail_run(conn, run_id, str(exc))
        raise
    finally:
        release_connection(conn)


def _fetch_listing() -> list[dict]:
    resp = http_utils.get(LISTING_URL)
    soup = BeautifulSoup(resp.content, 'html.parser')
    seen = set()
    entries = []
    for card in soup.select('article.news-card'):
        link = card.select_one('a[href*="/news/"]')
        title_el = card.select_one('h2, h3')
        date_el = card.select_one('time')
        if not link or not title_el:
            continue
        href = link['href']
        # Skip off-domain links
        if href.startswith('http') and not href.startswith(BASE_URL):
            continue
        url = BASE_URL + href if href.startswith('/') else href
        if url in seen:
            continue
        seen.add(url)
        entries.append({
            'url': url,
            'title': title_el.get_text(strip=True),
            'published_at': _parse_date(date_el.get_text(strip=True) if date_el else None),
            'body_text': None,
            'category': _extract_category(card),
            'tags': [],
        })
    return entries


def _extract_category(card) -> str | None:
    # Category is the first list item in article-header__byline before the date
    li = card.select_one('li.article-header__primary-area')
    return li.get_text(strip=True) if li else None


def _fetch_article_body(url: str) -> str | None:
    try:
        if urlparse(url).netloc != 'www.ucsf.edu':
            return None
        resp = http_utils.get(url)
        soup = BeautifulSoup(resp.content, 'html.parser')
        content = soup.find('div', class_='main-content')
        if not content:
            return None
        paragraphs = content.find_all('p')
        text = '\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        return text or None
    except Exception:
        return None


def _parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
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
