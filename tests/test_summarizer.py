from unittest.mock import MagicMock, patch
from agent.summarizer import run_summarizer, _fetch_article, _fetch_triage_result_id, _call_sonnet, _insert_briefing, MODEL


# =============================================================================
# _fetch_article
# =============================================================================

def test_fetch_article_returns_dict():
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (
        1, 'Deal Title', 'Full body text.'
    )
    result = _fetch_article(conn, 1)
    assert result == {'id': 1, 'title': 'Deal Title', 'body_text': 'Full body text.'}


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
# _fetch_triage_result_id
# =============================================================================

def test_fetch_triage_result_id_returns_id():
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (42,)
    assert _fetch_triage_result_id(conn, 1) == 42


def test_fetch_triage_result_id_returns_none_when_missing():
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = None
    assert _fetch_triage_result_id(conn, 1) is None


# =============================================================================
# _call_sonnet
# =============================================================================

def _make_client_mock(payload: dict) -> MagicMock:
    import json
    client = MagicMock()
    client.messages.create.return_value.content = [
        MagicMock(text=json.dumps(payload))
    ]
    return client


def test_call_sonnet_returns_all_four_fields():
    payload = {
        'what_happened': 'Northwell and Fidelis are terminating their contract.',
        'who': 'Northwell Health (provider) · Fidelis Care / Centene (insurer)',
        'impact': '240,000 members at risk.',
        'why_it_matters': 'Sets a precedent for Centene reimbursement posture.',
    }
    client = _make_client_mock(payload)
    article = {'id': 1, 'title': 'Deal', 'body_text': 'Full text here.'}
    result = _call_sonnet(client, article)
    assert result['what_happened'] == payload['what_happened']
    assert result['who'] == payload['who']
    assert result['impact'] == payload['impact']
    assert result['why_it_matters'] == payload['why_it_matters']


def test_call_sonnet_fills_not_stated_for_missing_fields():
    client = _make_client_mock({'what_happened': 'Something happened.'})
    article = {'id': 2, 'title': 'Title', 'body_text': 'Text.'}
    result = _call_sonnet(client, article)
    assert result['who'] == 'Not stated'
    assert result['impact'] == 'Not stated'
    assert result['why_it_matters'] == 'Not stated'


def test_call_sonnet_returns_not_stated_on_api_error():
    client = MagicMock()
    client.messages.create.side_effect = Exception('API error')
    article = {'id': 3, 'title': 'Title', 'body_text': 'Text.'}
    result = _call_sonnet(client, article)
    assert all(v == 'Not stated' for v in result.values())


def test_call_sonnet_strips_markdown_fences():
    client = MagicMock()
    client.messages.create.return_value.content = [
        MagicMock(text='```json\n{"what_happened": "A deal.", "who": "X", "impact": "Y", "why_it_matters": "Z"}\n```')
    ]
    article = {'id': 4, 'title': 'Title', 'body_text': 'Text.'}
    result = _call_sonnet(client, article)
    assert result['what_happened'] == 'A deal.'


# =============================================================================
# _insert_briefing
# =============================================================================

def test_insert_briefing_returns_id():
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (7,)
    brief = {
        'what_happened': 'A.',
        'who': 'B.',
        'impact': 'C.',
        'why_it_matters': 'D.',
    }
    result = _insert_briefing(conn, article_id=1, triage_result_id=2, run_id=3, brief=brief)
    assert result == 7
    conn.commit.assert_called_once()


def test_insert_briefing_passes_correct_fields():
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = (1,)
    brief = {'what_happened': 'W', 'who': 'X', 'impact': 'Y', 'why_it_matters': 'Z'}
    _insert_briefing(conn, article_id=10, triage_result_id=20, run_id=30, brief=brief)
    sql, params = cursor.execute.call_args.args
    assert 'briefings' in sql
    assert params == (10, 20, 30, 'W', 'X', 'Y', 'Z', MODEL)


# =============================================================================
# run_summarizer (integration-style with mocks)
# =============================================================================

def test_run_summarizer_returns_empty_for_no_articles():
    with patch('agent.summarizer.get_connection'), patch('agent.summarizer.release_connection'):
        result = run_summarizer([], run_id=1)
    assert result == []


def test_run_summarizer_returns_briefing_ids():
    article = {'id': 1, 'title': 'Deal', 'body_text': 'Text.'}
    brief = {'what_happened': 'W', 'who': 'X', 'impact': 'Y', 'why_it_matters': 'Z'}

    with patch('agent.summarizer.get_connection'), \
         patch('agent.summarizer.release_connection'), \
         patch('agent.summarizer._fetch_article', return_value=article), \
         patch('agent.summarizer._fetch_triage_result_id', return_value=5), \
         patch('agent.summarizer._call_sonnet', return_value=brief), \
         patch('agent.summarizer._insert_briefing', return_value=99), \
         patch('agent.summarizer.anthropic.Anthropic'), \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):

        result = run_summarizer([1], run_id=10)

    assert result == [99]


def test_run_summarizer_skips_article_with_no_triage_result():
    article = {'id': 2, 'title': 'Something', 'body_text': 'Text.'}

    with patch('agent.summarizer.get_connection'), \
         patch('agent.summarizer.release_connection'), \
         patch('agent.summarizer._fetch_article', return_value=article), \
         patch('agent.summarizer._fetch_triage_result_id', return_value=None), \
         patch('agent.summarizer._insert_briefing') as mock_insert, \
         patch('agent.summarizer.anthropic.Anthropic'), \
         patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):

        result = run_summarizer([2], run_id=1)

    assert result == []
    mock_insert.assert_not_called()
