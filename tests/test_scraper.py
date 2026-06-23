import pytest
import responses as responses_lib
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from agent.scraper import (
    _fetch_feed,
    _parse_feed_date,
    _parse_date_str,
    _already_seen,
    _insert_article,
    BECKERS_PAYER_FEED_URL,
)

# Fixture files stand in for real HTTP responses so tests never hit the network.
# beckerspayer_feed.xml is a saved copy of the actual RSS feed.
# beckerspayer_listing.html is a minimal stand-in for a category listing page.
FIXTURES = Path(__file__).parent / 'fixtures'
FEED_XML = (FIXTURES / 'beckerspayer_feed.xml').read_bytes()
LISTING_HTML = (FIXTURES / 'beckerspayer_listing.html').read_bytes()


# =============================================================================
# _fetch_feed
# Reads the Becker's Payer RSS feed and returns a list of article dicts.
# @responses_lib.activate intercepts the HTTP call and returns the fixture
# instead — no real network request is made.
# =============================================================================

@responses_lib.activate
def test_fetch_feed_returns_entries():
    # The live feed returns exactly 10 items; we should read all of them.
    responses_lib.add(responses_lib.GET, BECKERS_PAYER_FEED_URL, body=FEED_XML, status=200)
    entries = _fetch_feed()
    assert len(entries) == 10

@responses_lib.activate
def test_fetch_feed_entry_shape():
    # Every entry must carry these fields before it can be written to the DB.
    responses_lib.add(responses_lib.GET, BECKERS_PAYER_FEED_URL, body=FEED_XML, status=200)
    entries = _fetch_feed()
    entry = entries[0]
    assert 'url' in entry
    assert 'title' in entry
    assert 'body_text' in entry
    assert 'published_at' in entry
    assert 'category' in entry
    assert 'tags' in entry

@responses_lib.activate
def test_fetch_feed_strips_html_from_body():
    # The RSS content:encoded field is raw HTML. We store plain text in the DB,
    # so HTML tags must be stripped before insert.
    responses_lib.add(responses_lib.GET, BECKERS_PAYER_FEED_URL, body=FEED_XML, status=200)
    entries = _fetch_feed()
    for entry in entries:
        assert '<' not in entry['body_text'], f"HTML tag found in body: {entry['body_text'][:100]}"

@responses_lib.activate
def test_fetch_feed_extracts_category():
    # Category must come from the RSS feed's own tag taxonomy, not the URL.
    # (Parsing the URL was a bug — the fix is confirmed here.)
    responses_lib.add(responses_lib.GET, BECKERS_PAYER_FEED_URL, body=FEED_XML, status=200)
    entries = _fetch_feed()
    assert all(entry['category'] is not None for entry in entries)

@responses_lib.activate
def test_fetch_feed_extracts_tags_as_list():
    # Tags are stored as a PostgreSQL TEXT[] array, so Python must produce a list.
    responses_lib.add(responses_lib.GET, BECKERS_PAYER_FEED_URL, body=FEED_XML, status=200)
    entries = _fetch_feed()
    assert all(isinstance(entry['tags'], list) for entry in entries)

@responses_lib.activate
def test_fetch_feed_multi_tag_entry():
    # WordPress articles can carry multiple taxonomy terms (e.g. 'Payer' + 'Medicare Advantage').
    # We must store all of them, not just the first.
    responses_lib.add(responses_lib.GET, BECKERS_PAYER_FEED_URL, body=FEED_XML, status=200)
    entries = _fetch_feed()
    multi = [e for e in entries if len(e['tags']) > 1]
    assert len(multi) > 0, "Expected at least one entry with multiple tags"


# =============================================================================
# _parse_date_str
# Parses date strings found in the <time> element on individual article pages.
# Two formats observed in the wild: ISO 8601 and human-readable.
# Returns None instead of raising so a bad date never crashes the scraper.
# =============================================================================

def test_parse_date_str_iso():
    # ISO 8601 is the structured machine-readable format from the datetime attribute.
    dt = _parse_date_str('2026-06-04T00:00:00Z')
    assert dt.year == 2026
    assert dt.month == 6
    assert dt.day == 4
    assert dt.tzinfo == timezone.utc

def test_parse_date_str_human_readable():
    # Fallback format when the datetime attribute is absent — read from element text.
    dt = _parse_date_str('Thursday, June 4th, 2026')
    assert dt.year == 2026
    assert dt.month == 6
    assert dt.day == 4

def test_parse_date_str_none():
    # A missing date field must not raise — the article is still stored without a date.
    assert _parse_date_str(None) is None

def test_parse_date_str_empty():
    # An empty string (e.g. empty datetime attribute) is treated the same as missing.
    assert _parse_date_str('') is None


# =============================================================================
# _already_seen
# Checks the articles table for a URL before fetching or inserting.
# MagicMock stands in for the real psycopg2 connection — no DB required.
# The mock simulates the cursor context manager that _already_seen uses internally.
# fetchone returning (1,) = a row exists. None = no row found.
# =============================================================================

def test_already_seen_true():
    # If the URL is in the DB, skip it — don't re-fetch or re-insert.
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
    assert _already_seen(conn, 'https://example.com/article/') is True

def test_already_seen_false():
    # If the URL is not in the DB, it's a new article — proceed with fetch and insert.
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = None
    assert _already_seen(conn, 'https://example.com/article/') is False


# =============================================================================
# _insert_article
# Writes one article row to the DB using ON CONFLICT DO NOTHING on the URL column.
# rowcount = 1 means the row was inserted. rowcount = 0 means it already existed.
# We use MagicMock to avoid needing a real DB connection in unit tests.
# =============================================================================

def test_insert_article_returns_true_on_insert():
    # A new article should be written to the DB and return True so the run count is incremented.
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.rowcount = 1
    entry = {
        'url': 'https://www.beckerspayer.com/contracting/test/',
        'title': 'Test Article',
        'published_at': datetime(2026, 6, 4, tzinfo=timezone.utc),
        'body_text': 'Some body text.',
        'category': 'contracting',
        'tags': ['Legal', 'Contracting'],
    }
    assert _insert_article(conn, entry, run_id=1) is True

def test_insert_article_returns_false_on_conflict():
    # If the URL already exists, ON CONFLICT DO NOTHING fires and rowcount is 0.
    # Return False so the run count is not incremented for a duplicate.
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.rowcount = 0
    entry = {
        'url': 'https://www.beckerspayer.com/contracting/test/',
        'title': 'Test Article',
        'published_at': None,
        'body_text': '',
        'category': 'contracting',
        'tags': [],
    }
    assert _insert_article(conn, entry, run_id=1) is False

def test_insert_article_passes_correct_fields():
    # Guards against accidentally reordering the SQL parameters — the column order
    # in the INSERT must match the values tuple exactly or data ends up in the wrong column.
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.rowcount = 1
    entry = {
        'url': 'https://www.beckerspayer.com/payer/medicaid/test/',
        'title': 'Medicaid Article',
        'published_at': datetime(2026, 6, 1, tzinfo=timezone.utc),
        'body_text': 'Body text.',
        'category': 'payer',
        'tags': ['Medicaid', 'Payer'],
    }
    _insert_article(conn, entry, run_id=42)
    args = cursor.execute.call_args[0][1]  # positional args passed to cursor.execute
    assert args[0] == entry['url']
    assert args[1] == entry['title']
    assert args[4] == 'beckerspayer.com'  # source is always the domain, not the full URL
    assert args[5] == 'payer'
    assert args[6] == ['Medicaid', 'Payer']


# =============================================================================
# BACKFILL BEHAVIORAL SPECS (AGE-7)
# All tests below are stubs — they fail with ImportError until the functions
# are implemented. This commit is the "red" state in red-green-refactor.
#
# The backfill works differently from RSS:
#   1. Fetch category listing pages (e.g. /executive-moves/) with plain requests
#   2. Parse article URLs and dates from the listing — no CDP needed yet
#   3. Skip articles older than the cutoff date and URLs already in the DB
#   4. Only then open a Chrome CDP session to fetch the full article pages
# =============================================================================

LISTING_URL = 'https://www.beckerspayer.com/executive-moves/'
CUTOFF_RECENT = datetime(2026, 6, 17, tzinfo=timezone.utc)  # 5-day window: Jun 17–22
CUTOFF_FUTURE = datetime(2030, 1, 1, tzinfo=timezone.utc)   # nothing passes this cutoff


# =============================================================================
# load_config
# Reads scraper configuration from a JSON file.
# In production this would point to SSM Parameter Store or S3 instead.
# Fails loudly on missing file or missing fields so misconfiguration is obvious.
# =============================================================================

def test_load_config_returns_rss_feeds_when_given_valid_file():
    from agent.scraper import load_config
    config = load_config(str(FIXTURES / 'config.json'))
    assert isinstance(config['rss_feeds'], list)
    assert len(config['rss_feeds']) > 0

def test_load_config_returns_backfill_urls_when_given_valid_file():
    # These are category listing page URLs, not individual article URLs.
    from agent.scraper import load_config
    config = load_config(str(FIXTURES / 'config.json'))
    assert isinstance(config['backfill_urls'], list)
    assert len(config['backfill_urls']) > 0

def test_load_config_returns_min_articles_when_given_valid_file():
    from agent.scraper import load_config
    config = load_config(str(FIXTURES / 'config.json'))
    assert isinstance(config['min_articles'], int)

def test_load_config_returns_cutoff_date_when_given_valid_file():
    # cutoff_date is stored as a string in JSON but returned as a datetime object.
    from agent.scraper import load_config
    config = load_config(str(FIXTURES / 'config.json'))
    assert isinstance(config['cutoff_date'], datetime)

def test_load_config_raises_when_config_file_not_found():
    # A missing config file must raise immediately — not silently return empty config.
    from agent.scraper import load_config
    with pytest.raises(Exception):
        load_config(str(FIXTURES / 'nonexistent.json'))

def test_load_config_raises_when_required_field_is_missing():
    # A config file that omits backfill_urls (or any required field) must raise.
    from agent.scraper import load_config
    with pytest.raises(Exception):
        load_config(str(FIXTURES / 'config_missing_field.json'))

def test_load_config_raises_when_backfill_url_list_is_empty():
    # An empty backfill URL list means there is nothing to crawl — fail loudly.
    from agent.scraper import load_config
    with pytest.raises(Exception):
        load_config(str(FIXTURES / 'config_empty_backfill.json'))


# =============================================================================
# _fetch_listing_page
# Fetches one page of a category listing (e.g. /executive-moves/).
# Listing pages are Cloudflare-blocked — production uses CDP (page parameter).
# Unit tests pass page=None so the function falls back to requests, which
# responses_lib intercepts; the HTML parsing logic is identical either way.
# Returns (articles_within_cutoff, next_page_url_or_none).
# next_page_url is None when the cutoff is reached or there are no more pages.
# =============================================================================

@responses_lib.activate
def test_fetch_listing_page_returns_articles_with_url_title_and_date():
    # Each article in the returned list must carry url, title, and date
    # so the orchestrator can filter and then fetch the full page via CDP.
    from agent.scraper import _fetch_listing_page
    responses_lib.add(responses_lib.GET, LISTING_URL, body=LISTING_HTML, status=200)
    articles, _ = _fetch_listing_page(LISTING_URL, cutoff=CUTOFF_RECENT)
    assert len(articles) > 0
    for a in articles:
        assert 'url' in a and 'title' in a and 'date' in a

@responses_lib.activate
def test_fetch_listing_page_excludes_articles_older_than_cutoff():
    # Articles older than the cutoff must be filtered out at the listing stage —
    # their full pages must never be fetched via CDP.
    from agent.scraper import _fetch_listing_page
    responses_lib.add(responses_lib.GET, LISTING_URL, body=LISTING_HTML, status=200)
    articles, _ = _fetch_listing_page(LISTING_URL, cutoff=CUTOFF_FUTURE)
    assert articles == []

@responses_lib.activate
def test_fetch_listing_page_returns_next_page_url_when_recent_articles_exist():
    # If any article on this page passed the cutoff, there may be more on the next
    # page — return the Next link so the orchestrator continues paginating.
    from agent.scraper import _fetch_listing_page
    responses_lib.add(responses_lib.GET, LISTING_URL, body=LISTING_HTML, status=200)
    _, next_url = _fetch_listing_page(LISTING_URL, cutoff=CUTOFF_RECENT)
    assert next_url == 'https://www.beckerspayer.com/executive-moves/page/2/'

@responses_lib.activate
def test_fetch_listing_page_returns_no_next_page_url_when_cutoff_reached():
    # If all articles on this page are older than the cutoff, stop paginating —
    # older pages will only have even older articles.
    from agent.scraper import _fetch_listing_page
    responses_lib.add(responses_lib.GET, LISTING_URL, body=LISTING_HTML, status=200)
    _, next_url = _fetch_listing_page(LISTING_URL, cutoff=CUTOFF_FUTURE)
    assert next_url is None

@responses_lib.activate
def test_fetch_listing_page_skips_urls_already_in_database():
    # URLs already in the articles table must be excluded before CDP is opened —
    # we never re-fetch a page we already have.
    # MagicMock simulates a DB connection where every URL lookup returns a hit.
    from agent.scraper import _fetch_listing_page
    responses_lib.add(responses_lib.GET, LISTING_URL, body=LISTING_HTML, status=200)
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
    articles, _ = _fetch_listing_page(LISTING_URL, cutoff=CUTOFF_RECENT, conn=conn)
    assert articles == []
