"""Aetna (CVS Health) newsroom monitor.

news.aetna.com redirects to www.cvshealth.com. No RSS feed exists; instead
the sitemap at /sitemap.xml lists all /news/company-news/ and /news/community/
articles with <lastmod> dates. We pull the MAX_ENTRIES most recent entries by
lastmod and fetch each article page for body text and the canonical title.

Article pages expose <meta name="publishDate" content="MM/DD/YYYY"> for the
published date (more accurate than sitemap lastmod).
"""
from bs4 import BeautifulSoup
from datetime import datetime, timezone

from agent import http_utils
from db.connection import get_connection, release_connection

SOURCE = 'news.aetna.com'
LISTING_URL = 'https://www.cvshealth.com/news.html'
SITEMAP_URL = 'https://www.cvshealth.com/sitemap.xml'
MAX_ENTRIES = 10


def run_monitor() -> tuple[int, list[int]]:
    conn = get_connection()
    run_id = _open_run(conn, datetime.now(timezone.utc))
    try:
        entries = _fetch_listing()
        new_ids = []
        for entry in entries:
            if _already_seen(conn, entry['url']):
                continue
            title, published_at, body_text = _fetch_article_body(entry['url'])
            if body_text is None:
                continue
            # Override slug-derived values with canonical article page data.
            if title:
                entry['title'] = title
            if published_at:
                entry['published_at'] = published_at
            entry['body_text'] = body_text
            article_id = _insert_article(conn, entry, run_id)
            if article_id:
                new_ids.append(article_id)
        _close_run(conn, run_id, 'completed', len(entries), len(new_ids))
        print(f'[aetna-monitor] {len(entries)} found, {len(new_ids)} new.')
        return run_id, new_ids
    except Exception as exc:
        _fail_run(conn, run_id, str(exc))
        print(f'[aetna-monitor] failed: {exc}')
        return run_id, []
    finally:
        release_connection(conn)


def _fetch_listing() -> list[dict]:
    """Pull the MAX_ENTRIES most recent articles from the CVS Health sitemap."""
    resp = http_utils.get(SITEMAP_URL)
    soup = BeautifulSoup(resp.content, 'xml')

    raw = []
    for url_el in soup.find_all('url'):
        loc = url_el.find('loc')
        lastmod = url_el.find('lastmod')
        if not loc:
            continue
        href = loc.text
        if '/news/company-news/' not in href and '/news/community/' not in href:
            continue
        raw.append({
            'url': href,
            'lastmod': lastmod.text if lastmod else '1970-01-01',
        })

    raw.sort(key=lambda e: e['lastmod'], reverse=True)

    entries = []
    for e in raw[:MAX_ENTRIES]:
        entries.append({
            'url': e['url'],
            'title': _slug_to_title(e['url']),
            'published_at': _parse_lastmod(e['lastmod']),
            'body_text': None,
            'category': _category_from_url(e['url']),
            'tags': [],
        })
    return entries


def _slug_to_title(url: str) -> str:
    """Best-effort title from URL slug; overridden by article page h1 in body fetch."""
    slug = url.rstrip('/').rsplit('/', 1)[-1].replace('.html', '')
    return slug.replace('-', ' ').title()


def _category_from_url(url: str) -> str | None:
    if '/company-news/' in url:
        return 'Company News'
    if '/community/' in url:
        return 'Community'
    return None


def _parse_lastmod(date_str: str) -> datetime | None:
    """Parse YYYY-MM-DD sitemap date as UTC midnight."""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _fetch_article_body(url: str) -> tuple[str | None, datetime | None, str | None]:
    """Fetch article page; return (title, published_at, body_text).

    Single HTTP GET per article — extracts h1 title, publishDate meta, and
    all <p> body text in one pass.
    """
    try:
        resp = http_utils.get(url)
        soup = BeautifulSoup(resp.content, 'html.parser')

        h1 = soup.find('h1')
        title = h1.get_text(strip=True) if h1 else None

        published_at = None
        meta = soup.find('meta', attrs={'name': 'publishDate'})
        if meta and meta.get('content'):
            try:
                published_at = datetime.strptime(meta['content'], '%m/%d/%Y').replace(tzinfo=timezone.utc)
            except Exception:
                pass

        paragraphs = soup.find_all('p')
        body_text = '\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

        return title, published_at, body_text or None
    except Exception:
        return None, None, None


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
