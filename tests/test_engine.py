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
