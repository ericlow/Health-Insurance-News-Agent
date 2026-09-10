import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

from db.connection import get_connection, release_connection

SOURCE = 'pihhealth.org'
# Non-www entry point bypasses Akamai CDN bot block on www.pihhealth.org
# ponytail: browser UA required; shared http_utils UA gets 403 from Akamai
LISTING_URL = 'https://pihhealth.org/newsroom/'
_BASE_URL = 'https://www.pihhealth.org/about-us/newsroom/'
_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
}


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
        print(f'[pih-health-monitor] {len(entries)} found, {len(new_ids)} new.')
        return run_id, new_ids
    except Exception as exc:
        _fail_run(conn, run_id, str(exc))
        print(f'[pih-health-monitor] failed: {exc}')
        return run_id, []
    finally:
        release_connection(conn)


def _fetch_listing() -> list[dict]:
    resp = requests.get(LISTING_URL, headers=_HEADERS, timeout=30, allow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, 'html.parser')
    seen = set()
    entries = []

    # Press releases panel (#PanelSmartPanelRecentNews)
    for li in soup.find_all('li', id=lambda x: x and 'SmartPanelRecentNews_ResultsRepeater' in x):
        a = li.find('a', class_='Hdr')
        date_span = li.find('span', class_='PublicationDate')
        if not a:
            continue
        href = a['href']
        url = _BASE_URL + href if not href.startswith('http') else href
        if url in seen:
            continue
        seen.add(url)
        entries.append({
            'url': url,
            'title': a.get_text(strip=True),
            'published_at': _parse_date(date_span.get_text(strip=True) if date_span else None),
            'body_text': None,
            'category': 'Press Release',
            'tags': [],
        })

    # In-the-news panel (#PanelUserControlIntheMedia)
    for li in soup.find_all('li', id=lambda x: x and 'PanelUserControlIntheMedia_ResultsRepeater' in x):
        a = li.find('a')
        if not a:
            continue
        href = a['href']
        url = _BASE_URL + href if not href.startswith('http') else href
        if url in seen:
            continue
        seen.add(url)
        entries.append({
            'url': url,
            'title': a.get_text(strip=True),
            'published_at': None,  # in-the-news listings don't show date on listing page
            'body_text': None,
            'category': 'In the News',
            'tags': [],
        })

    return entries


def _fetch_article_body(url: str) -> str | None:
    """Fetch body text via non-www URL to bypass Akamai block."""
    try:
        # Convert canonical www URL back to non-www entry point for CDN bypass
        fetch_url = url.replace('https://www.pihhealth.org', 'https://pihhealth.org')
        resp = requests.get(fetch_url, headers=_HEADERS, timeout=30, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        paragraphs = soup.find_all('p')
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
