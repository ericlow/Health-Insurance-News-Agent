import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from urllib.parse import urlparse

from db.connection import get_connection, release_connection

SOURCE = 'kffhealthnews.org'
START_URL = 'https://kffhealthnews.org/state/california/'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; HealthInsuranceNewsAgent/1.0)'}
BACKFILL_DELAY_SECONDS = 1


def run_backfill(start_url=START_URL, page_limit=3):
    conn = get_connection()
    run_id = _open_run(conn, datetime.now(timezone.utc))
    try:
        new_count = 0
        url = start_url
        pages_fetched = 0
        candidate_urls = []

        while url and pages_fetched < page_limit:
            articles, next_url = _fetch_kff_listing_page(url, conn=conn)
            for a in articles:
                candidate_urls.append(a['url'])
            url = next_url
            pages_fetched += 1

        print(f'[kff-backfill] {len(candidate_urls)} articles to fetch.')
        for i, article_url in enumerate(candidate_urls, 1):
            try:
                entry = _fetch_kff_article(article_url, conn=conn)
                if _insert_article(conn, entry, run_id):
                    new_count += 1
                    print(f'  [{i}/{len(candidate_urls)}] saved: {article_url}')
                else:
                    print(f'  [{i}/{len(candidate_urls)}] skip: {article_url}')
            except Exception as exc:
                print(f'  [{i}/{len(candidate_urls)}] failed: {article_url} — {exc}')
            time.sleep(BACKFILL_DELAY_SECONDS)

        _close_run(conn, run_id, 'completed', len(candidate_urls), new_count)
        print(f'[kff-backfill] done. {new_count} articles saved.')
    except Exception as exc:
        _fail_run(conn, run_id, str(exc))
        raise
    finally:
        release_connection(conn)


def _fetch_kff_listing_page(url, conn=None):
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, 'html.parser')

    articles = []
    for article_el in soup.select('article'):
        if article_el.find_parent('aside'):
            continue

        link_el = article_el.select_one('h2 a')
        time_el = article_el.select_one('time[datetime]')
        if not link_el or not time_el:
            continue

        article_url = link_el.get('href', '')
        title = link_el.get_text(strip=True)
        date = time_el.get('datetime', '')

        if conn and _already_seen(conn, article_url):
            continue

        articles.append({'url': article_url, 'title': title, 'date': date})

    next_el = soup.select_one('a.next.page-numbers')
    next_url = next_el.get('href') if next_el else None

    return articles, next_url


def _fetch_kff_article(url, conn=None):
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, 'html.parser')

    title_el = soup.select_one('h1')
    title = title_el.get_text(strip=True) if title_el else ''

    time_el = soup.select_one('time[datetime]')
    published_at = _parse_date(time_el.get('datetime')) if time_el else None

    body_text = '\n'.join(p.get_text(strip=True) for p in soup.select('main p')).strip()

    tags = None
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string)
            nodes = [data] + data.get('@graph', [])
            article_node = next((n for n in nodes if n.get('@type') == 'Article'), None)
            if article_node and 'keywords' in article_node:
                tags = article_node['keywords']
                break
        except Exception:
            continue

    return {
        'url': url,
        'title': title,
        'published_at': published_at,
        'body_text': body_text,
        'source': SOURCE,
        'category': _extract_category_from_url(url),
        'tags': tags,
    }


def _extract_category_from_url(url):
    parts = [p for p in urlparse(url).path.split('/') if p]
    return parts[0] if parts else None


def _parse_date(date_str):
    if not date_str:
        return None
    try:
        from dateutil import parser as dateparser
        return dateparser.parse(date_str)
    except Exception:
        return None


def _already_seen(conn, url):
    with conn.cursor() as cur:
        cur.execute('SELECT 1 FROM articles WHERE url = %s', (url,))
        return cur.fetchone() is not None


def _open_run(conn, started_at):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO scrape_runs (source, started_at, status) VALUES (%s, %s, 'running') RETURNING id",
            (f'{SOURCE} [backfill]', started_at),
        )
        run_id = cur.fetchone()[0]
    conn.commit()
    return run_id


def _insert_article(conn, entry, run_id):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO articles (url, title, published_at, body_text, source, category, tags, first_seen_at, scrape_run_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
            """,
            (entry['url'], entry['title'], entry['published_at'], entry['body_text'],
             SOURCE, entry.get('category'), entry.get('tags'),
             datetime.now(timezone.utc), run_id),
        )
        inserted = cur.rowcount > 0
    conn.commit()
    return inserted


def _close_run(conn, run_id, status, articles_found, articles_new):
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


def _fail_run(conn, run_id, error_message):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE scrape_runs SET status = 'failed', completed_at = %s, error_message = %s WHERE id = %s",
            (datetime.now(timezone.utc), error_message, run_id),
        )
    conn.commit()


if __name__ == '__main__':
    run_backfill()
