import json
import os
import pytest
import responses as responses_lib
from unittest.mock import MagicMock, call, patch

from agent.discord import (
    send_alerts, send_no_alerts, post_health_check,
    _format_briefing, _format_no_article, DIVIDER,
)

_HC_ARTICLES = [
    ("Cigna exits Humana network", "https://beckers.com/a", "yes"),
    ("UHC revenue misses", "https://beckers.com/b", "uncertain"),
    ("FDA drug approval", "https://beckers.com/c", "no"),
]

def _make_no_row(triage_result_id=10, title="Rejected Article", url="https://example.com/no",
                 article_flag='no', title_reason="A. earnings reports",
                 title_confidence=4, title_scope="CA",
                 article_reason="A. earnings reports with no relationship change",
                 article_confidence=4, article_scope="national", article_summary="Anthem posted earnings."):
    return (triage_result_id, title, url, article_flag,
            title_reason, title_confidence, title_scope,
            article_reason, article_confidence, article_scope, article_summary)

HEALTH_CHECK_URL = "https://discord.com/api/webhooks/test/health-token"
MAIN_URL = "https://discord.com/api/webhooks/test/main"
UNCERTAIN_URL = "https://discord.com/api/webhooks/test/uncertain"
NO_URL = "https://discord.com/api/webhooks/test/no"

ENV = {
    "DISCORD_WEBHOOK_URL": MAIN_URL,
    "DISCORD_UNCERTAIN_WEBHOOK_URL": UNCERTAIN_URL,
    "DISCORD_NO_WEBHOOK_URL": NO_URL,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_briefing(id=1, title="Test Title", url="https://example.com/article"):
    return (id, "Something happened.", "Entity A (provider) · Entity B (insurer)",
            "100,000 members at risk.", "Sets a precedent.", title, url)


def _make_conn(yes_rows=None, uncertain_rows=None):
    """Build a mock connection where fetchall alternates yes/uncertain results."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchall.side_effect = [yes_rows or [], uncertain_rows or []]
    mock_conn.cursor.return_value = mock_cur
    return mock_conn, mock_cur


def _make_no_conn(rows=None):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = rows or []
    mock_conn.cursor.return_value = mock_cur
    return mock_conn, mock_cur


# ---------------------------------------------------------------------------
# _format_briefing
# ---------------------------------------------------------------------------

def test_format_briefing_contains_all_fields():
    row = _make_briefing(title="Northwell Fidelis Split", url="https://example.com/a")
    msg = _format_briefing(row)
    assert "📌 Northwell Fidelis Split" in msg
    assert "What happened: Something happened." in msg
    assert "Who's involved: Entity A (provider) · Entity B (insurer)" in msg
    assert "Members/revenue at stake: 100,000 members at risk." in msg
    assert "Why it matters: Sets a precedent." in msg
    assert "🔗 https://example.com/a" in msg


def test_format_briefing_wrapped_in_dividers():
    msg = _format_briefing(_make_briefing())
    assert msg.count(DIVIDER) == 2


# ---------------------------------------------------------------------------
# _format_no_article
# ---------------------------------------------------------------------------

def test_format_no_article_article_rejected_includes_label_reason_summary_and_meta():
    msg = _format_no_article(
        "Anthem Q3 Earnings", "https://example.com/a", 'no',
        "A. earnings", 3, "CA",
        "A. earnings reports with no relationship change", 4, "national",
        "Anthem reported Q3 earnings. Cost controls drove the beat.",
    )
    assert "[Anthem Q3 Earnings](https://example.com/a)" in msg
    assert "❌ Article rejected" in msg
    assert "Reason: A. earnings reports with no relationship change" in msg
    assert "Summary: Anthem reported Q3 earnings." in msg
    assert "Confidence: 4" in msg
    assert "Scope: national" in msg


def test_format_no_article_title_rejected_shows_label_and_no_summary():
    msg = _format_no_article(
        "Anthem Q3 Earnings", "https://example.com/a", None,
        "A. earnings reports", 3, "CA",
        None, None, None, None,
    )
    assert "[Anthem Q3 Earnings](https://example.com/a)" in msg
    assert "❌ Title rejected" in msg
    assert "Reason: A. earnings reports" in msg
    assert "Summary" not in msg
    assert "Confidence: 3" in msg
    assert "Scope: CA" in msg


# ---------------------------------------------------------------------------
# send_alerts — no unsent briefings → exits silently
# ---------------------------------------------------------------------------

def test_send_alerts_returns_zero_when_no_briefings():
    mock_conn, _ = _make_conn(yes_rows=[], uncertain_rows=[])

    with patch("agent.discord.get_connection", return_value=mock_conn), \
         patch("agent.discord.release_connection"), \
         patch.dict(os.environ, ENV):
        result = send_alerts(run_id=99)

    assert result == 0


# ---------------------------------------------------------------------------
# send_alerts — yes briefings go to main channel
# ---------------------------------------------------------------------------

@responses_lib.activate
def test_send_alerts_yes_goes_to_main_channel():
    responses_lib.add(responses_lib.POST, MAIN_URL, status=204)

    mock_conn, _ = _make_conn(yes_rows=[_make_briefing(id=7)], uncertain_rows=[])

    with patch("agent.discord.get_connection", return_value=mock_conn), \
         patch("agent.discord.release_connection"), \
         patch("agent.discord.time.sleep"), \
         patch.dict(os.environ, ENV):
        result = send_alerts(run_id=1)

    assert result == 1
    assert len(responses_lib.calls) == 1
    assert responses_lib.calls[0].request.url == MAIN_URL


# ---------------------------------------------------------------------------
# send_alerts — uncertain briefings go to uncertain channel
# ---------------------------------------------------------------------------

@responses_lib.activate
def test_send_alerts_uncertain_goes_to_uncertain_channel():
    responses_lib.add(responses_lib.POST, UNCERTAIN_URL, status=204)

    mock_conn, _ = _make_conn(yes_rows=[], uncertain_rows=[_make_briefing(id=8)])

    with patch("agent.discord.get_connection", return_value=mock_conn), \
         patch("agent.discord.release_connection"), \
         patch("agent.discord.time.sleep"), \
         patch.dict(os.environ, ENV):
        result = send_alerts(run_id=1)

    assert result == 1
    assert len(responses_lib.calls) == 1
    assert responses_lib.calls[0].request.url == UNCERTAIN_URL


@responses_lib.activate
def test_send_alerts_uncertain_not_sent_to_main_channel():
    responses_lib.add(responses_lib.POST, UNCERTAIN_URL, status=204)

    mock_conn, _ = _make_conn(yes_rows=[], uncertain_rows=[_make_briefing(id=9)])

    with patch("agent.discord.get_connection", return_value=mock_conn), \
         patch("agent.discord.release_connection"), \
         patch("agent.discord.time.sleep"), \
         patch.dict(os.environ, ENV):
        send_alerts(run_id=1)

    posted_urls = [c.request.url for c in responses_lib.calls]
    assert MAIN_URL not in posted_urls


# ---------------------------------------------------------------------------
# send_alerts — both verdicts in same run
# ---------------------------------------------------------------------------

@responses_lib.activate
def test_send_alerts_routes_yes_and_uncertain_to_separate_channels():
    responses_lib.add(responses_lib.POST, MAIN_URL, status=204)
    responses_lib.add(responses_lib.POST, UNCERTAIN_URL, status=204)

    mock_conn, mock_cur = _make_conn(
        yes_rows=[_make_briefing(id=1)],
        uncertain_rows=[_make_briefing(id=2)],
    )

    with patch("agent.discord.get_connection", return_value=mock_conn), \
         patch("agent.discord.release_connection"), \
         patch("agent.discord.time.sleep"), \
         patch.dict(os.environ, ENV):
        result = send_alerts()

    assert result == 2
    posted_urls = [c.request.url for c in responses_lib.calls]
    assert MAIN_URL in posted_urls
    assert UNCERTAIN_URL in posted_urls


@responses_lib.activate
def test_send_alerts_marks_both_verdicts_sent():
    responses_lib.add(responses_lib.POST, MAIN_URL, status=204)
    responses_lib.add(responses_lib.POST, UNCERTAIN_URL, status=204)

    mock_conn, mock_cur = _make_conn(
        yes_rows=[_make_briefing(id=3)],
        uncertain_rows=[_make_briefing(id=4)],
    )

    with patch("agent.discord.get_connection", return_value=mock_conn), \
         patch("agent.discord.release_connection"), \
         patch("agent.discord.time.sleep"), \
         patch.dict(os.environ, ENV):
        send_alerts()

    # Each article is marked sent immediately after posting — two separate UPDATEs
    update_calls = [c for c in mock_cur.execute.call_args_list if "UPDATE briefings" in str(c)]
    all_sent_ids = [id for c in update_calls for id in c.args[1][1]]
    assert 3 in all_sent_ids
    assert 4 in all_sent_ids


# ---------------------------------------------------------------------------
# send_alerts — webhook failure raises, does NOT mark sent
# ---------------------------------------------------------------------------

@responses_lib.activate
def test_send_alerts_does_not_mark_sent_on_webhook_error():
    responses_lib.add(responses_lib.POST, MAIN_URL, status=500)

    mock_conn, _ = _make_conn(yes_rows=[_make_briefing()], uncertain_rows=[])

    with patch("agent.discord.get_connection", return_value=mock_conn), \
         patch("agent.discord.release_connection"), \
         patch.dict(os.environ, ENV):
        with pytest.raises(Exception):
            send_alerts(run_id=1)

    mock_conn.commit.assert_not_called()


# ---------------------------------------------------------------------------
# send_no_alerts — no articles → exits silently
# ---------------------------------------------------------------------------

def test_send_no_alerts_returns_zero_when_nothing():
    mock_conn, _ = _make_no_conn(rows=[])

    with patch("agent.discord.get_connection", return_value=mock_conn), \
         patch("agent.discord.release_connection"), \
         patch.dict(os.environ, ENV):
        result = send_no_alerts(run_id=1)

    assert result == 0


# ---------------------------------------------------------------------------
# send_no_alerts — happy path: LLM fields posted to no channel
# ---------------------------------------------------------------------------

@responses_lib.activate
def test_send_no_alerts_posts_to_no_channel():
    responses_lib.add(responses_lib.POST, NO_URL, status=204)

    mock_conn, _ = _make_no_conn(rows=[_make_no_row()])

    with patch("agent.discord.get_connection", return_value=mock_conn), \
         patch("agent.discord.release_connection"), \
         patch("agent.discord.time.sleep"), \
         patch.dict(os.environ, ENV):
        result = send_no_alerts(run_id=1)

    assert result == 1
    assert responses_lib.calls[0].request.url == NO_URL
    body = responses_lib.calls[0].request.body.decode()
    assert "Rejected Article" in body
    assert "https://example.com/no" in body
    assert "Reason:" in body


@responses_lib.activate
def test_send_no_alerts_marks_triage_results_sent():
    responses_lib.add(responses_lib.POST, NO_URL, status=204)

    mock_conn, mock_cur = _make_no_conn(rows=[_make_no_row(triage_result_id=15)])

    with patch("agent.discord.get_connection", return_value=mock_conn), \
         patch("agent.discord.release_connection"), \
         patch("agent.discord.time.sleep"), \
         patch.dict(os.environ, ENV):
        send_no_alerts()

    update_call = mock_cur.execute.call_args_list[-1]
    assert 15 in update_call.args[1][1]


@responses_lib.activate
def test_send_no_alerts_returns_count():
    responses_lib.add(responses_lib.POST, NO_URL, status=204)
    responses_lib.add(responses_lib.POST, NO_URL, status=204)

    rows = [_make_no_row(triage_result_id=i, title=f"Article {i}") for i in range(1, 3)]
    mock_conn, _ = _make_no_conn(rows=rows)

    with patch("agent.discord.get_connection", return_value=mock_conn), \
         patch("agent.discord.release_connection"), \
         patch("agent.discord.time.sleep"), \
         patch.dict(os.environ, ENV):
        result = send_no_alerts()

    assert result == 2


@responses_lib.activate
def test_send_no_alerts_does_not_mark_sent_on_webhook_error():
    responses_lib.add(responses_lib.POST, NO_URL, status=500)

    mock_conn, mock_cur = _make_no_conn(rows=[_make_no_row(triage_result_id=20)])

    with patch("agent.discord.get_connection", return_value=mock_conn), \
         patch("agent.discord.release_connection"), \
         patch.dict(os.environ, ENV):
        with pytest.raises(Exception):
            send_no_alerts(run_id=1)

    mock_conn.commit.assert_not_called()


# ---------------------------------------------------------------------------
# post_health_check — happy path
# ---------------------------------------------------------------------------

@responses_lib.activate
def test_post_health_check_posts_message():
    responses_lib.add(responses_lib.POST, HEALTH_CHECK_URL, status=204)

    with patch.dict(os.environ, {"DISCORD_HEALTH_CHECK_WEBHOOK_URL": HEALTH_CHECK_URL}):
        post_health_check("Becker's Payer", _HC_ARTICLES)

    assert len(responses_lib.calls) == 1
    body = responses_lib.calls[0].request.body.decode()
    assert "Becker's Payer" in body
    assert "3 new articles" in body


@responses_lib.activate
def test_post_health_check_singular_article():
    responses_lib.add(responses_lib.POST, HEALTH_CHECK_URL, status=204)

    with patch.dict(os.environ, {"DISCORD_HEALTH_CHECK_WEBHOOK_URL": HEALTH_CHECK_URL}):
        post_health_check("KFF Health News", [("Some article", "https://kff.org/a", "yes")])

    body = responses_lib.calls[0].request.body.decode()
    assert "1 new article" in body
    assert "articles" not in body


@responses_lib.activate
def test_post_health_check_zero_articles_still_posts():
    responses_lib.add(responses_lib.POST, HEALTH_CHECK_URL, status=204)

    with patch.dict(os.environ, {"DISCORD_HEALTH_CHECK_WEBHOOK_URL": HEALTH_CHECK_URL}):
        post_health_check("KFF Health News", [])

    assert len(responses_lib.calls) == 1
    assert "0 new articles" in responses_lib.calls[0].request.body.decode()


@responses_lib.activate
def test_post_health_check_zero_articles_has_no_article_lines():
    responses_lib.add(responses_lib.POST, HEALTH_CHECK_URL, status=204)

    with patch.dict(os.environ, {"DISCORD_HEALTH_CHECK_WEBHOOK_URL": HEALTH_CHECK_URL}):
        post_health_check("KFF Health News", [])

    body = responses_lib.calls[0].request.body.decode()
    assert "✅" not in body
    assert "❓" not in body
    assert "❌" not in body


@responses_lib.activate
def test_post_health_check_includes_verdict_emojis_and_links():
    responses_lib.add(responses_lib.POST, HEALTH_CHECK_URL, status=204)

    with patch.dict(os.environ, {"DISCORD_HEALTH_CHECK_WEBHOOK_URL": HEALTH_CHECK_URL}):
        post_health_check("Becker's Payer", _HC_ARTICLES)

    content = json.loads(responses_lib.calls[0].request.body.decode())["content"]
    assert "✅ [Cigna exits Humana network](https://beckers.com/a)" in content
    assert "❓ [UHC revenue misses](https://beckers.com/b)" in content
    assert "❌ [FDA drug approval](https://beckers.com/c)" in content


@responses_lib.activate
def test_post_health_check_message_contains_la_timezone():
    responses_lib.add(responses_lib.POST, HEALTH_CHECK_URL, status=204)

    with patch.dict(os.environ, {"DISCORD_HEALTH_CHECK_WEBHOOK_URL": HEALTH_CHECK_URL}):
        post_health_check("Becker's Payer", _HC_ARTICLES)

    body = responses_lib.calls[0].request.body.decode()
    assert "PST" in body or "PDT" in body


# ---------------------------------------------------------------------------
# post_health_check — retry and failure handling
# ---------------------------------------------------------------------------

@responses_lib.activate
def test_post_health_check_retries_on_server_error():
    responses_lib.add(responses_lib.POST, HEALTH_CHECK_URL, status=500)
    responses_lib.add(responses_lib.POST, HEALTH_CHECK_URL, status=204)

    with patch("agent.discord.time.sleep"), \
         patch.dict(os.environ, {"DISCORD_HEALTH_CHECK_WEBHOOK_URL": HEALTH_CHECK_URL}):
        post_health_check("Becker's Payer", _HC_ARTICLES)

    assert len(responses_lib.calls) == 2


@responses_lib.activate
def test_post_health_check_does_not_raise_after_all_retries_exhausted():
    responses_lib.add(responses_lib.POST, HEALTH_CHECK_URL, status=500)
    responses_lib.add(responses_lib.POST, HEALTH_CHECK_URL, status=500)
    responses_lib.add(responses_lib.POST, HEALTH_CHECK_URL, status=500)

    with patch("agent.discord.time.sleep"), \
         patch.dict(os.environ, {"DISCORD_HEALTH_CHECK_WEBHOOK_URL": HEALTH_CHECK_URL}):
        post_health_check("Becker's Payer", _HC_ARTICLES)  # must not raise

    assert len(responses_lib.calls) == 3


def test_post_health_check_skips_when_env_var_not_set():
    env = {k: v for k, v in os.environ.items() if k != "DISCORD_HEALTH_CHECK_WEBHOOK_URL"}
    with patch.dict(os.environ, env, clear=True):
        post_health_check("Becker's Payer", _HC_ARTICLES)  # must not raise
