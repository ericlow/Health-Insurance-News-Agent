import pytest
import responses as responses_lib
from pathlib import Path
from unittest.mock import MagicMock, patch, call

# Fixture files stand in for real HTTP responses so tests never hit the network.
FIXTURES = Path(__file__).parent / 'fixtures'
KFF_LISTING_URL = 'https://kffhealthnews.org/state/california/'
KFF_LISTING_HTML = (FIXTURES / 'kff_listing.html').read_bytes()
KFF_LISTING_LAST_PAGE_HTML = (FIXTURES / 'kff_listing_last_page.html').read_bytes()
KFF_ARTICLE_URL = 'https://kffhealthnews.org/mental-health/article-one/'
KFF_ARTICLE_HTML = (FIXTURES / 'kff_article.html').read_bytes()
KFF_ARTICLE_NO_TAGS_HTML = (FIXTURES / 'kff_article_no_tags.html').read_bytes()
KFF_ARTICLE_NO_DATE_HTML = (FIXTURES / 'kff_article_no_date.html').read_bytes()


# =============================================================================
# _fetch_kff_listing_page
# Fetches one page of the KFF state/topic listing using plain requests.
# No CDP required — KFF is not Cloudflare-protected.
# Returns (articles_on_page, next_page_url_or_none).
# Spanish sidebar articles (inside aside.term-sidebar) are excluded.
# URLs already in the articles table are excluded before any article fetch.
# =============================================================================

@responses_lib.activate
def test_fetch_kff_listing_page_returns_articles_with_url_title_and_date():
    from agent.kff_scraper import _fetch_kff_listing_page
    responses_lib.add(responses_lib.GET, KFF_LISTING_URL, body=KFF_LISTING_HTML, status=200)
    articles, _ = _fetch_kff_listing_page(KFF_LISTING_URL)
    assert len(articles) > 0
    for a in articles:
        assert 'url' in a and 'title' in a and 'date' in a

@responses_lib.activate
def test_fetch_kff_listing_page_excludes_spanish_sidebar_articles():
    # Spanish articles live in aside.term-sidebar — they must never appear in results.
    from agent.kff_scraper import _fetch_kff_listing_page
    responses_lib.add(responses_lib.GET, KFF_LISTING_URL, body=KFF_LISTING_HTML, status=200)
    articles, _ = _fetch_kff_listing_page(KFF_LISTING_URL)
    urls = [a['url'] for a in articles]
    assert not any('/es/' in u for u in urls)

@responses_lib.activate
def test_fetch_kff_listing_page_returns_next_page_url_when_more_pages_exist():
    from agent.kff_scraper import _fetch_kff_listing_page
    responses_lib.add(responses_lib.GET, KFF_LISTING_URL, body=KFF_LISTING_HTML, status=200)
    _, next_url = _fetch_kff_listing_page(KFF_LISTING_URL)
    assert next_url == 'https://kffhealthnews.org/state/california/page/2/'

@responses_lib.activate
def test_fetch_kff_listing_page_returns_no_next_url_on_last_page():
    # When there is no next page link, pagination must stop.
    from agent.kff_scraper import _fetch_kff_listing_page
    responses_lib.add(responses_lib.GET, KFF_LISTING_URL, body=KFF_LISTING_LAST_PAGE_HTML, status=200)
    _, next_url = _fetch_kff_listing_page(KFF_LISTING_URL)
    assert next_url is None

@responses_lib.activate
def test_fetch_kff_listing_page_skips_urls_already_in_database():
    # A URL already in the articles table is excluded — its page is never fetched.
    from agent.kff_scraper import _fetch_kff_listing_page
    responses_lib.add(responses_lib.GET, KFF_LISTING_URL, body=KFF_LISTING_HTML, status=200)
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
    articles, _ = _fetch_kff_listing_page(KFF_LISTING_URL, conn=conn)
    assert articles == []


# =============================================================================
# _fetch_kff_article
# Fetches a single KFF article page using plain requests and returns a dict
# ready for insert. Extracts title, date, body, tags, category, and source.
# =============================================================================

@responses_lib.activate
def test_fetch_kff_article_returns_title_from_h1():
    from agent.kff_scraper import _fetch_kff_article
    responses_lib.add(responses_lib.GET, KFF_ARTICLE_URL, body=KFF_ARTICLE_HTML, status=200)
    article = _fetch_kff_article(KFF_ARTICLE_URL)
    assert article['title'] == 'Article One Title'

@responses_lib.activate
def test_fetch_kff_article_returns_body_text_from_main_p():
    # Body is all <p> elements inside <main>, concatenated and stripped.
    from agent.kff_scraper import _fetch_kff_article
    responses_lib.add(responses_lib.GET, KFF_ARTICLE_URL, body=KFF_ARTICLE_HTML, status=200)
    article = _fetch_kff_article(KFF_ARTICLE_URL)
    assert 'First paragraph' in article['body_text']
    assert 'Second paragraph' in article['body_text']

@responses_lib.activate
def test_fetch_kff_article_returns_date_from_json_ld_date_published():
    from agent.kff_scraper import _fetch_kff_article
    responses_lib.add(responses_lib.GET, KFF_ARTICLE_URL, body=KFF_ARTICLE_HTML, status=200)
    article = _fetch_kff_article(KFF_ARTICLE_URL)
    assert article['published_at'].year == 2026
    assert article['published_at'].month == 6
    assert article['published_at'].day == 18

@responses_lib.activate
def test_fetch_kff_article_returns_null_published_at_when_json_ld_date_published_absent():
    from agent.kff_scraper import _fetch_kff_article
    responses_lib.add(responses_lib.GET, KFF_ARTICLE_URL, body=KFF_ARTICLE_NO_DATE_HTML, status=200)
    article = _fetch_kff_article(KFF_ARTICLE_URL)
    assert article['published_at'] is None

@responses_lib.activate
def test_fetch_kff_article_returns_tags_from_json_ld_keywords():
    from agent.kff_scraper import _fetch_kff_article
    responses_lib.add(responses_lib.GET, KFF_ARTICLE_URL, body=KFF_ARTICLE_HTML, status=200)
    article = _fetch_kff_article(KFF_ARTICLE_URL)
    assert article['tags'] == ["Children's Health", "Immigrants"]

@responses_lib.activate
def test_fetch_kff_article_returns_null_tags_when_json_ld_keywords_absent():
    from agent.kff_scraper import _fetch_kff_article
    responses_lib.add(responses_lib.GET, KFF_ARTICLE_URL, body=KFF_ARTICLE_NO_TAGS_HTML, status=200)
    article = _fetch_kff_article(KFF_ARTICLE_URL)
    assert article['tags'] is None

@responses_lib.activate
def test_fetch_kff_article_sets_source_to_kffhealthnews():
    from agent.kff_scraper import _fetch_kff_article
    responses_lib.add(responses_lib.GET, KFF_ARTICLE_URL, body=KFF_ARTICLE_HTML, status=200)
    article = _fetch_kff_article(KFF_ARTICLE_URL)
    assert article['source'] == 'kffhealthnews.org'

@responses_lib.activate
def test_fetch_kff_article_sets_category_from_url_path():
    # Category is derived from the first path segment of the article URL.
    from agent.kff_scraper import _fetch_kff_article
    responses_lib.add(responses_lib.GET, KFF_ARTICLE_URL, body=KFF_ARTICLE_HTML, status=200)
    article = _fetch_kff_article(KFF_ARTICLE_URL)
    assert article['category'] == 'mental-health'


# =============================================================================
# _extract_category_from_url
# Derives a category string from the first path segment of a KFF article URL.
# e.g. https://kffhealthnews.org/mental-health/article-slug/ → 'mental-health'
# =============================================================================

def test_extract_category_from_url_returns_first_path_segment():
    from agent.kff_scraper import _extract_category_from_url
    result = _extract_category_from_url('https://kffhealthnews.org/mental-health/article-slug/')
    assert result == 'mental-health'

def test_extract_category_from_url_handles_insurance_segment():
    from agent.kff_scraper import _extract_category_from_url
    result = _extract_category_from_url('https://kffhealthnews.org/insurance/article-slug/')
    assert result == 'insurance'

def test_extract_category_from_url_returns_none_when_no_path_segment():
    from agent.kff_scraper import _extract_category_from_url
    result = _extract_category_from_url('https://kffhealthnews.org/')
    assert result is None


# =============================================================================
# run_backfill
# Orchestrates multi-page listing crawl: follows next_url across pages,
# stops when next_url is None OR page_limit is reached — whichever comes first.
# Each article URL is fetched and saved to the database.
# =============================================================================

_ARTICLE_STUB = {
    'title': 'Stub', 'published_at': None, 'body_text': 'stub body',
    'source': 'kffhealthnews.org', 'category': None, 'tags': None,
}

def _listing_entry(url):
    return {'url': url, 'title': 'T', 'date': '2026-01-01'}

def test_run_backfill_saves_articles_from_all_pages_when_last_page_has_no_next_url():
    from agent.kff_scraper import run_backfill
    mock_insert = MagicMock(return_value=True)
    with patch('agent.kff_scraper._fetch_kff_listing_page') as mock_listing, \
         patch('agent.kff_scraper._fetch_kff_article', side_effect=lambda url, conn=None: {**_ARTICLE_STUB, 'url': url}), \
         patch('agent.kff_scraper.get_connection', return_value=MagicMock()), \
         patch('agent.kff_scraper.release_connection'), \
         patch('agent.kff_scraper._open_run', return_value=1), \
         patch('agent.kff_scraper._close_run'), \
         patch('agent.kff_scraper._insert_article', mock_insert):
        mock_listing.side_effect = [
            ([_listing_entry('https://kffhealthnews.org/a/p1/')], 'https://kffhealthnews.org/state/california/page/2/'),
            ([_listing_entry('https://kffhealthnews.org/a/p2/')], 'https://kffhealthnews.org/state/california/page/3/'),
            ([_listing_entry('https://kffhealthnews.org/a/p3/')], None),
        ]
        run_backfill(page_limit=3)
    inserted_urls = [c.args[1]['url'] for c in mock_insert.call_args_list]
    assert 'https://kffhealthnews.org/a/p1/' in inserted_urls
    assert 'https://kffhealthnews.org/a/p2/' in inserted_urls
    assert 'https://kffhealthnews.org/a/p3/' in inserted_urls

def test_run_backfill_does_not_save_page_4_articles_when_page_limit_is_3():
    from agent.kff_scraper import run_backfill
    mock_insert = MagicMock(return_value=True)
    with patch('agent.kff_scraper._fetch_kff_listing_page') as mock_listing, \
         patch('agent.kff_scraper._fetch_kff_article', side_effect=lambda url, conn=None: {**_ARTICLE_STUB, 'url': url}), \
         patch('agent.kff_scraper.get_connection', return_value=MagicMock()), \
         patch('agent.kff_scraper.release_connection'), \
         patch('agent.kff_scraper._open_run', return_value=1), \
         patch('agent.kff_scraper._close_run'), \
         patch('agent.kff_scraper._insert_article', mock_insert):
        mock_listing.side_effect = [
            ([_listing_entry('https://kffhealthnews.org/a/p1/')], 'https://kffhealthnews.org/state/california/page/2/'),
            ([_listing_entry('https://kffhealthnews.org/a/p2/')], 'https://kffhealthnews.org/state/california/page/3/'),
            ([_listing_entry('https://kffhealthnews.org/a/p3/')], 'https://kffhealthnews.org/state/california/page/4/'),
        ]
        run_backfill(page_limit=3)
    inserted_urls = [c.args[1]['url'] for c in mock_insert.call_args_list]
    assert 'https://kffhealthnews.org/a/p4/' not in inserted_urls

def test_run_backfill_does_not_save_page_3_articles_when_page_2_has_no_next_url():
    from agent.kff_scraper import run_backfill
    mock_insert = MagicMock(return_value=True)
    with patch('agent.kff_scraper._fetch_kff_listing_page') as mock_listing, \
         patch('agent.kff_scraper._fetch_kff_article', side_effect=lambda url, conn=None: {**_ARTICLE_STUB, 'url': url}), \
         patch('agent.kff_scraper.get_connection', return_value=MagicMock()), \
         patch('agent.kff_scraper.release_connection'), \
         patch('agent.kff_scraper._open_run', return_value=1), \
         patch('agent.kff_scraper._close_run'), \
         patch('agent.kff_scraper._insert_article', mock_insert):
        mock_listing.side_effect = [
            ([_listing_entry('https://kffhealthnews.org/a/p1/')], 'https://kffhealthnews.org/state/california/page/2/'),
            ([_listing_entry('https://kffhealthnews.org/a/p2/')], None),
        ]
        run_backfill(page_limit=3)
    inserted_urls = [c.args[1]['url'] for c in mock_insert.call_args_list]
    assert 'https://kffhealthnews.org/a/p3/' not in inserted_urls
