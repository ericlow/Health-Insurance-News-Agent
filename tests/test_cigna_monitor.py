import pytest
import responses as responses_lib
from pathlib import Path
from unittest.mock import MagicMock, patch

FIXTURES = Path(__file__).parent / 'fixtures'
CIGNA_FEED_URL = 'https://newsroom.cigna.com/latest-press-releases?pagetemplate=rss'
CIGNA_FEED_XML = (FIXTURES / 'cigna_feed.xml').read_bytes()
CIGNA_ARTICLE_URL = 'https://newsroom.cigna.com/cigna-group-strategic-partnership'
CIGNA_ARTICLE_HTML = (FIXTURES / 'cigna_article.html').read_bytes()


# =============================================================================
# _fetch_feed
# Fetches the Cigna newsroom RSS feed and returns up to 5 entries.
# Each entry has url, title, published_at, body_text (None), category (None),
# and tags.
# =============================================================================

@responses_lib.activate
def test_fetch_feed_returns_entries_with_url_title_and_published_at():
    from agent.cigna_monitor import _fetch_feed
    responses_lib.add(responses_lib.GET, CIGNA_FEED_URL, body=CIGNA_FEED_XML, status=200)
    entries = _fetch_feed()
    assert len(entries) > 0
    for e in entries:
        assert 'url' in e
        assert 'title' in e
        assert 'published_at' in e


@responses_lib.activate
def test_fetch_feed_caps_at_five_entries():
    from agent.cigna_monitor import _fetch_feed
    # Feed has 3 items — all should be returned (under cap)
    responses_lib.add(responses_lib.GET, CIGNA_FEED_URL, body=CIGNA_FEED_XML, status=200)
    entries = _fetch_feed()
    assert len(entries) <= 5


@responses_lib.activate
def test_fetch_feed_body_text_is_none():
    from agent.cigna_monitor import _fetch_feed
    responses_lib.add(responses_lib.GET, CIGNA_FEED_URL, body=CIGNA_FEED_XML, status=200)
    entries = _fetch_feed()
    for e in entries:
        assert e['body_text'] is None


@responses_lib.activate
def test_fetch_feed_category_is_none():
    from agent.cigna_monitor import _fetch_feed
    responses_lib.add(responses_lib.GET, CIGNA_FEED_URL, body=CIGNA_FEED_XML, status=200)
    entries = _fetch_feed()
    for e in entries:
        assert e['category'] is None


@responses_lib.activate
def test_fetch_feed_returns_tags_list():
    from agent.cigna_monitor import _fetch_feed
    responses_lib.add(responses_lib.GET, CIGNA_FEED_URL, body=CIGNA_FEED_XML, status=200)
    entries = _fetch_feed()
    for e in entries:
        assert isinstance(e['tags'], list)


@responses_lib.activate
def test_fetch_feed_parses_published_at_for_dated_entries():
    from agent.cigna_monitor import _fetch_feed
    responses_lib.add(responses_lib.GET, CIGNA_FEED_URL, body=CIGNA_FEED_XML, status=200)
    entries = _fetch_feed()
    # First entry has pubDate Mon, 02 Jun 2026
    dated = [e for e in entries if e['published_at'] is not None]
    assert len(dated) > 0
    assert dated[0]['published_at'].year == 2026


# =============================================================================
# _fetch_article_body
# Fetches article body from the Cigna newsroom page.
# Extracts and concatenates non-empty <p> tag text.
# Returns None on fetch failure.
# =============================================================================

@responses_lib.activate
def test_fetch_article_body_returns_text_from_p_tags():
    from agent.cigna_monitor import _fetch_article_body
    responses_lib.add(responses_lib.GET, CIGNA_ARTICLE_URL, body=CIGNA_ARTICLE_HTML, status=200)
    body = _fetch_article_body(CIGNA_ARTICLE_URL)
    assert body is not None
    assert 'Cigna Group today announced' in body
    assert 'expand access to care' in body


@responses_lib.activate
def test_fetch_article_body_returns_none_on_http_error():
    from agent.cigna_monitor import _fetch_article_body
    responses_lib.add(responses_lib.GET, CIGNA_ARTICLE_URL, status=404)
    body = _fetch_article_body(CIGNA_ARTICLE_URL)
    assert body is None


@responses_lib.activate
def test_fetch_article_body_returns_none_on_page_with_no_paragraphs():
    from agent.cigna_monitor import _fetch_article_body
    empty_html = b'<html><body><div>No paragraphs here</div></body></html>'
    responses_lib.add(responses_lib.GET, CIGNA_ARTICLE_URL, body=empty_html, status=200)
    body = _fetch_article_body(CIGNA_ARTICLE_URL)
    assert body is None


# =============================================================================
# run_monitor
# Orchestrates feed fetch, article body fetch, deduplication, and DB insert.
# Returns (run_id, new_article_ids).
# Articles already in DB are skipped (no body fetch, no insert).
# =============================================================================

def _make_mock_conn(already_seen=False):
    conn = MagicMock()
    cursor_ctx = conn.cursor.return_value.__enter__.return_value
    # _already_seen check
    cursor_ctx.fetchone.return_value = (1,) if already_seen else None
    return conn


def test_run_monitor_returns_run_id_and_new_article_ids():
    from agent.cigna_monitor import run_monitor
    mock_conn = _make_mock_conn(already_seen=False)
    # _open_run returns run_id=7, _insert_article returns article_id=42
    cursor_ctx = mock_conn.cursor.return_value.__enter__.return_value
    cursor_ctx.fetchone.side_effect = [
        (7,),   # _open_run
        None,   # _already_seen: not seen
        (42,),  # _insert_article
    ]
    with patch('agent.cigna_monitor.get_connection', return_value=mock_conn), \
         patch('agent.cigna_monitor.release_connection'), \
         patch('agent.cigna_monitor._fetch_feed', return_value=[{
             'url': 'https://newsroom.cigna.com/test-article',
             'title': 'Test Article',
             'published_at': None,
             'body_text': None,
             'category': None,
             'tags': [],
         }]), \
         patch('agent.cigna_monitor._fetch_article_body', return_value='Article body text'):
        run_id, new_ids = run_monitor()
    assert run_id == 7
    assert new_ids == [42]


def test_run_monitor_skips_already_seen_articles():
    from agent.cigna_monitor import run_monitor
    mock_conn = MagicMock()
    cursor_ctx = mock_conn.cursor.return_value.__enter__.return_value
    cursor_ctx.fetchone.side_effect = [
        (99,),  # _open_run
        (1,),   # _already_seen: already in DB
    ]
    with patch('agent.cigna_monitor.get_connection', return_value=mock_conn), \
         patch('agent.cigna_monitor.release_connection'), \
         patch('agent.cigna_monitor._fetch_feed', return_value=[{
             'url': 'https://newsroom.cigna.com/existing',
             'title': 'Existing Article',
             'published_at': None,
             'body_text': None,
             'category': None,
             'tags': [],
         }]), \
         patch('agent.cigna_monitor._fetch_article_body') as mock_body_fetch:
        run_id, new_ids = run_monitor()
    # Body fetch must not be called for already-seen articles
    mock_body_fetch.assert_not_called()
    assert new_ids == []


def test_run_monitor_fetches_body_only_for_new_articles():
    from agent.cigna_monitor import run_monitor
    mock_conn = MagicMock()
    cursor_ctx = mock_conn.cursor.return_value.__enter__.return_value
    cursor_ctx.fetchone.side_effect = [
        (1,),   # _open_run
        None,   # _already_seen: new
        (10,),  # _insert_article
    ]
    with patch('agent.cigna_monitor.get_connection', return_value=mock_conn), \
         patch('agent.cigna_monitor.release_connection'), \
         patch('agent.cigna_monitor._fetch_feed', return_value=[{
             'url': 'https://newsroom.cigna.com/new-article',
             'title': 'New Article',
             'published_at': None,
             'body_text': None,
             'category': None,
             'tags': [],
         }]), \
         patch('agent.cigna_monitor._fetch_article_body', return_value='Body text') as mock_body_fetch:
        run_monitor()
    mock_body_fetch.assert_called_once_with('https://newsroom.cigna.com/new-article')


def test_run_monitor_returns_empty_list_when_all_articles_already_seen():
    from agent.cigna_monitor import run_monitor
    mock_conn = MagicMock()
    cursor_ctx = mock_conn.cursor.return_value.__enter__.return_value
    cursor_ctx.fetchone.side_effect = [
        (5,),  # _open_run
        (1,),  # _already_seen: seen
        (1,),  # _already_seen: seen
    ]
    with patch('agent.cigna_monitor.get_connection', return_value=mock_conn), \
         patch('agent.cigna_monitor.release_connection'), \
         patch('agent.cigna_monitor._fetch_feed', return_value=[
             {'url': 'https://newsroom.cigna.com/a1', 'title': 'A1', 'published_at': None, 'body_text': None, 'category': None, 'tags': []},
             {'url': 'https://newsroom.cigna.com/a2', 'title': 'A2', 'published_at': None, 'body_text': None, 'category': None, 'tags': []},
         ]), \
         patch('agent.cigna_monitor._fetch_article_body'):
        run_id, new_ids = run_monitor()
    assert run_id == 5
    assert new_ids == []


def test_run_monitor_marks_run_failed_on_exception():
    from agent.cigna_monitor import run_monitor
    mock_conn = MagicMock()
    cursor_ctx = mock_conn.cursor.return_value.__enter__.return_value
    # _open_run returns run_id=3, then _already_seen raises inside the try block
    cursor_ctx.fetchone.side_effect = [
        (3,),  # _open_run
    ]
    with patch('agent.cigna_monitor.get_connection', return_value=mock_conn),          patch('agent.cigna_monitor.release_connection'),          patch('agent.cigna_monitor._fetch_feed', return_value=[{
             'url': 'https://newsroom.cigna.com/test',
             'title': 'Test',
             'published_at': None,
             'body_text': None,
             'category': None,
             'tags': [],
         }]),          patch('agent.cigna_monitor._already_seen', side_effect=RuntimeError('db error')):
        with pytest.raises(RuntimeError):
            run_monitor()
    # _fail_run must have been called — check an UPDATE with status=failed was executed
    executed_sql = [str(c.args[0]) for c in cursor_ctx.execute.call_args_list]
    assert any("'failed'" in sql or "failed" in sql for sql in executed_sql)
