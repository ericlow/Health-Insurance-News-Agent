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

FIXTURES = Path(__file__).parent / 'fixtures'
FEED_XML = (FIXTURES / 'beckerspayer_feed.xml').read_bytes()
SITEMAP_INDEX_XML = (FIXTURES / 'beckerspayer_sitemap_index.xml').read_bytes()
POST_SITEMAP_XML = (FIXTURES / 'beckerspayer_post_sitemap.xml').read_bytes()


# --- _fetch_feed ---

@responses_lib.activate
def test_fetch_feed_returns_entries():
    responses_lib.add(responses_lib.GET, BECKERS_PAYER_FEED_URL, body=FEED_XML, status=200)
    entries = _fetch_feed()
    assert len(entries) == 10

@responses_lib.activate
def test_fetch_feed_entry_shape():
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
    responses_lib.add(responses_lib.GET, BECKERS_PAYER_FEED_URL, body=FEED_XML, status=200)
    entries = _fetch_feed()
    for entry in entries:
        assert '<' not in entry['body_text'], f"HTML tag found in body: {entry['body_text'][:100]}"

@responses_lib.activate
def test_fetch_feed_extracts_category():
    responses_lib.add(responses_lib.GET, BECKERS_PAYER_FEED_URL, body=FEED_XML, status=200)
    entries = _fetch_feed()
    assert all(entry['category'] is not None for entry in entries)

@responses_lib.activate
def test_fetch_feed_extracts_tags_as_list():
    responses_lib.add(responses_lib.GET, BECKERS_PAYER_FEED_URL, body=FEED_XML, status=200)
    entries = _fetch_feed()
    assert all(isinstance(entry['tags'], list) for entry in entries)

@responses_lib.activate
def test_fetch_feed_multi_tag_entry():
    responses_lib.add(responses_lib.GET, BECKERS_PAYER_FEED_URL, body=FEED_XML, status=200)
    entries = _fetch_feed()
    multi = [e for e in entries if len(e['tags']) > 1]
    assert len(multi) > 0, "Expected at least one entry with multiple tags"


# --- _parse_date_str ---

def test_parse_date_str_iso():
    dt = _parse_date_str('2026-06-04T00:00:00Z')
    assert dt.year == 2026
    assert dt.month == 6
    assert dt.day == 4
    assert dt.tzinfo == timezone.utc

def test_parse_date_str_human_readable():
    dt = _parse_date_str('Thursday, June 4th, 2026')
    assert dt.year == 2026
    assert dt.month == 6
    assert dt.day == 4

def test_parse_date_str_none():
    assert _parse_date_str(None) is None

def test_parse_date_str_empty():
    assert _parse_date_str('') is None


# --- _already_seen ---

def test_already_seen_true():
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
    assert _already_seen(conn, 'https://example.com/article/') is True

def test_already_seen_false():
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = None
    assert _already_seen(conn, 'https://example.com/article/') is False


# --- _insert_article ---

def test_insert_article_returns_true_on_insert():
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
    args = cursor.execute.call_args[0][1]
    assert args[0] == entry['url']
    assert args[1] == entry['title']
    assert args[4] == 'beckerspayer.com'
    assert args[5] == 'payer'
    assert args[6] == ['Medicaid', 'Payer']
