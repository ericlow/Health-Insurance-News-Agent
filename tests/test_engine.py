"""Tests for the AnalystAgent engine (Lambda B) — AGE-95.

DB tests require DATABASE_URL_LOCAL (local Docker Postgres). They are skipped
automatically when the env var is absent.
"""
import json
import os

import pytest
import responses as resp_mock

from agent.analyst import engine


# --- _split ---

def test_split_short():
    assert engine._split("hello") == ["hello"]


def test_split_exact_limit():
    text = "x" * 2000
    assert engine._split(text) == [text]


def test_split_over_limit():
    text = "a" * 2500
    chunks = engine._split(text)
    assert len(chunks) == 2
    assert chunks[0] == "a" * 2000
    assert chunks[1] == "a" * 500
    assert all(len(c) <= 2000 for c in chunks)


# --- _fetch_url ---

@resp_mock.activate
def test_fetch_url_returns_text():
    resp_mock.add(resp_mock.GET, "https://example.com/article",
                  body="<html><body><p>Hello world</p></body></html>", status=200)

    result = engine._fetch_url("https://example.com/article")

    assert "Hello world" in result
    assert isinstance(result, str)


@resp_mock.activate
def test_fetch_url_on_error_returns_json_error():
    resp_mock.add(resp_mock.GET, "https://example.com/blocked", status=403)

    result = engine._fetch_url("https://example.com/blocked")

    parsed = json.loads(result)
    assert "error" in parsed


# --- DB round-trip (integration, requires DATABASE_URL_LOCAL) ---

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
                CREATE TABLE IF NOT EXISTS a2_conversations (
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
    conv_id = engine._create_conversation(conn, messages)
    assert isinstance(conv_id, int)

    loaded = engine._load_conversation(conn, conv_id)
    assert loaded == messages

    messages.append({"role": "assistant", "content": [{"type": "text", "text": "Big impact."}]})
    engine._update_conversation(conn, conv_id, messages)

    reloaded = engine._load_conversation(conn, conv_id)
    assert len(reloaded) == 2
    assert reloaded[1]["role"] == "assistant"

    conn.close()


def test_load_missing_conversation(db):
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    result = engine._load_conversation(conn, 99999999)
    conn.close()
    assert result is None
