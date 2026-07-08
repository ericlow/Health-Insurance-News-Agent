from unittest.mock import MagicMock, patch, call
from agent.triage import run_triage, _fetch_article, _call_haiku, _insert_triage_result, MODEL


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
# _call_haiku
# =============================================================================

def _make_client_mock(flag: str, summary: str) -> MagicMock:
    import json
    client = MagicMock()
    client.messages.create.return_value.content = [
        MagicMock(text=json.dumps({'flag': flag, 'summary': summary}))
    ]
    return client


def test_call_haiku_returns_yes_flag():
    client = _make_client_mock('yes', 'Some summary.')
    article = {'id': 1, 'title': 'Deal announced', 'body_text': 'Details here.'}
    flag, summary = _call_haiku(client, article)
    assert flag == 'yes'
    assert summary == 'Some summary.'


def test_call_haiku_returns_no_flag():
    client = _make_client_mock('no', 'Not relevant.')
    article = {'id': 2, 'title': 'Clinical trial results', 'body_text': 'Medical data.'}
    flag, summary = _call_haiku(client, article)
    assert flag == 'no'


def test_call_haiku_returns_uncertain_flag():
    client = _make_client_mock('uncertain', 'Ambiguous signals.')
    article = {'id': 3, 'title': 'Insurer signals intent', 'body_text': 'Vague language.'}
    flag, summary = _call_haiku(client, article)
    assert flag == 'uncertain'


def test_call_haiku_normalises_unknown_flag_to_uncertain():
    import json
    client = MagicMock()
    client.messages.create.return_value.content = [
        MagicMock(text=json.dumps({'flag': 'maybe', 'summary': 'Odd response.'}))
    ]
    article = {'id': 4, 'title': 'Something', 'body_text': 'Text.'}
    flag, _ = _call_haiku(client, article)
    assert flag == 'uncertain'


def test_call_haiku_returns_uncertain_on_api_error():
    client = MagicMock()
    client.messages.create.side_effect = Exception('API timeout')
    article = {'id': 5, 'title': 'Something', 'body_text': 'Text.'}
    flag, summary = _call_haiku(client, article)
    assert flag == 'uncertain'
    assert summary == ''


def test_call_haiku_strips_markdown_fences():
    client = MagicMock()
    client.messages.create.return_value.content = [
        MagicMock(text='```json\n{"flag": "yes", "summary": "A deal."}\n```')
    ]
    article = {'id': 6, 'title': 'Deal', 'body_text': 'Details.'}
    flag, summary = _call_haiku(client, article)
    assert flag == 'yes'
    assert summary == 'A deal.'


def test_call_haiku_truncates_body_to_2000_chars():
    client = _make_client_mock('no', '')
    long_body = 'x' * 5000
    article = {'id': 7, 'title': 'Title', 'body_text': long_body}
    _call_haiku(client, article)
    call_args = client.messages.create.call_args
    user_content = call_args.kwargs['messages'][0]['content']
    assert 'x' * 2001 not in user_content


# =============================================================================
# _insert_triage_result
# =============================================================================

def test_insert_triage_result_writes_correct_fields():
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    _insert_triage_result(conn, article_id=10, run_id=5, flag='yes', summary='A summary.')
    sql, params = cursor.execute.call_args.args
    assert 'triage_results' in sql
    assert params == (10, 5, 'yes', 'A summary.', MODEL)
    conn.commit.assert_called_once()


# =============================================================================
# run_triage (integration-style with mocks)
# =============================================================================

def test_run_triage_returns_empty_for_no_articles():
    with patch('agent.triage.get_connection'), patch('agent.triage.release_connection'):
        result = run_triage([], run_id=1)
    assert result == []


def test_run_triage_returns_flagged_ids_only():
    article_yes = {'id': 1, 'title': 'Big deal', 'body_text': 'Details.'}
    article_no  = {'id': 2, 'title': 'Earnings report', 'body_text': 'Numbers.'}

    with patch('agent.triage.get_connection') as mock_conn_fn, \
         patch('agent.triage.release_connection'), \
         patch('agent.triage._fetch_article', side_effect=[article_yes, article_no]), \
         patch('agent.triage._call_haiku', side_effect=[('yes', 'Summary A.'), ('no', 'Summary B.')]), \
         patch('agent.triage._insert_triage_result') as mock_insert, \
         patch('agent.triage.anthropic.Anthropic'), \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):

        result = run_triage([1, 2], run_id=99)

    assert result == [1]
    assert mock_insert.call_count == 2


def test_run_triage_includes_uncertain_in_flagged():
    article = {'id': 3, 'title': 'Ambiguous', 'body_text': 'Mixed signals.'}

    with patch('agent.triage.get_connection'), \
         patch('agent.triage.release_connection'), \
         patch('agent.triage._fetch_article', return_value=article), \
         patch('agent.triage._call_haiku', return_value=('uncertain', 'Not sure.')), \
         patch('agent.triage._insert_triage_result'), \
         patch('agent.triage.anthropic.Anthropic'), \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):

        result = run_triage([3], run_id=1)

    assert result == [3]
