import json
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from agent.sutter_monitor import FEED_URL


# ---------------------------------------------------------------------------
# Sample API response fixture
# ---------------------------------------------------------------------------

_SAMPLE_POSTS = [
    {
        'link': 'https://vitals.sutterhealth.org/sutter-health-partners-with-acme/',
        'title': {'rendered': 'Sutter Health Partners with Acme'},
        'date': '2026-06-15T09:00:00',
        'content': {'rendered': '<p>First paragraph.</p><p>Second paragraph.</p>'},
        'slug': 'sutter-health-partners-with-acme',
    },
    {
        'link': 'https://vitals.sutterhealth.org/sutter-opens-new-clinic/',
        'title': {'rendered': 'Sutter Opens New Clinic'},
        'date': '2026-05-20T08:00:00',
        'content': {'rendered': '<p>Clinic body text.</p>'},
        'slug': 'sutter-opens-new-clinic',
    },
]

_SAMPLE_JSON = json.dumps(_SAMPLE_POSTS).encode()


# =============================================================================
# _fetch_feed
# Calls the WordPress REST API and returns a list of entry dicts.
# Each entry has url, title, published_at, and body_text.
# =============================================================================

def test_fetch_feed_returns_list_of_entries():
    from agent.sutter_monitor import _fetch_feed
    with patch('agent.sutter_monitor.requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = _SAMPLE_POSTS
        entries = _fetch_feed()
    assert len(entries) == 2


def test_fetch_feed_entry_has_required_keys():
    from agent.sutter_monitor import _fetch_feed
    with patch('agent.sutter_monitor.requests.get') as mock_get:
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = _SAMPLE_POSTS
        entries = _fetch_feed()
    for e in entries:
        assert 'url' in e
        assert 'title' in e
        assert 'published_at' in e
        assert 'body_text' in e


def test_fetch_feed_sets_url_from_link_field():
    from agent.sutter_monitor import _fetch_feed
    with patch('agent.sutter_monitor.requests.get') as mock_get:
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = _SAMPLE_POSTS
        entries = _fetch_feed()
    assert entries[0]['url'] == 'https://vitals.sutterhealth.org/sutter-health-partners-with-acme/'


def test_fetch_feed_strips_html_from_title():
    from agent.sutter_monitor import _fetch_feed
    posts = [
        {**_SAMPLE_POSTS[0], 'title': {'rendered': '<strong>Bold Title</strong>'}},
    ]
    with patch('agent.sutter_monitor.requests.get') as mock_get:
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = posts
        entries = _fetch_feed()
    assert entries[0]['title'] == 'Bold Title'


def test_fetch_feed_strips_html_from_body():
    from agent.sutter_monitor import _fetch_feed
    with patch('agent.sutter_monitor.requests.get') as mock_get:
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = _SAMPLE_POSTS
        entries = _fetch_feed()
    assert 'First paragraph.' in entries[0]['body_text']
    assert 'Second paragraph.' in entries[0]['body_text']
    assert '<p>' not in entries[0]['body_text']


def test_fetch_feed_parses_published_at_as_utc_datetime():
    from agent.sutter_monitor import _fetch_feed
    with patch('agent.sutter_monitor.requests.get') as mock_get:
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = _SAMPLE_POSTS
        entries = _fetch_feed()
    dt = entries[0]['published_at']
    assert isinstance(dt, datetime)
    assert dt.year == 2026
    assert dt.month == 6
    assert dt.day == 15
    assert dt.tzinfo is not None


# =============================================================================
# _parse_date
# Parses ISO 8601 strings from the WordPress API into aware datetimes.
# WordPress omits timezone — treat as UTC.
# =============================================================================

def test_parse_date_returns_utc_datetime_for_valid_string():
    from agent.sutter_monitor import _parse_date
    result = _parse_date('2026-06-15T09:00:00')
    assert result == datetime(2026, 6, 15, 9, 0, 0, tzinfo=timezone.utc)


def test_parse_date_returns_none_for_empty_string():
    from agent.sutter_monitor import _parse_date
    assert _parse_date('') is None


def test_parse_date_returns_none_for_none_input():
    from agent.sutter_monitor import _parse_date
    assert _parse_date(None) is None


def test_parse_date_returns_none_for_invalid_string():
    from agent.sutter_monitor import _parse_date
    assert _parse_date('not-a-date') is None


# =============================================================================
# _strip_html
# Removes all HTML tags and returns plain text.
# =============================================================================

def test_strip_html_removes_tags():
    from agent.sutter_monitor import _strip_html
    result = _strip_html('<p>Hello world.</p>')
    assert 'Hello world.' in result


def test_strip_html_handles_empty_string():
    from agent.sutter_monitor import _strip_html
    assert _strip_html('') == ''


# =============================================================================
# run_monitor
# Orchestrates fetch → dedup → insert → close run.
# Returns (run_id, new_article_ids).
# =============================================================================

def _mock_conn(already_seen=False):
    """Return a mock DB connection whose cursor returns sensible defaults."""
    conn = MagicMock()
    cursor_ctx = conn.cursor.return_value.__enter__.return_value
    # _already_seen check
    cursor_ctx.fetchone.return_value = (1,) if already_seen else None
    return conn


def test_run_monitor_returns_run_id_and_new_ids_when_articles_are_new():
    from agent.sutter_monitor import run_monitor
    conn = MagicMock()
    cursor_ctx = conn.cursor.return_value.__enter__.return_value
    # First call: _open_run → returns run_id=7
    # Subsequent calls: _already_seen → None (not seen), _insert_article → (42,) then (43,)
    cursor_ctx.fetchone.side_effect = [(7,), None, (42,), None, (43,)]

    with patch('agent.sutter_monitor._fetch_feed', return_value=[
            {'url': 'https://vitals.sutterhealth.org/a/', 'title': 'A', 'published_at': None, 'body_text': 'body a'},
            {'url': 'https://vitals.sutterhealth.org/b/', 'title': 'B', 'published_at': None, 'body_text': 'body b'},
        ]), \
         patch('agent.sutter_monitor.get_connection', return_value=conn), \
         patch('agent.sutter_monitor.release_connection'):
        run_id, new_ids = run_monitor()

    assert run_id == 7
    assert set(new_ids) == {42, 43}


def test_run_monitor_skips_already_seen_articles():
    from agent.sutter_monitor import run_monitor
    conn = MagicMock()
    cursor_ctx = conn.cursor.return_value.__enter__.return_value
    # _open_run → 1, _already_seen → (1,) = already seen for both
    cursor_ctx.fetchone.side_effect = [(1,), (1,), (1,)]

    with patch('agent.sutter_monitor._fetch_feed', return_value=[
            {'url': 'https://vitals.sutterhealth.org/a/', 'title': 'A', 'published_at': None, 'body_text': 'body'},
            {'url': 'https://vitals.sutterhealth.org/b/', 'title': 'B', 'published_at': None, 'body_text': 'body'},
        ]), \
         patch('agent.sutter_monitor.get_connection', return_value=conn), \
         patch('agent.sutter_monitor.release_connection'):
        run_id, new_ids = run_monitor()

    assert new_ids == []


def test_run_monitor_releases_connection_on_success():
    from agent.sutter_monitor import run_monitor
    conn = MagicMock()
    cursor_ctx = conn.cursor.return_value.__enter__.return_value
    cursor_ctx.fetchone.side_effect = [(99,)]

    with patch('agent.sutter_monitor._fetch_feed', return_value=[]), \
         patch('agent.sutter_monitor.get_connection', return_value=conn), \
         patch('agent.sutter_monitor.release_connection') as mock_release:
        run_monitor()

    mock_release.assert_called_once_with(conn)


def test_run_monitor_releases_connection_on_error():
    # Error occurs inside the try block (via _already_seen) so the finally runs.
    from agent.sutter_monitor import run_monitor
    conn = MagicMock()
    cursor_ctx = conn.cursor.return_value.__enter__.return_value
    cursor_ctx.fetchone.return_value = (1,)  # _open_run returns run_id=1

    with patch('agent.sutter_monitor._fetch_feed', return_value=[
            {'url': 'https://vitals.sutterhealth.org/x/', 'title': 'T', 'published_at': None, 'body_text': 'b'},
        ]), \
         patch('agent.sutter_monitor._already_seen', side_effect=RuntimeError('db error')), \
         patch('agent.sutter_monitor.get_connection', return_value=conn), \
         patch('agent.sutter_monitor.release_connection') as mock_release, \
         patch('agent.sutter_monitor._open_run', return_value=1), \
         patch('agent.sutter_monitor._fail_run'):
        with pytest.raises(RuntimeError):
            run_monitor()

    mock_release.assert_called_once_with(conn)


# =============================================================================
# Constants
# =============================================================================

def test_feed_url_points_to_sutter_health_press_releases():
    assert 'sutterhealth.org' in FEED_URL
    assert 'categories=542' in FEED_URL


def test_source_label_is_feed_url():
    # The source stored in the DB is the FEED_URL constant, not a bare hostname.
    from agent.sutter_monitor import FEED_URL, _insert_article
    conn = MagicMock()
    cursor_ctx = conn.cursor.return_value.__enter__.return_value
    cursor_ctx.fetchone.return_value = (1,)
    _insert_article(conn, {'url': 'https://vitals.sutterhealth.org/x/', 'title': 'T', 'published_at': None, 'body_text': 'b'}, run_id=1)
    call_args = cursor_ctx.execute.call_args
    # source is the 5th positional param in the INSERT VALUES tuple
    params = call_args[0][1]
    assert params[4] == FEED_URL
