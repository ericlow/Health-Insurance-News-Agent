import os
import pytest
import responses as responses_lib
from unittest.mock import MagicMock, patch

from agent.discord import send_alerts, post_health_check, _format_message, DIVIDER

HEALTH_CHECK_URL = "https://discord.com/api/webhooks/test/health-token"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_briefing(id=1, title="Test Title", url="https://example.com/article"):
    return (id, "Something happened.", "Entity A (provider) · Entity B (insurer)",
            "100,000 members at risk.", "Sets a precedent.", title, url)


# ---------------------------------------------------------------------------
# _format_message
# ---------------------------------------------------------------------------

def test_format_message_single_alert_label():
    msg = _format_message([_make_briefing()])
    assert "1 new alert\n" in msg
    assert "alerts" not in msg.split("1 new alert")[0]


def test_format_message_plural_label():
    msg = _format_message([_make_briefing(1), _make_briefing(2)])
    assert "2 new alerts" in msg


def test_format_message_contains_all_fields():
    row = _make_briefing(title="Northwell Fidelis Split", url="https://example.com/a")
    msg = _format_message([row])
    assert "📌 Northwell Fidelis Split" in msg
    assert "What happened: Something happened." in msg
    assert "Who's involved: Entity A (provider) · Entity B (insurer)" in msg
    assert "Members/revenue at stake: 100,000 members at risk." in msg
    assert "Why it matters: Sets a precedent." in msg
    assert "🔗 https://example.com/a" in msg


def test_format_message_dividers_wrap_each_briefing():
    msg = _format_message([_make_briefing(1), _make_briefing(2)])
    assert msg.count(DIVIDER) == 3  # one between header and first, between items, and final


# ---------------------------------------------------------------------------
# send_alerts — no unsent briefings → exits silently
# ---------------------------------------------------------------------------

def test_send_alerts_returns_zero_when_no_briefings():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = []
    mock_conn.cursor.return_value = mock_cur

    with patch("agent.discord.get_connection", return_value=mock_conn), \
         patch("agent.discord.release_connection"):
        result = send_alerts(run_id=99)

    assert result == 0


# ---------------------------------------------------------------------------
# send_alerts — happy path: posts webhook, marks delivered
# ---------------------------------------------------------------------------

@responses_lib.activate
def test_send_alerts_posts_webhook_and_marks_sent():
    webhook_url = "https://discord.com/api/webhooks/test/token"
    responses_lib.add(responses_lib.POST, webhook_url, status=204)

    briefing = _make_briefing(id=7)
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = [briefing]
    mock_conn.cursor.return_value = mock_cur

    with patch("agent.discord.get_connection", return_value=mock_conn), \
         patch("agent.discord.release_connection"), \
         patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": webhook_url}):
        result = send_alerts(run_id=1)

    assert result == 1
    # Verify the DB update was committed
    mock_conn.commit.assert_called_once()
    # Verify discord_sent_at was written for briefing id 7
    update_call = mock_cur.execute.call_args_list[-1]
    assert 7 in update_call.args[1][1]  # briefing id in the id list


@responses_lib.activate
def test_send_alerts_returns_count_of_sent_briefings():
    webhook_url = "https://discord.com/api/webhooks/test/token"
    responses_lib.add(responses_lib.POST, webhook_url, status=204)

    briefings = [_make_briefing(id=i) for i in range(1, 4)]
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = briefings
    mock_conn.cursor.return_value = mock_cur

    with patch("agent.discord.get_connection", return_value=mock_conn), \
         patch("agent.discord.release_connection"), \
         patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": webhook_url}):
        result = send_alerts()

    assert result == 3


# ---------------------------------------------------------------------------
# send_alerts — webhook failure raises, does NOT mark sent
# ---------------------------------------------------------------------------

@responses_lib.activate
def test_send_alerts_does_not_mark_sent_on_webhook_error():
    webhook_url = "https://discord.com/api/webhooks/test/token"
    responses_lib.add(responses_lib.POST, webhook_url, status=500)

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = [_make_briefing()]
    mock_conn.cursor.return_value = mock_cur

    with patch("agent.discord.get_connection", return_value=mock_conn), \
         patch("agent.discord.release_connection"), \
         patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": webhook_url}):
        with pytest.raises(Exception):
            send_alerts(run_id=1)

    mock_conn.commit.assert_not_called()


# ---------------------------------------------------------------------------
# post_health_check — happy path
# ---------------------------------------------------------------------------

@responses_lib.activate
def test_post_health_check_posts_message():
    responses_lib.add(responses_lib.POST, HEALTH_CHECK_URL, status=204)

    with patch.dict(os.environ, {"DISCORD_HEALTH_CHECK_WEBHOOK_URL": HEALTH_CHECK_URL}):
        post_health_check("Becker's Payer", 3)

    assert len(responses_lib.calls) == 1
    body = responses_lib.calls[0].request.body.decode()
    assert "Becker's Payer" in body
    assert "3 new articles" in body


@responses_lib.activate
def test_post_health_check_singular_article():
    responses_lib.add(responses_lib.POST, HEALTH_CHECK_URL, status=204)

    with patch.dict(os.environ, {"DISCORD_HEALTH_CHECK_WEBHOOK_URL": HEALTH_CHECK_URL}):
        post_health_check("KFF Health News", 1)

    body = responses_lib.calls[0].request.body.decode()
    assert "1 new article" in body
    assert "articles" not in body


@responses_lib.activate
def test_post_health_check_zero_articles_still_posts():
    responses_lib.add(responses_lib.POST, HEALTH_CHECK_URL, status=204)

    with patch.dict(os.environ, {"DISCORD_HEALTH_CHECK_WEBHOOK_URL": HEALTH_CHECK_URL}):
        post_health_check("KFF Health News", 0)

    assert len(responses_lib.calls) == 1
    assert "0 new articles" in responses_lib.calls[0].request.body.decode()


@responses_lib.activate
def test_post_health_check_message_contains_la_timezone():
    responses_lib.add(responses_lib.POST, HEALTH_CHECK_URL, status=204)

    with patch.dict(os.environ, {"DISCORD_HEALTH_CHECK_WEBHOOK_URL": HEALTH_CHECK_URL}):
        post_health_check("Becker's Payer", 2)

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
        post_health_check("Becker's Payer", 3)

    assert len(responses_lib.calls) == 2


@responses_lib.activate
def test_post_health_check_does_not_raise_after_all_retries_exhausted():
    responses_lib.add(responses_lib.POST, HEALTH_CHECK_URL, status=500)
    responses_lib.add(responses_lib.POST, HEALTH_CHECK_URL, status=500)
    responses_lib.add(responses_lib.POST, HEALTH_CHECK_URL, status=500)

    with patch("agent.discord.time.sleep"), \
         patch.dict(os.environ, {"DISCORD_HEALTH_CHECK_WEBHOOK_URL": HEALTH_CHECK_URL}):
        post_health_check("Becker's Payer", 3)  # must not raise

    assert len(responses_lib.calls) == 3


def test_post_health_check_skips_when_env_var_not_set():
    env = {k: v for k, v in os.environ.items() if k != "DISCORD_HEALTH_CHECK_WEBHOOK_URL"}
    with patch.dict(os.environ, env, clear=True):
        post_health_check("Becker's Payer", 3)  # must not raise
