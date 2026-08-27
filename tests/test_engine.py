"""Tests for the AnalystAgent engine modules (AGE-95)."""
import json
import os

import pytest
import responses as resp_mock

from agent.analyst import discord as disc
from agent.analyst import persistence
from agent.analyst.tools import fetch_url


# --- discord.split ---

def test_split_short():
    assert disc.split("hello") == ["hello"]


def test_split_exact_limit():
    text = "x" * 2000
    assert disc.split(text) == [text]


def test_split_over_limit():
    text = "a" * 2500
    chunks = disc.split(text)
    assert len(chunks) == 2
    assert chunks[0] == "a" * 2000
    assert chunks[1] == "a" * 500
    assert all(len(c) <= 2000 for c in chunks)


# --- tools.fetch_url ---

@resp_mock.activate
def test_fetch_url_returns_text():
    resp_mock.add(resp_mock.GET, "https://example.com/article",
                  body="<html><body><p>Hello world</p></body></html>", status=200)

    result = fetch_url("https://example.com/article")

    assert "Hello world" in result
    assert isinstance(result, str)


@resp_mock.activate
def test_fetch_url_on_error_returns_json_error():
    resp_mock.add(resp_mock.GET, "https://example.com/blocked", status=403)
    # no Jina mock → both fetches fail → error JSON

    parsed = json.loads(fetch_url("https://example.com/blocked"))
    assert "error" in parsed


# --- persistence (integration, requires DATABASE_URL_LOCAL) ---

@pytest.fixture
def db(monkeypatch):
    url = os.environ.get("DATABASE_URL_LOCAL")
    if not url:
        pytest.skip("DATABASE_URL_LOCAL not set")
    monkeypatch.setenv("DATABASE_URL", url)
    import psycopg2
    conn = psycopg2.connect(url)
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id SERIAL PRIMARY KEY,
                    messages JSONB NOT NULL DEFAULT '[]',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
    conn.close()
    yield


def test_conversation_round_trip(db):
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    messages = [{"role": "user", "content": "What is the impact on Anthem?"}]
    conv_id = persistence.create_conversation(conn, messages)
    assert isinstance(conv_id, int)

    loaded = persistence.load_conversation(conn, conv_id)
    assert loaded == messages

    messages.append({"role": "assistant", "content": [{"type": "text", "text": "Big impact."}]})
    persistence.update_conversation(conn, conv_id, messages)

    reloaded = persistence.load_conversation(conn, conv_id)
    assert len(reloaded) == 2
    assert reloaded[1]["role"] == "assistant"

    conn.close()


def test_load_missing_conversation(db):
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    result = persistence.load_conversation(conn, 99999999)
    conn.close()
    assert result is None


# --- engine: _run_loop, _cite, _fact_check ---

from unittest.mock import MagicMock, patch
from agent.analyst.engine import _run_loop, _cite, _fact_check


def _make_resp(text: str, stop_reason: str = "end_turn") -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.stop_reason = stop_reason
    block = MagicMock()
    block.type = "text"
    block.text = text
    block.model_dump.return_value = {"type": "text", "text": text}
    mock_resp.content = [block]
    return mock_resp


def test_run_loop_returns_3_tuple():
    messages = [{"role": "user", "content": "test query"}]

    with patch("agent.analyst.engine.anthropic.Anthropic") as mock_anthropic, \
         patch("agent.analyst.engine.post_channel_message", return_value="msg-id-123"):
        mock_anthropic.return_value.messages.create.return_value = _make_resp("analysis text")
        result = _run_loop(messages, "token", "channel-999")

    assert isinstance(result, tuple) and len(result) == 3
    analysis, urls, last_mid = result
    assert isinstance(analysis, str) and "analysis text" in analysis
    assert isinstance(urls, list)
    assert last_mid is None or isinstance(last_mid, str)


def test_cite_adds_sources_footer():
    with patch("agent.analyst.engine.anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = _make_resp("Great analysis (1) here.")
        result = _cite("Great analysis here.", ["https://example.com/source"])

    assert "Sources" in result
    assert "https://example.com/source" in result


def test_fact_check_posts_to_thread_not_channel():
    with patch("agent.analyst.engine.anthropic.Anthropic") as mock_anthropic, \
         patch("agent.analyst.engine.post_channel_message", return_value="msg-456") as mock_post:
        mock_anthropic.return_value.messages.create.return_value = _make_resp("Corrected analysis.")
        corrected, urls = _fact_check("draft", ["https://example.com"], "thread-123", "channel-456")

    channel_calls = [c for c in mock_post.call_args_list if c.args[0] == "channel-456"]
    assert len(channel_calls) == 0, "fact_check must not post directly to channel"
    assert isinstance(corrected, str)
    assert isinstance(urls, list)
