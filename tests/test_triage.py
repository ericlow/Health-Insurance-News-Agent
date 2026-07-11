from unittest.mock import MagicMock, patch
import json

from agent.triage import (
    run_triage, _fetch_article, _call_haiku_title, _call_haiku_article,
    _insert_triage_result, _parse_response, MODEL,
)


# =============================================================================
# _fetch_article
# =============================================================================

def test_fetch_article_returns_dict():
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (
        1, 'Test Title', 'Body text here.'
    )
    result = _fetch_article(conn, 1)
    assert result == {'id': 1, 'title': 'Test Title', 'body_text': 'Body text here.'}


def test_fetch_article_returns_none_when_missing():
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = None
    assert _fetch_article(conn, 999) is None


def test_fetch_article_coerces_none_fields():
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (1, None, None)
    result = _fetch_article(conn, 1)
    assert result['title'] == ''
    assert result['body_text'] == ''


# =============================================================================
# _parse_response
# =============================================================================

def test_parse_response_plain_json():
    result = _parse_response('{"flag": "yes"}')
    assert result == {'flag': 'yes'}


def test_parse_response_strips_markdown_fences():
    result = _parse_response('```json\n{"flag": "no"}\n```')
    assert result == {'flag': 'no'}


# =============================================================================
# _call_haiku_title
# =============================================================================

def _make_title_mock(flag='yes', confidence=4, scope='CA', reason='9. Cigna vs UC Health'):
    client = MagicMock()
    client.messages.create.return_value.content = [
        MagicMock(text=json.dumps({
            'flag': flag, 'confidence': confidence, 'scope': scope, 'reason': reason,
        }))
    ]
    return client


def test_call_haiku_title_returns_expected_fields():
    client = _make_title_mock(flag='yes', confidence=5, scope='CA', reason='9. Cigna vs UC Health')
    article = {'id': 1, 'title': 'Cigna exits CA', 'body_text': ''}
    flag, confidence, scope, reason = _call_haiku_title(client, article)
    assert flag == 'yes'
    assert confidence == 5
    assert scope == 'CA'
    assert '9' in reason


def test_call_haiku_title_returns_no():
    client = _make_title_mock(flag='no', confidence=5, scope='', reason='')
    article = {'id': 2, 'title': 'Q2 earnings beat', 'body_text': ''}
    flag, _, _, _ = _call_haiku_title(client, article)
    assert flag == 'no'


def test_call_haiku_title_normalises_unknown_flag():
    client = MagicMock()
    client.messages.create.return_value.content = [
        MagicMock(text=json.dumps({'flag': 'maybe', 'confidence': 3, 'scope': '', 'reason': ''}))
    ]
    article = {'id': 3, 'title': 'Something', 'body_text': ''}
    flag, _, _, _ = _call_haiku_title(client, article)
    assert flag == 'uncertain'


def test_call_haiku_title_returns_uncertain_on_api_error():
    client = MagicMock()
    client.messages.create.side_effect = Exception('timeout')
    article = {'id': 4, 'title': 'Something', 'body_text': ''}
    flag, confidence, scope, reason = _call_haiku_title(client, article)
    assert flag == 'uncertain'
    assert confidence == 3


# =============================================================================
# _call_haiku_article
# =============================================================================

def _make_article_mock(flag='yes', confidence=4, summary='A deal.', scope='national', reason='1. ACA'):
    client = MagicMock()
    client.messages.create.return_value.content = [
        MagicMock(text=json.dumps({
            'flag': flag, 'confidence': confidence, 'summary': summary,
            'scope': scope, 'reason': reason,
        }))
    ]
    return client


def test_call_haiku_article_returns_all_fields():
    client = _make_article_mock(flag='yes', confidence=4, summary='Big deal.', scope='CA', reason='4. Merger')
    article = {'id': 1, 'title': 'Merger', 'body_text': 'Details.'}
    flag, confidence, summary, scope, reason = _call_haiku_article(client, article)
    assert flag == 'yes'
    assert confidence == 4
    assert summary == 'Big deal.'
    assert scope == 'CA'
    assert '4' in reason


def test_call_haiku_article_truncates_body_to_2000_chars():
    client = _make_article_mock()
    article = {'id': 2, 'title': 'Title', 'body_text': 'x' * 5000}
    _call_haiku_article(client, article)
    user_content = client.messages.create.call_args.kwargs['messages'][0]['content']
    assert 'x' * 2001 not in user_content


def test_call_haiku_article_returns_uncertain_on_api_error():
    client = MagicMock()
    client.messages.create.side_effect = Exception('timeout')
    article = {'id': 3, 'title': 'Something', 'body_text': 'Text.'}
    flag, confidence, summary, scope, reason = _call_haiku_article(client, article)
    assert flag == 'uncertain'
    assert summary == ''


# =============================================================================
# _insert_triage_result
# =============================================================================

def test_insert_triage_result_writes_all_fields():
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    _insert_triage_result(
        conn, article_id=10, run_id=5,
        title_flag='yes', title_confidence=4, title_scope='CA', title_reason='9. Cigna',
        article_flag='yes', article_confidence=4, article_summary='A summary.',
        article_scope='CA', article_reason='9. Cigna',
    )
    sql, params = cursor.execute.call_args.args
    assert 'triage_results' in sql
    assert params == (10, 5, 'yes', 4, 'CA', '9. Cigna', 'yes', 4, 'A summary.', 'CA', '9. Cigna', MODEL)
    conn.commit.assert_called_once()


def test_insert_triage_result_accepts_null_article_fields():
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    _insert_triage_result(
        conn, article_id=10, run_id=5,
        title_flag='no', title_confidence=5, title_scope='', title_reason='',
        article_flag=None, article_confidence=None, article_summary=None,
        article_scope=None, article_reason=None,
    )
    _, params = cursor.execute.call_args.args
    assert params[6] is None   # article_flag
    assert params[8] is None   # article_summary


# =============================================================================
# run_triage (integration-style with mocks)
# =============================================================================

def test_run_triage_returns_empty_for_no_articles():
    with patch('agent.triage.get_connection'), patch('agent.triage.release_connection'):
        result = run_triage([], run_id=1)
    assert result == []


def test_run_triage_saves_row_for_title_dropped_article():
    article = {'id': 1, 'title': 'Earnings report', 'body_text': 'Numbers.'}

    with patch('agent.triage.get_connection'), \
         patch('agent.triage.release_connection'), \
         patch('agent.triage._fetch_article', return_value=article), \
         patch('agent.triage._call_haiku_title', return_value=('no', 5, '', '')) as m_title, \
         patch('agent.triage._call_haiku_article') as m_article, \
         patch('agent.triage._insert_triage_result') as m_insert, \
         patch('agent.triage.anthropic.Anthropic'), \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
        result = run_triage([1], run_id=1)

    assert result == []
    m_article.assert_not_called()
    m_insert.assert_called_once()
    # article_flag is the 8th positional arg (conn, article_id, run_id, title_*, article_flag, ...)
    assert m_insert.call_args.args[7] is None


def test_run_triage_saves_both_stages_when_title_passes():
    article = {'id': 1, 'title': 'Cigna exits CA', 'body_text': 'Details.'}

    with patch('agent.triage.get_connection'), \
         patch('agent.triage.release_connection'), \
         patch('agent.triage._fetch_article', return_value=article), \
         patch('agent.triage._call_haiku_title', return_value=('yes', 5, 'CA', '9. Cigna')), \
         patch('agent.triage._call_haiku_article', return_value=('yes', 5, 'Big deal.', 'CA', '9. Cigna')), \
         patch('agent.triage._insert_triage_result') as m_insert, \
         patch('agent.triage.anthropic.Anthropic'), \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
        result = run_triage([1], run_id=99)

    assert result == [1]
    m_insert.assert_called_once()


def test_run_triage_returns_flagged_ids_only():
    articles = [
        {'id': 1, 'title': 'Big deal', 'body_text': 'Details.'},
        {'id': 2, 'title': 'Earnings report', 'body_text': 'Numbers.'},
    ]

    with patch('agent.triage.get_connection'), \
         patch('agent.triage.release_connection'), \
         patch('agent.triage._fetch_article', side_effect=articles), \
         patch('agent.triage._call_haiku_title', side_effect=[('yes', 4, 'CA', '4.'), ('no', 5, '', '')]), \
         patch('agent.triage._call_haiku_article', return_value=('yes', 4, 'A deal.', 'CA', '4.')), \
         patch('agent.triage._insert_triage_result'), \
         patch('agent.triage.anthropic.Anthropic'), \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
        result = run_triage([1, 2], run_id=99)

    assert result == [1]


def test_run_triage_includes_uncertain_in_flagged():
    article = {'id': 3, 'title': 'Ambiguous', 'body_text': 'Mixed.'}

    with patch('agent.triage.get_connection'), \
         patch('agent.triage.release_connection'), \
         patch('agent.triage._fetch_article', return_value=article), \
         patch('agent.triage._call_haiku_title', return_value=('uncertain', 3, 'national', '1.')), \
         patch('agent.triage._call_haiku_article', return_value=('uncertain', 3, 'Not sure.', 'national', '1.')), \
         patch('agent.triage._insert_triage_result'), \
         patch('agent.triage.anthropic.Anthropic'), \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
        result = run_triage([3], run_id=1)

    assert result == [3]
